from datetime import date
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import bad_request
from app.core.security import mask_data
from app.utils.file_utils import safe_stem


def build_preview(result: dict, document_type: str, reference_date: date | None = None) -> dict:
    if document_type not in settings.output_directories:
        raise bad_request("문서특성은 회의록, 공문, 보고서, 공고문, 기타(예외) 중 하나를 선택해 주세요.")
    if result.get("status") != "SUCCESS":
        raise bad_request("성공한 분석 결과만 저장할 수 있습니다.")
    selected_date = reference_date or date.fromisoformat(result["document"]["reference_date"])
    file_name = f"{safe_stem(document_type)}-{selected_date.isoformat()}.md"
    directory = settings.output_directories[document_type]
    candidate = directory / file_name
    number = 0
    while candidate.exists():
        number += 1
        candidate = directory / f"{safe_stem(document_type)}-{selected_date.isoformat()}-{number}.md"
    return {
        "document_type": document_type,
        "reference_date": selected_date.isoformat(),
        "directory": str(directory),
        "file_name": candidate.name,
        "duplicate_number": number,
        "save_available": True,
    }


def _markdown(result: dict, preview: dict) -> str:
    document = result["document"]
    analysis = result["analysis"]
    summary = result["summary"]
    verification = result["verification"]

    def text(data: dict, *keys: str) -> str:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return "확인 필요"

    def items(data: dict, *keys: str) -> list[str]:
        for key in keys:
            value = data.get(key)
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return value
        return []

    lines = [
        "# 문서 분석 결과", "", "## 1. 문서 기본 정보",
        f"- 문서 제목: {text(analysis, 'title')}", f"- 문서 유형: {preview['document_type']}",
        f"- 기준 일자: {preview['reference_date']} ({document.get('reference_date_source', '확인 필요')})",
        f"- 작성 소속(기관): {text(analysis, 'organization')}", f"- 부서: {text(analysis, 'department')}",
        "", "## 2. 문서 구조와 핵심 내용",
        f"- 목차·본문 구조: {', '.join(items(analysis, 'table_of_contents')) or '확인 필요'}",
        f"- 핵심 문장: {' / '.join(items(analysis, 'key_sentences')) or '확인 필요'}",
        f"- 수치·기한: {', '.join(items(analysis, 'numerical_values')) or '확인 필요'}",
        f"- 조건·예외: {', '.join(items(analysis, 'conditions')) or '확인 필요'}",
        f"- 결정 사항: {', '.join(items(analysis, 'decisions')) or '확인 필요'}",
        "", "## 3. 문서 핵심 요약",
        f"- 문서 개요: {text(summary, 'document_overview', 'background')}",
        f"- 문서 목적·주요 내용: {text(summary, 'document_purpose', 'main_content')}",
        f"- 결론 및 핵심 메시지: {text(summary, 'conclusion_or_key_message', 'conclusion')}",
        f"- 주요 내용: {', '.join(items(summary, 'main_contents', 'follow_up_actions')) or '확인 필요'}", "", "## 4. 주요 키워드",
        f"- 키워드: {', '.join(items(analysis, 'keywords')) or '확인 필요'}", "", "## 5. 문서 검증 결과",
        f"- 검증 통과: {'예' if verification.get('passed') else '아니오'}",
        f"- 수정·확인 방향: {text(verification, 'revision_instruction')}",
    ]
    issues = verification.get("issues", [])
    if issues:
        lines.extend(["", "| 검증 항목 | 문제가 되는 이유 | 관련 원문 근거 | 사람이 확인할 항목 |", "| --- | --- | --- | --- |"])
        for item in issues:
            lines.append(
                f"| {item['category']} | {item['reason']} | "
                f"{'<br>'.join(item['source_evidence'])} | {item['human_check']} |"
            )
    else:
        lines.append("- 확인이 필요한 검증 문제 없음")
    review_items = [*items(summary, "review_items"), *items(analysis, "review_items"), *(item["human_check"] for item in issues)]
    lines.extend(["", "## 6. 사람이 확인할 항목"])
    lines.extend(f"- {item}" for item in review_items or ["없음"])
    lines.extend(["", "## 7. 최종 검토 정보", "- 검토 상태: 사용자 최종 확인 완료", ""])
    return "\n".join(lines)


def save_result(result: dict, preview: dict, review_confirmed: bool, user_confirmed: bool) -> dict:
    if not review_confirmed or not user_confirmed:
        raise bad_request("관리자 검토와 사용자 최종 확인 후에만 저장할 수 있습니다.")
    directory = Path(preview["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    current_preview = build_preview(result, preview["document_type"], date.fromisoformat(preview["reference_date"]))
    path = directory / current_preview["file_name"]
    path.write_text(_markdown(mask_data(result), current_preview), encoding="utf-8")
    return {"saved": True, "file_name": path.name, "path": str(path)}
