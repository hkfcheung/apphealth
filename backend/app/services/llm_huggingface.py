"""Simplified Hugging Face integration using the Inference API."""
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class HuggingFaceInference:
    """Use Hugging Face models via the Inference API (no local model loading needed)."""
    
    @staticmethod
    async def chat(
        model_name: str,
        messages: List[Dict[str, str]], 
        context: str,
        api_token: Optional[str] = None,
        max_new_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Use Hugging Face Inference API for chat.
        
        Args:
            model_name: HuggingFace model ID (e.g., "openai/gpt-oss-20b")
            messages: Chat messages
            context: Context string
            api_token: Optional HuggingFace API token
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated response text
        """
        # Check if using GPT-OSS model which requires special handling
        is_gpt_oss = "gpt-oss" in model_name.lower()
        
        # Prepare messages in chat format
        formatted_messages = []
        
        # Add system message with context
        formatted_messages.append({
            "role": "system",
            "content": context
        })
        
        # Add conversation history
        formatted_messages.extend(messages)
        
        # Determine API URL based on model
        if is_gpt_oss and ":cerebras" in model_name:
            # Use HF Router for GPT-OSS with Cerebras
            api_url = "https://router.huggingface.co/v1/chat/completions"
        else:
            # Use standard inference API
            api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        
        headers = {
            "Content-Type": "application/json",
        }
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        
        # Prepare payload based on endpoint
        if "router.huggingface.co" in api_url:
            # OpenAI-compatible format for router
            payload = {
                "model": model_name,
                "messages": formatted_messages,
                "max_tokens": max_new_tokens,
                "temperature": temperature
            }
        else:
            # Standard HF Inference API format
            last_user_msg = messages[-1]["content"] if messages else ""
            prompt = f"{context}\n\nUser: {last_user_msg}\n\nAssistant:"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_new_tokens,
                    "temperature": temperature,
                    "return_full_text": False,
                }
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Handle router response format
                    if "router.huggingface.co" in api_url:
                        if "choices" in result and len(result["choices"]) > 0:
                            return result["choices"][0]["message"]["content"]
                        return "No response generated"
                    
                    # Handle standard inference API response
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "No response generated")
                    return str(result)
                else:
                    error_msg = f"HuggingFace API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    
                    # Check for specific error types
                    if response.status_code == 503:
                        return "The model is currently loading. Please try again in a few moments."
                    elif response.status_code == 401:
                        return "Authentication failed. Please check your Hugging Face API token."
                    elif response.status_code == 429:
                        return "Rate limit exceeded. Please try again later or add an API token."
                    else:
                        return f"Error: {response.status_code} - Unable to get response from model."
                    
        except httpx.TimeoutError:
            logger.error("HuggingFace API timeout")
            return "Request timed out. The model might be loading or overloaded."
        except Exception as e:
            logger.error(f"HuggingFace Inference API error: {e}")
            return f"Error connecting to model: {str(e)}"
            
    @staticmethod
    async def analyze_advisory(
        model_name: str,
        prompt: str,
        api_token: Optional[str] = None,
        max_new_tokens: int = 500,
        temperature: float = 0.3
    ) -> str:
        """
        Use Hugging Face Inference API for advisory analysis.
        
        Args:
            model_name: HuggingFace model ID
            prompt: Analysis prompt
            api_token: Optional HuggingFace API token
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated analysis
        """
        api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        
        headers = {
            "Content-Type": "application/json",
        }
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "return_full_text": False,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "")
                    return str(result)
                else:
                    logger.error(f"HuggingFace API error: {response.status_code} - {response.text}")
                    raise Exception(f"HuggingFace API returned status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"HuggingFace Inference API error: {e}")
            raise