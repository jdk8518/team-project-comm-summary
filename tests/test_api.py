import os
import re
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import db

client = TestClient(app)

FULL_DOC_CONTENT = (
    "2026년 상반기 부서별 주요 업무보고\n\n"
    "1. 추진 배경 및 목적\n"
    "본 보고서는 2026년 상반기 부서별 주요 성과를 점검하고 "
    "AI Agent 기반 문서 분석 시스템 구축을 추진합니다.\n\n"
    "2. 주요 내용\n"
    "- 오는 2026년 8월 31일까지 MVP 구축을 완료할 예정입니다.\n"
    "- 홍길동 팀장 및 김철수 수석 참여 예정."
).encode("utf-8")

def test_dashboard_html_disables_stale_javascript_cache():
    res = client.get("/")
    assert res.status_code == 200
    assert "no-store" in res.headers.get("cache-control", "")


def test_result_endpoint_handles_unsaved_document_without_null_archiving_fields():
    """루트 검색에서 노출되는 미저장 문서도 상세 수정 화면용 JSON을 반환해야 한다."""
    analyzed = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("unsaved-root.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert analyzed.status_code == 200, analyzed.text
    file_id = analyzed.json()["data"]["file_id"]

    doc = db.get_document_by_id(file_id)
    doc["saved_folder"] = None
    doc["saved_filename"] = None
    db.save_doc_to_sqlite(doc)

    result = client.get(f"/api/v1/documents/{file_id}/result")
    assert result.status_code == 200, result.text
    assert result.json()["data"]["archiving_info"]["recommended_folder"]


def test_department_recommendation_returns_registered_candidates():
    analyzed = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("department-recommend.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert analyzed.status_code == 200, analyzed.text
    file_id = analyzed.json()["data"]["file_id"]

    response = client.post(
        f"/api/v1/documents/{file_id}/recommend-department",
        json={"summary": ["부서 업무보고"], "purpose": "REPORT", "message": "검토 필요", "keywords": {}},
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["recommendations"], list)

# ============================================================
# 전체 12단계 MVP 파이프라인 통합 테스트
# ============================================================
def test_full_12step_mvp_pipeline():
    """
    1.  문서 한 개 입력
    2.  파일 형식·내용·크기 검증 (내부 처리)
    3.  PDF·DOCX·TXT·PPTX·HWPX 텍스트 추출 (내부 처리)
    4.  AI 문서 분석 (내부 처리)
    5.  AI 요약 생성 (내부 처리)
    6.  원문과 요약 결과 검증 (내부 처리)
    7.  분석 결과 화면 출력 — IntegratedResultResponse DTO 반환 확인
    8.  사용자의 최종 검토 — 폴더/파일명/요약 수정 가능 필드 확인
    9.  DB와 파일시스템에 저장 — POST /{file_id}/save
    10. DB에서 리스트 검색 — GET /search
    11. 검색한 파일 요약 수정 저장 — PUT /{file_id}/summary
    12. 검색한 파일 삭제 — DELETE /{file_id}
    """
    # ─── 1~7: 업로드 & 통합 분석 ─────────────────────────────
    res = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("2026_업무보고.txt", FULL_DOC_CONTENT, "text/plain")}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True

    data = body["data"]
    file_id = data["file_id"]

    # 7: 출력 DTO 필드 완정성 확인
    assert "document_info" in data
    assert "analysis_data" in data
    assert "summary_data" in data
    assert "verification_data" in data
    assert "archiving_info" in data  # 8: 사용자 수정 가능 추천 경로

    # ─── 9: DB & 파일시스템 저장 ─────────────────────────────
    target_folder = "temp/test_12step_output"
    target_filename = "사용자 입력 이름.txt"

    save_res = client.post(
        f"/api/v1/documents/{file_id}/save",
        json={
            "folder_path": target_folder,
            "filename": target_filename,
            "document_overview": ["저장 요약 1", "저장 요약 2"]
        }
    )
    assert save_res.status_code == 200, save_res.text
    save_body = save_res.json()
    assert save_body["success"] is True
    assert save_body["file_id"] == file_id
    # 파일시스템에 실제 보관 확인
    archived_path = save_body["archived_file_path"].replace("\\", "/")
    assert archived_path.startswith("output/temp/test_12step_output/")
    assert os.path.exists(save_body["archived_file_path"])
    assert re.search(r"/\d{4}-\d{2}-\d{2}_2026_업무보고(?:\(\d+\))?\.txt$", archived_path)
    summary_path = os.path.splitext(save_body["archived_file_path"])[0] + ".md"
    assert os.path.exists(summary_path)
    with open(summary_path, encoding="utf-8") as summary_file:
        assert "저장 요약 1" in summary_file.read()
    md_res = client.get(f"/api/v1/documents/{file_id}/markdown")
    assert md_res.status_code == 200
    assert md_res.headers["content-type"].startswith("text/markdown")
    assert "저장 요약 1" in md_res.text

    # ─── 10: DB 리스트 검색 ──────────────────────────────────
    search_res = client.get("/api/v1/documents/search?keyword=업무보고")
    assert search_res.status_code == 200, search_res.text
    search_body = search_res.json()
    assert search_body["total_count"] >= 1
    found_ids = [item["file_id"] for item in search_body["data"]]
    assert file_id in found_ids

    # ─── 11: 요약 수정 저장 ──────────────────────────────────
    update_res = client.put(
        f"/api/v1/documents/{file_id}/summary",
        json={"overview_summary": ["수정된 요약 A", "수정된 요약 B"]}
    )
    assert update_res.status_code == 200, update_res.text
    assert update_res.json()["success"] is True

    # ─── 11.5: 1-Click 다운로드 ──────────────────────────────
    dl_res = client.get(f"/api/v1/documents/{file_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.content == FULL_DOC_CONTENT

    # ─── 12: 파일 삭제 ───────────────────────────────────────
    del_res = client.delete(f"/api/v1/documents/{file_id}")
    assert del_res.status_code == 200, del_res.text
    del_body = del_res.json()
    assert del_body["success"] is True
    assert del_body["file_id"] == file_id
    assert not os.path.exists(summary_path)

    # 삭제 후 검색에서 사라졌는지 확인
    search_after = client.get("/api/v1/documents/search")
    found_after = [item["file_id"] for item in search_after.json().get("data", [])]
    assert file_id not in found_after

    # 삭제 후 재삭제 시도 → 404
    del_again = client.delete(f"/api/v1/documents/{file_id}")
    assert del_again.status_code == 404


# ============================================================
# 예외 처리 테스트
# ============================================================
def test_unsupported_file_extension():
    """2단계: 미지원 확장자 → 400"""
    res = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("data.xlsx", b"test content", "application/vnd.ms-excel")}
    )
    assert res.status_code == 400
    assert "지원하지 않는 파일 형식" in res.json()["error"]["message"]


