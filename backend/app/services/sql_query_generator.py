"""SQL Query Generator with Guardrails and Self-Checking."""
import asyncio
import json
import logging
import sqlite3
import re
from typing import Dict, Any, Optional, List
from app.models import AppSettings
from app.database import engine, Session
from app.services.llm import LLMService

logger = logging.getLogger(__name__)

# SQL Generation Backend Options
SQL_BACKEND_OLLAMA = "ollama"
SQL_BACKEND_SQLCODER = "sqlcoder"
SQL_BACKEND_CUSTOM = "custom"  # User's fine-tuned sqlite-expert model
DEFAULT_SQL_BACKEND = SQL_BACKEND_OLLAMA  # Can be changed to custom/sqlcoder once tested

# Custom Model Configuration
CUSTOM_MODEL_NAME = "eeezeecee/sqlite-expert-v1"  # User's fine-tuned model
CUSTOM_MODEL_USE_QUANTIZATION = True  # 8-bit quantization for GPU

# Forbidden tokens for SQLite validation
FORBIDDEN_TOKENS = [
    "INTERVAL", "NOW()", "DATE_TRUNC", "TIMESTAMPDIFF",
    "CURRENT_TIMESTAMP AT TIME ZONE", "FROM_UNIXTIME",
    "EXTRACT(EPOCH FROM", "::timestamp", "CAST(ts AS TIMESTAMP)",
    "GREATEST(", "LEAST("  # Use MAX()/MIN() instead
]

# Advanced policy patterns for uptime/duration calculations
UPTIME_PATTERNS = {
    "requires_lead": ["uptime", "duration", "time-weighted", "interval"],
    "requires_partition": ["per site", "by site", "each service", "all services"],
    "requires_window_clip": ["last 30 days", "last 7 days", "window", "time range"],
    "requires_seed_state": ["window start", "seed", "initial state", "beginning"]
}

# Database schema for the dashboard
DB_SCHEMA = """
tables:
  - sites(id TEXT PK, display_name TEXT, status_page TEXT, feed_url TEXT, 
          poll_frequency_seconds INTEGER, parser TEXT, is_active INTEGER, 
          console_only INTEGER, use_playwright INTEGER, auth_state_file TEXT,
          downdetector_url TEXT, latest_downdetector_screenshot TEXT,
          downdetector_screenshot_uploaded_at TEXT ISO8601,
          last_notified_at TEXT ISO8601, last_notified_status TEXT,
          created_at TEXT ISO8601, updated_at TEXT ISO8601)
  
  - readings(id INTEGER PK, site_id TEXT FK, status TEXT, summary TEXT,
             source_type TEXT, raw_snapshot JSON, last_changed_at TEXT ISO8601,
             error_message TEXT, downdetector_reports INTEGER,
             downdetector_chart TEXT, created_at TEXT ISO8601)
  
  - advisories(id INTEGER PK, site_id TEXT FK, title TEXT, description TEXT,
               severity TEXT, criticality TEXT, affects_us INTEGER,
               affected_modules JSON, relevance_reason TEXT,
               is_informational INTEGER, source_url TEXT,
               published_at TEXT ISO8601, resolved_at TEXT ISO8601,
               created_at TEXT ISO8601)
  
  - site_modules(id INTEGER PK, site_id TEXT FK, module_name TEXT,
                 enabled INTEGER, created_at TEXT ISO8601)
  
  - chat_messages(id INTEGER PK, role TEXT, content TEXT,
                  context_data JSON, created_at TEXT ISO8601)
  
  - app_settings(id INTEGER PK, smtp_host TEXT, smtp_port INTEGER,
                 smtp_username TEXT, smtp_password TEXT,
                 smtp_from_email TEXT, notification_email TEXT,
                 notification_cooldown_minutes INTEGER,
                 llm_provider TEXT, llm_api_key TEXT, llm_model TEXT,
                 updated_at TEXT ISO8601)

relationships:
  readings.site_id -> sites.id (many-to-one)
  advisories.site_id -> sites.id (many-to-one)
  site_modules.site_id -> sites.id (many-to-one)

common_patterns:
  - status values: 'operational', 'recently_resolved', 'degraded', 'incident', 'maintenance', 'unknown'
  - dates are TEXT in ISO8601 format (use datetime(), julianday(), strftime())
  - booleans are INTEGER (0/1)
  - JSON columns use json_extract() for querying
"""


