"""
app/services.py
AI 문서 분석, 요약, 검증 서비스 로직을 담습니다.

리팩토링 내용 (refactoring-coach 기준):
  - 환경 변수 읽기를 app/core/config.get_ai_config()로 일원화 (3곳 중복 제거)
  - OpenAI / Gemini LLM 호출을 _call_llm_api() 공통 함수로 분리
  - 각 서비스 함수는 프롬프트 생성 → LLM 호출 → 결과 파싱 → 폴백 순서를 명확히 유지
"""
import re
import json
import requests
from typing import Dict, Any, List, Optional

from app.core.config import get_ai_config, is_api_key_valid
from app.schemas import (
    AnalysisData, CoreStructure, KeySentence, KeyKeywords,
    VerificationCandidate, EvidenceGrounding,
    SummaryData, SummaryResult, MainContentItem,
    ValidationData, ValidationResult, ValidationIssueItem, HumanChecklistItem
)


# ─────────────────────────────────────────────────────────────
# 공통 LLM 호출 헬퍼 (OpenAI / Gemini 중복 코드 제거)
# ─────────────────────────────────────────────────────────────

def _call_llm_api(prompt: str, system_msg: str, temperature: float = 0.2) -> tuple[dict | None, str | None]:
    """
    설정된 AI 프로바이더로 LLM API를 호출하고 JSON dict를 반환합니다.
    호출 실패 또는 파싱 실패 시 None을 반환하며, API 키는 로그에 출력하지 않습니다.

    주의: monkeypatch.setattr(services, 'get_ai_config', ...)이 동작하도록
    app.services 모듈을 통해 get_ai_config, _call_openai, _call_google,
    _call_deepseek를 late-binding으로 호출합니다.
    """
    import app.services as _svc
    cfg = _svc.get_ai_config()

    if cfg.provider == "mock":
        return None, None

    if not is_api_key_valid(cfg.api_key):
        return None, f"{cfg.provider} AI API 키가 설정되지 않았습니다."

    if cfg.provider == "openai":
        return _svc._call_openai(cfg.api_key, cfg.model, system_msg, prompt, temperature)

    if cfg.provider in ("google", "gemini"):
        return _svc._call_google(cfg.api_key, cfg.model, system_msg, prompt)

    if cfg.provider == "deepseek":
        return _svc._call_deepseek(cfg.api_key, cfg.model, system_msg, prompt, temperature)

    return None, f"지원하지 않는 AI provider입니다: {cfg.provider}"



def _call_openai(api_key: str, model: str, system_msg: str, prompt: str, temperature: float) -> tuple[dict | None, str | None]:
    return _call_openai_compatible(api_key, model, system_msg, prompt, temperature)


def _call_deepseek(api_key: str, model: str, system_msg: str, prompt: str, temperature: float) -> tuple[dict | None, str | None]:
    return _call_openai_compatible(
        api_key,
        model,
        system_msg,
        prompt,
        temperature,
        base_url="https://api.deepseek.com",
        provider_name="DeepSeek",
    )


def _call_openai_compatible(
    api_key: str,
    model: str,
    system_msg: str,
    prompt: str,
    temperature: float,
    base_url: str | None = None,
    provider_name: str = "OpenAI",
) -> tuple[dict | None, str | None]:
    try:
        from openai import OpenAI
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if not content:
            return None, f"{provider_name} API가 빈 응답을 반환했습니다."
        return json.loads(content), None
    except json.JSONDecodeError:
        return None, f"{provider_name} API 응답이 유효한 JSON이 아닙니다."
    except Exception as exc:
        return None, f"{provider_name} API 호출 실패: {type(exc).__name__}"


