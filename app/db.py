import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# In-memory database store for MVP
document_db: Dict[str, Dict[str, Any]] = {}
document_files: Dict[str, bytes] = {}

def store_uploaded_document(file_id: str, original_filename: str, format_str: str, file_bytes: bytes, file_path: str):
    """Store raw file bytes and initial metadata."""
    document_files[file_id] = file_bytes
    
    # Rule-based recommended folder and filename
    rec_folder = f"output/archive/디지털혁신팀/"
    rec_filename = f"2026_{format_str}_{original_filename}"

    document_db[file_id] = {
        "file_id": file_id,
        "original_filename": original_filename,
        "recommended_folder": rec_folder,
        "recommended_filename": rec_filename,
        "format": format_str,
        "size_bytes": len(file_bytes),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "UPLOADED",
        "file_path": file_path,
        "department": "디지털혁신팀"
    }

def update_document_extracted(file_id: str, raw_text: str, structured_content: Dict[str, Any]):
    if file_id in document_db:
        document_db[file_id]["raw_text"] = raw_text
        document_db[file_id]["structured_content"] = structured_content
        document_db[file_id]["status"] = "EXTRACTED"

def update_document_analysis(file_id: str, analysis_data: Any):
    if file_id in document_db:
        document_db[file_id]["analysis_data"] = analysis_data
        document_db[file_id]["status"] = "ANALYZED"

def update_document_summary(file_id: str, summary_data: Any):
    if file_id in document_db:
        document_db[file_id]["summary_data"] = summary_data
        document_db[file_id]["status"] = "SUMMARIZED"

def update_document_validation(file_id: str, validation_data: Any):
    if file_id in document_db:
        document_db[file_id]["validation_data"] = validation_data
        document_db[file_id]["status"] = "COMPLETED"

def archive_and_save_document(file_id: str, folder_path: str, filename: str, document_overview: List[str]) -> Tuple[bool, str]:
    """
    Save original file to specified folder_path/filename and store updated summary in DB.
    """
    if file_id not in document_db or file_id not in document_files:
        return False, "문서를 찾을 수 없습니다."

    try:
        os.makedirs(folder_path, exist_ok=True)
        archived_full_path = os.path.join(folder_path, filename)
        
        # Save original file bytes to destination folder
        file_bytes = document_files[file_id]
        with open(archived_full_path, "wb") as f:
            f.write(file_bytes)

        # Update DB record
        doc = document_db[file_id]
        doc["status"] = "SAVED"
        doc["archived_path"] = archived_full_path
        doc["saved_folder"] = folder_path
        doc["saved_filename"] = filename
        
        if "summary_data" in doc and doc["summary_data"]:
            doc["summary_data"].summary_result.document_overview = document_overview

        return True, archived_full_path

    except Exception as e:
        return False, f"파일 저장 중 오류가 발생했습니다: {str(e)}"

