from app.core.exceptions import ai_response_invalid
from app.core.security import mask_data, mask_text
from app.services.openai_client import request_document_summary


STRING_FIELDS = {"document_overview", "document_purpose", "conclusion_or_key_message"}
LIST_FIELDS = {"main_contents"}


def create_summary(source_text: str, analysis: dict) -> dict:
    """Create a factual summary only from the extracted text and analysis result."""
    summary = request_document_summary(mask_text(source_text), mask_data(analysis))
    if not isinstance(summary, dict):
        raise ai_response_invalid("AI 요약 응답 형식이 올바르지 않습니다.")

    for field in STRING_FIELDS:
        if not isinstance(summary.get(field), str):
            raise ai_response_invalid(f"AI 요약 응답에 {field} 항목이 없습니다.")
    for field in LIST_FIELDS:
        if not isinstance(summary.get(field), list) or not all(
            isinstance(item, str) for item in summary[field]
        ):
            raise ai_response_invalid(f"AI 요약 응답의 {field} 항목이 올바르지 않습니다.")

    return {field: summary[field] for field in STRING_FIELDS | LIST_FIELDS}
