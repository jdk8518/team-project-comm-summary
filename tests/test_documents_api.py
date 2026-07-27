from fastapi.testclient import TestClient

from app.main import app
from app.services.analysis_session import get_session, save_session

client = TestClient(app)


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_home_page_has_mvp_sections() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "문서 파일 업로드" in response.text and "검증 결과" in response.text
    assert "문서 저장" in response.text and "분석 결과 문서 저장" in response.text
    assert "문서특성" in response.text and "업로드 화면으로 이동" in response.text


def test_unsupported_file_is_rejected_before_ai_call() -> None:
    assert client.post("/api/v1/documents/extract", files={"file": ("malware.exe", b"x", "application/octet-stream")}).status_code == 422


def test_folder_document_list_returns_supported_documents() -> None:
    response = client.get("/api/v1/documents/folder", params={"folder_path": "other_docs"})
    assert response.status_code == 200
    assert all(item["file_type"] in {"PDF", "DOC", "DOCX", "HWP", "HWPX", "PPT", "PPTX", "TXT"} for item in response.json()["documents"])


def test_missing_folder_is_rejected() -> None:
    assert client.get("/api/v1/documents/folder", params={"folder_path": "not-a-folder"}).status_code == 400


def test_text_extraction_api_does_not_require_openai_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/documents/extract", files={"file": ("meeting.txt", "2026-07-25 회의 결과", "text/plain")})
    assert response.status_code == 200 and response.json()["text_preview"] == "2026-07-25 회의 결과"


def test_missing_openai_key_is_reported(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    document_id = "missing-openai-key"
    save_session(document_id, {"document_id": document_id, "status": "EXTRACTED", "document": {"file_name": "meeting.txt"}, "extracted_text": "회의 결과"})
    response = client.post(f"/api/v1/documents/{document_id}/analyze", json={"categories": ["회의록"]})
    assert response.status_code == 503


def test_analysis_response_masks_sensitive_values(monkeypatch) -> None:
    def fake_workflow(document_id, document, text, categories):
        return {"document_id": document_id, "status": "SUMMARIZED", "document": document | {"title": "성명: 홍길동", "organization": "기관", "department": "총무부"}, "analysis": {"title": "성명: 홍길동", "department": "총무부", "keywords": ["010-1234-5678"]}, "summary": {"document_overview": "개요", "document_purpose": "목적", "main_contents": [], "conclusion_or_key_message": "결론"}}
    monkeypatch.setattr("app.api.routes.documents.analyze_extracted_document", fake_workflow)
    extracted = client.post("/api/v1/documents/extract", files={"file": ("meeting.txt", "회의 결과", "text/plain")})
    response = client.post(f"/api/v1/documents/{extracted.json()['document_id']}/analyze", json={"categories": ["회의록"]})
    assert response.status_code == 200
    assert response.json()["analysis"]["keywords"] == ["010-1234-XXXX"]


def test_analysis_returns_summary_without_verification(monkeypatch) -> None:
    document_id = "analysis-only"
    save_session(document_id, {"document_id": document_id, "status": "EXTRACTED", "document": {"file_name": "meeting.txt"}, "extracted_text": "회의 결과"})
    monkeypatch.setattr("app.api.routes.documents.analyze_extracted_document", lambda doc_id, document, text, categories: {"document_id": doc_id, "status": "SUMMARIZED", "document": document, "analysis": {"title": "회의 결과", "keywords": []}, "summary": {"document_overview": "개요", "document_purpose": "목적", "main_contents": [], "conclusion_or_key_message": "결론"}})
    response = client.post(f"/api/v1/documents/{document_id}/analyze", json={"categories": ["회의록"]})
    assert response.status_code == 200
    assert response.json()["status"] == "SUMMARIZED"
    assert response.json()["summary"]["document_purpose"] == "목적"
    assert "verification" not in response.json()


def test_save_requires_completed_analysis() -> None:
    extracted = client.post("/api/v1/documents/extract", files={"file": ("meeting.txt", "회의 결과", "text/plain")})
    response = client.post(f"/api/v1/documents/{extracted.json()['document_id']}/save-preview", json={"document_type": "회의록"})
    assert response.status_code == 400


def test_verification_api_requires_preceding_data() -> None:
    assert client.post("/api/v1/documents/verify", json={}).status_code == 400


def test_verification_uses_prior_document_session(monkeypatch) -> None:
    document_id = "verification-session"
    save_session(document_id, {"document_id": document_id, "status": "SUMMARIZED", "extracted_text": "원문", "analysis": {"title": "분석"}, "summary": {"document_overview": "요약"}})
    captured = {}

    def fake_verify(source_text, analysis, summary):
        captured.update({"source_text": source_text, "analysis": analysis, "summary": summary})
        return {"passed": True, "issues": [], "revision_instruction": "검토 완료"}

    monkeypatch.setattr("app.api.routes.documents.verify_document", fake_verify)
    response = client.post("/api/v1/documents/verify", json={"document_id": document_id})
    assert response.status_code == 200
    assert captured == {"source_text": "원문", "analysis": {"title": "분석"}, "summary": {"document_overview": "요약"}}
    assert get_session(document_id)["status"] == "SUCCESS"
    assert get_session(document_id)["verification"] == response.json()
