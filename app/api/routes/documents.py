import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

from app.agents.document_workflow import analyze_extracted_document
from app.api.schemas.documents import AnalysisResponse, AnalyzeRequest, FolderDocumentListResponse, SavePreviewRequest, SaveResultRequest, TextExtractionResponse, VerificationRequest, VerificationResponse
from app.core.config import settings
from app.core.exceptions import bad_request
from app.services.analysis_session import get_session, save_session
from app.services.document_validation import SUPPORTED_EXTENSIONS, validate_upload
from app.services.result_presenter import present_result
from app.services.result_storage import build_preview, save_result
from app.services.text_extraction import extract_text
from app.services.verification import verify_document
from app.utils.file_utils import find_document_date

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _supported_documents(folder: Path) -> list[dict]:
    documents = []
    for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            file_stat = path.stat()
            documents.append({
                "file_name": path.name,
                "file_type": path.suffix.lstrip(".").upper(),
                "file_size": file_stat.st_size,
                "modified_date": datetime.fromtimestamp(file_stat.st_mtime).date().isoformat(),
            })
    return documents


def _save_extracted_session(document_id: str, document: dict, extracted_text: str) -> None:
    save_session(document_id, {
        "document_id": document_id,
        "status": "EXTRACTED",
        "document": document,
        "extracted_text": extracted_text,
    })


def _verify_session_document(document_id: str, request: VerificationRequest) -> dict:
    result = get_session(document_id)
    verification = verify_document(
        request.source_text or result.get("extracted_text", ""),
        request.analysis or result.get("analysis", {}),
        request.summary or result.get("summary", {}),
    )
    result["verification"] = verification
    result["status"] = "SUCCESS"
    save_session(document_id, result)
    return verification


@router.get("/folder", response_model=FolderDocumentListResponse, summary="지정 폴더의 지원 문서 목록 조회")
def list_folder_documents(folder_path: str) -> dict:
    folder = Path(folder_path).expanduser()
    if not folder.exists() or not folder.is_dir():
        raise bad_request("확인할 수 있는 폴더 경로를 입력해 주세요.")
    return {"folder_path": str(folder), "documents": _supported_documents(folder)}


@router.post("/extract", response_model=TextExtractionResponse, summary="문서 텍스트 추출")
async def extract_document_text(file: UploadFile = File(...)) -> dict:
    file_name = file.filename or "document"
    content = await file.read()
    suffix = validate_upload(file_name, content)
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / file_name
        path.write_bytes(content)
        text = extract_text(path)
        reference_date, date_source = find_document_date(text, path)
    document_id = str(uuid.uuid4())
    document = {
        "file_name": file_name, "file_type": suffix.lstrip(".").upper(), "file_size": len(content),
        "reference_date": reference_date.isoformat(), "reference_date_source": date_source,
    }
    _save_extracted_session(document_id, document, text)
    return {
        "document_id": document_id, "file_name": file_name, "file_type": suffix.lstrip(".").upper(),
        "file_size": len(content), "reference_date": reference_date.isoformat(),
        "reference_date_source": date_source, "text_length": len(text), "text_preview": text[:1000],
    }


@router.post("/{document_id}/analyze", response_model=AnalysisResponse, summary="추출 완료 문서 AI 분석·분류 추천")
def analyze_document(document_id: str, request: AnalyzeRequest) -> dict:
    extracted = get_session(document_id)
    if extracted.get("status") != "EXTRACTED":
        raise bad_request("텍스트 추출이 완료된 문서만 AI 분석할 수 있습니다.")
    categories = [category.strip() for category in request.categories if category.strip()] or list(settings.default_categories)
    result = analyze_extracted_document(document_id, extracted["document"], extracted["extracted_text"], categories)
    result["extracted_text"] = extracted["extracted_text"]
    save_session(document_id, result)
    return present_result(result)


@router.post("/{document_id}/save-preview", summary="Markdown 저장 경로 미리보기")
def preview_document_save(document_id: str, request: SavePreviewRequest) -> dict:
    return build_preview(get_session(document_id), request.document_type, request.reference_date)


@router.post("/{document_id}/save", summary="검토 확인 후 Markdown 저장")
def save_document_result(document_id: str, request: SaveResultRequest) -> dict:
    result = get_session(document_id)
    preview = build_preview(result, request.document_type, request.reference_date)
    return save_result(result, preview, request.review_confirmed, request.user_confirmed)


@router.post("/verify", response_model=VerificationResponse, summary="원문·분석·요약 결과 검증")
def verify_document_result(request: VerificationRequest) -> dict:
    if request.document_id:
        return _verify_session_document(request.document_id, request)
    return verify_document(request.source_text or "", request.analysis or {}, request.summary or {})
