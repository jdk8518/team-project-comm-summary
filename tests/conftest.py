import pytest


@pytest.fixture(autouse=True)
def disable_external_ai_calls(monkeypatch):
    """Keep the test suite deterministic and prevent calls to configured .env providers."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_MODEL", "mock")