class SQLQueryGenerator:
    """Generate and validate SQL queries with guardrails."""

    @staticmethod
    async def _generate_with_sqlcoder(task: str, output_contract: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate SQL using SQLCoder model.

        Returns dict with same structure as LLM JSON output:
        {
            "introspect_sql": None,
            "plan": str,
            "sql": str,
            "checks": [],
            "warnings": []
        }
        """
        try:
            from app.services.sqlcoder_service import SQLCoderService

            # Ensure model is loaded
            if not SQLCoderService.is_available():
                logger.info("Loading SQLCoder model...")
                SQLCoderService.load_model(use_quantization=True)

            # Generate SQL using SQLCoder
            sql = SQLCoderService.generate_sql(
                question=task,
                schema=DB_SCHEMA,
                num_beams=4,
                max_new_tokens=500  # Allow longer queries for complex uptime calculations
            )

            # Wrap in expected JSON format
            return {
                "introspect_sql": None,
                "plan": f"Generated SQL query for: {task}",
                "sql": sql,
                "checks": [
                    "SQL generated by SQLCoder-7b-2",
                    "Dialect: SQLite",
                    "Will validate forbidden tokens post-generation"
                ],
                "warnings": []
            }

        except ImportError as e:
            logger.error(f"SQLCoder not available: {e}")
            raise RuntimeError("SQLCoder dependencies not installed. Install transformers and torch.")
        except Exception as e:
            logger.error(f"SQLCoder generation failed: {e}")
            raise

    @staticmethod
    async def _generate_with_ollama(task: str, output_contract: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate SQL using Ollama/LLM with full JSON prompt.

        Returns parsed JSON from LLM response.
        """
        initial_prompt = SQLQueryGenerator._create_initial_prompt(task, output_contract)
        messages = [{"role": "user", "content": initial_prompt}]
        response_text = await LLMService.chat(messages, context=None)

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return json.loads(response_text)

    @staticmethod
    async def _generate_with_custom_model(
        task: str,
        output_contract: Optional[str] = None,
        wrap_with_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Generate SQL using custom fine-tuned sqlite-expert model.

        Args:
            task: Natural language task/question
            output_contract: Expected output columns (optional)
            wrap_with_llm: If True, use LLM to validate/explain the generated SQL

        Returns dict with same structure as other backends:
        {
            "introspect_sql": None,
            "plan": str,
            "sql": str,
            "checks": [],
            "warnings": []
        }
        """
        try:
            from app.services.custom_sql_model import CustomSQLModel

            # Ensure model is loaded
            if not CustomSQLModel.is_available():
                logger.info(f"Loading custom SQL model: {CUSTOM_MODEL_NAME}")
                CustomSQLModel.load_model(
                    model_name=CUSTOM_MODEL_NAME,
                    use_quantization=CUSTOM_MODEL_USE_QUANTIZATION
                )

            # Generate SQL using custom fine-tuned model
            logger.info(f"Calling CustomSQLModel.generate_sql for: {task}")
            sql = await asyncio.get_event_loop().run_in_executor(
                None,
                CustomSQLModel.generate_sql,
                task,  # question
                DB_SCHEMA,  # schema
                500,  # max_new_tokens
                0.1,  # temperature
            )

            # Option 1: Return SQL directly (trust the fine-tuned model)
            if not wrap_with_llm:
                return {
                    "introspect_sql": None,
                    "plan": f"Generated SQL for: {task}",
                    "sql": sql,
                    "checks": [
                        f"SQL generated by custom fine-tuned model ({CUSTOM_MODEL_NAME})",
                        "Model fine-tuned specifically for this SQLite schema",
                        "Dialect: SQLite"
                    ],
                    "warnings": []
                }

            # Option 2: Use LLM to validate/explain the SQL
            logger.info("Wrapping custom SQL with LLM validation...")
            validation_prompt = f"""Review this SQLite query and provide a structured response.

Task: {task}
Generated SQL:
```sql
{sql}
```

Respond with JSON (no markdown, no prose):
{{
    "introspect_sql": null,
    "plan": "Brief explanation of what the query does (1-2 sentences)",
    "sql": "{sql}",  // Keep the SQL as-is unless you find errors
    "checks": ["list", "of", "validations"],
    "warnings": ["list", "of", "potential", "issues"]
}}
"""

            messages = [{"role": "user", "content": validation_prompt}]
            response_text = await LLMService.chat(messages, context=None)

            # Extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Ensure the SQL from custom model is preserved
                result["sql"] = sql
                result["checks"].insert(0, f"Generated by {CUSTOM_MODEL_NAME}")
                return result
            else:
                # Fallback if LLM validation fails
                logger.warning("LLM validation failed, returning raw custom model output")
                return {
                    "introspect_sql": None,
                    "plan": f"Generated SQL for: {task}",
                    "sql": sql,
                    "checks": [f"Generated by {CUSTOM_MODEL_NAME}"],
                    "warnings": ["LLM validation failed"]
                }

        except ImportError as e:
            logger.error(f"Custom SQL model not available: {e}")
            raise RuntimeError("Custom SQL model dependencies not installed. Install transformers and torch.")
        except Exception as e:
            logger.error(f"Custom model generation failed: {e}")
            raise

    @staticmethod
    def _create_initial_prompt(task: str, output_contract: Optional[str] = None) -> str:
        """Create initial prompt with guardrails."""
        # Build output contract section
        contract_section = ""
        if output_contract:
            contract_section = f"\n# OUTPUT CONTRACT (must match exactly)\n{output_contract}\n"

        return f"""You are a senior data engineer writing SQL for **SQLite** only.

HARD CONSTRAINTS:
- DIALECT: SQLite. Do NOT use: NOW, INTERVAL, DATE_TRUNC, TIMESTAMPDIFF, AT TIME ZONE.
- TIME MATH: Use julianday(), datetime(), date(), strftime() as needed.
- WINDOW FUNCTIONS: Use PARTITION BY correctly. Use LEAD/LAG/ROW_NUMBER where appropriate.
- IDENTIFIERS: Use columns and tables exactly as in the provided schema. Do not invent columns.
- OUTPUT FORMAT: Return a single JSON object (no prose) with keys:
  - "introspect_sql": string | null  (SQL to discover schema if needed; keep lightweight)
  - "plan": string  (≤ 3 sentences, what you will compute + key techniques)
  - "sql": string   (final executable SQLite query)
  - "checks": string[] (bulleted self-checks you passed)
  - "warnings": string[] (any assumptions or potential issues)
- SECURITY: No multi-statement SQL. No DDL/DML unless explicitly asked (assume SELECT-only).
- PERFORMANCE: Prefer CTEs + indexes when applicable; avoid N+1 subqueries if a window function works.

FORBIDDEN TOKENS (must not appear in "sql"):
  INTERVAL, NOW(), DATE_TRUNC, TIMESTAMPDIFF, CURRENT_TIMESTAMP AT TIME ZONE,
  FROM_UNIXTIME, EXTRACT(EPOCH FROM ...), CAST(ts AS TIMESTAMP), ::timestamp

ALLOWED FUNCTIONS (examples):
  julianday, datetime, date, time, strftime, coalesce, upper, lower, cast, sum, avg, min, max,
  case when, lead, lag, row_number, count, round

# TASK
{task}

# SCHEMA SNAPSHOT
{DB_SCHEMA}
{contract_section}
# STRATEGY REQUIREMENTS
- If time-interval math is needed:
  * Build a timeline with LEAD(created_at) OVER (PARTITION BY site_id ORDER BY created_at) as next_ts
  * Seed window start using last pre-window reading (or earliest in-window; else UNKNOWN)
  * Close intervals: durations run from each event's created_at to next_ts (or datetime('now') for tail)
  * Clip intervals to [window_start, window_end) using MAX(start, window_start) and MIN(end, window_end)
  * Use julianday(end)-julianday(start) * 86400 for seconds
  * Normalize status: UPPER(status) = 'OPERATIONAL' for case-insensitive comparison
- Treat status='operational' as up; 'recently_resolved' as recently fixed; everything else as down (unless told otherwise).
- If the task references "latest per site": use ROW_NUMBER() PARTITION BY site_id ORDER BY created_at DESC = 1.
- If schema is uncertain: populate "introspect_sql" with a single SELECT/PRAGMA to verify columns before producing the final query.

# UPTIME PERCENTAGE PATTERN (for time-weighted uptime over N days)
When calculating uptime%, you MUST follow these steps EXACTLY:

1. **Seed the state at window start**: Get the last pre-window reading (before datetime('now', '-N days')),
   or use earliest in-window reading, else default to UNKNOWN status. This establishes the initial state.

2. **Close intervals with LEAD**: Use LEAD(created_at) OVER (PARTITION BY site_id ORDER BY created_at) as next_ts.
   Durations run from each event's created_at to the next_ts (or datetime('now') for the tail).

3. **Clip each interval to window bounds**:
   - interval_start = MAX(created_at, datetime('now', '-N days'))
   - interval_end = MIN(COALESCE(next_ts, datetime('now')), datetime('now'))
   - Only include intervals where interval_start < interval_end

4. **Normalize status**: Use UPPER(status) = 'OPERATIONAL' for case-insensitive comparison

5. **Calculate duration**: (julianday(interval_end) - julianday(interval_start)) * 86400 for seconds

6. **Sum operational seconds**: SUM(CASE WHEN UPPER(status) = 'OPERATIONAL' THEN duration ELSE 0 END)

7. **Total window seconds**: (julianday(datetime('now')) - julianday(datetime('now', '-N days'))) * 86400

8. **Return**: (operational_seconds / window_seconds) * 100 as uptime_percent
FORBIDDEN: Do NOT use COUNT(*), GREATEST/LEAST, or direct timestamp subtraction

# SELF-CHECK POLICY (must populate "checks")
- "Dialect is SQLite; no forbidden tokens"
- "Window functions use PARTITION BY correctly"
- "Time math uses julianday/datetime"
- "No invented columns; only those in schema snapshot"
- "Result columns exactly match the Output Contract"
- "Single-statement SELECT; no DDL/DML"

# RETURN FORMAT
Return a single JSON object with keys: introspect_sql, plan, sql, checks, warnings.
No additional text. Start with {{{{ and end with }}}}.
"""

    @staticmethod
    def _create_repair_prompt(
        task: str,
        output_contract: Optional[str],
        previous_output: Dict[str, Any],
        exec_error: Optional[str],
        result_columns: List[str],
        row_count: int,
        policy_failures: List[str]
    ) -> str:
        """Create repair prompt with execution artifacts."""
        forbidden_detected = any(
            token.upper() in previous_output.get("sql", "").upper()
            for token in FORBIDDEN_TOKENS
        )

        # Build output contract section
        contract_section = ""
        if output_contract:
            contract_section = f"\n# OUTPUT CONTRACT (must match exactly)\n{output_contract}\n"

        return f"""You must repair the prior SQLite query to satisfy constraints and pass execution. Keep all hard constraints from the previous instruction. Return only the JSON object described (no prose).

# ORIGINAL REQUEST
{task}

# SCHEMA SNAPSHOT
{DB_SCHEMA}
{contract_section}
# YOUR PREVIOUS OUTPUT (verbatim JSON)
{json.dumps(previous_output, indent=2)}

# EXECUTION ARTIFACTS
exec_error: {json.dumps(exec_error)}
result_columns: {json.dumps(result_columns)}
row_count: {row_count}
forbidden_token_detected: {json.dumps(forbidden_detected)}
policy_failures: {json.dumps(policy_failures)}

# REPAIR RULES
- If exec_error != null: fix the SQL to eliminate the error.
- If result_columns don't match the output contract: rewrite SELECT aliases to match exactly.
- If forbidden_token_detected or policy_failures non-empty: remove violations.
- If column names don't exist: introspect using PRAGMA/table lists in "introspect_sql" (one lightweight query) and adjust.
- Keep a single SELECT statement; no DDL/DML.

# SPECIFIC POLICY FAILURE FIXES
- wrong_dialect_token(GREATEST/LEAST): Replace with MAX(..., ...) or MIN(..., ...)
- wrong_dialect_token(NOW): Replace with datetime('now')
- missing_LEAD: Use LEAD(created_at) OVER (PARTITION BY site_id ORDER BY created_at) to get next timestamp
- no_partition_by_site: Add PARTITION BY site_id to window functions for per-site calculations
- direct_timestamp_subtraction: Use (julianday(end) - julianday(start)) * 86400 for seconds
- row_counts_instead_of_durations: Calculate time intervals using julianday(), not COUNT(*)
- no_seed_or_clip: Seed window start with last pre-window reading; clip intervals with MAX(start, window_start) and MIN(end, window_end)
- no_window_bounds: Define window as datetime('now', '-30 days') to datetime('now')
- case_sensitive_status_check: Use UPPER(status) = 'OPERATIONAL' instead of status = 'operational' for case-insensitive matching

# UPTIME CALCULATION PATTERN (if applicable)
For uptime percentage over N days, follow these steps EXACTLY:

1. **Seed the state at window start**: Get last pre-window reading (before datetime('now', '-N days')),
   or use earliest in-window reading, else default to UNKNOWN status

2. **Close intervals with LEAD**: Use LEAD(created_at) OVER (PARTITION BY site_id ORDER BY created_at) as next_ts
   Durations run from each event's created_at to the next_ts (or datetime('now') for tail)

3. **Clip each interval to [window_start, window_end)**:
   - interval_start = MAX(created_at, datetime('now', '-N days'))
   - interval_end = MIN(COALESCE(next_ts, datetime('now')), datetime('now'))
   - Filter: WHERE interval_start < interval_end

4. **Normalize status**: Use UPPER(status) = 'OPERATIONAL' for case-insensitive matching

5. **Calculate duration**: (julianday(interval_end) - julianday(interval_start)) * 86400 seconds

6. **Sum operational seconds**: SUM(CASE WHEN UPPER(status) = 'OPERATIONAL' THEN duration ELSE 0 END)

7. **Total window seconds**: (julianday(datetime('now')) - julianday(datetime('now', '-N days'))) * 86400

8. **Return percentage**: (operational_seconds / window_seconds) * 100

# RETURN FORMAT
A single JSON object with keys: introspect_sql, plan, sql, checks, warnings.
Start with {{{{ and end with }}}}.
"""

    @staticmethod
    def _validate_policy(sql: str, task: str = "") -> List[str]:
        """Validate SQL against policy rules."""
        failures = []
        sql_upper = sql.upper()
        task_lower = task.lower()

        # Check for forbidden tokens
        for token in FORBIDDEN_TOKENS:
            if token.upper() in sql_upper:
                failures.append(f"wrong_dialect_token({token.replace('(', '').replace(')', '')})")

        # Check for multi-statement
        if ";" in sql.strip()[:-1]:  # Ignore trailing semicolon
            failures.append("multi_statement")

        # Check for DDL/DML
        ddl_dml_keywords = ["CREATE", "DROP", "ALTER", "INSERT", "UPDATE", "DELETE", "TRUNCATE"]
        for keyword in ddl_dml_keywords:
            if re.search(rf'\b{keyword}\b', sql_upper):
                failures.append(f"ddl_dml:{keyword}")

        # Advanced checks for uptime/duration queries
        task_needs_lead = any(pattern in task_lower for pattern in UPTIME_PATTERNS["requires_lead"])
        task_needs_partition = any(pattern in task_lower for pattern in UPTIME_PATTERNS["requires_partition"])
        task_needs_clip = any(pattern in task_lower for pattern in UPTIME_PATTERNS["requires_window_clip"])
        task_needs_seed = any(pattern in task_lower for pattern in UPTIME_PATTERNS["requires_seed_state"])

        # Check for LEAD/LAG window function when calculating durations
        if task_needs_lead and "LEAD(" not in sql_upper and "LAG(" not in sql_upper:
            failures.append("missing_LEAD")

        # Check for PARTITION BY when query involves per-site calculations
        if task_needs_partition and "PARTITION BY" not in sql_upper:
            failures.append("no_partition_by_site")

        # Check for window clipping (datetime('now', '-X days'))
        if task_needs_clip:
            if not re.search(r"datetime\s*\(\s*['\"]now['\"]", sql, re.IGNORECASE):
                failures.append("no_window_bounds")
            # Check for MAX/MIN clipping logic
            if "MAX(" not in sql_upper or "MIN(" not in sql_upper:
                failures.append("no_seed_or_clip")

        # Check for seeding window start
        if task_needs_seed and "ROW_NUMBER" not in sql_upper and "PARTITION BY" not in sql_upper:
            failures.append("no_seed_state")

        # Check for direct timestamp subtraction (should use julianday)
        if re.search(r'-\s*(created_at|last_changed_at|timestamp)', sql, re.IGNORECASE):
            if "julianday(" not in sql.lower():
                failures.append("direct_timestamp_subtraction")

        # Check if counting rows when should calculate duration
        if task_needs_lead and "COUNT(" in sql_upper and "julianday" not in sql.lower():
            failures.append("row_counts_instead_of_durations")

        # Check for case-sensitive status comparison (should use UPPER())
        if any(keyword in task_lower for keyword in ["uptime", "operational", "status", "degraded", "incident"]):
            # Look for status = 'operational' (or other statuses) without UPPER()
            if re.search(r"status\s*=\s*['\"](?:operational|degraded|incident|maintenance|recently_resolved)['\"]", sql, re.IGNORECASE):
                if "UPPER(status)" not in sql and "LOWER(status)" not in sql:
                    failures.append("case_sensitive_status_check")

        return failures

    @staticmethod
    def _execute_sql(sql: str, db_path: str = "/data/status_dashboard.db") -> Dict[str, Any]:
        """Execute SQL and return results with metadata."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(sql)
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            conn.close()
            
            return {
                "success": True,
                "exec_error": None,
                "result_columns": columns,
                "row_count": len(rows),
                "rows": rows
            }
        except Exception as e:
            return {
                "success": False,
                "exec_error": str(e),
                "result_columns": [],
                "row_count": 0,
                "rows": []
            }

    @staticmethod
    async def generate_query(
        task: str,
        output_contract: Optional[str] = None,
        max_repairs: int = 2,
        backend: str = DEFAULT_SQL_BACKEND
    ) -> Dict[str, Any]:
        """
        Generate SQL query with guardrails and self-correction.

        Args:
            task: Natural language description of the query
            output_contract: Optional specification of required output columns
            max_repairs: Maximum number of repair attempts (default: 2)
            backend: SQL generation backend ('ollama', 'sqlcoder', or 'custom', default from DEFAULT_SQL_BACKEND)

        Returns:
            Dict with: sql, result, success, attempts, errors
        """
        logger.info(f"Generating SQL query using backend: {backend}")

        # Step 1: Generate initial query with selected backend
        try:
            if backend == SQL_BACKEND_SQLCODER:
                llm_output = await SQLQueryGenerator._generate_with_sqlcoder(task, output_contract)
            elif backend == SQL_BACKEND_OLLAMA:
                llm_output = await SQLQueryGenerator._generate_with_ollama(task, output_contract)
            elif backend == SQL_BACKEND_CUSTOM:
                logger.info(f"Using custom SQL backend for task: {task}")
                llm_output = await SQLQueryGenerator._generate_with_custom_model(task, output_contract, wrap_with_llm=False)
            else:
                raise ValueError(f"Unknown SQL backend: {backend}. Use '{SQL_BACKEND_OLLAMA}', '{SQL_BACKEND_SQLCODER}', or '{SQL_BACKEND_CUSTOM}'")
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "sql": None,
                "plan": None,
                "checks": [],
                "warnings": [],
                "result": None,
                "error": f"Failed to parse LLM JSON response: {e}",
                "policy_failures": [],
                "attempts": 0,
                "repair_history": []
            }

        # Step 2: Run introspect_sql if provided
        if llm_output.get("introspect_sql"):
            introspect_result = SQLQueryGenerator._execute_sql(llm_output["introspect_sql"])
            logger.info(f"Introspect query executed: {introspect_result['success']}")

        # Step 3: Validate and execute main SQL
        sql = llm_output.get("sql", "")
        policy_failures = SQLQueryGenerator._validate_policy(sql, task)
        exec_result = SQLQueryGenerator._execute_sql(sql)

        attempts = [{"llm_output": llm_output, "exec_result": exec_result, "policy_failures": policy_failures}]

        # Step 4: Repair loop if needed
        repair_count = 0
        while (not exec_result["success"] or policy_failures) and repair_count < max_repairs:
            repair_count += 1
            logger.info(f"Repair attempt {repair_count}/{max_repairs}")

            # Create repair prompt
            repair_prompt = SQLQueryGenerator._create_repair_prompt(
                task=task,
                output_contract=output_contract,
                previous_output=llm_output,
                exec_error=exec_result["exec_error"],
                result_columns=exec_result["result_columns"],
                row_count=exec_result["row_count"],
                policy_failures=policy_failures
            )

            # Get repaired query
            repair_messages = [{"role": "user", "content": repair_prompt}]
            repair_response = await LLMService.chat(repair_messages, context=None)

            # Parse repaired JSON
            try:
                json_match = re.search(r'\{.*\}', repair_response, re.DOTALL)
                if json_match:
                    llm_output = json.loads(json_match.group())
                else:
                    llm_output = json.loads(repair_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse repair JSON: {e}")
                break

            # Re-validate and execute
            sql = llm_output.get("sql", "")
            policy_failures = SQLQueryGenerator._validate_policy(sql, task)
            exec_result = SQLQueryGenerator._execute_sql(sql)

            attempts.append({"llm_output": llm_output, "exec_result": exec_result, "policy_failures": policy_failures})

        # Final result
        final_success = exec_result["success"] and not policy_failures

        return {
            "success": final_success,
            "sql": sql,
            "plan": llm_output.get("plan"),
            "checks": llm_output.get("checks", []),
            "warnings": llm_output.get("warnings", []),
            "result": {
                "columns": exec_result["result_columns"],
                "rows": exec_result["rows"],
                "row_count": exec_result["row_count"]
            } if exec_result["success"] else None,
            "error": exec_result["exec_error"],
            "policy_failures": policy_failures,
            "attempts": len(attempts),
            "repair_history": attempts
        }
