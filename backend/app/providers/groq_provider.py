import json
import time
import re
import random
from typing import List, Dict, Any, Optional, Type, Callable
import groq
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.providers.base import (
    LLMProvider,
    ProviderResult,
    ProviderStructuredResult,
    ProviderToolResult,
    TokenUsage,
    ToolCallRequest
)

def make_groq_strict_schema(model_cls: Type[BaseModel]) -> Dict[str, Any]:
    """
    Recursively updates Pydantic JSON schema to comply with GroqCloud strict schema mode:
    1. Sets additionalProperties: False on every object (including in $defs).
    2. Ensures all defined properties are listed in required.
    """
    schema = model_cls.model_json_schema()

    def _apply_strict(node: Any):
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            node["additionalProperties"] = False
            if "properties" in node:
                node["required"] = list(node["properties"].keys())
        for k, v in list(node.items()):
            if isinstance(v, dict):
                _apply_strict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _apply_strict(item)

    _apply_strict(schema)
    return schema

def _execute_with_backoff(operation: Callable, max_attempts: int = 3, initial_wait: float = 2.0) -> Any:
    """Executes an API call with exponential backoff on rate limits (HTTP 429)."""
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except groq.RateLimitError as e:
            if attempt == max_attempts:
                logger.error(f"Rate limit exceeded after {max_attempts} attempts: {e}")
                raise
            jitter = random.uniform(0.1, 0.5)
            wait_time = initial_wait * (2 ** (attempt - 1)) + jitter
            # Check for 'try again in X ms' or 'X s' in message
            match = re.search(r"try again in (\d+)(ms|s)", str(e), re.IGNORECASE)
            if match:
                val, unit = int(match.group(1)), match.group(2).lower()
                parsed_wait = (val / 1000.0) if unit == "ms" else val
                wait_time = max(wait_time, parsed_wait + 1.0 + jitter)
            logger.warning(f"Groq 429 RateLimit. Waiting {wait_time:.1f}s before retry ({attempt}/{max_attempts})...")
            time.sleep(wait_time)
        except Exception as e:
            # Check if 429 code is in error message
            if "429" in str(e) and attempt < max_attempts:
                wait_time = initial_wait * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                logger.warning(f"429 detected in exception. Waiting {wait_time:.1f}s before retry ({attempt}/{max_attempts})...")
                time.sleep(wait_time)
            else:
                raise

class GroqProvider(LLMProvider):
    """Production provider integrating directly with the GroqCloud API free tier."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.GROQ_API_KEY
        if not key:
            raise ValueError("GROQ_API_KEY is not configured.")
        self.client = groq.Groq(api_key=key)
        self.gen_model = settings.GROQ_MODEL
        self.judge_model = settings.GROQ_JUDGE_MODEL

    def _extract_usage(self, response: Any) -> TokenUsage:
        if hasattr(response, "usage") and response.usage:
            return TokenUsage(
                prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(response.usage, "total_tokens", 0) or 0
            )
        return TokenUsage()

    def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 3000
    ) -> ProviderResult:
        target_model = model or self.gen_model
        start_time = time.time()

        def _call():
            return self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

        resp = _execute_with_backoff(_call)
        latency = (time.time() - start_time) * 1000.0
        content = resp.choices[0].message.content or ""
        return ProviderResult(
            content=content,
            token_usage=self._extract_usage(resp),
            latency_ms=latency,
            model=target_model
        )

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Type[BaseModel],
        model: Optional[str] = None,
        temperature: float = 0.1
    ) -> ProviderStructuredResult:
        target_model = model or self.judge_model
        start_time = time.time()

        strict_schema = make_groq_strict_schema(schema)
        req_schema = {
            "name": schema.__name__,
            "strict": True,
            "schema": strict_schema
        }

        def _call_strict():
            return self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_schema", "json_schema": req_schema}
            )

        try:
            resp = _execute_with_backoff(_call_strict)
            raw = resp.choices[0].message.content or "{}"
            parsed_data = json.loads(raw)
            if isinstance(parsed_data, list):
                parsed_data = {"checkpoints": parsed_data, "evaluator_summary": "Evaluation completed."}
            validated = schema.model_validate(parsed_data)
            latency = (time.time() - start_time) * 1000.0
            return ProviderStructuredResult(
                parsed=validated,
                raw_content=raw,
                token_usage=self._extract_usage(resp),
                latency_ms=latency,
                model=target_model
            )
        except groq.BadRequestError as e:
            err_msg = str(e).lower()
            if not any(kw in err_msg for kw in ["json_schema", "schema", "response_format", "not supported"]):
                # Permanent bad request unrelated to schema parameter
                raise
            logger.warning(f"Strict json_schema mode unsupported by endpoint, attempting json_object fallback: {e}")
            fallback_messages = list(messages)
            if fallback_messages and "json" not in fallback_messages[0]["content"].lower():
                fallback_messages[0] = {
                    "role": fallback_messages[0]["role"],
                    "content": fallback_messages[0]["content"] + " Respond with a valid json object."
                }

            def _call_json():
                return self.client.chat.completions.create(
                    model=target_model,
                    messages=fallback_messages,
                    temperature=temperature,
                    response_format={"type": "json_object"}
                )

            resp = _execute_with_backoff(_call_json)
            raw = resp.choices[0].message.content or "{}"
            parsed_data = json.loads(raw)
            if isinstance(parsed_data, list):
                parsed_data = {"checkpoints": parsed_data, "evaluator_summary": "Evaluation completed."}
            elif isinstance(parsed_data, dict) and "checkpoints" not in parsed_data:
                # If wrapped under a key like 'evaluation' or 'results'
                for k in ["evaluation", "results", "rubric", "checks"]:
                    if k in parsed_data and isinstance(parsed_data[k], list):
                        parsed_data = {"checkpoints": parsed_data[k], "evaluator_summary": "Evaluation completed."}
                        break
            validated = schema.model_validate(parsed_data)
            latency = (time.time() - start_time) * 1000.0
            return ProviderStructuredResult(
                parsed=validated,
                raw_content=raw,
                token_usage=self._extract_usage(resp),
                latency_ms=latency,
                model=target_model
            )

    def call_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> ProviderToolResult:
        target_model = model or self.gen_model
        start_time = time.time()

        def _call():
            return self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature
            )

        resp = _execute_with_backoff(_call)
        latency = (time.time() - start_time) * 1000.0
        msg = resp.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {"query": tc.function.arguments}
                tool_calls.append(
                    ToolCallRequest(
                        call_id=tc.id,
                        function_name=tc.function.name,
                        arguments=args
                    )
                )
        return ProviderToolResult(
            content=msg.content,
            tool_calls=tool_calls,
            token_usage=self._extract_usage(resp),
            latency_ms=latency,
            model=target_model
        )
