"""
app/agents/document_agent.py
AI Workflow & Agent Layer

LangChain/LangGraph 기반 AI Agent 호출 레이어.
현재 MVP 단계에서는 app.services의 LLM 호출 함수를 re-export하며,
향후 LangGraph 상태 머신 도입 시 이 모듈에서 Agent 그래프를 정의합니다.

입력:  file_id (str), raw_text (str), structured_content (dict), analysis_data (AnalysisData)
출력:  AnalysisData, SummaryData, ValidationData
"""
from app.services import (
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
