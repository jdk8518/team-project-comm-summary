import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_index_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI 문서 분석" in response.text

def test_full_pipeline_upload_save_search_edit_download():
    content = ("2026년 상반기 부서별 주요 업무보고\n\n1. 추진 배경 및 목적\n본 보고서는 2026년 상반기 부서별 주요 성과를 점검하고 AI Agent 기반 문서 분석 시스템 구축을 추진합니다.\n\n2. 주요 내용\n- 오는 2026년 8월 31일까지 MVP 구축을 완료할 예정입니다.\n- 홍길동 팀장 및 김철수 수석 참여 예정.").encode("utf-8")
    
    # 1. Tab 1: Upload & Analyze Document
    response = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("2026_업무보고.txt", content, "text/plain")}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    file_id = res_data["data"]["file_id"]

    # 2. Tab 1: Save Document (Original file saved to folder/filename & Summary saved to DB)
    target_folder = "temp/test_archive_output"
    target_filename = "2026_업무보고_아카이빙.txt"
    
    save_resp = client.post(
        f"/api/v1/documents/{file_id}/save",
        json={
            "folder_path": target_folder,
            "filename": target_filename,
            "document_overview": ["수정된 팩트 요약 1", "수정된 팩트 요약 2"]
        }
    )
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["success"] is True
    assert save_data["file_id"] == file_id

    # 3. Tab 2: DB Document Search
    search_resp = client.get("/api/v1/documents/search?keyword=업무보고")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total_count"] >= 1

    # 4. Tab 2: Edit Summary in DB
    update_resp = client.put(
        f"/api/v1/documents/{file_id}/summary",
        json={"overview_summary": ["DB 수정 요약문 1", "DB 수정 요약문 2"]}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["success"] is True

    # 5. Tab 2: Download Original File
    download_resp = client.get(f"/api/v1/documents/{file_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.content == content

def test_unsupported_file_extension():
    response = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("data.xlsx", b"test content", "application/vnd.ms-excel")}
    )
    assert response.status_code == 400
    assert "지원하지 않는 파일 형식" in response.json()["error"]["message"]

def test_empty_file_content():
    response = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("empty.txt", b"short text", "text/plain")}
    )
    assert response.status_code == 422
    assert "분석할 수 있는 텍스트 내용이 존재하지 않습니다" in response.json()["error"]["message"]
