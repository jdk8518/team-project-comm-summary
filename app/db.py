import os
import re
import json
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from app.schemas import (
    SummaryData, ValidationData, AnalysisData, SummaryResult, ValidationResult
)

from dotenv import load_dotenv
load_dotenv()

raw_archive_root = (os.getenv("ARCHIVE_ROOT") or os.getenv("FILE_STORAGE_ROOT") or "output").strip().replace("\\", "/").strip("/")
ARCHIVE_ROOT = raw_archive_root or "output"
DB_PATH = os.path.join(ARCHIVE_ROOT, "documents.db")

# In-memory document binary buffer for uploaded/archived raw bytes
document_files: Dict[str, bytes] = {}

# In-memory document dict index (kept in sync with SQLite DB)
document_db: Dict[str, Dict[str, Any]] = {}


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite database connection with row factory."""
    os.makedirs(ARCHIVE_ROOT, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db() -> None:
    """Initialize SQLite database table and load existing records into memory cache."""
    os.makedirs(ARCHIVE_ROOT, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                file_id TEXT PRIMARY KEY,
                original_filename TEXT,
                recommended_folder TEXT,
                recommended_filename TEXT,
                saved_folder TEXT,
                saved_filename TEXT,
                archived_path TEXT,
                summary_path TEXT,
                format TEXT,
                size_bytes INTEGER,
                uploaded_at TEXT,
                department TEXT,
                status TEXT,
                file_path TEXT,
                raw_text TEXT,
                structured_content TEXT,
                analysis_data TEXT,
                summary_data TEXT,
                validation_data TEXT,
                user_confirmed INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN user_confirmed INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        conn.commit()

        # Load existing database records into memory cache on startup
        cursor.execute("SELECT * FROM documents")
        rows = cursor.fetchall()
        for row in rows:
            record = dict(row)
            doc_id = record["file_id"]

            # Reconstruct Pydantic object models from JSON text if present
            if record.get("analysis_data"):
                try:
                    record["analysis_data"] = AnalysisData.model_validate_json(record["analysis_data"])
                except Exception:
                    try:
                        record["analysis_data"] = AnalysisData(**json.loads(record["analysis_data"]))
                    except Exception:
                        pass

            if record.get("summary_data"):
                try:
                    record["summary_data"] = SummaryData.model_validate_json(record["summary_data"])
                except Exception:
                    try:
                        data_dict = json.loads(record["summary_data"])
                        record["summary_data"] = SummaryData(
                            file_id=doc_id,
                            summary_result=SummaryResult(**data_dict.get("summary_result", data_dict))
                        )
                    except Exception:
                        pass

            if record.get("validation_data"):
                try:
                    record["validation_data"] = ValidationData.model_validate_json(record["validation_data"])
                except Exception:
                    try:
                        data_dict = json.loads(record["validation_data"])
                        record["validation_data"] = ValidationData(
                            file_id=doc_id,
                            validation_result=ValidationResult(**data_dict.get("validation_result", data_dict))
                        )
                    except Exception:
                        pass

            if record.get("structured_content") and isinstance(record["structured_content"], str):
                try:
                    record["structured_content"] = json.loads(record["structured_content"])
                except Exception:
                    pass

            record["user_confirmed"] = bool(record.get("user_confirmed", 0))
            document_db[doc_id] = record


# Initialize SQLite table on module load
init_sqlite_db()


def _serialize_pydantic(obj: Any) -> Optional[str]:
    """Serialize Pydantic models or dicts to JSON string for SQLite storage."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump_json"):
        return obj.model_dump_json()
    if hasattr(obj, "json"):
        return obj.json()
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False)
    return str(obj)


