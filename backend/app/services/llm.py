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
        if settings.llm_provider in ["openai", "anthropic"]:
            return bool(settings.llm_api_key)
        # Ollama and fallback don't need API key
        return True

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

        try:
            if settings.llm_provider == "openai":
                return await LLMService._openai_chat(messages, context, settings)
            elif settings.llm_provider == "anthropic":
                return await LLMService._anthropic_chat(messages, context, settings)
            elif settings.llm_provider == "ollama":
                # Check if we should use vision (llava model)
                model = settings.llm_model or ""
                if "llava" in model.lower():
                    logger.info(f"Using Ollama vision model: {model}")
                    return await LLMService._ollama_chat_with_vision(messages, context, settings)
                else:
                    return await LLMService._ollama_chat(messages, context, settings)
            else:
                return LLMService._fallback_chat(messages, context)
        except Exception as e:
            logger.error(f"Chat LLM failed: {e}")
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
            max_tokens=500  # Limit length to encourage brevity
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
        base_prompt = """You are a status dashboard assistant. Answer questions accurately and concisely based ONLY on the provided data.

CRITICAL RULES:
1. ONLY use data explicitly provided below - never guess or infer
2. If asked about CURRENT status, use the "All Services" section ONLY
3. Historical data is for context - clearly distinguish past vs present
4. If data is missing or unclear, say "I don't have that information"
5. Be brief and factual - list facts without elaboration"""

        if context:
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
                base_prompt += "\n\n=== CURRENT STATUS (Use this for 'current' questions) ==="
                base_prompt += "\nAll Services Right Now:"
                for service in context["all_services"]:
                    base_prompt += f"\n- {service['site']}: {service['status']}"

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
                base_prompt += f"\n\n=== HISTORICAL DATA (Past 24h - for trend analysis only) ==="
                base_prompt += f"\nHistorical Status Changes ({len(historical)} readings):"
                # Group by service and show status changes
                from collections import defaultdict
                from datetime import datetime

                by_service = defaultdict(list)
                for reading in historical:
                    by_service[reading['site']].append(reading)

                for service_name in sorted(by_service.keys()):
                    readings = by_service[service_name][:5]  # Last 5 per service
                    if len(readings) > 0:
                        base_prompt += f"\n  {service_name}:"
                        for r in readings:
                            timestamp = r['timestamp'].split('T')[1][:5] if 'T' in r['timestamp'] else r['timestamp']
                            base_prompt += f"\n    - {timestamp}: {r['status']}"
                            if r['status'] != 'operational':
                                base_prompt += f" ({r['summary']})"

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
