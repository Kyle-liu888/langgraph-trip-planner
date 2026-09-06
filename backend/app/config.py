"""Application configuration loaded from ``backend/.env``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime settings with provider-neutral LLM names."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LangGraph 智能旅行助手"
    app_version: str = "2.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:3000"
    )

    amap_api_key: SecretStr | None = None
    unsplash_access_key: SecretStr | None = None
    unsplash_secret_key: SecretStr | None = None

    llm_provider: str = "openai_compatible"
    llm_model: str = Field(
        default="deepseek-chat",
        validation_alias=AliasChoices("LLM_MODEL", "LLM_MODEL_ID"),
    )
    llm_api_key: SecretStr | None = None
    llm_base_url: str | None = None
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_timeout: float = Field(default=180, gt=0)
    llm_max_retries: int = Field(default=0, ge=0, le=10)
    llm_streaming: bool = True
    llm_progress_interval: float = Field(default=10, gt=0, le=60)
    llm_structured_output_mode: str = "auto"
    llm_thinking_mode: str = "auto"
    llm_model_kwargs: dict[str, Any] = Field(default_factory=dict)

    planner_max_attempts: int = Field(default=3, ge=1, le=10)
    planner_request_timeout: int = Field(default=600, gt=0)
    planner_enable_rerank: bool = True
    planner_rerank_candidate_count: int = Field(default=3, ge=1, le=10)
    planner_rerank_temperature_step: float = Field(default=0.08, ge=0, le=1)
    log_level: str = "INFO"
    log_format: str = "console"
    log_file_enabled: bool = True
    log_dir: Path = BACKEND_DIR / "logs"
    database_url: SecretStr | None = None
    session_cookie_secure: bool = False
    daily_trip_limit: int = Field(default=3, ge=1)
    max_concurrent_runs: int = Field(default=2, ge=1, le=8)
    max_resume_attempts: int = Field(default=3, ge=0, le=10)
    sse_heartbeat_seconds: float = Field(default=15, ge=1, le=60)

    def get_cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def secret_value(self, field_name: str) -> str:
        value = getattr(self, field_name, None)
        return value.get_secret_value() if isinstance(value, SecretStr) else ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def validate_config(settings: Settings | None = None) -> bool:
    current = settings or get_settings()
    errors: list[str] = []
    if not current.secret_value("amap_api_key"):
        errors.append("AMAP_API_KEY 未配置")
    if current.llm_provider.lower() not in {"ollama", "fake"} and not current.secret_value("llm_api_key"):
        errors.append("LLM_API_KEY 未配置")
    if not current.llm_model.strip():
        errors.append("LLM_MODEL 未配置")
    if errors:
        raise ValueError("配置错误:\n" + "\n".join(f"  - {item}" for item in errors))
    return True


def print_config(settings: Settings | None = None) -> None:
    current = settings or get_settings()
    print(f"应用名称: {current.app_name}")
    print(f"版本: {current.app_version}")
    print(f"服务器: {current.host}:{current.port}")
    print(f"高德地图 API Key: {'已配置' if current.secret_value('amap_api_key') else '未配置'}")
    print(f"LLM Provider: {current.llm_provider}")
    print(f"LLM Model: {current.llm_model}")
    print(f"LLM API Key: {'已配置' if current.secret_value('llm_api_key') else '未配置'}")
    print(f"LLM Base URL: {current.llm_base_url or '供应商默认地址'}")
    print(f"结构化输出模式: {current.llm_structured_output_mode}")
    print(f"日志级别: {current.log_level}")