def save_doc_to_sqlite(doc: Dict[str, Any]) -> None:
    """Insert or replace a document record in SQLite DB."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO documents (
                file_id, original_filename, recommended_folder, recommended_filename,
                saved_folder, saved_filename, archived_path, summary_path,
                format, size_bytes, uploaded_at, department, status, file_path,
                raw_text, structured_content, analysis_data, summary_data, validation_data,
                user_confirmed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc.get("file_id"),
            doc.get("original_filename"),
            doc.get("recommended_folder"),
            doc.get("recommended_filename"),
            doc.get("saved_folder"),
            doc.get("saved_filename"),
            doc.get("archived_path"),
            doc.get("summary_path"),
            doc.get("format"),
            doc.get("size_bytes"),
            doc.get("uploaded_at"),
            doc.get("department"),
            doc.get("status"),
            doc.get("file_path"),
            doc.get("raw_text"),
            _serialize_pydantic(doc.get("structured_content")),
            _serialize_pydantic(doc.get("analysis_data")),
            _serialize_pydantic(doc.get("summary_data")),
            _serialize_pydantic(doc.get("validation_data")),
            1 if doc.get("user_confirmed") else 0,
            doc.get("created_at") or now_str,
            now_str
        ))
        conn.commit()


def delete_doc_from_sqlite(file_id: str) -> None:
    """Delete a document record from SQLite DB."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE file_id = ?", (file_id,))
        conn.commit()


def get_database_status() -> Dict[str, Any]:
    """Return an explicit health report for the SQLite database backend."""
    try:
        root_exists = os.path.isdir(ARCHIVE_ROOT)
        db_exists = os.path.isfile(DB_PATH)
        return {
            "connected": True,
            "backend": "sqlite",
            "persistent": True,
            "db_path": DB_PATH,
            "db_exists": db_exists,
            "document_count": len(document_db),
            "file_count": len(document_files),
            "archive_root": ARCHIVE_ROOT,
            "archive_root_exists": root_exists,
            "migration_recommendation": "SQLite 데이터베이스(output/documents.db)가 정상 연결되어 영구 저장 기능을 제공합니다.",
        }
    except Exception as exc:
        return {"connected": False, "backend": "sqlite", "error": type(exc).__name__}


def normalize_archive_folder_path(folder_path: Optional[str]) -> str:
    """Normalize every archive folder into the fixed output root."""
    raw_path = (folder_path or "").strip().replace("\\", "/").strip("/")
    root = ARCHIVE_ROOT.replace("\\", "/").strip("/")

    if not raw_path or raw_path == root:
        normalized = root
    elif raw_path.startswith(f"{root}/"):
        normalized = raw_path
    else:
        normalized = f"{root}/{raw_path}"

    root_abs = os.path.abspath(root)
    normalized_abs = os.path.abspath(normalized)
    if os.path.commonpath([root_abs, normalized_abs]) != root_abs:
        raise ValueError(f"Archive folder must be under {ARCHIVE_ROOT}.")

    return normalized


def is_archive_root(folder_path: Optional[str]) -> bool:
    return normalize_archive_folder_path(folder_path).rstrip("/") == ARCHIVE_ROOT


def build_unique_archive_filename(file_id: str, folder_path: str, now: Optional[datetime] = None) -> str:
    """Build YYYY-MM-DD_original-name.ext, adding a sequence only on collision."""
    doc = document_db.get(file_id)
    if not doc:
        raise ValueError("문서를 찾을 수 없습니다.")
    original = os.path.basename(doc.get("original_filename") or "document")
    stem, extension = os.path.splitext(original)
    stem = re.sub(r"[\\/:*?\"<>|]", "_", stem).strip() or "document"
    date_prefix = (now or datetime.now()).strftime("%Y-%m-%d")
    normalized_folder = normalize_archive_folder_path(folder_path)
    os.makedirs(normalized_folder, exist_ok=True)
    base_name = f"{date_prefix}_{stem}{extension}"
    if not os.path.exists(os.path.join(normalized_folder, base_name)):
        return base_name

    pattern = re.compile(rf"^{re.escape(date_prefix)}_{re.escape(stem)}\((\d+)\){re.escape(extension)}$", re.IGNORECASE)
    sequence = 1
    for name in os.listdir(normalized_folder):
        match = pattern.match(name)
        if match:
            sequence = max(sequence, int(match.group(1)) + 1)
    return f"{date_prefix}_{stem}({sequence}){extension}"


