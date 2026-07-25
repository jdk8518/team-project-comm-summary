"""
app/parsers.py
문서 파일 유효성 검증 및 텍스트 추출 기능을 담습니다.

리팩토링 내용 (refactoring-coach 기준):
  - PDF 이미지 전용 문서 대응: 텍스트 추출 후 20자 미만이면 pytesseract OCR 폴백 시도
  - OCR 시도 후에도 텍스트 부족이면 기존과 동일한 422 오류를 발생시킴
  - 기존 API 경로·오류 메시지 형식은 유지
"""
import os
import io
import re
from typing import Tuple, Dict, Any, List

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".hwp", ".hwpx", ".pptx"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB
OCR_MIN_CHARS = 20                        # 이 기준 미만이면 OCR 폴백 시도


class DocumentParsingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ─────────────────────────────────────────────────────────────
# 1. 유효성 검증 (확장자, 용량)
# ─────────────────────────────────────────────────────────────

def validate_file_metadata(filename: str, size_bytes: int) -> str:
    """파일 확장자와 용량(50MB)을 검증하고 포맷 문자열을 반환합니다."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentParsingError(
            f"지원하지 않는 파일 형식입니다. (지원 형식: PDF, DOCX, TXT, HWP, HWPX, PPTX / 입력: {ext})",
            status_code=400,
        )
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise DocumentParsingError(
            f"파일 크기가 제한 용량(50MB)을 초과했습니다. (입력 크기: {size_bytes / (1024*1024):.1f}MB)",
            status_code=413,
        )
    return ext[1:].upper()


# ─────────────────────────────────────────────────────────────
# 2. 형식별 텍스트 추출
# ─────────────────────────────────────────────────────────────

def extract_text_from_file(file_bytes: bytes, file_ext: str) -> str:
    """
    파일 형식에 맞게 텍스트를 추출합니다.
    PDF의 경우 텍스트가 부족하면 OCR(pytesseract)으로 재시도합니다.
    """
    ext = file_ext.lower().replace(".", "")
    try:
        if ext == "txt":
            extracted_text = _extract_txt(file_bytes)
        elif ext == "pdf":
            extracted_text = _extract_pdf(file_bytes)
        elif ext == "docx":
            extracted_text = _extract_docx(file_bytes)
        elif ext in ("hwpx", "hwp"):
            extracted_text = _extract_hwp(file_bytes)
        elif ext == "pptx":
            extracted_text = _extract_pptx(file_bytes)
        else:
            extracted_text = ""
    except DocumentParsingError:
        raise
    except Exception as e:
        raise DocumentParsingError(f"문서 파싱 중 오류가 발생했습니다: {str(e)}", status_code=422)

    cleaned = _clean_text(extracted_text)

    if len(cleaned) < OCR_MIN_CHARS:
        raise DocumentParsingError(
            "분석할 수 있는 텍스트 내용이 존재하지 않습니다. "
            "(스캔 이미지 전용 문서는 OCR 기능이 필요합니다.)",
            status_code=422,
        )
    return cleaned


# ─────────────────────────────────────────────────────────────
# 3. 형식별 파서 (각 함수는 추출된 raw text를 반환)
# ─────────────────────────────────────────────────────────────

def _extract_txt(file_bytes: bytes) -> str:
    try:
        import chardet
        encoding = chardet.detect(file_bytes).get("encoding") or "utf-8"
    except Exception:
        encoding = "utf-8"
    return file_bytes.decode(encoding, errors="replace")


def _extract_pdf(file_bytes: bytes) -> str:
    """
    PyMuPDF로 텍스트를 추출합니다.
    추출된 텍스트가 OCR_MIN_CHARS 미만이면 pytesseract로 OCR을 시도합니다.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text = [page.get_text() for page in doc]
        text = "\n\n".join(pages_text)
    except Exception as e:
        raise DocumentParsingError(f"PDF 파싱 실패: {str(e)}", status_code=422)

    if len(_clean_text(text)) >= OCR_MIN_CHARS:
        return text

    # ── OCR 폴백: 이미지 전용 PDF ──────────────────────────
    return _ocr_pdf_fallback(file_bytes)


