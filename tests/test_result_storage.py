from datetime import date
from types import SimpleNamespace

import pytest

from app.core.exceptions import DocumentProcessingError
from app.services.result_storage import build_preview, save_result


def sample_result() -> dict:
    return {"status": "SUCCESS", "document": {"reference_date": "2026-07-25", "reference_date_source": "문서 기재일"}, "analysis": {"title": "성명: 홍길동", "organization": "기관", "department": "총무부", "table_of_contents": ["본문"], "key_sentences": ["일정을 확정한다."], "keywords": ["일정"], "numerical_values": ["2026-07-25"], "conditions": [], "decisions": ["일정 확정"]}, "summary": {"background": "배경", "main_content": "내용", "conclusion": "결론", "follow_up_actions": [], "review_items": []}, "verification": {"passed": True, "issues": [], "revision_instruction": "원문 근거 유지"}}


def current_api_result() -> dict:
    return {
        "status": "SUCCESS",
        "document": {"reference_date": "2026-07-27", "reference_date_source": "파일 생성일"},
        "analysis": {
            "title": "업무보고", "organization": "기관", "department": "부서",
            "table_of_contents": ["본문"], "key_sentences": ["핵심 문장"], "keywords": ["업무"],
            "numerical_values": [], "conditions": [], "decisions": [], "review_items": ["최종 검토 필요"],
        },
        "summary": {
            "document_overview": "문서 개요", "document_purpose": "문서 목적",
            "conclusion_or_key_message": "핵심 메시지", "main_contents": ["주요 내용"],
        },
        "verification": {"passed": True, "issues": [], "revision_instruction": "원문 근거 유지"},
    }


def test_preview_requires_known_document_type() -> None:
    with pytest.raises(DocumentProcessingError): build_preview(sample_result(), "기타")


def test_save_requires_confirmation() -> None:
    preview = build_preview(sample_result(), "회의록", date(2026, 7, 25))
    with pytest.raises(DocumentProcessingError): save_result(sample_result(), preview, False, True)


def test_save_writes_masked_markdown_to_result_directory(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.services.result_storage.settings", SimpleNamespace(output_directories={"회의록": tmp_path, "공문": tmp_path, "보고서": tmp_path}))
    preview = build_preview(sample_result(), "회의록", date(2026, 7, 25))
    saved = save_result(sample_result(), preview, True, True)
    content = (tmp_path / saved["file_name"]).read_text(encoding="utf-8")
    assert saved["saved"] is True and "홍길동" not in content and "문서 분석 결과" in content


def test_save_writes_current_analysis_and_summary_response(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.services.result_storage.settings", SimpleNamespace(output_directories={"회의록": tmp_path}))
    result = current_api_result()
    preview = build_preview(result, "회의록", date(2026, 7, 27))
    saved = save_result(result, preview, True, True)
    content = (tmp_path / saved["file_name"]).read_text(encoding="utf-8")
    assert "문서 개요" in content and "최종 검토 필요" in content
