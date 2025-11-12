"""LLM service with support for OpenAI, Anthropic, Ollama, and fallback models."""
import logging
import json
import re
import base64
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.models import AppSettings
from app.database import engine, Session

logger = logging.getLogger(__name__)


class LLMService:
    """Handles LLM operations with multiple provider support."""

    @staticmethod
    def get_settings() -> Optional[AppSettings]:
        """Get LLM settings from database."""
        with Session(engine) as session:
            return session.get(AppSettings, 1)

    @staticmethod
    def is_configured() -> bool:
        """Check if LLM is configured."""
        settings = LLMService.get_settings()
        if not settings or not settings.llm_provider:
            return False

        # Check if provider has necessary configuration
        if settings.llm_provider in ["openai", "anthropic"]:
            return bool(settings.llm_api_key and settings.llm_model)
        elif settings.llm_provider == "ollama":
            return bool(settings.llm_model)  # Ollama doesn't require API key
        elif settings.llm_provider == "huggingface":
            return bool(settings.llm_model)

        return False

    @staticmethod
    async def analyze_advisory(
        title: str,
        description: str,
        severity: Optional[str],
        configured_modules: List[str],
        service_name: str
    ) -> Dict[str, Any]:
        """
        Analyze an advisory to determine criticality and relevance.

        Returns:
            {
                "criticality": "high|medium|low",
                "affects_us": bool,
                "affected_modules": [list of module names],
                "relevance_reason": str
            }
        """
        settings = LLMService.get_settings()

        if not settings or not settings.llm_provider:
            # Use fallback analysis
            return LLMService._fallback_analyze_advisory(
                title, description, severity, configured_modules
            )

        try:
            if settings.llm_provider == "openai":
                return await LLMService._openai_analyze_advisory(
                    title, description, severity, configured_modules, service_name, settings
                )
            elif settings.llm_provider == "anthropic":
                return await LLMService._anthropic_analyze_advisory(
                    title, description, severity, configured_modules, service_name, settings
                )
            elif settings.llm_provider == "ollama":
                return await LLMService._ollama_analyze_advisory(
                    title, description, severity, configured_modules, service_name, settings
                )
            elif settings.llm_provider == "huggingface":
                return await LLMService._huggingface_analyze_advisory(
                    title, description, severity, configured_modules, service_name, settings
                )
            else:
                return LLMService._fallback_analyze_advisory(
                    title, description, severity, configured_modules
                )
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}, falling back to basic analysis")
            return LLMService._fallback_analyze_advisory(
                title, description, severity, configured_modules
            )

    @staticmethod
    async def _openai_analyze_advisory(
        title: str, description: str, severity: Optional[str],
        configured_modules: List[str], service_name: str, settings: AppSettings
    ) -> Dict[str, Any]:
        """Use OpenAI API for advisory analysis."""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.llm_api_key)

            prompt = LLMService._create_analysis_prompt(
                title, description, severity, configured_modules, service_name
            )

            response = await client.chat.completions.create(
                model=settings.llm_model or "gpt-4",
                messages=[
                    {"role": "system", "content": "You are a technical analyst evaluating service advisories for impact assessment. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            return LLMService._parse_llm_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    @staticmethod
    async def _anthropic_analyze_advisory(
        title: str, description: str, severity: Optional[str],
        configured_modules: List[str], service_name: str, settings: AppSettings
    ) -> Dict[str, Any]:
        """Use Anthropic API for advisory analysis."""
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.llm_api_key)

            prompt = LLMService._create_analysis_prompt(
                title, description, severity, configured_modules, service_name
            )

            response = await client.messages.create(
                model=settings.llm_model or "claude-3-5-sonnet-20241022",
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return LLMService._parse_llm_response(response.content[0].text)
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    @staticmethod
    async def _ollama_analyze_advisory(
        title: str, description: str, severity: Optional[str],
        configured_modules: List[str], service_name: str, settings: AppSettings
    ) -> Dict[str, Any]:
        """Use Ollama (local) API for advisory analysis."""
        try:
            import openai

            # Ollama endpoint (default: http://host.docker.internal:11434/v1 for Docker)
            ollama_base_url = settings.llm_api_key or "http://host.docker.internal:11434/v1"

            client = openai.AsyncOpenAI(
                base_url=ollama_base_url,
                api_key="ollama"  # Ollama doesn't use API keys but the client requires one
            )

            prompt = LLMService._create_analysis_prompt(
                title, description, severity, configured_modules, service_name
            )

            response = await client.chat.completions.create(
                model=settings.llm_model or "llama3.2",
                messages=[
                    {"role": "system", "content": "You are a technical analyst evaluating service advisories for impact assessment. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            return LLMService._parse_llm_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    @staticmethod
    def _create_analysis_prompt(
        title: str, description: str, severity: Optional[str],
        configured_modules: List[str], service_name: str
    ) -> str:
        """Create the analysis prompt for LLM."""
        modules_str = ", ".join(configured_modules) if configured_modules else "none configured"

        return f"""Analyze this service advisory for {service_name}:

Title: {title}
Description: {description or "No description"}
Vendor Severity: {severity or "Not specified"}

Our organization uses these modules/components: {modules_str}

Determine:
1. Criticality level (high/medium/low) based on impact and urgency
2. Whether it affects our configured modules
3. Which specific modules are affected (if any)
4. Brief explanation of relevance

Respond with ONLY this JSON format (no markdown, no extra text):
{{
    "criticality": "high|medium|low",
    "affects_us": true|false,
    "affected_modules": ["module1", "module2"],
    "relevance_reason": "Brief explanation of why this does/doesn't affect us"
}}

Guidelines:
- "high": Service down, data loss risk, security issue
- "medium": Degraded performance, partial outage, upcoming changes
- "low": Informational, scheduled maintenance, minor issues
- affects_us = true if ANY configured module is mentioned or implied
- Extract module names matching our configured list when possible"""

    @staticmethod
    def _parse_llm_response(response_text: str) -> Dict[str, Any]:
        """Parse LLM response and ensure valid format."""
        try:
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            response_text = response_text.strip()

            data = json.loads(response_text)

            # Validate required fields
            return {
                "criticality": data.get("criticality", "low"),
                "affects_us": bool(data.get("affects_us", False)),
                "affected_modules": data.get("affected_modules", []),
                "relevance_reason": data.get("relevance_reason", "No analysis available")
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}\nResponse: {response_text}")
            return {
                "criticality": "low",
                "affects_us": False,
                "affected_modules": [],
                "relevance_reason": "Analysis parsing failed"
            }

    @staticmethod
    def _fallback_analyze_advisory(
        title: str, description: str, severity: Optional[str],
        configured_modules: List[str]
    ) -> Dict[str, Any]:
        """Basic keyword-based analysis when no LLM is configured."""
        text = f"{title} {description or ''}".lower()

        # Determine criticality from keywords and vendor severity
        criticality = "low"
        if severity and severity.lower() in ["critical", "high", "severe"]:
            criticality = "high"
        elif severity and severity.lower() in ["medium", "moderate", "warning"]:
            criticality = "medium"

        # Check for high-criticality keywords
        high_keywords = ["outage", "down", "offline", "unavailable", "failed", "data loss", "security"]
        medium_keywords = ["degraded", "slow", "latency", "intermittent", "investigating"]

        if any(keyword in text for keyword in high_keywords):
            criticality = "high"
        elif any(keyword in text for keyword in medium_keywords) and criticality == "low":
            criticality = "medium"

        # Check if it affects configured modules
        affects_us = False
        affected_modules = []

        for module in configured_modules:
            if module.lower() in text:
                affects_us = True
                affected_modules.append(module)

        reason = "Basic analysis: "
        if affects_us:
            reason += f"Mentions configured modules: {', '.join(affected_modules)}"
        else:
            if configured_modules:
                reason += f"Does not mention configured modules ({', '.join(configured_modules[:3])})"
            else:
                reason += "No modules configured for filtering"

        return {
            "criticality": criticality,
            "affects_us": affects_us,
            "affected_modules": affected_modules,
            "relevance_reason": reason
        }

    @staticmethod
    async def _try_sql_query(user_message: str) -> Optional[Dict[str, Any]]:
        """
        SQL query disabled for speed.
        """
        return None
        # Keywords that indicate analytical SQL queries about dashboard data
        # Be more selective - only trigger SQL for actual data queries
        sql_keywords = [
            "uptime", "percentage", "calculate", "average", "total", "count",
            "how many services", "statistics", "over the last", "in the past",
            "time-weighted", "time weighted", "downtime", "availability",
            "mean time", "mttr", "resolution", "duration", "how long",
            "metrics", "analysis", "trend", "pattern", "frequency"
        ]
        
        # Additional context that indicates a dashboard data query
        dashboard_context = [
            "service", "services", "operational", "degraded", "incident",
            "outage", "status", "monitoring", "dashboard", "alert",
            "smartsheet", "zoom", "slack", "microsoft", "aws", "netlify",
            "openai", "anthropic", "adobe", "atlassian", "box", "docusign"
        ]

        message_lower = user_message.lower()
        
        # Check if it has SQL keywords AND dashboard context
        has_sql_keyword = any(keyword in message_lower for keyword in sql_keywords)
        has_dashboard_context = any(context in message_lower for context in dashboard_context)
        
        # Only generate SQL if it's actually about dashboard data
        requires_sql = has_sql_keyword or (has_dashboard_context and 
                      any(word in message_lower for word in ["status", "how", "what", "which", "list", "show"]))

        if not requires_sql:
            return None

        logger.info(f"Detected SQL query need in message: {user_message[:100]}")

        try:
            from app.services.sql_query_generator import SQLQueryGenerator, SQL_BACKEND_OLLAMA, SQL_BACKEND_CUSTOM
            
            # Check if we should use the custom SQL model
            settings = LLMService.get_settings()
            backend = SQL_BACKEND_OLLAMA  # Default
            
            # Use custom backend if Hugging Face is configured
            if settings and settings.llm_provider == "huggingface":
                backend = SQL_BACKEND_CUSTOM
                logger.info("Using custom SQL model for query generation")

            # Generate and execute SQL query
            result = await SQLQueryGenerator.generate_query(
                task=user_message,
                output_contract=None,  # Let LLM infer the output
                max_repairs=2,
                backend=backend
            )

            if result.get("success"):
                logger.info(f"SQL query succeeded: {result.get('sql', '')[:200]}")
                return {
                    "task": user_message,
                    "sql": result.get("sql"),
                    "results": result.get("result", {}).get("rows", []),
                    "columns": result.get("result", {}).get("columns", []),
                    "row_count": result.get("result", {}).get("row_count", 0)
                }
            else:
                logger.warning(f"SQL query failed: {result.get('error')}")
                return None

        except Exception as e:
            logger.error(f"Error executing SQL query for chat: {e}")
            return None

    @staticmethod
    async def chat(messages: List[Dict[str, str]], context: Optional[Dict] = None) -> str:
        """
        Chat with LLM about status dashboard data.

        Args:
            messages: List of {role, content} messages
            context: Optional context data (current outages, recent advisories, etc.)

        Returns:
            Assistant response text
        """
        settings = LLMService.get_settings()

        if not settings or not settings.llm_provider:
            return LLMService._fallback_chat(messages, context)

        # Skip SQL query analysis for speed

        try:
            if settings.llm_provider == "openai":
                return await LLMService._openai_chat(messages, context, settings)
            elif settings.llm_provider == "anthropic":
                return await LLMService._anthropic_chat(messages, context, settings)
            elif settings.llm_provider == "ollama":
                return await LLMService._ollama_chat(messages, context, settings)
            elif settings.llm_provider == "huggingface":
                return await LLMService._huggingface_chat(messages, context, settings)
            else:
                return LLMService._fallback_chat(messages, context)
        except Exception as e:
            logger.error(f"Chat LLM failed: {e}", exc_info=True)
            return LLMService._fallback_chat(messages, context)

    @staticmethod
    async def _openai_chat(
        messages: List[Dict[str, str]], context: Optional[Dict], settings: AppSettings
    ) -> str:
        """Chat using OpenAI."""
        import openai
        client = openai.AsyncOpenAI(api_key=settings.llm_api_key)

        system_prompt = LLMService._create_chat_system_prompt(context)

        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(messages)

        response = await client.chat.completions.create(
            model=settings.llm_model or "gpt-4",
            messages=api_messages,
            temperature=0.7,
            max_tokens=1000
        )

        return response.choices[0].message.content

    @staticmethod
    async def _anthropic_chat(
        messages: List[Dict[str, str]], context: Optional[Dict], settings: AppSettings
    ) -> str:
        """Chat using Anthropic."""
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.llm_api_key)

        system_prompt = LLMService._create_chat_system_prompt(context)

        # Anthropic doesn't use system messages in the messages array
        api_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]

        response = await client.messages.create(
            model=settings.llm_model or "claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.7,
            system=system_prompt,
            messages=api_messages
        )

        return response.content[0].text

    @staticmethod
    async def _ollama_chat(
        messages: List[Dict[str, str]], context: Optional[Dict], settings: AppSettings
    ) -> str:
        """Chat using Ollama (local)."""
        import openai

        # Ollama endpoint (default: http://host.docker.internal:11434/v1 for Docker)
        ollama_base_url = settings.llm_api_key or "http://host.docker.internal:11434/v1"

        client = openai.AsyncOpenAI(
            base_url=ollama_base_url,
            api_key="ollama"  # Ollama doesn't use API keys but the client requires one
        )

        system_prompt = LLMService._create_chat_system_prompt(context)

        api_messages = [{"role": "system", "content": system_prompt}]
        api_messages.extend(messages)

        response = await client.chat.completions.create(
            model=settings.llm_model or "llama3.2",
            messages=api_messages,
            temperature=0.1,  # Very low temperature to minimize hallucinations
            max_tokens=1500  # Allow longer responses for detailed lists
        )

        return response.choices[0].message.content

    @staticmethod
    async def _ollama_chat_with_vision(
        messages: List[Dict[str, str]],
        context: Optional[Dict],
        settings: AppSettings
    ) -> str:
        """Chat using Ollama with vision support (llava model)."""
        import openai

        ollama_base_url = settings.llm_api_key or "http://host.docker.internal:11434/v1"

        client = openai.AsyncOpenAI(
            base_url=ollama_base_url,
            api_key="ollama"
        )

        system_prompt = LLMService._create_chat_system_prompt(context)

        # Prepare messages with vision content
        api_messages = []

        # Add system message as first user message content (llava doesn't support system role)
        first_content = [{"type": "text", "text": system_prompt}]

        # Add DownDetector images if available
        if context and context.get("downdetector_images"):
            images = context["downdetector_images"]
            logger.info(f"Including {len(images)} DownDetector screenshots in vision request")

            for img_data in images[:5]:  # Limit to 5 images to avoid token limits
                image_path = img_data["path"]
                if os.path.exists(image_path):
                    try:
                        with open(image_path, 'rb') as f:
                            image_bytes = f.read()
                            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

                        first_content.append({
                            "type": "text",
                            "text": f"\n\n--- DownDetector Chart for {img_data['site']} ---"
                        })
                        first_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            }
                        })
                    except Exception as e:
                        logger.error(f"Failed to encode image {image_path}: {e}")

        # Add first message with system prompt and images
        api_messages.append({"role": "user", "content": first_content})

        # Add conversation history
        for msg in messages:
            # Skip if it's a system message (we already added it)
            if msg["role"] == "system":
                continue

            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        response = await client.chat.completions.create(
            model=settings.llm_model or "llava",
            messages=api_messages,
            temperature=0.3,
            max_tokens=800  # Increase token limit for vision responses
        )

        return response.choices[0].message.content

    @staticmethod
    def _create_chat_system_prompt(context: Optional[Dict]) -> str:
        """Create system prompt for chat with context."""
        # If no context, use a simple helpful prompt
        if not context:
            return """You are a helpful AI assistant for a service status monitoring dashboard.

You can help users with:
- General questions about how to use the dashboard
- Information about AI models and capabilities
- Friendly conversation

Be concise, helpful, and friendly. If asked what model you are, share information about the OpenAI model being used."""

        # Has context - build detailed prompt with service data
        base_prompt = """You are a helpful status dashboard assistant. You help users monitor and understand their service status data.

When users ask general questions or greet you, respond naturally and helpfully.
When users ask about service status data, use ONLY the data provided below.

IMPORTANT RULES FOR SERVICE DATA QUERIES:
1. ONLY use data explicitly provided below - never guess or infer about service status
2. When listing services, only list each service ONCE (not multiple times)
3. If service status data is missing or unclear, say "I don't have that information"
4. Be brief and factual - list facts without elaboration

CRITICAL: CURRENT vs HISTORICAL QUERIES:
- "What's down NOW?" / "Current issues?" → Use CURRENT STATUS section
- "Any issues TODAY?" / "Last 24 hours?" / "During [time]?" → Use HISTORICAL DATA section
- "recently_resolved" status means: had issues in last 24h, but currently operational
- When asked about a time period (today, last 24h, etc.), ALWAYS check HISTORICAL DATA even if current status is operational

UPTIME CALCULATION:
When asked about uptime, calculate it from the historical readings:
- Uptime % = (number of "operational" readings / total readings) × 100
- Count readings with status="operational" vs other statuses (degraded, outage, etc.)
- Historical data covers the last 30 days
- Show uptime as a percentage (e.g., "99.5% uptime")"""

        # Add SQL query results if available (priority information)
        if context.get("sql_query_results"):
            sql_data = context["sql_query_results"]
            base_prompt += "\n\n=== SQL QUERY RESULTS (Use this to answer the user's question) ==="
            base_prompt += f"\nQuery: {sql_data.get('task', 'N/A')}"

            # Format results concisely
            results = sql_data.get('results', [])
            columns = sql_data.get('columns', [])
            row_count = sql_data.get('row_count', 0)

            if results and columns:
                base_prompt += f"\nResults ({row_count} rows):"
                # Limit to 10 rows and format concisely
                for row in results[:10]:
                    row_dict = dict(zip(columns, row))
                    base_prompt += f"\n  {row_dict}"
                if row_count > 10:
                    base_prompt += f"\n  ... and {row_count - 10} more rows"
            else:
                base_prompt += "\nNo results returned"

            base_prompt += "\n\nIMPORTANT: Use the SQL results above to answer the question."
            # Skip adding the full dashboard data to save tokens
            return base_prompt

        # Add note about DownDetector images if present
        if context.get("downdetector_images"):
            num_images = len(context["downdetector_images"])
            base_prompt += f"\n\nNOTE: {num_images} DownDetector chart images are included below. Analyze these charts to understand report patterns and trends."
        base_prompt += "\n\n=== CURRENT DASHBOARD DATA ===\n"

        # Total services
        total = context.get("total_services", 0)
        base_prompt += f"\nTotal Monitored Services: {total}"

        # All services status
        if context.get("all_services"):
            base_prompt += "\n\n=== CURRENT STATUS (Use this for 'current' or 'recently resolved' questions) ==="
            base_prompt += "\nAll Services Right Now (each listed ONCE):"
            for service in context["all_services"]:
                base_prompt += f"\n- {service['site']}: {service['status']}"
                if service.get('summary'):
                    base_prompt += f" - {service['summary'][:100]}"

        # Active issues
        issues = context.get("current_issues", [])
        if issues:
            base_prompt += f"\n\nActive Issues ({len(issues)}):"
            for issue in issues:
                base_prompt += f"\n- {issue['site']}: {issue['status']} - {issue['summary']}"
        else:
            base_prompt += "\n\nActive Issues: None - All services operational"

        # Historical readings (last 24 hours)
        historical = context.get("historical_readings", [])
        if historical:
            base_prompt += f"\n\n=== HISTORICAL DATA (Past 24h with timestamps) ==="
            base_prompt += f"\nHistorical Status Changes ({len(historical)} readings in Pacific Time):"
            base_prompt += "\nNOTE: Use these timestamps when answering time-related questions."
            base_prompt += "\nIncident types: VENDOR_INCIDENT = actual vendor issue, OUR_NETWORK_ERROR = our connectivity issue"
            # Group by service and show status changes
            from collections import defaultdict
            from datetime import datetime

            by_service = defaultdict(list)
            for reading in historical:
                by_service[reading['site']].append(reading)

            for service_name in sorted(by_service.keys()):
                readings = by_service[service_name][:3]  # Limit to 3 most recent per service
                if len(readings) > 0:
                    base_prompt += f"\n  {service_name}:"
                    for r in readings:
                        timestamp = r.get('timestamp', 'unknown')
                        incident_type = r.get('incident_type', 'VENDOR_INCIDENT')
                        status = r['status']
                        summary = r.get('summary', '')

                        # Format: timestamp, status, incident type, summary
                        base_prompt += f"\n    - {timestamp} | {status} | {incident_type}"
                        if status != 'operational' and summary:
                            base_prompt += f" | {summary}"

        # Recent advisories
        advisories = context.get("recent_advisories", [])
        if advisories:
            base_prompt += f"\n\nRecent Advisories ({len(advisories)} in last 24h):"
            for adv in advisories[:5]:
                base_prompt += f"\n- {adv['site_id']}: {adv['title']} [{adv['criticality']}]"

        # Configured modules
        if context.get("configured_modules"):
            base_prompt += f"\n\nMonitored Modules: {', '.join(context['configured_modules'][:10])}"

        return base_prompt

    @staticmethod
    def _fallback_chat(messages: List[Dict[str, str]], context: Optional[Dict]) -> str:
        """Fallback chat response when no LLM configured."""
        last_message = messages[-1]["content"].lower() if messages else ""

        # Simple keyword-based responses
        if "outage" in last_message or "down" in last_message:
            return "To view current outages, check the status cards on the dashboard. Services with non-operational status are highlighted. Configure an LLM API key in Admin settings for detailed analysis."

        if "today" in last_message:
            return "Check the dashboard for today's status. Enable LLM integration in Admin settings for intelligent summaries of daily incidents."

        if "affect" in last_message:
            return "Configure modules in site settings and enable LLM to automatically analyze which advisories affect your organization."

        return "LLM chat is not configured. Add an OpenAI or Anthropic API key in Admin settings to enable intelligent conversation about your service status data."

    @staticmethod
    async def _huggingface_analyze_advisory(
        title: str, description: str, severity: Optional[str],
        configured_modules: List[str], service_name: str, settings: AppSettings
    ) -> Dict[str, Any]:
        """Use Hugging Face model for advisory analysis via Inference API."""
        try:
            from app.services.llm_huggingface import HuggingFaceInference
            
            model_name = settings.llm_model or "eeezeecee/sqlite-expert-v1"
            prompt = LLMService._create_analysis_prompt(
                title, description, severity, configured_modules, service_name
            )
            
            # Use the Inference API
            response = await HuggingFaceInference.analyze_advisory(
                model_name=model_name,
                prompt=prompt,
                api_token=settings.llm_api_key,  # Optional, can be None
                max_new_tokens=500,
                temperature=0.3
            )
            
            return LLMService._parse_llm_response(response)
        except Exception as e:
            logger.error(f"Hugging Face API error: {e}")
            raise

    @staticmethod
    async def _huggingface_chat(
        messages: List[Dict[str, str]], context: Optional[Dict], settings: AppSettings
    ) -> str:
        """Chat using Hugging Face Inference API."""
        try:
            from app.services.llm_huggingface import HuggingFaceInference
            
            model_name = settings.llm_model or "openai/gpt-oss-20b"
            logger.info(f"Using Hugging Face Inference API with model: {model_name}")
            
            # Use HuggingFace Inference API
            response = await HuggingFaceInference.chat(
                model_name=model_name,
                messages=messages,
                context=LLMService._create_chat_system_prompt(context),
                api_token=settings.llm_api_key,
                max_new_tokens=1000,
                temperature=0.7
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Hugging Face chat failed: {e}", exc_info=True)
            return LLMService._simple_chat_fallback(messages, context)

    @staticmethod
    def _simple_chat_fallback(messages: List[Dict[str, str]], context: Optional[Dict]) -> str:
        """Simple fallback for when model is not available."""
        last_user_msg = messages[-1]["content"] if messages else ""
        msg_lower = last_user_msg.lower()
        
        # First check if we have SQL query results
        if context and "sql_query_results" in context:
            sql_data = context["sql_query_results"]
            results = sql_data.get("results", [])
            columns = sql_data.get("columns", [])
            
            if results and columns:
                # Format the SQL results into a readable response
                if "mean time" in msg_lower and "resolution" in msg_lower:
                    # Handle MTTR results
                    response = "Mean Time to Resolution (MTTR):\n\n"
                    logger.info(f"MTTR Results - Columns: {columns}, First row: {results[0] if results else 'No rows'}")
                    for row in results:
                        row_dict = dict(zip(columns, row))
                        # Try different column names
                        service = row_dict.get("service", row_dict.get("site_id", row_dict.get("service_name", "Unknown")))
                        avg_minutes = row_dict.get("avg_resolution_minutes", 0)
                        incident_count = row_dict.get("total_incidents", row_dict.get("incident_count", 0))
                        
                        if avg_minutes and avg_minutes > 0:
                            hours = int(avg_minutes // 60)
                            minutes = int(avg_minutes % 60)
                            if hours > 0:
                                time_str = f"{hours}h {minutes}m"
                            else:
                                time_str = f"{minutes}m"
                            response += f"{service}: {time_str} average resolution time ({incident_count} incidents)\n"
                        else:
                            response += f"{service}: No incidents recorded\n"
                    
                    return response.strip()
                elif ("was" in msg_lower or "been" in msg_lower or "had" in msg_lower) and \
                     ("degraded" in msg_lower or "down" in msg_lower or "issues" in msg_lower):
                    # Handle historical queries
                    if results:
                        # Extract service name from first result
                        first_row = dict(zip(columns, results[0]))
                        service_name = first_row.get("display_name", "The service")
                        
                        # Format the response
                        response = f"Yes, {service_name} experienced issues in the requested time period:\n\n"
                        for i, row in enumerate(results):
                            row_dict = dict(zip(columns, row))
                            status = row_dict.get("status", "unknown")
                            summary = row_dict.get("summary", "No details available")
                            timestamp = row_dict.get("created_at", "")
                            
                            response += f"{i+1}. {timestamp}: {status}"
                            if summary and summary != "No details available":
                                response += f" - {summary}"
                            response += "\n"
                        
                        return response.strip()
                    else:
                        # No issues found
                        return "No, the service did not experience any issues in the requested time period."
                elif "status" in msg_lower:
                    # Handle status queries with natural language
                    if results:
                        row_dict = dict(zip(columns, results[0]))
                        service_name = row_dict.get("display_name", "The service")
                        status = row_dict.get("status", "unknown").replace("_", " ").title()
                        summary = row_dict.get("summary", "")
                        last_updated = row_dict.get("last_updated", "")
                        
                        if status.lower() == "operational":
                            response = f"{service_name} is currently operational with no reported issues."
                        elif status.lower() == "recently resolved":
                            response = f"{service_name} recently experienced issues that have now been resolved."
                            if summary:
                                response += f" The issue was: {summary}"
                        elif status.lower() in ["degraded", "incident", "maintenance"]:
                            response = f"{service_name} is currently experiencing issues with status: {status}."
                            if summary:
                                response += f" Details: {summary}"
                        else:
                            response = f"{service_name} status is {status}."
                            if summary:
                                response += f" Details: {summary}"
                        
                        # Add timing information
                        if last_updated:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(last_updated.replace(" ", "T"))
                                time_ago = datetime.now() - dt
                                if time_ago.seconds < 3600:
                                    mins = time_ago.seconds // 60
                                    response += f" (Last updated {mins} minutes ago)"
                                elif time_ago.seconds < 86400:
                                    hours = time_ago.seconds // 3600
                                    response += f" (Last updated {hours} hours ago)"
                                else:
                                    days = time_ago.days
                                    response += f" (Last updated {days} days ago)"
                            except:
                                response += f" (Last updated: {last_updated})"
                        
                        return response
                    else:
                        return "No status information available for that service."
                else:
                    # Generic SQL result formatting
                    response = f"Query results for: {sql_data.get('task', 'your query')}\n\n"
                    for i, row in enumerate(results[:10]):  # Limit to 10 rows
                        row_dict = dict(zip(columns, row))
                        response += f"{i+1}. {', '.join([f'{k}: {v}' for k, v in row_dict.items()])}\n"
                    if len(results) > 10:
                        response += f"\n... and {len(results) - 10} more results"
                    return response.strip()
            else:
                # Check if it's an MTTR query with no incidents
                if "mean time" in msg_lower and "resolution" in msg_lower:
                    if "zoom" in msg_lower:
                        return "Zoom has no recorded incidents in the current data, so Mean Time to Resolution cannot be calculated."
                    elif "smartsheet" in msg_lower:
                        return "Smartsheet has no recorded incidents in the current data, so Mean Time to Resolution cannot be calculated."
                    else:
                        return "No services have recorded incidents in the current data, so Mean Time to Resolution cannot be calculated."
                return "No results found for your query."
        
        if context and "all_services" in context:
            services = context["all_services"]
            
            # Check for specific service queries
            for service in services:
                service_name = service["site"].lower()
                if service_name in msg_lower:
                    status = service["status"]
                    summary = service.get("summary", "No details available")
                    
                    # Handle "why was X down" questions
                    if ("why" in msg_lower and ("was" in msg_lower or "is" in msg_lower)) or "what happened" in msg_lower:
                        if status == "recently_resolved":
                            return f"{service['site']} experienced issues that are now resolved. Last known issue: {summary}"
                        elif status == "operational":
                            # Check historical data for recent issues
                            if context.get("historical_readings"):
                                recent_issues = [r for r in context["historical_readings"] 
                                               if r["site"] == service["site"] and r["status"] != "operational"]
                                if recent_issues:
                                    latest_issue = recent_issues[0]  # Assuming sorted by time
                                    return f"{service['site']} previously had issues: {latest_issue.get('summary', 'No details available')} at {latest_issue.get('timestamp', 'unknown time')}"
                            return f"{service['site']} is currently operational with no recent issues recorded."
                        else:
                            return f"{service['site']} is currently down. Issue: {summary}"
                    
                    if "uptime" in msg_lower or "status" in msg_lower:
                        if status == "operational":
                            return f"{service['site']} is currently operational. Status: {summary}"
                        elif status == "recently_resolved":
                            return f"{service['site']} had issues recently but is now operational. Status: {summary}"
                        else:
                            return f"{service['site']} is experiencing issues. Status: {status}. Details: {summary}"
            
            # General status queries
            if "down" in msg_lower or "outage" in msg_lower:
                issues = [s for s in services if s["status"] not in ["operational", "recently_resolved"]]
                if issues:
                    return f"Currently experiencing issues: {', '.join([s['site'] for s in issues])}"
                else:
                    return "All services are operational."
            
            if "uptime" in msg_lower and "zoom" in msg_lower:
                zoom_service = next((s for s in services if s["site"].lower() == "zoom"), None)
                if zoom_service:
                    if zoom_service["status"] == "operational":
                        return "Zoom is currently operational with no reported issues."
                    elif zoom_service["status"] == "recently_resolved":
                        return "Zoom had recent issues but is now operational."
                    else:
                        return f"Zoom status: {zoom_service['status']}. {zoom_service.get('summary', '')}"
                else:
                    return "No Zoom service data available."
        
        return "I can help you check service status. Try asking about specific services or 'What services are currently down?'"
