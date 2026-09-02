"""Model capability hints used to choose safe output strategies."""

from dataclasses import dataclass

from .config import ModelConfig


@dataclass(frozen=True)
class ModelCapabilities:
    structured_output_methods: tuple[str, ...]
    supports_thinking_toggle: bool = False


def infer_capabilities(config: ModelConfig) -> ModelCapabilities:
    """Return a conservative ordered strategy list for a configured model."""
    if config.structured_output_mode != "auto":
        return ModelCapabilities(
            structured_output_methods=(config.structured_output_mode,),
            supports_thinking_toggle=config.provider == "deepseek",
        )

    provider_methods = {
        "openai": ("json_schema", "function_calling", "json_mode", "prompt"),
        "azure_openai": ("json_schema", "function_calling", "json_mode", "prompt"),
        "anthropic": ("function_calling", "prompt"),
        "google_genai": ("json_schema", "function_calling", "prompt"),
        "deepseek": ("json_mode", "prompt"),
        "ollama": ("json_schema", "json_mode", "prompt"),
        "openai_compatible": ("json_mode", "prompt"),
    }
    return ModelCapabilities(
        structured_output_methods=provider_methods.get(config.provider, ("prompt",)),
        supports_thinking_toggle=config.provider == "deepseek",
    )
