import json
import os

from openai import OpenAI

from app.core.config import settings
from app.core.exceptions import ai_response_invalid, ai_unavailable


def _request_json(prompt: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ai_unavailable("OPENAI_API_KEY가 설정되지 않았습니다. 로컬 기본 분석은 제공하지 않습니다.")
    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ai_response_invalid("OpenAI가 빈 분석 응답을 반환했습니다. 다시 시도해 주세요.")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise ai_response_invalid("OpenAI 분석 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.") from error
        if not isinstance(data, dict):
            raise ai_response_invalid("OpenAI 분석 응답이 JSON 객체가 아닙니다. 다시 시도해 주세요.")
        return data
    except Exception as error:
        if hasattr(error, "status_code"):
            raise
        raise ai_unavailable("OpenAI 문서 분석 처리에 실패했습니다. API 설정과 네트워크 상태를 확인한 뒤 재시도해 주세요.") from error


def request_document_analysis(text: str, categories: list[str]) -> dict:
    prompt = f"""업무 문서를 분석해 JSON 객체만 반환하세요.
카테고리 후보: {', '.join(categories)}
필수 키와 타입:
- title, organization, department, subject, purpose, recommended_category, category_reason: 문자열
- table_of_contents, key_points, key_sentences, keywords, numerical_values, conditions,
  schedules, decisions, evidence, review_items: 문자열 배열
table_of_contents에는 문서의 목차 또는 본문 제목 순서를, key_sentences에는 핵심 원문 문장을,
numerical_values와 conditions에는 원문에 있는 수치·기한·조건만 넣으세요.
evidence는 원문에서 짧게 인용한 근거 문장만 사용하세요. 요약문을 작성하지 말고,
근거 없는 사실이나 최종 업무 판단을 만들지 마세요. 불명확하거나 누락된 값은 review_items에 넣으세요.

문서:
{text}"""
    return _request_json(prompt)


def request_integrated_analysis(partial_results: list[dict], categories: list[str]) -> dict:
    prompt = f"""아래는 긴 업무 문서를 여러 구간으로 나누어 분석한 결과입니다.
카테고리 후보: {', '.join(categories)}
부분 결과를 중복 없이 통합하여 JSON 객체만 반환하세요.
필수 키와 타입은 title, organization, department, recommended_category, category_reason, subject, purpose(문자열),
table_of_contents, key_points, key_sentences, keywords, numerical_values, conditions,
schedules, decisions, evidence, review_items(문자열 배열)입니다.
근거 없는 사실을 추가하지 말고, 서로 상충하거나 누락된 내용은 review_items에 넣으세요.

부분 분석 결과:
{json.dumps(partial_results, ensure_ascii=False)}"""
    return _request_json(prompt)


def request_document_summary(source_text: str, analysis: dict) -> dict:
    prompt = f"""업무 문서의 원문과 분석 결과를 근거로 JSON 객체만 반환하세요.
원문과 분석 결과에 없는 사실, 추측, 과장된 단정, 새로운 일정·수치·결정 사항을 추가하지 마세요.
불명확한 내용은 일반화하지 말고 분석 결과의 review_items에 있는 검토 필요 맥락을 유지하세요.

필수 키와 타입:
- document_overview, document_purpose, conclusion_or_key_message: 문자열
- main_contents: 문자열 배열

원문:
{source_text}

문서 분석 결과:
{json.dumps(analysis, ensure_ascii=False)}"""
    return _request_json(prompt)


def request_document_verification(source_text: str, analysis: dict, summary: dict) -> dict:
    prompt = f"""당신은 업무 문서 결과를 점검하는 Validator입니다.
원문, AI 분석 결과, AI 요약 결과만 근거로 JSON 객체를 반환하세요.
새로운 사실을 생성하거나 원문·분석·요약을 수정하거나 보완하지 마세요.
근거가 부족하면 문제로 단정하지 말고 사람이 확인할 항목으로 표시하세요.

검증 항목:
1. 중요 내용 누락
2. 원문과 요약의 의미 불일치
3. 수치와 날짜
4. 조건과 예외
5. 원문보다 강한 단정
6. 추가 확인이 필요한 표현

반환 형식:
{{
  "passed": true 또는 false,
  "issues": [
    {{"category": "검증 항목", "reason": "문제가 되는 이유", "source_evidence": ["관련 원문 근거"], "human_check": "사람이 확인할 항목"}}
  ],
  "revision_instruction": "새 사실 없이 수정·재검토할 방향"
}}

원문:
{source_text}

AI 문서 분석 결과:
{json.dumps(analysis, ensure_ascii=False)}

AI 요약 결과:
{json.dumps(summary, ensure_ascii=False)}"""
    return _request_json(prompt)
