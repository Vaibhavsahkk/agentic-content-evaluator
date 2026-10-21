from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ProviderResult(BaseModel):
    content: str
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    model: str = ""

class ProviderStructuredResult(BaseModel):
    parsed: Any
    raw_content: str
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    model: str = ""

class ToolCallRequest(BaseModel):
    call_id: str
    function_name: str
    arguments: Dict[str, Any]

class ProviderToolResult(BaseModel):
    content: Optional[str] = None
    tool_calls: List[ToolCallRequest] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    model: str = ""

class LLMProvider(ABC):
    """Abstract interface for LLM interaction decoupling application logic from SDK details."""

    @abstractmethod
    def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 3000
    ) -> ProviderResult:
        pass

    @abstractmethod
    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Type[BaseModel],
        model: Optional[str] = None,
        temperature: float = 0.1
    ) -> ProviderStructuredResult:
        pass

    @abstractmethod
    def call_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> ProviderToolResult:
        pass
