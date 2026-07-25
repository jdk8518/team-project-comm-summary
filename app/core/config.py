"""
app/core/config.py
환경 변수와 AI 프로바이더 설정값을 한 곳에서 관리합니다.
services.py 내 동일한 환경 변수 읽기 코드가 3회 반복되던 것을 제거합니다.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AIConfig:
    """AI 프로바이더 설정을 담는 데이터 클래스."""
    provider: str
    api_key: str | None
    model: str


SUPPORTED_AI_PROVIDERS = ("openai", "google", "deepseek", "mock")
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "google": "gemini-2.0-flash",
    "deepseek": "deepseek-chat",
    "mock": "mock",
}


def get_ai_config() -> AIConfig:
    """
    환경 변수에서 AI 프로바이더 설정을 읽어 AIConfig를 반환합니다.
    """
    provider = os.getenv("AI_PROVIDER", "openai").lower().strip()
    api_key = os.getenv("AI_API_KEY", "").strip() or None
    model = os.getenv("AI_MODEL", "").strip() or DEFAULT_MODELS.get(provider, "")
    return AIConfig(provider=provider, api_key=api_key, model=model)


def is_api_key_valid(api_key: str | None) -> bool:
    """API 키가 실제 값인지(플레이스홀더 제외) 확인합니다."""
    return bool(api_key and api_key not in {"your_api_key_here", ""})


def is_supported_provider(provider: str) -> bool:
    return provider.lower().strip() in SUPPORTED_AI_PROVIDERS