def test_empty_file_content():
    """2단계: 20자 미만 텍스트 → 422"""
    res = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("empty.txt", b"short text", "text/plain")}
    )
    assert res.status_code == 422
    assert "분석할 수 있는 텍스트 내용이 존재하지 않습니다" in res.json()["error"]["message"]


def test_delete_nonexistent_document():
    """12단계: 존재하지 않는 file_id 삭제 → 404"""
    res = client.delete("/api/v1/documents/nonexistent_id_xyz")
    assert res.status_code == 404
    assert "문서를 찾을 수 없습니다" in res.json()["detail"]


# ============================================================
# 파일 이동 및 폴더 추천 테스트
# ============================================================
def test_move_document_folder():
    """파일 저장 경로 변경: 업로드 → 저장 → 경로 이동 → 신규 경로 확인"""
    # 1. 업로드 & 분석
    res = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("이동테스트.txt", FULL_DOC_CONTENT, "text/plain")}
    )
    assert res.status_code == 200
    file_id = res.json()["data"]["file_id"]

    # 2. 저장
    old_folder = "temp/test_move_src"
    save_res = client.post(
        f"/api/v1/documents/{file_id}/save",
        json={"folder_path": old_folder, "filename": "before_move.txt", "document_overview": ["테스트"]}
    )
    assert save_res.status_code == 200, save_res.text
    old_summary = os.path.splitext(save_res.json()["archived_file_path"])[0] + ".md"
    assert os.path.exists(old_summary)

    # 3. 경로 이동
    new_folder = "temp/test_move_dst"
    move_res = client.put(
        f"/api/v1/documents/{file_id}/folder",
        json={"new_folder_path": new_folder}
    )
    assert move_res.status_code == 200, move_res.text
    body = move_res.json()
    assert body["success"] is True
    assert new_folder in body["new_path"]

    # 4. 새 경로에 파일 실존 확인
    assert os.path.exists(body["new_path"])
    new_summary = os.path.splitext(body["new_path"])[0] + ".md"
    assert os.path.exists(new_summary)
    assert not os.path.exists(old_summary)

    # 정리
    client.delete(f"/api/v1/documents/{file_id}")


