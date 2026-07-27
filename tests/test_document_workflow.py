from types import SimpleNamespace

import pytest

from app.agents.document_workflow import analyze_extracted_document
from app.core.exceptions import DocumentProcessingError
from app.services.document_analysis import analyze_document
from app.services.summarization import create_summary
from app.services.verification import verify_document


def analysis_result() -> dict:
    return {
        "title": "회의 결과", "organization": "기관", "department": "총무부", "recommended_category": "회의록",
        "category_reason": "회의 내용을 기록함", "subject": "일정", "purpose": "공유",
        "table_of_contents": ["회의 안건"], "key_points": ["일정을 확정함"], "key_sentences": ["일정을 확정한다."],
        "keywords": ["일정"], "numerical_values": ["2026-07-25"], "conditions": ["참석자 확인 후"], "schedules": ["2026-07-25"],
        "decisions": ["일정 확정"], "evidence": ["일정 확정"], "review_items": [],
    }


def summary_result() -> dict:
    return {"document_overview": "회의 일정 논의", "document_purpose": "일정 공유", "main_contents": ["일정 확정"], "conclusion_or_key_message": "일정을 확정함"}


def test_workflow_returns_analysis_and_summary(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.document_workflow.analyze_document", lambda text, categories: analysis_result())
    monkeypatch.setattr("app.agents.document_workflow.create_summary", lambda text, analysis: summary_result())
    result = analyze_extracted_document("doc-1", {"file_name": "meeting.txt"}, "2026-07-25 회의 결과", ["회의록"])
    assert result["status"] == "SUMMARIZED"
    assert result["document"]["title"] == "회의 결과"
    assert result["analysis"]["recommended_category"] == "회의록"
    assert result["summary"]["conclusion_or_key_message"] == "일정을 확정함"
    assert "verification" not in result


def test_invalid_ai_response_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr("app.services.document_analysis.request_document_analysis", lambda text, categories: {"title": "불완전 응답"})
    with pytest.raises(DocumentProcessingError):
        analyze_document("회의 결과", ["회의록"])


def test_missing_openai_key_is_rejected(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(DocumentProcessingError):
        analyze_document("회의 결과", ["회의록"])


def test_invalid_summary_response_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr("app.services.summarization.request_document_summary", lambda text, analysis: {"document_overview": "개요"})
    with pytest.raises(DocumentProcessingError):
        create_summary("원문", analysis_result())


def test_verification_requires_all_preceding_results() -> None:
    with pytest.raises(DocumentProcessingError):
        verify_document("", analysis_result(), summary_result())
    with pytest.raises(DocumentProcessingError):
        verify_document("원문", {}, summary_result())
    with pytest.raises(DocumentProcessingError):
        verify_document("원문", analysis_result(), {})


def test_verification_returns_only_structured_review_items(monkeypatch) -> None:
    mocked = {
        "passed": False,
        "issues": [{
            "category": "수치와 날짜", "reason": "요약 날짜가 원문과 다릅니다.",
            "source_evidence": ["일정은 2026-07-25"], "human_check": "날짜를 확인하세요.",
        }],
        "revision_instruction": "원문 근거와 비교해 검토하세요.",
    }
    monkeypatch.setattr("app.services.verification.request_document_verification", lambda source, analysis, summary: mocked)
    result = verify_document("일정은 2026-07-25", analysis_result(), summary_result())
    assert result["passed"] is False
    assert result["issues"][0]["human_check"] == "날짜를 확인하세요."


def test_invalid_verification_response_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr("app.services.verification.request_document_verification", lambda source, analysis, summary: {"passed": True, "issues": []})
    with pytest.raises(DocumentProcessingError):
        verify_document("원문", analysis_result(), summary_result())


def test_long_document_uses_chunk_analysis_and_integration(monkeypatch) -> None:
    calls = {"chunk": 0, "integrate": 0}
    def fake_chunk(text: str, categories: list[str]) -> dict:
        calls["chunk"] += 1
        return analysis_result()
    def fake_integration(results: list[dict], categories: list[str]) -> dict:
        calls["integrate"] += 1
        return analysis_result()
    monkeypatch.setattr("app.services.document_analysis.settings", SimpleNamespace(max_llm_input_chars=1000, chunk_overlap_chars=0, max_analysis_chunks=10))
    monkeypatch.setattr("app.services.document_analysis.request_document_analysis", fake_chunk)
    monkeypatch.setattr("app.services.document_analysis.request_integrated_analysis", fake_integration)
    result = analyze_document("가나다라마바사" * 400, ["회의록"])
    assert calls["chunk"] >= 2 and calls["integrate"] >= 1
    assert result["long_document_policy"]["chunk_count"] == calls["chunk"]
