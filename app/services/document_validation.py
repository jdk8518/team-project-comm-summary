from pathlib import Path

from app.core.config import settings
from app.core.exceptions import unprocessable

SUPPORTED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".hwp", ".hwpx", ".ppt", ".pptx", ".txt",
    ".jpg", ".jpeg", ".png", ".tif", ".tiff",
}


def validate_upload(file_name: str, content: bytes) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise unprocessable("지원하지 않는 파일입니다. PDF, DOC, DOCX, HWP, HWPX, PPT, PPTX, TXT, JPG, JPEG, PNG, TIFF 파일을 업로드해 주세요.")
    if not content:
        raise unprocessable("분석할 내용이 없는 파일입니다. 내용이 포함된 문서를 다시 업로드해 주세요.")
    if len(content) > settings.max_file_size:
        raise unprocessable("파일 크기는 10MB 이하로 업로드해 주세요.")
    return suffix
