import pytest

from app.core.config import AIConfig, get_ai_config
from app import services


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("openai", "gpt-test"),
        ("google", "gemini-test"),
        ("deepseek", "deepseek-test"),
    ],
)
def test_ai_config_reads_provider_key_and_model_from_env(monkeypatch, provider, model):
    monkeypatch.setenv("AI_PROVIDER", provider)
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", model)

    config = get_ai_config()

    assert config.provider == provider
    assert config.api_key == "test-key"
    assert config.model == model


@pytest.mark.parametrize("provider", ["openai", "google", "deepseek"])
def test_llm_dispatch_supports_all_configured_providers(monkeypatch, provider):
    monkeypatch.setattr(services, "get_ai_config", lambda: AIConfig(provider, "test-key", "test-model"))
    monkeypatch.setattr(services, "_call_openai", lambda *args: ({"provider": "openai"}, None))
    monkeypatch.setattr(services, "_call_google", lambda *args: ({"provider": "google"}, None))
    monkeypatch.setattr(services, "_call_deepseek", lambda *args: ({"provider": "deepseek"}, None))

    result, error = services._call_llm_api("prompt", "system")

    assert error is None
    assert result == {"provider": provider}


def test_legacy_provider_key_is_not_used(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-key")

    config = get_ai_config()

    assert config.api_key is None