def test_recommend_folder_returns_list():
    """폴더 추천 API: 업로드 후 추천 목록이 list 형태로 반환되는지 확인"""
    res = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("추천테스트.txt", FULL_DOC_CONTENT, "text/plain")}
    )
    assert res.status_code == 200
    file_id = res.json()["data"]["file_id"]

    rec_res = client.get(f"/api/v1/documents/{file_id}/recommend-folder")
    assert rec_res.status_code == 200, rec_res.text
    body = rec_res.json()
    assert body["success"] is True
    assert "recommendations" in body
    assert isinstance(body["recommendations"], list)

    edited_res = client.post(
        f"/api/v1/documents/{file_id}/recommend-folder",
        json={
            "summary": ["사용자 수정 요약"],
            "purpose": "업무 보고",
            "message": "핵심 추진 일정",
            "keywords": {"concepts": ["AI", "업무"], "organizations": ["디지털혁신팀"]},
            "folders": ["output", "output/archive/디지털혁신팀"],
        },
    )
    assert edited_res.status_code == 200, edited_res.text
    assert edited_res.json()["recommendations"]

    client.delete(f"/api/v1/documents/{file_id}")


def test_move_nonexistent_document():
    """존재하지 않는 문서 이동 → 404"""
    res = client.put(
        "/api/v1/documents/no_such_id/folder",
        json={"new_folder_path": "temp/nowhere"}
    )
    assert res.status_code == 404


def test_save_folder_is_normalized_under_output_root():
    res = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("output-root.txt", FULL_DOC_CONTENT, "text/plain")}
    )
    assert res.status_code == 200
    file_id = res.json()["data"]["file_id"]

    save_res = client.post(
        f"/api/v1/documents/{file_id}/save",
        json={
            "folder_path": "archive/root_default",
            "filename": "root_default.txt",
            "document_overview": ["root normalized"]
        }
    )
    assert save_res.status_code == 200, save_res.text
    body = save_res.json()
    assert body["archived_file_path"].replace("\\", "/").startswith("output/archive/root_default/")
    assert os.path.exists(body["archived_file_path"])

    client.delete(f"/api/v1/documents/{file_id}")


def test_search_folder_filter_includes_descendants_and_root_has_no_filter():
    saved_ids = []
    for name, folder in [
        ("parent.txt", "archive/search_parent"),
        ("child.txt", "archive/search_parent/child"),
    ]:
        res = client.post(
            "/api/v1/documents/analyze",
            files={"file": (name, FULL_DOC_CONTENT, "text/plain")}
        )
        assert res.status_code == 200
        file_id = res.json()["data"]["file_id"]
        saved_ids.append(file_id)

        save_res = client.post(
            f"/api/v1/documents/{file_id}/save",
            json={
                "folder_path": folder,
                "filename": name,
                "document_overview": [f"saved {name}"]
            }
        )
        assert save_res.status_code == 200, save_res.text

    parent_res = client.get("/api/v1/documents/search?folder=archive/search_parent")
    assert parent_res.status_code == 200, parent_res.text
    parent_ids = {item["file_id"] for item in parent_res.json()["data"]}
    assert set(saved_ids).issubset(parent_ids)

    root_res = client.get("/api/v1/documents/search?folder=output")
    assert root_res.status_code == 200, root_res.text
    root_ids = {item["file_id"] for item in root_res.json()["data"]}
    assert set(saved_ids).issubset(root_ids)

    for file_id in saved_ids:
        client.delete(f"/api/v1/documents/{file_id}")


def test_db_health_reports_mvp_backend_and_limitation():
    res = client.get("/api/v1/documents/health/db")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["connected"] is True
    assert body["data"]["backend"] == "sqlite"
    assert body["data"]["persistent"] is True
    assert body["data"]["migration_recommendation"]


