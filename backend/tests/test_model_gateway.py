from unittest.mock import Mock, patch

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr

from app.llm.capabilities import infer_capabilities
from app.llm.config import ModelConfig
from app.llm.factory import create_chat_model


def test_openai_compatible_maps_to_openai_provider() -> None:
    fake_model = Mock(spec=BaseChatModel)
    config = ModelConfig(
        provider="openai_compatible",
        model="custom-chat",
        api_key=SecretStr("test-key"),
        base_url="https://models.example.com/v1",
    )

    with patch("app.llm.factory.init_chat_model", return_value=fake_model) as init_model:
        result = create_chat_model(config)

    assert result is fake_model
    init_model.assert_called_once_with(
        model="custom-chat",
        model_provider="openai",
        temperature=0.2,
        timeout=180.0,
        max_retries=0,
        api_key="test-key",
        base_url="https://models.example.com/v1",
    )


def test_arbitrary_provider_is_forwarded_without_graph_changes() -> None:
    fake_model = Mock(spec=BaseChatModel)
    config = ModelConfig(
        provider="bedrock_converse",
        model="anthropic.claude-model-v1:0",
        model_kwargs={"region_name": "ap-southeast-1"},
    )

    with patch("app.llm.factory.init_chat_model", return_value=fake_model) as init_model:
        create_chat_model(config)

    assert init_model.call_args.kwargs["model_provider"] == "bedrock_converse"
    assert init_model.call_args.kwargs["region_name"] == "ap-southeast-1"


def test_deepseek_auto_mode_uses_conservative_fallback_order() -> None:
    config = ModelConfig(provider="deepseek", model="deepseek-chat")
    capabilities = infer_capabilities(config)
    assert capabilities.structured_output_methods == ("json_mode", "prompt")
    assert capabilities.supports_thinking_toggle is True
