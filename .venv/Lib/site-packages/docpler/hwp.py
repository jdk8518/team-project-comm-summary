"""
HWP (한글 워드프로세서) → Markdown 변환기.
markitdown 플러그인 및 독립 사용 모두 지원.
"""
from pathlib import Path
from typing import Any, BinaryIO, Optional


ACCEPTED_EXTENSIONS = frozenset({".hwp"})
ACCEPTED_MIME_TYPES = frozenset({
    "application/x-hwp",
    "application/haansofthwp",
    "application/vnd.hancom.hwp",
})


def convert(path: str | Path) -> str:
    """HWP 파일을 Markdown 문자열로 변환한다."""
    from ._docpler import hwp_to_markdown
    return hwp_to_markdown(str(path))


class HwpConverter:
    """markitdown 컨버터: HWP 파일을 Markdown으로 변환."""

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: Any,
        **kwargs,
    ) -> bool:
        ext = getattr(stream_info, "extension", "") or ""
        mime = getattr(stream_info, "mimetype", "") or ""
        return ext.lower() in ACCEPTED_EXTENSIONS or mime in ACCEPTED_MIME_TYPES

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: Any,
        **kwargs,
    ):
        from markitdown import DocumentConverterResult

        local_path = getattr(stream_info, "local_path", None)
        if not local_path:
            return None

        markdown_text = convert(local_path)
        return DocumentConverterResult(markdown=markdown_text)


class HwpConverterPlugin:
    """markitdown 플러그인 엔트리포인트."""

    @staticmethod
    def register_converters(markitdown_instance, **kwargs):
        markitdown_instance.register_converter(HwpConverter())