def search_documents_in_db(keyword: Optional[str] = None, department: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search DB records by keyword or department."""
    results = []
    for doc_id, doc in document_db.items():
        if department and department.strip() and doc.get("department") != department:
            continue
        
        match = True
        if keyword and keyword.strip():
            kw = keyword.strip().lower()
            text_pool = f"{doc.get('original_filename', '')} {doc.get('saved_filename', '')} {doc.get('raw_text', '')}".lower()
            if kw not in text_pool:
                match = False
        
        if match:
            # Build search item
            summary_obj = doc.get("summary_data")
            overview_text = ""
            if summary_obj and hasattr(summary_obj, "summary_result"):
                ov = summary_obj.summary_result.document_overview
                overview_text = " ".join(ov) if isinstance(ov, list) else str(ov)

            val_obj = doc.get("validation_data")
            status_badge = val_obj.validation_result.status_badge if val_obj and hasattr(val_obj, "validation_result") else "확인 필요"

            results.append({
                "file_id": doc_id,
                "original_filename": doc.get("original_filename", "file.pdf"),
                "renamed_filename": doc.get("saved_filename", doc.get("recommended_filename", doc.get("original_filename"))),
                "format": doc.get("format", "PDF"),
                "department": doc.get("department", "디지털혁신팀"),
                "uploaded_at": doc.get("uploaded_at", datetime.now().strftime("%Y-%m-%d")),
                "one_line_summary": overview_text[:120] + ("..." if len(overview_text) > 120 else "") or "요약문이 생성되어 있습니다.",
                "confidence_score": 92.5,
                "status_badge": status_badge
            })
    return results

def update_summary_content(file_id: str, one_line_summary: Optional[str] = None, overview_summary: Optional[List[str]] = None) -> bool:
    """Update summary content in DB."""
    if file_id not in document_db:
        return False
    doc = document_db[file_id]
    if "summary_data" in doc and doc["summary_data"] and hasattr(doc["summary_data"], "summary_result"):
        if overview_summary is not None:
            doc["summary_data"].summary_result.document_overview = overview_summary
        return True
    return False

def get_document_by_id(file_id: str) -> Optional[Dict[str, Any]]:
    return document_db.get(file_id)

def get_document_file_bytes(file_id: str) -> Optional[Tuple[bytes, str]]:
    if file_id in document_files and file_id in document_db:
        return document_files[file_id], document_db[file_id]["original_filename"]
    return None

def delete_document_from_db(file_id: str) -> Tuple[bool, str]:
    """DB 레코드 및 아카이빙 원본 파일을 삭제한다."""
    if file_id not in document_db:
        return False, "문서를 찾을 수 없습니다."

    doc = document_db[file_id]

    # 1. 아카이빙된 원본 파일 물리 삭제 (존재하는 경우에만)
    archived_path = doc.get("archived_path")
    if archived_path and os.path.exists(archived_path):
        try:
            os.remove(archived_path)
        except Exception as e:
            return False, f"아카이빙 파일 삭제 중 오류: {str(e)}"

    # 2. 임시 업로드 파일 물리 삭제
    temp_file_path = doc.get("file_path")
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
        except Exception:
            pass  # 임시 파일 삭제 실패는 무시

    # 3. 인메모리 DB 레코드 및 바이너리 제거
    document_db.pop(file_id, None)
    document_files.pop(file_id, None)

    return True, f"문서 {file_id} 가 성공적으로 삭제되었습니다."

def move_document_file(
    file_id: str,
    new_folder_path: str,
    new_filename: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """
    아카이빙된 원본 파일을 새 경로로 이동하고 DB를 업데이트한다.

    Returns:
        (success, old_path, new_path)
        실패 시 (False, "", 오류 메시지)
    """
    if file_id not in document_db:
        return False, "", "문서를 찾을 수 없습니다."

    doc = document_db[file_id]
    old_path: str = doc.get("archived_path", "")

    # 이동할 파일명 결정 (생략 시 기존 파일명 유지)
    filename = new_filename or doc.get("saved_filename") or doc.get("original_filename", "unknown")

    try:
        os.makedirs(new_folder_path, exist_ok=True)
        new_full_path = os.path.join(new_folder_path, filename)

        if old_path and os.path.exists(old_path):
            import shutil
            shutil.move(old_path, new_full_path)
        else:
            # 아카이빙 파일이 없으면 인메모리 바이너리로 새로 생성
            file_bytes = document_files.get(file_id)
            if file_bytes is None:
                return False, "", "이동할 원본 파일 데이터가 존재하지 않습니다."
            with open(new_full_path, "wb") as f:
                f.write(file_bytes)

        # DB 경로 업데이트
        doc["archived_path"] = new_full_path
        doc["saved_folder"] = new_folder_path
        doc["saved_filename"] = filename

        return True, old_path, new_full_path

    except Exception as e:
        return False, "", f"파일 이동 중 오류가 발생했습니다: {str(e)}"


ARCHIVE_ROOT = "output/archive"  # 폴더 추천 기준 루트

def get_existing_archive_folders() -> List[str]:
    """
    ARCHIVE_ROOT 하위에 실존하는 폴더 경로 목록을 반환한다.
    루트가 없으면 빈 리스트를 반환한다.
    """
    if not os.path.isdir(ARCHIVE_ROOT):
        return []

    folders: List[str] = []
    for dirpath, dirnames, _ in os.walk(ARCHIVE_ROOT):
        for d in dirnames:
            folders.append(os.path.join(dirpath, d).replace("\\", "/"))
    # 루트 자체도 포함
    folders.insert(0, ARCHIVE_ROOT)
    return folders


def get_folder_tree() -> Dict[str, Any]:
    """
    DB에 저장된 문서 레코드를 폴더 경로 기준으로 계층화하여 반환한다.

    반환 구조:
    {
        "folders": {
            "output/archive": {
                "path": "output/archive",
                "children": {
                    "output/archive/디지털혁신팀": {
                        "path": "output/archive/디지털혁신팀",
                        "children": {},
                        "files": [{"file_id": ..., "filename": ..., "uploaded_at": ...}]
                    }
                },
                "files": []
            }
        },
        "total_files": 3
    }
    """
    # 폴더 트리를 dict로 표현. key = 정규화된 폴더 경로
    tree: Dict[str, Any] = {}

    def _ensure_node(path: str) -> Dict[str, Any]:
        normalized = path.replace("\\", "/").rstrip("/")
        if normalized not in tree:
            tree[normalized] = {"path": normalized, "children": {}, "files": []}
        return tree[normalized]

    for file_id, doc in document_db.items():
        folder = doc.get("saved_folder") or doc.get("recommended_folder", ARCHIVE_ROOT)
        folder = folder.replace("\\", "/").rstrip("/")
        filename = doc.get("saved_filename") or doc.get("original_filename", "unknown")
        uploaded_at = doc.get("uploaded_at", "")

        node = _ensure_node(folder)
        node["files"].append({
            "file_id": file_id,
            "filename": filename,
            "uploaded_at": uploaded_at,
        })

        # 상위 폴더도 트리에 등록
        parts = folder.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            child = "/".join(parts[:i + 1])
            _ensure_node(parent)
            _ensure_node(child)
            tree[parent]["children"][child] = tree[child]

    # 루트가 없으면 빈 루트 생성
    if not tree:
        _ensure_node(ARCHIVE_ROOT)

    # 최상위(루트) 노드만 골라서 반환
    # — 다른 노드의 children에 포함된 경우 root가 아님
    all_children: set[str] = set()
    for node in tree.values():
        all_children.update(node["children"].keys())
    roots = {k: v for k, v in tree.items() if k not in all_children}

    return {
        "folders": roots,
        "total_files": sum(len(node["files"]) for node in tree.values()),
    }
