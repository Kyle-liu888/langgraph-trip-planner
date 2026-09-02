"""Provider-neutral model configuration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from ..config import Settings, get_settings


StructuredOutputMode = Literal["auto", "json_schema", "function_calling", "json_mode", "prompt"]
ThinkingMode = Literal["auto", "enabled", "disabled"]


class ModelConfig(BaseModel):
    """Everything needed to construct one LangChain chat model."""

    model_config = ConfigDict(frozen=True)
    provider: str = "openai_compatible"
    model: str
    api_key: SecretStr | None = None
    base_url: str | None = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout: float = Field(default=90, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    structured_output_mode: StructuredOutputMode = "auto"
    thinking_mode: ThinkingMode = "auto"
    model_kwargs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider", "model")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        aliases = {
            "claude": "anthropic",
            "gemini": "google_genai",
            "google": "google_genai",
            "openai-compatible": "openai_compatible",
        }
        normalized = value.lower().replace("-", "_")
        return aliases.get(normalized, normalized)

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ModelConfig":
        current = settings or get_settings()
        return cls(
            provider=current.llm_provider,
            model=current.llm_model,
            api_key=current.llm_api_key,
            base_url=current.llm_base_url,
            temperature=current.llm_temperature,
            timeout=current.llm_timeout,
            max_retries=current.llm_max_retries,
            structured_output_mode=current.llm_structured_output_mode,
            thinking_mode=current.llm_thinking_mode,
            model_kwargs=current.llm_model_kwargs,
        )

    @property
    def display_name(self) -> str:
        return f"{self.provider}:{self.model}"
