import re
from typing import Any


def _mask_name(match: re.Match[str]) -> str:
    name = match.group(1)
    return f"성명: {name[0]}{'0' * (len(name) - 1)}"


def mask_text(value: str) -> str:
    """Mask display and saved-output values without changing the original file."""
    value = re.sub(r"성명\s*[:：]\s*([가-힣]{2,4})", _mask_name, value)
    value = re.sub(r"\b(01[016789])[- ]?(\d{3,4})[- ]?(\d{4})\b", lambda m: f"{m.group(1)}-{m.group(2)}-XXXX", value)
    value = re.sub(r"\b(?:19|20)\d{2}[-.]?(?:0[1-9]|1[0-2])[-.]?(?:0[1-9]|[12]\d|3[01])\b", "0000-**-**", value)
    value = re.sub(r"\b\d{2,4}-\d{2,6}-\d{2,8}\b", "[계좌정보 마스킹]", value)
    value = re.sub(r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)[^\n,]{0,35}(?:로|길|동)\s*\d*", "[주소 마스킹]", value)
    return re.sub(r"대외비|기밀|비공개|보안등급", "[기밀정보]", value, flags=re.IGNORECASE)


def mask_data(value: Any) -> Any:
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, list):
        return [mask_data(item) for item in value]
    if isinstance(value, dict):
        return {key: mask_data(item) for key, item in value.items()}
    return value
