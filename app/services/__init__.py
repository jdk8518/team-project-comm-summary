"""
app/services/__init__.py
Application Services 패키지 초기화.

기존 app/services.py 코드를 _service_impl.py로 이동하고,
이 __init__.py가 모든 공개 함수를 re-export하여 하위 호환성을 유지합니다.

- test_ai_config.py: from app import services  (services.run_document_analysis 등 사용)
- app/api/routes/documents.py: from app.services import run_document_analysis, ...
"""
from app.services._service_impl import (
    run_document_analysis,
    run_document_summarization,
    run_document_validation,
    recommend_department,
    recommend_folder,
    _call_llm_api,
    _call_openai,
    _call_deepseek,
    _call_openai_compatible,
    _call_google,
    _build_analysis_prompt,
    _parse_analysis_response,
    _analysis_fallback,
    _build_summary_prompt,
    _parse_summary_response,
    _summary_fallback,
    _build_validation_prompt,
    _parse_validation_response,
    _validation_fallback,
)
# monkeypatch.setattr(services, 'get_ai_config', ...) 호환성 유지
from app.core.config import get_ai_config, is_api_key_valid  # noqa: F401

__all__ = [
    "run_document_analysis",
    "run_document_summarization",
    "run_document_validation",
    "recommend_department",
    "recommend_folder",
]
