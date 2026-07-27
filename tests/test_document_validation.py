import pytest
from types import SimpleNamespace

from app.core.exceptions import DocumentProcessingError
from app.services.document_validation import validate_upload
from app.services.text_extraction import extract_text


def test_supported_text_file_is_valid() -> None:
    assert validate_upload("meeting.txt", b"content") == ".txt"
    assert validate_upload("scanned.png", b"image") == ".png"


@pytest.mark.parametrize("file_name, content", [("malware.exe", b"x"), ("empty.txt", b"")])
def test_invalid_upload_is_rejected(file_name: str, content: bytes) -> None:
    with pytest.raises(DocumentProcessingError):
        validate_upload(file_name, content)


def test_file_larger_than_10mb_is_rejected() -> None:
    with pytest.raises(DocumentProcessingError):
        validate_upload("large.txt", b"x" * (10 * 1024 * 1024 + 1))


def test_extract_utf8_text_and_normalize_whitespace(tmp_path) -> None:
    document = tmp_path / "meeting.txt"
    document.write_text("회의   결과\n\n\n다음 일정", encoding="utf-8")

    assert extract_text(document) == "회의 결과\n\n다음 일정"


def test_extract_empty_text_is_rejected(tmp_path) -> None:
    document = tmp_path / "empty.txt"
    document.write_text("   \n\n", encoding="utf-8")

    with pytest.raises(DocumentProcessingError, match="분석할 내용"):
        extract_text(document)


def test_extract_text_over_llm_limit_is_passed_to_analysis_policy(tmp_path, monkeypatch) -> None:
    document = tmp_path / "long.txt"
    document.write_text("가나다라마바사", encoding="utf-8")
    monkeypatch.setattr(
        "app.services.text_extraction.settings",
        SimpleNamespace(max_text_length=100_000_000, max_llm_input_chars=5),
    )

    assert extract_text(document) == "가나다라마바사"
