import os
import io
import re
from typing import Tuple, Dict, Any, List

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".hwp", ".hwpx", ".pptx"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

class DocumentParsingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def validate_file_metadata(filename: str, size_bytes: int) -> str:
    """Validate file extension and size (50MB max)."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentParsingError(
            f"지원하지 않는 파일 형식입니다. (지원 형식: PDF, DOCX, TXT, HWP, HWPX, PPTX / 입력: {ext})",
            status_code=400
        )
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise DocumentParsingError(
            f"파일 크기가 제한 용량(50MB)을 초과했습니다. (입력 크기: {size_bytes / (1024*1024):.1f}MB)",
            status_code=413
        )
    return ext[1:].upper()

def extract_text_from_file(file_bytes: bytes, file_ext: str) -> str:
    """Extract text based on file format."""
    ext = file_ext.lower().replace(".", "")
    extracted_text = ""

    try:
        if ext == "txt":
            try:
                import chardet
                detected = chardet.detect(file_bytes)
                encoding = detected.get("encoding") or "utf-8"
                extracted_text = file_bytes.decode(encoding, errors="replace")
            except Exception:
                extracted_text = file_bytes.decode("utf-8", errors="replace")

        elif ext == "pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                pages = [page.get_text() for page in doc]
                extracted_text = "\n\n".join(pages)
            except Exception as e:
                raise DocumentParsingError(f"PDF 파싱 실패: {str(e)}", status_code=422)

        elif ext == "docx":
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                extracted_text = "\n\n".join(paragraphs)
            except Exception as e:
                raise DocumentParsingError(f"DOCX 파싱 실패: {str(e)}", status_code=422)

        elif ext in ["hwpx", "hwp"]:
            # Rule 8 in AGENTS.md: python-hwpx for HWPX
            parsed = False
            try:
                from hwpx import HwpxDocument
                # Try opening stream or writing temporary file for python-hwpx
                temp_hwpx_path = "temp_parse.hwpx"
                with open(temp_hwpx_path, "wb") as f:
                    f.write(file_bytes)
                doc = HwpxDocument.open(temp_hwpx_path)
                # Extract text sections from HwpxDocument if method exists
                if hasattr(doc, "get_text"):
                    extracted_text = doc.get_text()
                elif hasattr(doc, "sections"):
                    extracted_text = "\n\n".join([str(sec) for sec in doc.sections])
                parsed = True
                if os.path.exists(temp_hwpx_path):
                    os.remove(temp_hwpx_path)
            except Exception:
                parsed = False

            if not parsed:
                # Fallback zipfile xml parsing for hwpx or binary text extraction
                import zipfile
                try:
                    with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                        section_files = [f for f in z.namelist() if "section" in f.lower() or "content" in f.lower()]
                        texts = []
                        for sf in section_files:
                            content = z.read(sf).decode("utf-8", errors="ignore")
                            # Strip XML tags
                            clean_t = re.sub(r"<[^>]+>", " ", content)
                            texts.append(clean_t)
                        extracted_text = "\n\n".join(texts)
                except Exception:
                    # Generic string extraction fallback
                    raw_str = file_bytes.decode("utf-8", errors="ignore")
                    extracted_text = re.sub(r"[^\w\s\.\,\-\:\(\)가-힣]", " ", raw_str)

        elif ext == "pptx":
            try:
                import pptx
                prs = pptx.Presentation(io.BytesIO(file_bytes))
                slide_texts = []
                for slide in prs.slides:
                    slide_str = []
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text:
                            slide_str.append(shape.text)
                    if slide_str:
                        slide_texts.append("\n".join(slide_str))
                extracted_text = "\n\n".join(slide_texts)
            except Exception as e:
                raise DocumentParsingError(f"PPTX 파싱 실패: {str(e)}", status_code=422)

    except DocumentParsingError:
        raise
    except Exception as e:
        raise DocumentParsingError(f"문서 파싱 중 오류가 발생했습니다: {str(e)}", status_code=422)

    # Clean text
    cleaned_text = re.sub(r"\n{3,}", "\n\n", extracted_text).strip()

    # Check for empty text / scan OCR requirement
    if len(cleaned_text.strip()) < 20:
        raise DocumentParsingError(
            "문서 내 분석할 수 있는 텍스트 내용이 존재하지 않습니다. (스캔 이미지 전용 문서는 OCR 기능이 필요합니다.)",
            status_code=422
        )

    return cleaned_text

def structure_text(cleaned_text: str) -> Dict[str, Any]:
    """Structure cleaned text into title and sections."""
    lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]
    title = lines[0] if lines else "제목 없음"
    
    sections = []
    current_title = "1. 추진 배경 및 목적"
    current_lines = []
    section_id = 1

    for line in lines[1:]:
        if re.match(r"^\d+[\.\)]\s+", line) or line.startswith("제") and "절" in line:
            if current_lines:
                sections.append({
                    "section_id": section_id,
                    "section_title": current_title,
                    "content": "\n".join(current_lines),
                    "content_type": "paragraph"
                })
                section_id += 1
                current_lines = []
            current_title = line
        else:
            current_lines.append(line)

    if current_lines or not sections:
        sections.append({
            "section_id": section_id,
            "section_title": current_title,
            "content": "\n".join(current_lines) if current_lines else cleaned_text,
            "content_type": "paragraph"
        })

    return {
        "title": title,
        "sections": sections
    }
