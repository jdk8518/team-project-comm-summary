import json

from app.core.config import settings
from app.core.exceptions import ai_response_invalid
from app.services.openai_client import request_document_analysis, request_integrated_analysis


def _validate_result(result: dict, categories: list[str]) -> dict:
    string_fields = {
        "title", "organization", "department", "recommended_category",
        "category_reason", "subject", "purpose",
    }
    list_fields = {
        "table_of_contents", "key_points", "key_sentences", "keywords",
        "numerical_values", "conditions", "schedules", "decisions", "evidence",
        "review_items",
    }
    missing = [field for field in string_fields | list_fields if field not in result]
    invalid = [field for field in string_fields if not isinstance(result.get(field), str)]
    invalid += [field for field in list_fields if not isinstance(result.get(field), list) or not all(isinstance(item, str) for item in result.get(field, []))]
    if missing or invalid:
        raise ai_response_invalid("OpenAI 분석 응답에 필수 항목이 없거나 형식이 올바르지 않습니다. 다시 시도해 주세요.")
    if result["recommended_category"] not in categories:
        result["review_items"].append("AI 추천 유형이 사용자 지정 카테고리에 없어 최종 선택이 필요합니다.")
        result["recommended_category"] = "확인 필요"
    return result


def _split_text(text: str) -> list[str]:
    limit = settings.max_llm_input_chars
    overlap = min(settings.chunk_overlap_chars, max(0, limit // 4))
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start + limit // 2, end), text.rfind(". ", start + limit // 2, end))
            if boundary > start:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    if len(chunks) > settings.max_analysis_chunks:
        raise ai_response_invalid("문서 분할 수가 설정된 최대 분석 횟수를 초과했습니다. 입력 한도 또는 최대 분할 수를 조정해 주세요.")
    return [chunk for chunk in chunks if chunk]


def _batches(results: list[dict]) -> list[list[dict]]:
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_size = 2
    for result in results:
        size = len(json.dumps(result, ensure_ascii=False)) + 1
        if size > settings.max_llm_input_chars:
            raise ai_response_invalid("부분 분석 결과가 LLM 입력 한도를 초과했습니다. 입력 한도 또는 분석 출력 크기를 조정해 주세요.")
        if current and current_size + size > settings.max_llm_input_chars:
            batches.append(current)
            current, current_size = [], 2
        current.append(result)
        current_size += size
    if current:
        batches.append(current)
    return batches


def analyze_document(text: str, categories: list[str]) -> dict:
    if len(text) <= settings.max_llm_input_chars:
        return _validate_result(request_document_analysis(text, categories), categories)

    partial_results = [_validate_result(request_document_analysis(chunk, categories), categories) for chunk in _split_text(text)]
    rounds = 0
    while len(partial_results) > 1:
        next_results = [_validate_result(request_integrated_analysis(batch, categories), categories) for batch in _batches(partial_results)]
        if len(next_results) >= len(partial_results):
            raise ai_response_invalid("부분 분석 결과를 현재 LLM 입력 한도 안에서 통합할 수 없습니다. 입력 한도를 조정해 주세요.")
        partial_results = next_results
        rounds += 1
    result = partial_results[0]
    result["long_document_policy"] = {"chunk_count": len(_split_text(text)), "integration_rounds": rounds}
    return result