def summary_markdown_path(archived_path: str) -> str:
    return os.path.splitext(archived_path)[0] + ".md"


def write_summary_markdown(file_id: str, archived_path: str) -> str:
    """Write the AI summary next to the archived source file as a Markdown sidecar."""
    doc = document_db.get(file_id)
    if not doc:
        raise ValueError("문서를 찾을 수 없습니다.")

    summary_obj = doc.get("summary_data")
    summary = getattr(summary_obj, "summary_result", None)
    validation_obj = doc.get("validation_data")
    validation = getattr(validation_obj, "validation_result", None)
    analysis = doc.get("analysis_data")
    overview = getattr(summary, "document_overview", None) or ["요약 내용이 없습니다."]
    lines = [f"# {doc.get('original_filename', '문서')} 요약", ""]
    if getattr(summary, "error_message", None):
        lines.extend([f"> 요약 오류: {summary.error_message}", ""])
    lines.extend(["## 문서 개요", ""])
    lines.extend(f"- {item}" for item in overview)
    lines.extend([
        "",
        "## 문서 목적",
        "",
        getattr(summary, "document_purpose", "내용 없음"),
        "",
        "## 주요 내용",
        "",
    ])
    for item in getattr(summary, "main_contents_list", []) or []:
        lines.append(f"### {getattr(item, 'category', '')}")
        lines.extend(f"- {point}" for point in getattr(item, "points", []))
        lines.append("")
    lines.extend([
        "## 결론 및 핵심 메시지",
        "",
        getattr(summary, "conclusion_or_core_message", "내용 없음"),
        "",
    ])
    if analysis and getattr(analysis, "error_message", None):
        lines.extend([f"> 분석 오류: {analysis.error_message}", ""])
    if validation:
        lines.extend(["## 검증 상태", "", f"- 상태: {validation.status_badge}", f"- 통과 여부: {'예' if validation.is_passed else '아니오'}", ""])
        if analysis:
            lines.extend(["## AI 분석 결과", "", f"- 중심 주제: {getattr(analysis, 'document_subject', '')}", f"- 작성 목적: {getattr(analysis, 'document_purpose', '')}", ""])
            keywords = getattr(analysis, "key_keywords", None)
            if keywords:
                lines.append("### 주요 키워드")
                for label, attr in (("인물", "persons"), ("기관", "organizations"), ("일정", "schedules"), ("수치", "metrics"), ("개념", "concepts")):
                    lines.append(f"- {label}: {', '.join(getattr(keywords, attr, []) or []) or '없음'}")
                lines.append("")
            if getattr(analysis, "core_structure", None):
                lines.append("### 핵심 구조")
                lines.extend(f"- [{getattr(item, 'category', '')}] {getattr(item, 'content_summary', '')}" for item in analysis.core_structure)
                lines.append("")
            if getattr(analysis, "key_sentences", None):
                lines.append("### 핵심 문장")
                lines.extend(f"- {getattr(item, 'text', '')}" for item in analysis.key_sentences)
                lines.append("")
        if getattr(validation, "issue_list", None):
            lines.append("### 검증 이슈")
            for issue in validation.issue_list:
                lines.extend([f"- [{getattr(issue, 'issue_type', '')}] {getattr(issue, 'issue_title', '')}: {getattr(issue, 'reason_description', '')}", f"  - 근거: {getattr(issue, 'relevant_original_evidence', '')}"])
            lines.append("")
        if getattr(validation, "human_review_checklist", None):
            lines.append("### 사람 확인 체크리스트")
            lines.extend(f"- [{'x' if getattr(item, 'checked', False) else ' '}] {getattr(item, 'title', '')}: {getattr(item, 'description', '')}" for item in validation.human_review_checklist)
            lines.append("")
        if getattr(validation, "error_message", None):
            lines.extend([f"> 검증 오류: {validation.error_message}", ""])

    markdown_path = summary_markdown_path(archived_path)
    with open(markdown_path, "w", encoding="utf-8", newline="\n") as markdown_file:
        markdown_file.write("\n".join(lines).rstrip() + "\n")
    doc["summary_path"] = markdown_path
    save_doc_to_sqlite(doc)
    return markdown_path


