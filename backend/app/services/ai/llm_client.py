import json
import logging
import re
import time
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIClientService:
    """Shared, production-grade asynchronous OpenAI / LLM client service.
    
    Provides structured JSON chat completions with automatic markdown fence stripping,
    graceful offline/test fallback handling, and token / latency tracking.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 45.0,
    ):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL or "gpt-4o"
        self.base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout
        self.last_latency_ms: float = 0.0
        self.last_usage: Dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    @staticmethod
    def clean_json_text(text: str) -> str:
        """Strips markdown code fences and surrounding commentary from LLM output.
        
        Handles:
          - ```json ... ```
          - ``` ... ```
          - Surrounding conversational preamble or trailer around outermost JSON `{...}` or `[...]`
        """
        cleaned = text.strip()

        # Check for standard markdown code blocks first
        code_fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.IGNORECASE)
        if code_fence_match:
            candidate = code_fence_match.group(1).strip()
            # If the candidate parses as JSON or starts with { / [, return it
            if candidate.startswith(("{", "[")):
                return candidate

        # If no code fence matched or candidate didn't match JSON structure,
        # extract outermost JSON object or array
        obj_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if obj_match:
            return obj_match.group(1).strip()

        # Fallback strip standard leading/trailing backticks
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimates token count for English, Hindi, and Hinglish text.
        
        Uses rule of thumb ~3.5 chars per token for Latin script and ~2 chars per token
        for Devanagari script.
        """
        if not text:
            return 0
        # Count devanagari characters (Unicode range \u0900-\u097F)
        devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))
        other_count = len(text) - devanagari_count

        est = (other_count / 3.8) + (devanagari_count / 2.0)
        return max(1, int(round(est)))

    async def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        fallback_data: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Executes chat completion with JSON mode, parsing, and tracking."""
        start_time = time.perf_counter()
        active_model = model or self.model
        prompt_tokens = self.estimate_tokens(system_prompt + " " + user_prompt)

        # 1. Fallback handling when OPENAI_API_KEY is missing or empty
        if not self.api_key or not self.api_key.strip():
            logger.info("OPENAI_API_KEY is not configured. Utilizing fallback response.")
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            completion_tokens = self.estimate_tokens(json.dumps(fallback_data or {}))
            self.last_latency_ms = latency_ms
            self.last_usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            if fallback_data is not None:
                return fallback_data
            return {}

        # 2. Live HTTP OpenAI API call
        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        call_timeout = timeout or self.timeout

        try:
            async with httpx.AsyncClient(timeout=call_timeout) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.last_latency_ms = latency_ms

            if res.status_code != 200:
                logger.error(f"OpenAI API error ({res.status_code}): {res.text}")
                if fallback_data is not None:
                    logger.warning("Returning fallback data due to OpenAI API status error.")
                    return fallback_data
                res.raise_for_status()

            data = res.json()
            usage = data.get("usage", {})
            self.last_usage = {
                "prompt_tokens": usage.get("prompt_tokens", prompt_tokens),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", prompt_tokens),
            }

            raw_content = data["choices"][0]["message"]["content"]
            cleaned_json = self.clean_json_text(raw_content)
            parsed = json.loads(cleaned_json)
            return parsed

        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.last_latency_ms = latency_ms
            logger.exception(f"Exception during LLM chat completion: {exc}")
            if fallback_data is not None:
                logger.warning("Returning fallback data due to LLM call exception.")
                return fallback_data
            raise exc
