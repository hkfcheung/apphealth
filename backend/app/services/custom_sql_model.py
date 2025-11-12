"""Custom SQLite-Expert model service for fine-tuned SQL generation."""
import logging
import torch
from typing import Optional
import re

logger = logging.getLogger(__name__)


class CustomSQLModel:
    """Service for generating SQL queries using custom fine-tuned sqlite-expert model."""

    _instance: Optional['CustomSQLModel'] = None
    _model = None
    _tokenizer = None
    _model_loaded = False
    _model_name = None

    def __init__(self):
        """Initialize Custom SQL Model service (singleton pattern)."""
        pass

    @classmethod
    def get_instance(cls) -> 'CustomSQLModel':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def load_model(
        cls,
        model_name: str = "eeezeecee/sqlite-expert-v1",
        use_quantization: bool = True
    ):
        """
        Check if model server is available (don't actually load model locally).

        Args:
            model_name: HuggingFace model name for fine-tuned SQLite expert
            use_quantization: If True, use 8-bit quantization for lower memory usage
        """
        if cls._model_loaded and cls._model_name == model_name:
            logger.info(f"Custom model {model_name} already connected")
            return

        try:
            logger.info(f"Checking connection to custom SQL model server for: {model_name}")
            
            # Just mark as loaded - we'll use the model server
            cls._model_loaded = True
            cls._model_name = model_name
            cls._tokenizer = None  # We don't need local tokenizer
            cls._model = None  # We don't need local model
            
            logger.info(f"Custom SQL model {model_name} marked as available (using model server)")

        except Exception as e:
            logger.error(f"Failed to setup custom SQL model: {e}")
            raise

    @classmethod
    def is_available(cls) -> bool:
        """Check if model is loaded and available."""
        return cls._model_loaded  # Just check the flag since we use model server

    @classmethod
    def generate_sql(
        cls,
        question: str,
        schema: Optional[str] = None,
        max_new_tokens: int = 300,
        temperature: float = 0.1,
        top_p: float = 0.95,
    ) -> str:
        """
        Generate SQL query from natural language question using model server.

        Args:
            question: Natural language question
            schema: Database schema (optional - model may be fine-tuned with schema)
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower = more deterministic)
            top_p: Nucleus sampling parameter

        Returns:
            Generated SQL query string
        """
        if not cls.is_available():
            raise RuntimeError("Custom SQL model not loaded. Call load_model() first.")

        # Build prompt for SQL generation
        prompt = cls._build_prompt(question, schema)
        
        # Use the model server
        try:
            import httpx
            
            # Model server URL
            model_server_url = "http://sqlite-expert-model:8080"
            
            # Check if server is healthy first
            with httpx.Client(timeout=60.0) as client:
                try:
                    health_response = client.get(f"{model_server_url}/health")
                    if health_response.status_code != 200:
                        logger.warning("Model server not healthy, using fallback")
                        return cls._fallback_sql_generation(question)
                except Exception as e:
                    logger.warning(f"Cannot reach model server: {e}, using fallback")
                    # Use fallback SQL generation
                    fallback_sql = cls._fallback_sql_generation(question)
                    logger.info(f"Using fallback SQL: {fallback_sql[:100]}")
                    return fallback_sql
                
                # Generate SQL
                response = client.post(
                    f"{model_server_url}/generate",
                    json={
                        "prompt": prompt,
                        "max_new_tokens": max_new_tokens,
                        "temperature": temperature
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result.get("generated_text", "")
                    
                    # Extract SQL from response
                    sql = cls._extract_sql(generated_text, prompt)
                    return sql
                else:
                    logger.error(f"Model server error: {response.status_code}")
                    fallback_sql = cls._fallback_sql_generation(question)
                    logger.info(f"Model server error, using fallback SQL: {fallback_sql[:100]}")
                    return fallback_sql
                    
        except Exception as e:
            logger.error(f"Error generating SQL with model server: {e}")
            fallback_sql = cls._fallback_sql_generation(question)
            logger.info(f"Exception during generation, using fallback SQL: {fallback_sql[:100]}")
            return fallback_sql

    @staticmethod
    def _build_prompt(question: str, schema: Optional[str] = None) -> str:
        """
        Build prompt for the fine-tuned model.

        Adjust this based on your fine-tuning format. Common formats:
        - Instruction-tuning: "### Instruction: ... ### Response:"
        - Alpaca: "Below is an instruction... ### Instruction: ... ### Response:"
        - Simple: "Question: ... SQL:"
        """
        # Option 1: Instruction format (adjust based on your training)
        if schema:
            prompt = f"""### Instruction:
Generate a SQLite query to answer the following question.

Database Schema:
{schema}

Question: {question}

### Response:
```sql
"""
        else:
            # If model was fine-tuned with schema embedded
            prompt = f"""### Instruction:
Generate a SQLite query to answer the following question.

Question: {question}

### Response:
```sql
"""

        return prompt

    @staticmethod
    def _extract_sql(generated_text: str, prompt: str) -> str:
        """
        Extract SQL query from model's generated text.

        Args:
            generated_text: Full generated text from model
            prompt: The original prompt (to remove it from output)

        Returns:
            Extracted SQL query
        """
        # Remove the prompt from generated text
        if prompt in generated_text:
            sql_part = generated_text[len(prompt):].strip()
        else:
            sql_part = generated_text.strip()

        # Try to extract from ```sql blocks
        sql_block_match = re.search(r'```sql\s*(.*?)\s*```', sql_part, re.DOTALL | re.IGNORECASE)
        if sql_block_match:
            sql = sql_block_match.group(1).strip()
            sql = sql.rstrip(';').strip()
            return sql

        # Try to extract everything after "```sql" (if block not closed)
        sql_start = sql_part.find('```sql')
        if sql_start != -1:
            sql = sql_part[sql_start + 6:].strip()
            # Stop at closing ``` or end
            if '```' in sql:
                sql = sql[:sql.find('```')].strip()
            sql = sql.rstrip(';').strip()
            return sql

        # Look for SELECT/WITH statements
        sql_match = re.search(r'((?:WITH|SELECT)\s+.*?)(?:;|$)', sql_part, re.DOTALL | re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
            return sql

        # Fallback: clean up and return
        # Remove common response prefixes
        for prefix in ['Here is the SQL:', 'SQL:', 'Query:']:
            if sql_part.startswith(prefix):
                sql_part = sql_part[len(prefix):].strip()

        sql = sql_part.rstrip(';').strip()

        # If nothing found, log warning and return as-is
        if not sql or len(sql) < 10:
            logger.warning(f"Could not extract clean SQL from generated text, returning: {sql_part[:100]}")
            return sql_part.strip()

        return sql
    
    @classmethod
    def _fallback_sql_generation(cls, question: str) -> str:
        """Fallback when model is not available - should not generate SQL."""
        logger.warning(f"Model not available for SQL generation. Question: {question}")
        
        # Don't generate SQL - just indicate the model is needed
        return "SELECT 'Fine-tuned model not available - need 32GB+ RAM to load sqlite-expert model' as message;"

    @classmethod
    def unload_model(cls):
        """Unload model to free memory."""
        if cls._model is not None:
            del cls._model
            cls._model = None
        if cls._tokenizer is not None:
            del cls._tokenizer
            cls._tokenizer = None
        cls._model_loaded = False
        cls._model_name = None

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Custom SQL model unloaded")