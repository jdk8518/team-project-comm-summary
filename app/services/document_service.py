"""
app/services/document_service.py
Application Service Pipeline Orchestrator Layer

업로드, 파싱, AI분석/요약/검증, 아카이빙 전체 흐름을 오케스트레이션합니다.
현재 MVP 단계에서 실제 파이프라인 로직은 app/api/routes/documents.py 에서 직접 호출되며,
향후 이 모듈에서 파이프라인 함수를 독립적으로 제공할 수 있습니다.

입력:  file_bytes (bytes), filename (str), department (str)
출력:  IntegratedResultData
"""
from app.services._service_impl import (
    run_document_analysis,
    run_document_summarization,
    run_document_validation,
    recommend_folder,
)

__all__ = [
    "run_document_analysis",
    "run_document_summarization",
    "run_document_validation",
    "recommend_folder",
]
