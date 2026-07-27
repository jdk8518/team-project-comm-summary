import re
from datetime import date, datetime
from pathlib import Path


def clean_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def find_document_date(text: str, path: Path) -> tuple[date, str]:
    match = re.search(r"\b((?:19|20)\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))), "문서 기재일"
        except ValueError:
            pass
    stat = path.stat()
    created = getattr(stat, "st_birthtime", None) or stat.st_ctime
    return datetime.fromtimestamp(created).date(), "파일 생성일"


def safe_stem(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "", value).strip()
    return cleaned or "문서분석결과"
