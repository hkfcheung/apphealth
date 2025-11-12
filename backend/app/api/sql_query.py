"""SQL Query API endpoints with guardrails."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from app.services.sql_query_generator import (
    SQLQueryGenerator,
    SQL_BACKEND_OLLAMA,
    SQL_BACKEND_SQLCODER,
    SQL_BACKEND_CUSTOM,
    DEFAULT_SQL_BACKEND
)

router = APIRouter(prefix="/sql", tags=["sql"])


class SQLQueryRequest(BaseModel):
    """SQL query generation request."""
    task: str
    output_contract: Optional[str] = None
    max_repairs: int = 2
    backend: str = DEFAULT_SQL_BACKEND  # 'ollama' or 'sqlcoder'


class SQLQueryResponse(BaseModel):
    """SQL query generation response."""
    success: bool
    sql: Optional[str]
    plan: Optional[str]
    checks: List[str] = []
    warnings: List[str] = []
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    policy_failures: List[str] = []
    attempts: int
    repair_history: List[Dict[str, Any]] = []


@router.post("/generate", response_model=SQLQueryResponse)
async def generate_sql_query(request: SQLQueryRequest):
    """
    Generate SQL query from natural language with guardrails and self-correction.

    Example request:
    {
        "task": "Show me all services that are currently in recently_resolved status",
        "output_contract": "display_name TEXT, status TEXT, summary TEXT",
        "backend": "sqlcoder"
    }

    Backends:
    - "ollama": Use Ollama with llama3.2 (default, requires Ollama running)
    - "sqlcoder": Use SQLCoder-7b-2 specialized SQL model (requires GPU/CPU inference)
    - "custom": Use custom fine-tuned sqlite-expert model (eeezeecee/sqlite-expert-v1)
    """
    result = await SQLQueryGenerator.generate_query(
        task=request.task,
        output_contract=request.output_contract,
        max_repairs=request.max_repairs,
        backend=request.backend
    )

    return SQLQueryResponse(**result)


@router.get("/examples")
def get_query_examples():
    """Get example SQL query tasks."""
    return {
        "examples": [
            {
                "task": "Show me all services that are currently in recently_resolved status",
                "output_contract": "display_name TEXT, status TEXT, summary TEXT"
            },
            {
                "task": "Calculate uptime percentage for each service over the last 7 days",
                "output_contract": "site_id TEXT, display_name TEXT, uptime_percent REAL, total_checks INTEGER"
            },
            {
                "task": "List all incidents in the last 24 hours with their duration",
                "output_contract": "site TEXT, status TEXT, start_time TEXT, duration_minutes REAL"
            },
            {
                "task": "Show services with the most status changes in the last week",
                "output_contract": "display_name TEXT, change_count INTEGER, latest_status TEXT"
            },
            {
                "task": "Get the average time to resolution for incidents by service",
                "output_contract": "service TEXT, avg_resolution_hours REAL, incident_count INTEGER"
            }
        ],
        "schema_info": {
            "tables": ["sites", "readings", "advisories", "site_modules", "chat_messages"],
            "key_columns": {
                "sites": ["id", "display_name", "status_page"],
                "readings": ["site_id", "status", "created_at", "last_changed_at"]
            },
            "status_values": ["operational", "recently_resolved", "degraded", "incident", "maintenance", "unknown"]
        }
    }