def test_search_documents_with_checkbox_fields_or_operation_and_path_and_operation():
    res = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("체크박스_검색테스트.txt", FULL_DOC_CONTENT, "text/plain")}
    )
    assert res.status_code == 200
    file_id = res.json()["data"]["file_id"]

    save_res = client.post(
        f"/api/v1/documents/{file_id}/save",
        json={
            "folder_path": "archive/search_test_folder",
            "filename": "체크박스_검색테스트.txt",
            "document_overview": ["특별한개요키워드XYZ"]
        }
    )
    assert save_res.status_code == 200

    search_fn = client.get("/api/v1/documents/search?keyword=검색테스트&fields=filename")
    assert search_fn.status_code == 200
    assert file_id in [item["file_id"] for item in search_fn.json()["data"]]

    search_ov = client.get("/api/v1/documents/search?keyword=특별한개요키워드XYZ&fields=overview")
    assert search_ov.status_code == 200
    assert file_id in [item["file_id"] for item in search_ov.json()["data"]]

    search_fail = client.get("/api/v1/documents/search?keyword=특별한개요키워드XYZ&fields=filename")
    assert search_fail.status_code == 200
    assert file_id not in [item["file_id"] for item in search_fail.json()["data"]]

    search_or = client.get("/api/v1/documents/search?keyword=특별한개요키워드XYZ&fields=filename,overview")
    assert search_or.status_code == 200
    assert file_id in [item["file_id"] for item in search_or.json()["data"]]

    search_and_path = client.get("/api/v1/documents/search?keyword=특별한개요키워드XYZ&folder=archive/search_test_folder&fields=overview")
    assert search_and_path.status_code == 200
    assert file_id in [item["file_id"] for item in search_and_path.json()["data"]]

    search_diff_path = client.get("/api/v1/documents/search?keyword=특별한개요키워드XYZ&folder=archive/other_folder&fields=overview")
    assert search_diff_path.status_code == 200
    assert file_id not in [item["file_id"] for item in search_diff_path.json()["data"]]

    client.delete(f"/api/v1/documents/{file_id}")


def test_save_duplicate_original_uses_incrementing_sequence():
    file_ids = []
    paths = []
    for _ in range(2):
        res = client.post(
            "/api/v1/documents/analyze",
            files={"file": ("duplicate.txt", FULL_DOC_CONTENT, "text/plain")},
        )
        assert res.status_code == 200, res.text
        file_id = res.json()["data"]["file_id"]
        file_ids.append(file_id)
        save_res = client.post(
            f"/api/v1/documents/{file_id}/save",
            json={"folder_path": "archive/duplicate-name", "filename": "ignored.txt", "document_overview": []},
        )
        assert save_res.status_code == 200, save_res.text
        paths.append(save_res.json()["archived_file_path"].replace("\\", "/"))

    assert paths[0].endswith("_duplicate.txt")
    assert paths[1].endswith("_duplicate(1).txt")
    assert paths[0] != paths[1]
    for file_id in file_ids:
        client.delete(f"/api/v1/documents/{file_id}")


