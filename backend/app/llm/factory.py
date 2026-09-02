"""Construct LangChain chat models without leaking provider details to graph nodes."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from .config import ModelConfig


class ModelConfigurationError(RuntimeError):
    """The configured provider cannot be initialized."""


PROVIDER_ALIASES = {"openai_compatible": "openai"}


def create_chat_model(config: ModelConfig | None = None) -> BaseChatModel:
    """Create a standard LangChain chat model for any installed integration."""
    current = config or ModelConfig.from_settings()
    provider = PROVIDER_ALIASES.get(current.provider, current.provider)
    kwargs = dict(current.model_kwargs)
    kwargs.setdefault("temperature", current.temperature)
    kwargs.setdefault("timeout", current.timeout)
    kwargs.setdefault("max_retries", current.max_retries)
    if current.api_key:
        kwargs.setdefault("api_key", current.api_key.get_secret_value())
    if current.base_url:
        kwargs.setdefault("base_url", current.base_url)

    try:
        model = init_chat_model(
            model=current.model,
            model_provider=provider,
            **kwargs,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        package_hint = provider.replace("_", "-")
        raise ModelConfigurationError(
            f"模型供应商 {current.provider!r} 的 LangChain 集成未安装。"
            f"请安装对应的 langchain-{package_hint} 包。"
        ) from exc
    except Exception as exc:
        raise ModelConfigurationError(f"无法初始化模型 {current.display_name}: {exc}") from exc

    if not isinstance(model, BaseChatModel):
        raise ModelConfigurationError(f"{current.display_name} 没有返回 LangChain BaseChatModel")
    return model
