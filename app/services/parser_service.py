"""
app/services/parser_service.py
Document Parser Service Layer

6종 포맷(PDF, DOCX, TXT, HWP, HWPX, PPTX) 파싱 및 구조화 유틸리티.
app.parsers 모듈의 파싱 함수를 서비스 레이어로 노출합니다.

입력:  file_bytes (bytes), format_str (str), filename (str), file_size (int)
출력:  raw_text (str), structured_content (dict)
"""
from app.parsers import (
    validate_file_metadata,
    extract_text_from_file,
    structure_text,
    DocumentParsingError,
)

__all__ = [
    "validate_file_metadata",
    "extract_text_from_file",
    "structure_text",
    "DocumentParsingError",
]
