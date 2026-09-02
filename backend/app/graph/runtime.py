"""Dependencies injected into graph nodes at invocation time."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from ..config import Settings
from ..llm.config import ModelConfig


@dataclass
class PlannerRuntime:
    model: BaseChatModel
    model_config: ModelConfig
    context_builder: Any
    settings: Settings