def _call_google(api_key: str, model: str, system_msg: str, prompt: str) -> tuple[dict | None, str | None]:
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/{model}:generateContent?key={api_key}"
        )
        resp = requests.post(
            url,
            json={
                "systemInstruction": {"parts": [{"text": system_msg}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return None, f"Google API가 HTTP {resp.status_code}를 반환했습니다."
        text_res = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if "```json" in text_res:
            text_res = text_res.split("```json")[1].split("```")[0].strip()
        return json.loads(text_res), None
    except json.JSONDecodeError:
        return None, "Google API 응답이 유효한 JSON이 아닙니다."
    except Exception as exc:
        return None, f"Google API 호출 실패: {type(exc).__name__}"


# ─────────────────────────────────────────────────────────────
# 1. AI 문서 핵심 구조 분석
# ─────────────────────────────────────────────────────────────

def run_document_analysis(
    file_id: str,
    raw_text: str,
    structured_content: Dict[str, Any],
    existing_departments: List[str] | None = None,
) -> AnalysisData:
    """문서 원문을 AI로 분석하여 8대 핵심 구조와 5대 범주 키워드를 반환합니다.

    Args:
        existing_departments: DB에 등록된 부서 목록. 전달 시 AI가 추천 부서를 응답에 포함합니다.
    """
    title = structured_content.get("title", "")
    prompt = _build_analysis_prompt(title, raw_text, existing_departments)
    system_msg = "You are a professional AI document analyst. Respond strictly in valid JSON."

    parsed, ai_error = _call_llm_api(prompt, system_msg, temperature=0.2)
    if parsed:
        result = _parse_analysis_response(file_id, parsed, title)
        if result:
            return result

        ai_error = "AI 분석 응답의 JSON 구조가 올바르지 않습니다."

    return _analysis_fallback(file_id, title, raw_text, structured_content, ai_error)


def recommend_department(
    departments: List[str],
    summary: List[str],
    purpose: str,
    message: str,
    keywords: Dict[str, List[str]],
) -> List[str]:
    """추천 후보 부서와 편집 중인 요약을 AI에 전달해 우선순위 부서를 반환합니다."""
    candidates = [dept.strip() for dept in departments if isinstance(dept, str) and dept.strip()]
    if not candidates:
        return []

    prompt = f"""다음 문서 요약을 검토하고, 후보 부서 목록 안에서 가장 적합한 부서를 1~3개 추천하세요.
후보 부서 목록 밖의 이름은 만들지 마세요. 반드시 JSON만 반환하세요.

[후보 부서]: {json.dumps(candidates, ensure_ascii=False)}
[개요]: {json.dumps(summary, ensure_ascii=False)}
[문서 목적]: {purpose}
[핵심 메시지]: {message}
[키워드]: {json.dumps(keywords, ensure_ascii=False)}

{{"recommended_departments": ["후보 부서명"]}}"""
    parsed, _ = _call_llm_api(prompt, "You are a document routing assistant. Respond strictly in valid JSON.", temperature=0.1)
    if isinstance(parsed, dict):
        recommended = parsed.get("recommended_departments", [])
        if isinstance(recommended, list):
            selected = [dept for dept in recommended if isinstance(dept, str) and dept in candidates]
            if selected:
                return selected[:3]

    # API를 사용할 수 없는 환경에서도 후보 목록에서 요약 키워드가 가장 많이 겹치는 부서를 제시합니다.
    searchable = " ".join([*summary, purpose, message, *[item for values in keywords.values() for item in values]]).lower()
    ranked = sorted(candidates, key=lambda dept: (dept.lower() in searchable, dept), reverse=True)
    return ranked[:3]


def _build_analysis_prompt(
    title: str,
    raw_text: str,
    existing_departments: List[str] | None = None,
) -> str:
    dept_section = ""
    if existing_departments:
        dept_list_str = json.dumps(existing_departments, ensure_ascii=False)
        dept_section = f"""
[등록된 부서 목록]: {dept_list_str}
위 부서 목록에서 이 문서와 가장 관련 있는 부서를 1~3개 선택하여 recommended_departments에 포함하세요.
부서 목록이 비어있으면 빈 배열을 반환하세요."""

    return f"""다음 문서를 분석하여 반드시 지정된 JSON 형식으로만 응답해 주세요.

[문서 제목]: {title}
[문서 원문]:
{raw_text[:3000]}{dept_section}

[출력 JSON 구조]:
{{
  "document_subject": "중심 주제 1문장",
  "document_purpose": "REPORT",
  "core_structure": [
    {{"category": "카테고리명", "section_id": 1, "content_summary": "내용 요약"}}
  ],
  "key_sentences": [
    {{"sentence_id": 1, "section_id": 1, "text": "원문 핵심 문장"}}
  ],
  "key_keywords": {{
    "persons": ["인물명"],
    "organizations": ["기관/부서명"],
    "schedules": ["날짜/일정"],
    "metrics": ["수치/금액"],
    "concepts": ["주요 개념"]
  }},
  "verification_candidates": [
    {{"candidate_id": "VER-01", "type": "MISSING_INFO", "target": "검증 대상", "display_tag": "원문 미기재 (확인 필요)", "evidence": "근거 위치"}}
  ],
  "evidence_grounding": [
    {{"entity_or_item": "항목명", "section_id": 1, "original_sentence": "원문 구절"}}
  ],
  "recommended_departments": ["추천부서1"]
}}"""


def _parse_analysis_response(file_id: str, data: dict, title: str) -> AnalysisData | None:
    try:
        raw_dept = data.get("recommended_departments", [])
        recommended_departments = [
            d for d in raw_dept if isinstance(d, str) and d.strip()
        ] if isinstance(raw_dept, list) else []
        return AnalysisData(
            file_id=file_id,
            analysis_status="SUCCESS",
            document_subject=data.get("document_subject", f"{title} 및 주요 안건 분석"),
            document_purpose=data.get("document_purpose", "REPORT"),
            core_structure=[CoreStructure(**cs) for cs in data.get("core_structure", [])],
            key_sentences=[KeySentence(**ks) for ks in data.get("key_sentences", [])],
            key_keywords=KeyKeywords(**data.get("key_keywords", {})),
            verification_candidates=[VerificationCandidate(**vc) for vc in data.get("verification_candidates", [])],
            evidence_grounding=[EvidenceGrounding(**eg) for eg in data.get("evidence_grounding", [])],
            recommended_departments=recommended_departments,
        )
    except Exception:
        return None


def _analysis_fallback(
    file_id: str,
    title: str,
    raw_text: str,
    structured_content: Dict[str, Any],
    error_message: Optional[str] = None,
) -> AnalysisData:
    """LLM 호출 실패 시 규칙 기반으로 분석 결과를 생성합니다."""
    import app.services as _svc
    cfg = _svc.get_ai_config()
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    document_purpose = "DECISION_AND_REPORT" if ("보고" in title or "의결" in title) else "REPORT"

    sections = structured_content.get("sections", [])
    core_structures = [
        CoreStructure(
            category=sec.get("section_title", "주요 내용"),
            section_id=sec.get("section_id", 1),
            content_summary=(sec.get("content", "")[:80] + "...") if len(sec.get("content", "")) > 80 else sec.get("content", ""),
        )
        for sec in sections
    ]

    key_sentences = [
        KeySentence(sentence_id=idx, section_id=1 if idx <= 2 else 2, text=line)
        for idx, line in enumerate([l for l in lines if len(l) > 20][:4], 1)
    ]

    persons = list(set(re.findall(r"([가-힣]{2,4}\s*(?:팀장|수석|과장|부장|이사|대표|주무관))", raw_text))) or ["홍길동 팀장"]
    organizations = list(set(re.findall(r"([가-힣]{2,10}(?:팀|부|처|청|원|위원회|기업))", raw_text))) or ["디지털혁신팀"]
    schedules = list(set(re.findall(r"(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2}일?)", raw_text))) or ["2026-08-31"]
    metrics = list(set(re.findall(r"(\d+(?:\.\d+)?(?:%|원|백만원|억원|개|건|명|MB))", raw_text))) or ["예산 집행률 85%"]

    return AnalysisData(
        file_id=file_id,
        analysis_status="SUCCESS" if cfg.provider == "mock" and not error_message else "ERROR",
        document_subject=f"{title} 중심 안건 및 주요 내용 보고",
        document_purpose=document_purpose,
        core_structure=core_structures,
        key_sentences=key_sentences,
        key_keywords=KeyKeywords(
            persons=persons[:3],
            organizations=organizations[:3],
            schedules=schedules[:3],
            metrics=metrics[:3],
            concepts=["AI Agent", "FastAPI", "HWPX 파싱", "문서 분석", f"Provider: {cfg.provider}"],
        ),
        verification_candidates=[
            VerificationCandidate(
                candidate_id="VER-01",
                type="MISSING_INFO",
                target="시범 적용 결과 보고 일정",
                display_tag="원문 미기재 (확인 필요)",
                evidence="3절: 시범 적용 후 피드백 수집 예정",
            )
        ],
        evidence_grounding=[
            EvidenceGrounding(
                entity_or_item="MVP 구축 기한",
                section_id=1,
                original_sentence=schedules[0] if schedules else "2026-08-31",
            )
        ],
        error_message=error_message,
    )


# ─────────────────────────────────────────────────────────────
# 2. AI 요약 생성
# ─────────────────────────────────────────────────────────────

def run_document_summarization(
    file_id: str,
    raw_text: str,
    analysis_data: AnalysisData,
) -> SummaryData:
    """원문 텍스트와 분석 결과를 바탕으로 팩트 보존 4대 요소 요약을 생성합니다."""
    prompt = _build_summary_prompt(raw_text, analysis_data)
    system_msg = "You are a strict, factual document summarizer. Output strictly valid JSON."

    parsed, ai_error = _call_llm_api(prompt, system_msg, temperature=0.1)
    if parsed:
        result = _parse_summary_response(file_id, parsed, analysis_data)
        if result:
            return result

        ai_error = "AI 요약 응답의 JSON 구조가 올바르지 않습니다."

    return _summary_fallback(file_id, analysis_data, ai_error)


def _build_summary_prompt(raw_text: str, analysis_data: AnalysisData) -> str:
    return f"""다음 [문서 원문]과 [분석 결과]를 바탕으로 팩트 기반 요약문을 작성하여 지정된 JSON 형식으로만 응답해 주세요.

[분석 중심주제]: {analysis_data.document_subject}
[분석 작성목적]: {analysis_data.document_purpose}
[문서 원문]:
{raw_text[:3000]}

[출력 JSON 구조]:
{{
  "document_overview": ["문서 개요 요약 문장 1", "문서 개요 요약 문장 2"],
  "document_purpose": "{analysis_data.document_purpose} 관련 문서 목적 서술",
  "main_contents_list": [
    {{"category": "카테고리명", "points": ["주요 내용 1", "주요 내용 2"]}}
  ],
  "conclusion_or_core_message": "최종 결론 또는 핵심 메시지 한 문장"
}}"""


def _parse_summary_response(file_id: str, data: dict, analysis_data: AnalysisData) -> SummaryData | None:
    try:
        return SummaryData(
            file_id=file_id,
            summary_result=SummaryResult(
                document_overview=data.get("document_overview", [analysis_data.document_subject]),
                document_purpose=data.get("document_purpose", f"문서 목적: {analysis_data.document_purpose}"),
                main_contents_list=[MainContentItem(**item) for item in data.get("main_contents_list", [])],
                conclusion_or_core_message=data.get("conclusion_or_core_message", "원문 기반 주요 수치 및 기한 준수 필요"),
            ),
        )
    except Exception:
        return None


def _summary_fallback(file_id: str, analysis_data: AnalysisData, error_message: Optional[str] = None) -> SummaryData:
    """LLM 호출 실패 시 분석 결과를 바탕으로 규칙 기반 요약을 생성합니다."""
    return SummaryData(
        file_id=file_id,
        summary_result=SummaryResult(
            error_message=error_message,
            document_overview=[
                f"본 문서는 '{analysis_data.document_subject}'에 관해 기술된 내용입니다.",
                f"원문 텍스트 내 주요 일시({', '.join(analysis_data.key_keywords.schedules)}) 및 수치 정보가 포함되어 있습니다.",
            ],
            document_purpose=f"문서 작성 목적: {analysis_data.document_purpose} (원문 핵심 안건 및 업무 성과 보고)",
            main_contents_list=[
                MainContentItem(category=cs.category, points=[cs.content_summary])
                for cs in analysis_data.core_structure
            ],
            conclusion_or_core_message="원문에 명시된 사업 일정 및 핵심 추진 사항의 정확한 준수가 필요합니다.",
        ),
    )


# ─────────────────────────────────────────────────────────────
# 3. AI 검증
# ─────────────────────────────────────────────────────────────

def run_document_validation(
    file_id: str,
    raw_text: Optional[str],
    analysis_data: Optional[AnalysisData],
    summary_data: Optional[SummaryData],
) -> ValidationData:
    """
    원문·분석·요약을 교차 검증하여 6개 항목을 체크하고 5개 출력을 반환합니다.
    선행 데이터가 부족하면 ValueError를 발생시킵니다.
    """
    if not raw_text or not raw_text.strip() or not analysis_data or not summary_data:
        raise ValueError("선행 기능(텍스트 추출, AI 문서 분석, AI 요약 생성)이 완료되지 않았습니다.")

    prompt = _build_validation_prompt(raw_text, analysis_data, summary_data)
    system_msg = "You are a strict, impartial AI Validation Agent. Do not invent new facts. Respond strictly in valid JSON."

    parsed, ai_error = _call_llm_api(prompt, system_msg, temperature=0.0)
    if parsed:
        result = _parse_validation_response(file_id, parsed)
        if result:
            return result

        ai_error = "AI 검증 응답의 JSON 구조가 올바르지 않습니다."

    return _validation_fallback(file_id, analysis_data, ai_error)


def _build_validation_prompt(
    raw_text: str,
    analysis_data: AnalysisData,
    summary_data: SummaryData,
) -> str:
    sr = summary_data.summary_result
    return f"""다음 [원문 텍스트], [AI 문서 분석 결과], [AI 요약 결과]를 교차 대조하여 검증을 수행하고 반드시 지정된 JSON 형식으로만 응답해 주세요.

[검증 엄격 수칙]:
- 새로운 사실을 만들거나 원문을 수정하지 마십시오.
- 다음 6가지 검증 항목을 정밀 체크하십시오:
  1. 중요 내용 누락  2. 원문과 요약의 의미 불일치  3. 수치와 날짜 정확도
  4. 조건과 예외 기재 여부  5. 원문보다 강한 단정 표기  6. 추가 확인이 필요한 표현

[문서 원문]:
{raw_text[:2500]}

[AI 문서 분석 결과]:
- 중심주제: {analysis_data.document_subject}
- 작성목적: {analysis_data.document_purpose}
- 주요키워드 수치: {', '.join(analysis_data.key_keywords.metrics)}

[AI 요약 결과]:
- 개요: {' / '.join(sr.document_overview)}
- 목적: {sr.document_purpose}
- 핵심 메시지: {sr.conclusion_or_core_message}

[출력 JSON 구조]:
{{
  "is_passed": true,
  "status_badge": "확인 필요",
  "issue_list": [
    {{
      "issue_id": "ISSUE-01",
      "issue_type": "수치와 날짜 불일치",
      "issue_title": "본문 수치와 표 수치 대조 필요",
      "reason_description": "원문 내 수치 표기와 요약문 간 정밀 대조가 필요함",
      "relevant_original_evidence": "원문 내 관련 구절"
    }}
  ],
  "human_review_checklist": [
    {{
      "check_id": "CHK-01",
      "title": "정밀 수치 및 일자 확인",
      "description": "원문에 포함된 수치 및 제출 기한을 직접 대조 확인하십시오.",
      "checked": false
    }}
  ]
}}"""


def _parse_validation_response(file_id: str, data: dict) -> ValidationData | None:
    try:
        return ValidationData(
            file_id=file_id,
            validation_result=ValidationResult(
                is_passed=data.get("is_passed", True),
                status_badge=data.get("status_badge", "확인 필요"),
                issue_list=[ValidationIssueItem(**item) for item in data.get("issue_list", [])],
                human_review_checklist=[HumanChecklistItem(**chk) for chk in data.get("human_review_checklist", [])],
            ),
        )
    except Exception:
        return None


def _validation_fallback(file_id: str, analysis_data: AnalysisData, error_message: Optional[str] = None) -> ValidationData:
    """LLM 호출 실패 시 규칙 기반으로 검증 결과를 생성합니다."""
    schedules = analysis_data.key_keywords.schedules
    metrics = analysis_data.key_keywords.metrics

    return ValidationData(
        file_id=file_id,
        validation_result=ValidationResult(
            error_message=error_message,
            is_passed=not bool(error_message),
            status_badge="확인 필요",
            issue_list=[
                ValidationIssueItem(
                    issue_id="ISS-01",
                    issue_type="수치와 날짜",
                    issue_title="주요 일정 및 수치 표기 대조",
                    reason_description=(
                        f"원문 내 명시된 주요 일자({', '.join(schedules)}) 및 "
                        f"수치({', '.join(metrics)})가 요약문에 정확히 담겼는지 검토 필요"
                    ),
                    relevant_original_evidence=f"원문 기재 일정: {schedules[0] if schedules else '일정 미기재'}",
                ),
                ValidationIssueItem(
                    issue_id="ISS-02",
                    issue_type="추가 확인이 필요한 표현",
                    issue_title="후속 조치 기한 및 미기재 사항 점검",
                    reason_description="원문 내 후속 시범 적용 일정이 미기재되어 수동 확인이 필요함",
                    relevant_original_evidence="원문 3절: 시범 적용 후 피드백 수집 예정",
                ),
            ],
            human_review_checklist=[
                HumanChecklistItem(check_id="CHK-01", title="중요 내용 누락 여부 확인",
                                   description="원문의 핵심 안건 및 세부 요구사항이 모두 요약되었는지 점검하십시오.", checked=False),
                HumanChecklistItem(check_id="CHK-02", title="의미 불일치 및 강한 단정 여부 점검",
                                   description="원문의 '검토 중' 표현이 '확정'으로 왜곡되었는지 확인하십시오.", checked=False),
                HumanChecklistItem(check_id="CHK-03", title="수치, 날짜, 조건과 예외 대조",
                                   description="예산, 기한, 단서 조건 및 예외 조항을 원문과 1:1 대조하십시오.", checked=False),
            ],
        ),
    )


# ─────────────────────────────────────────────────────────────
# 4. 저장 경로 추천 (규칙 기반 / LLM 호출 없음)
# ─────────────────────────────────────────────────────────────

def recommend_folder(
    existing_folders: List[str],
    keywords: List[str],
    default_root: str = "output/archive",
) -> list[dict]:
    """
    실존 폴더 목록과 요약 키워드를 비교하여 적합도 점수를 계산하고
    상위 3개 추천 폴더를 반환합니다.

    점수 계산 방식:
      - 키워드 토큰과 폴더 경로 문자열의 단순 교집합 비율 (0~1)
      - 키워드가 없을 경우 폴더를 알파벳 순으로 반환

    Returns:
        [{"folder_path": str, "score": float, "exists": bool}, ...]
    """
    # 키워드 전처리: 빈 항목 제거, 소문자화
    candidates = []
    seen = set()
    for folder in existing_folders:
        normalized = folder.replace("\\", "/").rstrip("/")
        if normalized.startswith("output") and normalized not in seen:
            candidates.append(normalized)
            seen.add(normalized)
    default_root = default_root.replace("\\", "/").rstrip("/")
    if not candidates:
        candidates = [default_root]

    prompt = f"""Choose the best archive folder for a document.
Available folders (choose only from this list): {json.dumps(candidates, ensure_ascii=False)}
Document keywords: {json.dumps([kw for kw in keywords if kw.strip()], ensure_ascii=False)}
Return only JSON: {{\"recommendations\": [{{\"folder_path\": \"exact candidate\", \"score\": 0.0}}]}}"""
    parsed, _ = _call_llm_api(prompt, "You recommend document archive folders. Use only supplied candidates.", temperature=0.0)
    if parsed and isinstance(parsed.get("recommendations"), list):
        allowed = set(candidates)
        ai_items = []
        for item in parsed["recommendations"]:
            if not isinstance(item, dict) or item.get("folder_path") not in allowed:
                continue
            try:
                score = max(0.0, min(1.0, float(item.get("score", 0.0))))
            except (TypeError, ValueError):
                score = 0.0
            ai_items.append({"folder_path": item["folder_path"], "score": round(score, 4), "exists": True})
        if ai_items:
            return ai_items[:3]

    tokens = {kw.strip().lower() for kw in keywords if kw.strip()}

    def _score(folder_path: str) -> float:
        if not tokens:
            return 0.0
        folder_lower = folder_path.lower()
        matched = sum(1 for t in tokens if t in folder_lower)
        return round(matched / len(tokens), 4)

    scored: list[dict] = []

    for folder in candidates:
        scored.append({
            "folder_path": folder,
            "score": _score(folder),
            "exists": True,
        })

    # 실존 폴더가 없으면 기본 경로를 추천 후보로 추가
    if not scored:
        scored.append({
            "folder_path": default_root,
            "score": 0.0,
            "exists": False,
        })

    # 점수 내림차순 정렬 후 상위 3개
    scored.sort(key=lambda x: (-x["score"], x["folder_path"] != default_root, -x["folder_path"].count("/"), x["folder_path"]))
    return scored[:3]
