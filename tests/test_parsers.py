import io
import zipfile

import pytest

from app.parsers import DocumentParsingError, extract_text_from_file


def test_hwp_uses_docpler_converter(monkeypatch):
    docpler_hwp = pytest.importorskip("docpler.hwp")

    monkeypatch.setattr(
        docpler_hwp,
        "convert",
        lambda path: "문서 변환 결과입니다. HWP 본문 텍스트입니다.",
    )
    ole_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"invalid hwp payload"

    text = extract_text_from_file(ole_header, "hwp")

    assert "HWP 본문 텍스트" in text


def test_invalid_hwp_returns_actionable_parsing_error():
    ole_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"invalid hwp payload"

    with pytest.raises(DocumentParsingError, match=r"HWP 텍스트 추출.*"):
        extract_text_from_file(ole_header, "hwp")


def test_valid_hwp_x_zip_uses_xml_fallback_when_needed():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("Contents/section0.xml", "<p>HWPX fallback text with enough content.</p>")

    text = extract_text_from_file(stream.getvalue(), "hwpx")

    assert "HWPX fallback text" in text