def store_uploaded_document(file_id: str, original_filename: str, format_str: str, file_bytes: bytes, file_path: str, department: str = "디지털혁신팀"):
    """Store raw file bytes and initial metadata in memory and SQLite DB."""
    document_files[file_id] = file_bytes

    dept_str = (department or "").strip() or "디지털혁신팀"
    rec_folder = f"output/archive/{dept_str}/"
    stem, extension = os.path.splitext(os.path.basename(original_filename))
    rec_filename = f"{datetime.now().strftime('%Y-%m-%d')}_{stem}{extension}"

    doc = {
        "file_id": file_id,
        "original_filename": original_filename,
        "recommended_folder": rec_folder,
        "recommended_filename": rec_filename,
        "saved_folder": None,
        "saved_filename": None,
        "archived_path": None,
        "summary_path": None,
        "format": format_str,
        "size_bytes": len(file_bytes),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "UPLOADED",
        "file_path": file_path,
        "department": dept_str,
        "raw_text": None,
        "structured_content": None,
        "analysis_data": None,
        "summary_data": None,
        "validation_data": None,
        "user_confirmed": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    document_db[file_id] = doc


def get_all_departments() -> List[str]:
    """Return distinct non-empty departments ordered ascending."""
    departments = set()
    for doc in document_db.values():
        dept = doc.get("department")
        if dept and str(dept).strip():
            departments.add(str(dept).strip())

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT department FROM documents WHERE department IS NOT NULL AND TRIM(department) != '' ORDER BY department ASC")
            rows = cursor.fetchall()
            for r in rows:
                if r["department"]:
                    departments.add(r["department"].strip())
    except Exception:
        pass

    return sorted(list(departments))


def get_unconfirmed_documents() -> List[Dict[str, Any]]:
    """Return list of documents with user_confirmed == False for multi-file work list."""
    results = []
    for doc_id, doc in document_db.items():
        if not doc.get("user_confirmed", False):
            summary_obj = doc.get("summary_data")
            overview_text = ""
            if summary_obj and hasattr(summary_obj, "summary_result"):
                ov = summary_obj.summary_result.document_overview
                overview_text = " ".join(ov) if isinstance(ov, list) else str(ov)

            results.append({
                "file_id": doc_id,
                "original_filename": doc.get("original_filename", "file.pdf"),
                "renamed_filename": doc.get("saved_filename") or doc.get("recommended_filename") or doc.get("original_filename") or "document",
                "saved_folder": doc.get("saved_folder") or doc.get("recommended_folder", f"output/archive/{doc.get('department', '디지털혁신팀')}/"),
                "department": doc.get("department", "디지털혁신팀"),
                "one_line_summary": overview_text or "요약문이 생성되어 있습니다.",
                "user_confirmed": False,
                "uploaded_at": doc.get("uploaded_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            })
    return results


def confirm_document(file_id: str, folder_path: str, document_overview: List[str], department: Optional[str] = None) -> Tuple[bool, str]:
    """Update document folder path, overview & department, set user_confirmed = True."""
    if file_id not in document_db:
        return False, "문서를 찾을 수 없습니다."

    doc = document_db[file_id]

    if department and department.strip():
        doc["department"] = department.strip()

    # Update summary overview
    if "summary_data" in doc and doc["summary_data"]:
        summary_obj = doc["summary_data"]
        if hasattr(summary_obj, "summary_result"):
            summary_obj.summary_result.document_overview = document_overview

    # Move file if folder_path changed
    current_folder = doc.get("saved_folder") or doc.get("recommended_folder")
    if folder_path and folder_path != current_folder:
        move_document_file(file_id, folder_path)

    doc["user_confirmed"] = True
    save_doc_to_sqlite(doc)

    if doc.get("archived_path"):
        write_summary_markdown(file_id, doc["archived_path"])

    return True, "문서가 성공적으로 확정(저장)되었습니다."


def batch_confirm_documents(items: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """Confirm multiple documents in a single batch operation."""
    success_count = 0
    failed_ids = []
    for item in items:
        f_id = item.get("file_id")
        folder = item.get("folder_path", "")
        overview = item.get("document_overview", [])
        dept = item.get("department")
        ok, _ = confirm_document(f_id, folder, overview, department=dept)
        if ok:
            success_count += 1
        else:
            failed_ids.append(f_id)
    return success_count, failed_ids


def batch_delete_documents(file_ids: List[str]) -> Tuple[int, List[str]]:
    """Delete multiple documents in a single batch operation."""
    success_count = 0
    failed_ids = []
    for f_id in file_ids:
        ok, _ = delete_document_from_db(f_id)
        if ok:
            success_count += 1
        else:
            failed_ids.append(f_id)
    return success_count, failed_ids


def update_document_recommendation(file_id: str, folder_path: str) -> bool:
    if file_id not in document_db:
        return False
    doc = document_db[file_id]
    doc["recommended_folder"] = normalize_archive_folder_path(folder_path)
    save_doc_to_sqlite(doc)
    return True


def update_document_extracted(file_id: str, raw_text: str, structured_content: Dict[str, Any]):
    if file_id in document_db:
        doc = document_db[file_id]
        doc["raw_text"] = raw_text
        doc["structured_content"] = structured_content
        doc["status"] = "EXTRACTED"
        save_doc_to_sqlite(doc)


def update_document_analysis(file_id: str, analysis_data: Any):
    if file_id in document_db:
        doc = document_db[file_id]
        doc["analysis_data"] = analysis_data
        doc["status"] = "ANALYZED"
        save_doc_to_sqlite(doc)


def update_document_summary(file_id: str, summary_data: Any):
    if file_id in document_db:
        doc = document_db[file_id]
        doc["summary_data"] = summary_data
        doc["status"] = "SUMMARIZED"
        save_doc_to_sqlite(doc)


def update_document_validation(file_id: str, validation_data: Any):
    if file_id in document_db:
        doc = document_db[file_id]
        doc["validation_data"] = validation_data
        validation_result = getattr(validation_data, "validation_result", None)
        doc["status"] = "ERROR" if getattr(validation_result, "error_message", None) else "COMPLETED"
        save_doc_to_sqlite(doc)


def update_document_results(file_id: str, analysis_data: Any, summary_data: Any, validation_data: Any, department: Optional[str] = None) -> bool:
    """Update AI analysis/summary/validation results and department in SQLite DB and regenerate Markdown."""
    if file_id not in document_db:
        return False
    doc = document_db[file_id]
    if department and department.strip():
        doc["department"] = department.strip()
    doc["analysis_data"] = analysis_data
    doc["summary_data"] = SummaryData(file_id=file_id, summary_result=summary_data)
    doc["validation_data"] = ValidationData(file_id=file_id, validation_result=validation_data)
    doc["status"] = "ERROR" if any(getattr(item, "error_message", None) for item in (analysis_data, summary_data, validation_data)) else "COMPLETED"
    archived_path = doc.get("archived_path")
    if archived_path:
        write_summary_markdown(file_id, archived_path)
    else:
        save_doc_to_sqlite(doc)
    return True


def archive_and_save_document(file_id: str, folder_path: str, filename: str, document_overview: List[str], analysis_data: Any = None, summary_data: Any = None, verification_data: Any = None, department: Optional[str] = None) -> Tuple[bool, str]:
    """Save original file to specified folder_path/filename and insert/update DB record in SQLite."""
    if file_id not in document_db:
        return False, "문서를 찾을 수 없습니다."

    try:
        normalized_folder_path = normalize_archive_folder_path(folder_path)
        filename = build_unique_archive_filename(file_id, normalized_folder_path)
        archived_full_path = os.path.join(normalized_folder_path, filename)

        # Save original file bytes to destination folder
        file_bytes = get_document_file_bytes(file_id)[0] if get_document_file_bytes(file_id) else b""
        with open(archived_full_path, "xb") as f:
            f.write(file_bytes)

        # Update DB record
        doc = document_db[file_id]
        if department and department.strip():
            doc["department"] = department.strip()
        doc["status"] = "SAVED"
        doc["archived_path"] = archived_full_path
        doc["saved_folder"] = normalized_folder_path
        doc["saved_filename"] = filename

        if "summary_data" in doc and doc["summary_data"]:
            summary_obj = doc["summary_data"]
            if hasattr(summary_obj, "summary_result"):
                summary_obj.summary_result.document_overview = document_overview

        if analysis_data is not None and summary_data is not None and verification_data is not None:
            update_document_results(file_id, analysis_data, summary_data, verification_data)

        save_doc_to_sqlite(doc)
        write_summary_markdown(file_id, archived_full_path)

        return True, archived_full_path

    except Exception as e:
        return False, f"파일 저장 중 오류가 발생했습니다: {str(e)}"


def _extract_field_text(doc: Dict[str, Any], field: str) -> str:
    """Extract string content for a specified search field from document record."""
    texts: List[str] = []

    if field == "filename":
        texts.append(doc.get("original_filename") or "")
        texts.append(doc.get("saved_filename") or "")
        texts.append(doc.get("recommended_filename") or "")

    elif field == "overview":
        summary_obj = doc.get("summary_data")
        if summary_obj and hasattr(summary_obj, "summary_result"):
            ov = summary_obj.summary_result.document_overview
            if isinstance(ov, list):
                texts.extend(ov)
            elif ov:
                texts.append(str(ov))

    elif field == "keywords":
        analysis = doc.get("analysis_data")
        if analysis and hasattr(analysis, "key_keywords"):
            kw = analysis.key_keywords
            for attr in ("persons", "organizations", "schedules", "metrics", "concepts"):
                items = getattr(kw, attr, []) or []
                texts.extend(items)

    elif field == "subject_purpose":
        analysis = doc.get("analysis_data")
        if analysis:
            texts.append(getattr(analysis, "document_subject", "") or "")
            texts.append(getattr(analysis, "document_purpose", "") or "")
        summary_obj = doc.get("summary_data")
        if summary_obj and hasattr(summary_obj, "summary_result"):
            texts.append(getattr(summary_obj.summary_result, "document_purpose", "") or "")

    elif field == "main_contents":
        summary_obj = doc.get("summary_data")
        if summary_obj and hasattr(summary_obj, "summary_result"):
            for item in getattr(summary_obj.summary_result, "main_contents_list", []) or []:
                texts.append(getattr(item, "category", "") or "")
                texts.extend(getattr(item, "points", []) or [])

    elif field == "conclusion":
        summary_obj = doc.get("summary_data")
        if summary_obj and hasattr(summary_obj, "summary_result"):
            texts.append(getattr(summary_obj.summary_result, "conclusion_or_core_message", "") or "")

    elif field == "core_structure":
        analysis = doc.get("analysis_data")
        if analysis and getattr(analysis, "core_structure", None):
            for item in analysis.core_structure:
                texts.append(getattr(item, "category", "") or "")
                texts.append(getattr(item, "content_summary", "") or "")

    elif field == "key_sentences":
        analysis = doc.get("analysis_data")
        if analysis and getattr(analysis, "key_sentences", None):
            for item in analysis.key_sentences:
                texts.append(getattr(item, "text", "") or "")

    elif field == "issues":
        val_obj = doc.get("validation_data")
        if val_obj and hasattr(val_obj, "validation_result"):
            val_res = val_obj.validation_result
            for issue in getattr(val_res, "issue_list", []) or []:
                texts.append(getattr(issue, "issue_title", "") or "")
                texts.append(getattr(issue, "reason_description", "") or "")
                texts.append(getattr(issue, "relevant_original_evidence", "") or "")

    elif field == "raw_text":
        texts.append(doc.get("raw_text") or "")

    return " ".join(t for t in texts if t)


def search_documents_in_db(
    keyword: Optional[str] = None,
    department: Optional[str] = None,
    folder: Optional[str] = None,
    checked_fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Search SQLite document records with:
    - Storage path (folder) & Department: AND operation
    - Keyword match across selected checked_fields: OR operation
    Default checked_fields: ['filename', 'overview', 'keywords']
    """
    if checked_fields is None or len(checked_fields) == 0:
        checked_fields = ["filename", "overview", "keywords"]

    results = []
    kw_clean = keyword.strip().lower() if keyword and keyword.strip() else None

    # Path filter normalization
    normalized_folder_filter = None
    if folder and folder.strip():
        try:
            normalized_folder_filter = normalize_archive_folder_path(folder).rstrip("/")
        except ValueError:
            pass

    for doc_id, doc in document_db.items():
        # 1. Department filter (AND condition)
        if department and department.strip() and doc.get("department") != department:
            continue

        # 2. Folder / Storage path filter (AND condition)
        if normalized_folder_filter and not is_archive_root(normalized_folder_filter):
            doc_folder = normalize_archive_folder_path(
                doc.get("saved_folder") or doc.get("recommended_folder", "")
            ).rstrip("/")
            if not (doc_folder == normalized_folder_filter or doc_folder.startswith(f"{normalized_folder_filter}/")):
                continue

        # 3. Keyword match across selected checked_fields (OR condition across fields)
        if kw_clean:
            field_matched = False
            for field_name in checked_fields:
                field_text = _extract_field_text(doc, field_name)
                if kw_clean in field_text.lower():
                    field_matched = True
                    break
            if not field_matched:
                continue

        # Build item for API response
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
            "renamed_filename": doc.get("saved_filename") or doc.get("recommended_filename") or doc.get("original_filename") or "document",
            "format": doc.get("format", "PDF"),
            "department": doc.get("department", "디지털혁신팀"),
            "uploaded_at": doc.get("uploaded_at", datetime.now().strftime("%Y-%m-%d")),
            "one_line_summary": overview_text[:120] + ("..." if len(overview_text) > 120 else "") or "요약문이 생성되어 있습니다.",
            "confidence_score": 92.5,
            "status_badge": status_badge
        })

    return results


def update_summary_content(file_id: str, one_line_summary: Optional[str] = None, overview_summary: Optional[List[str]] = None) -> bool:
    """Update summary content in SQLite DB."""
    if file_id not in document_db:
        return False
    doc = document_db[file_id]
    if "summary_data" in doc and doc["summary_data"] and hasattr(doc["summary_data"], "summary_result"):
        if overview_summary is not None:
            doc["summary_data"].summary_result.document_overview = overview_summary
        save_doc_to_sqlite(doc)
        if doc.get("archived_path"):
            write_summary_markdown(file_id, doc["archived_path"])
        return True
    return False


def get_document_by_id(file_id: str) -> Optional[Dict[str, Any]]:
    return document_db.get(file_id)


def get_document_file_bytes(file_id: str) -> Optional[Tuple[bytes, str]]:
    if file_id in document_files and file_id in document_db:
        return document_files[file_id], document_db[file_id]["original_filename"]
    if file_id in document_db:
        doc = document_db[file_id]
        archived_path = doc.get("archived_path")
        if archived_path and os.path.exists(archived_path):
            with open(archived_path, "rb") as f:
                content = f.read()
            document_files[file_id] = content
            return content, doc.get("original_filename", "document")
        file_path = doc.get("file_path")
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            document_files[file_id] = content
            return content, doc.get("original_filename", "document")
    return None


def delete_document_from_db(file_id: str) -> Tuple[bool, str]:
    """Delete document record from SQLite DB and remove archived/temp files from disk."""
    if file_id not in document_db:
        return False, "문서를 찾을 수 없습니다."

    doc = document_db[file_id]

    # 1. Remove archived file
    archived_path = doc.get("archived_path")
    if archived_path and os.path.exists(archived_path):
        try:
            os.remove(archived_path)
        except Exception as e:
            return False, f"아카이빙 파일 삭제 중 오류: {str(e)}"

    summary_path = doc.get("summary_path") or (summary_markdown_path(archived_path) if archived_path else None)
    if summary_path and os.path.exists(summary_path):
        try:
            os.remove(summary_path)
        except Exception as e:
            return False, f"요약 Markdown 삭제 중 오류: {str(e)}"

    # 2. Remove temporary uploaded file
    temp_file_path = doc.get("file_path")
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
        except Exception:
            pass

    # 3. Delete from SQLite DB and memory cache
    delete_doc_from_sqlite(file_id)
    document_db.pop(file_id, None)
    document_files.pop(file_id, None)

    return True, f"문서 {file_id} 가 성공적으로 삭제되었습니다."


def move_document_file(
    file_id: str,
    new_folder_path: str,
    new_filename: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """Move archived document file to new folder path and update SQLite DB record."""
    if file_id not in document_db:
        return False, "", "문서를 찾을 수 없습니다."

    doc = document_db[file_id]
    old_path: str = doc.get("archived_path", "")
    old_summary_path = doc.get("summary_path") or (summary_markdown_path(old_path) if old_path else None)

    filename = new_filename or doc.get("saved_filename") or doc.get("original_filename", "unknown")

    try:
        normalized_folder_path = normalize_archive_folder_path(new_folder_path)
        os.makedirs(normalized_folder_path, exist_ok=True)
        new_full_path = os.path.join(normalized_folder_path, filename)

        if old_path and os.path.abspath(old_path) == os.path.abspath(new_full_path):
            pass
        elif old_path and os.path.exists(old_path):
            import shutil
            shutil.move(old_path, new_full_path)
        else:
            file_bytes_tuple = get_document_file_bytes(file_id)
            if file_bytes_tuple is None:
                return False, "", "이동할 원본 파일 데이터가 존재하지 않습니다."
            with open(new_full_path, "wb") as f:
                f.write(file_bytes_tuple[0])

        new_summary_path = summary_markdown_path(new_full_path)
        if old_summary_path and os.path.abspath(old_summary_path) != os.path.abspath(new_summary_path):
            if os.path.exists(old_summary_path):
                import shutil
                shutil.move(old_summary_path, new_summary_path)

        # Update DB record & SQLite
        doc["archived_path"] = new_full_path
        doc["saved_folder"] = normalized_folder_path
        doc["saved_filename"] = filename
        save_doc_to_sqlite(doc)
        write_summary_markdown(file_id, new_full_path)

        return True, old_path, new_full_path

    except Exception as e:
        return False, "", f"파일 이동 중 오류가 발생했습니다: {str(e)}"


def get_existing_archive_folders() -> List[str]:
    """Return list of existing archive directories under ARCHIVE_ROOT."""
    if not os.path.isdir(ARCHIVE_ROOT):
        return []

    folders: List[str] = []
    for dirpath, dirnames, _ in os.walk(ARCHIVE_ROOT):
        for d in dirnames:
            folders.append(os.path.join(dirpath, d).replace("\\", "/"))
    folders.insert(0, ARCHIVE_ROOT)
    return folders


def get_folder_tree() -> Dict[str, Any]:
    """Return hierarchical folder tree of stored documents."""
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

        parts = folder.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            child = "/".join(parts[:i + 1])
            _ensure_node(parent)
            _ensure_node(child)
            tree[parent]["children"][child] = tree[child]

    if not tree:
        _ensure_node(ARCHIVE_ROOT)

    all_children: set[str] = set()
    for node in tree.values():
        all_children.update(node["children"].keys())
    roots = {k: v for k, v in tree.items() if k not in all_children}

    return {
        "folders": roots,
        "total_files": sum(len(node["files"]) for node in tree.values()),
    }
