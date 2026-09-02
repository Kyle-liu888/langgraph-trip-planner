"""Portable structured-output invocation with explicit fallback strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel

from .capabilities import infer_capabilities
from .config import ModelConfig


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredOutputError(ValueError):
    """All configured structured-output strategies failed."""


@dataclass
class StructuredResult:
    parsed: BaseModel
    strategy: str
    raw_message: AIMessage | None = None
    strategy_errors: list[str] = field(default_factory=list)


def message_text(message: AIMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    if isinstance(message.content, list):
        parts: list[str] = []
        for item in message.content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return str(message.content or "")


def _is_capability_error(error: Exception) -> bool:
    if isinstance(error, (NotImplementedError, TypeError, AttributeError)):
        return True
    text = str(error).lower()
    markers = (
        "response_format",
        "json_schema",
        "function_calling",
        "tool_choice",
        "structured output",
        "not support",
        "unsupported",
    )
    return any(marker in text for marker in markers)


async def ainvoke_structured(
    model: BaseChatModel,
    model_config: ModelConfig,
    schema: type[SchemaT],
    messages: list[BaseMessage],
    *,
    text_parser: Callable[[str], dict[str, Any]],
    invocation_kwargs: dict[str, Any] | None = None,
) -> StructuredResult:
    """Invoke a model using native methods first and prompt parsing last."""
    errors: list[str] = []
    kwargs = invocation_kwargs or {}

    for method in infer_capabilities(model_config).structured_output_methods:
        try:
            if method == "prompt":
                raw = await model.ainvoke(messages, **kwargs)
                parsed = schema.model_validate(text_parser(message_text(raw)))
                return StructuredResult(parsed, method, raw, errors)

            runnable = model.with_structured_output(
                schema,
                method=method,
                include_raw=True,
            )
            result = await runnable.ainvoke(messages, **kwargs)
            parsing_error = result.get("parsing_error")
            if parsing_error:
                raise StructuredOutputError(str(parsing_error))
            parsed_value = result.get("parsed")
            if parsed_value is None:
                raise StructuredOutputError("模型没有返回结构化结果")
            parsed = parsed_value if isinstance(parsed_value, schema) else schema.model_validate(parsed_value)
            raw = result.get("raw")
            return StructuredResult(
                parsed=parsed,
                strategy=method,
                raw_message=raw if isinstance(raw, AIMessage) else None,
                strategy_errors=errors,
            )
        except StructuredOutputError as exc:
            errors.append(f"{method}: {exc}")
        except Exception as exc:
            if not _is_capability_error(exc):
                raise
            errors.append(f"{method}: {exc}")

    raise StructuredOutputError("; ".join(errors) or "没有可用的结构化输出策略")
