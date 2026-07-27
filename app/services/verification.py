from app.core.exceptions import ai_response_invalid, bad_request
from app.core.security import mask_data, mask_text
from app.services.openai_client import request_document_verification

ANALYSIS_STRING_FIELDS = {
    "title", "organization", "department", "recommended_category",
    "category_reason", "subject", "purpose",
}
ANALYSIS_LIST_FIELDS = {
    "table_of_contents", "key_points", "key_sentences", "keywords",
    "numerical_values", "conditions", "schedules", "decisions", "evidence",
    "review_items",
}
SUMMARY_STRING_FIELDS = {"document_overview", "document_purpose", "conclusion_or_key_message"}
SUMMARY_LIST_FIELDS = {"main_contents"}
ISSUE_FIELDS = {"category", "reason", "source_evidence", "human_check"}


def _has_expected_fields(data: object, string_fields: set[str], list_fields: set[str]) -> bool:
    if not isinstance(data, dict) or not (string_fields | list_fields).issubset(data):
        return False
    return all(isinstance(data[field], str) for field in string_fields) and all(
        isinstance(data[field], list) and all(isinstance(item, str) for item in data[field])
        for field in list_fields
    )


def verify_document(source_text: str, analysis: dict, summary: dict) -> dict:
    if not isinstance(source_text, str) or not source_text.strip():
        raise bad_request("검증을 실행하려면 선행 문서 텍스트 추출 결과가 필요합니다.")
    if not _has_expected_fields(analysis, ANALYSIS_STRING_FIELDS, ANALYSIS_LIST_FIELDS):
        raise bad_request("검증을 실행하려면 선행 AI 문서 분석 결과가 필요합니다.")
    if not _has_expected_fields(summary, SUMMARY_STRING_FIELDS, SUMMARY_LIST_FIELDS):
        raise bad_request("검증을 실행하려면 선행 AI 요약 결과가 필요합니다.")

    result = request_document_verification(mask_text(source_text), mask_data(analysis), mask_data(summary))
    if not isinstance(result.get("passed"), bool) or not isinstance(result.get("issues"), list) or not isinstance(result.get("revision_instruction"), str):
        raise ai_response_invalid("OpenAI 검증 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.")
    for issue in result["issues"]:
        if not isinstance(issue, dict) or not ISSUE_FIELDS.issubset(issue):
            raise ai_response_invalid("OpenAI 검증 문제 목록 형식이 올바르지 않습니다. 다시 시도해 주세요.")
        if not all(isinstance(issue[field], str) for field in ISSUE_FIELDS - {"source_evidence"}) or not isinstance(issue["source_evidence"], list) or not all(isinstance(item, str) for item in issue["source_evidence"]):
            raise ai_response_invalid("OpenAI 검증 문제 목록의 필드 형식이 올바르지 않습니다. 다시 시도해 주세요.")
    return result
