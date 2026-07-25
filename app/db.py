import os
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from app.schemas import SummaryData, ValidationData

# In-memory database store for MVP
document_db: Dict[str, Dict[str, Any]] = {}
document_files: Dict[str, bytes] = {}

ARCHIVE_ROOT = "output"


def get_database_status() -> Dict[str, Any]:
    """Return an explicit health report for the MVP database backend."""
    try:
        root_exists = os.path.isdir(ARCHIVE_ROOT)
        return {
            "connected": True,
            "backend": "in_memory",
            "persistent": False,
            "document_count": len(document_db),
            "file_count": len(document_files),
            "archive_root": ARCHIVE_ROOT,
            "archive_root_exists": root_exists,
            "migration_recommendation": "운영 환경에서는 SQLite 또는 PostgreSQL로 교체하고 DATABASE_URL 기반 저장소를 사용해야 합니다.",
        }
    except Exception as exc:
        return {"connected": False, "backend": "in_memory", "error": type(exc).__name__}


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
        lines.append(f"### {item.category}")
        lines.extend(f"- {point}" for point in item.points)
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
                lines.extend(f"- [{item.category}] {item.content_summary}" for item in analysis.core_structure)
                lines.append("")
            if getattr(analysis, "key_sentences", None):
                lines.append("### 핵심 문장")
                lines.extend(f"- {item.text}" for item in analysis.key_sentences)
                lines.append("")
        if getattr(validation, "issue_list", None):
            lines.append("### 검증 이슈")
            for issue in validation.issue_list:
                lines.extend([f"- [{issue.issue_type}] {issue.issue_title}: {issue.reason_description}", f"  - 근거: {issue.relevant_original_evidence}"])
            lines.append("")
        if getattr(validation, "human_review_checklist", None):
            lines.append("### 사람 확인 체크리스트")
            lines.extend(f"- [{'x' if item.checked else ' '}] {item.title}: {item.description}" for item in validation.human_review_checklist)
            lines.append("")
        if getattr(validation, "error_message", None):
            lines.extend([f"> 검증 오류: {validation.error_message}", ""])

    markdown_path = summary_markdown_path(archived_path)
    with open(markdown_path, "w", encoding="utf-8", newline="\n") as markdown_file:
        markdown_file.write("\n".join(lines).rstrip() + "\n")
    doc["summary_path"] = markdown_path
    return markdown_path


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

def store_uploaded_document(file_id: str, original_filename: str, format_str: str, file_bytes: bytes, file_path: str):
    """Store raw file bytes and initial metadata."""
    document_files[file_id] = file_bytes
    
    # Rule-based recommended folder and filename
    rec_folder = f"output/archive/디지털혁신팀/"
    stem, extension = os.path.splitext(os.path.basename(original_filename))
    rec_filename = f"{datetime.now().strftime('%Y-%m-%d')}_{stem}{extension}"

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

def update_document_recommendation(file_id: str, folder_path: str) -> bool:
    if file_id not in document_db:
        return False
    document_db[file_id]["recommended_folder"] = normalize_archive_folder_path(folder_path)
    return True


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
        validation_result = getattr(validation_data, "validation_result", None)
        document_db[file_id]["status"] = "ERROR" if getattr(validation_result, "error_message", None) else "COMPLETED"

def update_document_results(file_id: str, analysis_data: Any, summary_data: Any, validation_data: Any) -> bool:
    """분석·요약·검증 결과를 한 트랜잭션 단위로 갱신하고 Markdown도 재생성한다."""
    if file_id not in document_db:
        return False
    doc = document_db[file_id]
    doc["analysis_data"] = analysis_data
    doc["summary_data"] = SummaryData(file_id=file_id, summary_result=summary_data)
    doc["validation_data"] = ValidationData(file_id=file_id, validation_result=validation_data)
    doc["status"] = "ERROR" if any(getattr(item, "error_message", None) for item in (analysis_data, summary_data, validation_data)) else "COMPLETED"
    archived_path = doc.get("archived_path")
    if archived_path:
        write_summary_markdown(file_id, archived_path)
    return True

def archive_and_save_document(file_id: str, folder_path: str, filename: str, document_overview: List[str], analysis_data: Any = None, summary_data: Any = None, verification_data: Any = None) -> Tuple[bool, str]:
    """
    Save original file to specified folder_path/filename and store updated summary in DB.
    """
    if file_id not in document_db or file_id not in document_files:
        return False, "문서를 찾을 수 없습니다."

    try:
        normalized_folder_path = normalize_archive_folder_path(folder_path)
        filename = build_unique_archive_filename(file_id, normalized_folder_path)
        archived_full_path = os.path.join(normalized_folder_path, filename)
        
        # Save original file bytes to destination folder
        file_bytes = document_files[file_id]
        with open(archived_full_path, "xb") as f:
            f.write(file_bytes)

        # Update DB record
        doc = document_db[file_id]
        doc["status"] = "SAVED"
        doc["archived_path"] = archived_full_path
        doc["saved_folder"] = normalized_folder_path
        doc["saved_filename"] = filename
        
        if "summary_data" in doc and doc["summary_data"]:
            doc["summary_data"].summary_result.document_overview = document_overview
        if analysis_data is not None and summary_data is not None and verification_data is not None:
            update_document_results(file_id, analysis_data, summary_data, verification_data)
        write_summary_markdown(file_id, archived_full_path)

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
        if doc.get("archived_path"):
            write_summary_markdown(file_id, doc["archived_path"])
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

    summary_path = doc.get("summary_path") or (summary_markdown_path(archived_path) if archived_path else None)
    if summary_path and os.path.exists(summary_path):
        try:
            os.remove(summary_path)
        except Exception as e:
            return False, f"요약 Markdown 삭제 중 오류: {str(e)}"

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
    old_summary_path = doc.get("summary_path") or (summary_markdown_path(old_path) if old_path else None)

    # 이동할 파일명 결정 (생략 시 기존 파일명 유지)
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
            # 아카이빙 파일이 없으면 인메모리 바이너리로 새로 생성
            file_bytes = document_files.get(file_id)
            if file_bytes is None:
                return False, "", "이동할 원본 파일 데이터가 존재하지 않습니다."
            with open(new_full_path, "wb") as f:
                f.write(file_bytes)

        new_summary_path = summary_markdown_path(new_full_path)
        if old_summary_path and os.path.abspath(old_summary_path) != os.path.abspath(new_summary_path):
            if os.path.exists(old_summary_path):
                import shutil
                shutil.move(old_summary_path, new_summary_path)

        # DB 경로 업데이트
        doc["archived_path"] = new_full_path
        doc["saved_folder"] = normalized_folder_path
        doc["saved_filename"] = filename
        write_summary_markdown(file_id, new_full_path)

        return True, old_path, new_full_path

    except Exception as e:
        return False, "", f"파일 이동 중 오류가 발생했습니다: {str(e)}"

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
