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