def _ocr_pdf_fallback(file_bytes: bytes) -> str:
    """
    pytesseract + Pillow를 사용해 PDF 페이지를 이미지로 변환한 뒤 OCR을 수행합니다.
    pytesseract 또는 Tesseract가 설치되지 않은 경우 빈 문자열을 반환합니다.
    """
    try:
        import fitz
        from PIL import Image
        import pytesseract

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        ocr_texts: List[str] = []
        for page in doc:
            # 페이지를 2배 해상도 이미지로 렌더링
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            page_text = pytesseract.image_to_string(img, lang="kor+eng")
            if page_text.strip():
                ocr_texts.append(page_text)
        return "\n\n".join(ocr_texts)
    except ImportError:
        # pytesseract / Pillow 미설치: 빈 문자열 반환 → 상위에서 422 처리
        return ""
    except Exception:
        return ""


def _extract_docx(file_bytes: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        raise DocumentParsingError(f"DOCX 파싱 실패: {str(e)}", status_code=422)


def _extract_hwp(file_bytes: bytes) -> str:
    """HWPX/HWP 텍스트 추출. python-hwpx → zipfile XML → 바이너리 순으로 폴백."""
    # 1차 시도: python-hwpx
    try:
        from hwpx import HwpxDocument
        temp_path = "temp_parse.hwpx"
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
        doc = HwpxDocument.open(temp_path)
        text = doc.get_text() if hasattr(doc, "get_text") else "\n\n".join(str(s) for s in doc.sections)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return text
    except Exception:
        pass

    # 2차 시도: zipfile XML 파싱
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            section_files = [f for f in z.namelist() if "section" in f.lower() or "content" in f.lower()]
            texts = []
            for sf in section_files:
                content = z.read(sf).decode("utf-8", errors="ignore")
                texts.append(re.sub(r"<[^>]+>", " ", content))
            return "\n\n".join(texts)
    except Exception:
        pass

    # 3차 폴백: 바이너리 문자열 추출
    raw = file_bytes.decode("utf-8", errors="ignore")
    return re.sub(r"[^\w\s\.\,\-\:\(\)가-힣]", " ", raw)


def _extract_pptx(file_bytes: bytes) -> str:
    try:
        import pptx
        prs = pptx.Presentation(io.BytesIO(file_bytes))
        slide_texts = []
        for slide in prs.slides:
            texts = [shape.text for shape in slide.shapes if hasattr(shape, "text") and shape.text]
            if texts:
                slide_texts.append("\n".join(texts))
        return "\n\n".join(slide_texts)
    except Exception as e:
        raise DocumentParsingError(f"PPTX 파싱 실패: {str(e)}", status_code=422)


# ─────────────────────────────────────────────────────────────
# 4. 텍스트 정제 및 구조화
# ─────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """연속 빈 줄을 2줄 이하로 정규화하고 양끝 공백을 제거합니다."""
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def structure_text(cleaned_text: str) -> Dict[str, Any]:
    """정제된 텍스트를 제목과 섹션 목록으로 구조화합니다."""
    lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]
    title = lines[0] if lines else "제목 없음"

    sections: List[Dict[str, Any]] = []
    current_title = "1. 추진 배경 및 목적"
    current_lines: List[str] = []
    section_id = 1

    for line in lines[1:]:
        is_new_section = re.match(r"^\d+[.)] ", line) or ("절" in line and line.startswith("제"))
        if is_new_section:
            if current_lines:
                sections.append(_make_section(section_id, current_title, current_lines))
                section_id += 1
                current_lines = []
            current_title = line
        else:
            current_lines.append(line)

    # 마지막 섹션 추가
    if current_lines or not sections:
        content = "\n".join(current_lines) if current_lines else cleaned_text
        sections.append(_make_section(section_id, current_title, content_lines=None, content_str=content))

    return {"title": title, "sections": sections}


def _make_section(
    section_id: int,
    title: str,
    content_lines: List[str] | None = None,
    content_str: str | None = None,
) -> Dict[str, Any]:
    content = "\n".join(content_lines) if content_lines is not None else (content_str or "")
    return {"section_id": section_id, "section_title": title, "content": content, "content_type": "paragraph"}