def test_update_all_ai_results_persists_schema_and_markdown():
    res = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("editable-results.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert res.status_code == 200
    file_id = res.json()["data"]["file_id"]
    data = res.json()["data"]
    save_res = client.post(
        f"/api/v1/documents/{file_id}/save",
        json={"folder_path": "archive/editable-results", "filename": "ignored.txt", "document_overview": ["초기"]},
    )
    assert save_res.status_code == 200

    edited = {
        "analysis_data": data["analysis_data"],
        "summary_data": data["summary_data"],
        "verification_data": data["verification_data"],
    }
    edited["analysis_data"]["document_subject"] = "사용자 수정 분석 주제"
    edited["summary_data"]["document_overview"] = ["사용자 수정 요약"]
    edited["verification_data"]["status_badge"] = "사용자 확인"
    update_res = client.put(f"/api/v1/documents/{file_id}/results", json=edited)
    assert update_res.status_code == 200, update_res.text

    result_res = client.get(f"/api/v1/documents/{file_id}/result")
    assert result_res.json()["data"]["analysis_data"]["document_subject"] == "사용자 수정 분석 주제"
    assert result_res.json()["data"]["verification_data"]["status_badge"] == "사용자 확인"
    md_path = os.path.splitext(save_res.json()["archived_file_path"])[0] + ".md"
    with open(md_path, encoding="utf-8") as markdown_file:
        markdown = markdown_file.read()
    assert "사용자 수정 분석 주제" in markdown
    assert "사용자 확인" in markdown
    client.delete(f"/api/v1/documents/{file_id}")


def test_unconfirmed_work_list_and_batch_operations():
    # 1. Analyze auto (user_confirmed = False)
    res = client.post(
        "/api/v1/documents/analyze-auto",
        files={"file": ("auto-test1.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert res.status_code == 200
    file_id1 = res.json()["data"]["file_id"]

    # 2. Get unconfirmed list
    unconfirmed_res = client.get("/api/v1/documents/unconfirmed")
    assert unconfirmed_res.status_code == 200
    unconfirmed_ids = [item["file_id"] for item in unconfirmed_res.json()["data"]]
    assert file_id1 in unconfirmed_ids

    # 3. Confirm single document
    confirm_res = client.put(
        f"/api/v1/documents/{file_id1}/confirm",
        json={"folder_path": "archive/confirmed_folder", "document_overview": ["확정 요약"]}
    )
    assert confirm_res.status_code == 200

    # Assert removed from unconfirmed list
    unconfirmed_after = client.get("/api/v1/documents/unconfirmed")
    assert file_id1 not in [item["file_id"] for item in unconfirmed_after.json()["data"]]

    # 4. Analyze two more documents for batch operations
    res2 = client.post(
        "/api/v1/documents/analyze-auto",
        files={"file": ("auto-test2.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    res3 = client.post(
        "/api/v1/documents/analyze-auto",
        files={"file": ("auto-test3.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    file_id2 = res2.json()["data"]["file_id"]
    file_id3 = res3.json()["data"]["file_id"]

    # 5. Batch confirm for file_id2
    batch_confirm_res = client.post(
        "/api/v1/documents/batch-confirm",
        json={"items": [{"file_id": file_id2, "folder_path": "archive/batch_folder", "document_overview": ["일괄 확정 요약"]}]}
    )
    assert batch_confirm_res.status_code == 200
    assert batch_confirm_res.json()["success_count"] == 1

    # 6. Batch delete for file_id3
    batch_delete_res = client.post(
        "/api/v1/documents/batch-delete",
        json={"file_ids": [file_id3]}
    )
    assert batch_delete_res.status_code == 200
    assert batch_delete_res.json()["success_count"] == 1

    # Cleanup file_id1 & file_id2
    client.delete(f"/api/v1/documents/{file_id1}")
    client.delete(f"/api/v1/documents/{file_id2}")


def test_departments_endpoint_and_custom_department_saving():
    res1 = client.post(
        "/api/v1/documents/analyze",
        data={"department": "기획조정실"},
        files={"file": ("dept-test1.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert res1.status_code == 200
    file_id1 = res1.json()["data"]["file_id"]

    res2 = client.post(
        "/api/v1/documents/analyze",
        data={"department": "AI개발팀"},
        files={"file": ("dept-test2.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert res2.status_code == 200
    file_id2 = res2.json()["data"]["file_id"]

    dept_res = client.get("/api/v1/documents/departments")
    assert dept_res.status_code == 200
    depts = dept_res.json()["data"]
    assert "기획조정실" in depts
    assert "AI개발팀" in depts
    assert depts == sorted(depts)

    # Update department via /save
    save_res = client.post(
        f"/api/v1/documents/{file_id1}/save",
        json={
            "folder_path": "archive/기획조정실",
            "filename": "dept-test1.txt",
            "document_overview": ["부서 변경 검증"],
            "department": "경영지원본부"
        }
    )
    assert save_res.status_code == 200

    dept_res_after = client.get("/api/v1/documents/departments")
    assert "경영지원본부" in dept_res_after.json()["data"]

    client.delete(f"/api/v1/documents/{file_id1}")
    client.delete(f"/api/v1/documents/{file_id2}")


def test_folder_relative_path_filename_upload():
    res = client.post(
        "/api/v1/documents/analyze-auto",
        files={"file": ("my_folder/sub/nested_doc.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert res.status_code == 200
    assert res.json()["success"] is True
    file_id = res.json()["data"]["file_id"]

    doc = client.get(f"/api/v1/documents/{file_id}/result")
    assert doc.status_code == 200
    assert doc.json()["data"]["document_info"]["original_filename"] == "nested_doc.txt"

    client.delete(f"/api/v1/documents/{file_id}")


def test_duplicate_filename_move_increments_sequence():
    """이동할 위치에 동일 파일이 존재할 경우 (1) 등 순번을 증가시켜 저장함을 검증"""
    res1 = client.post(
        "/api/v1/documents/analyze-auto",
        files={"file": ("dup_test.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert res1.status_code == 200
    file_id1 = res1.json()["data"]["file_id"]

    res2 = client.post(
        "/api/v1/documents/analyze-auto",
        files={"file": ("dup_test.txt", FULL_DOC_CONTENT, "text/plain")},
    )
    assert res2.status_code == 200
    file_id2 = res2.json()["data"]["file_id"]

    target_folder = "archive/중복테스트폴더"

    move1 = client.put(f"/api/v1/documents/{file_id1}/folder", json={"new_folder_path": target_folder, "new_filename": "dup_test.txt"})
    assert move1.status_code == 200

    move2 = client.put(f"/api/v1/documents/{file_id2}/folder", json={"new_folder_path": target_folder, "new_filename": "dup_test.txt"})
    assert move2.status_code == 200
    move2_json = move2.json()
    assert "dup_test(1).txt" in move2_json["new_path"] or "dup_test(1).txt" in move2_json["message"]

    client.delete(f"/api/v1/documents/{file_id1}")
    client.delete(f"/api/v1/documents/{file_id2}")
