# 작업 완료 보고서

## 작업 지시사항 원문

> 문서 분석 요청 화면과 검색 수정 화면에서 JSON 전체 결과를 노출하지 않고 요약, 목적, 메시지, 키워드, 저장 경로만 텍스트 입력으로 수정한다. 추천경로는 수정값과 output 하위 폴더를 AI API에 전달해 제안하고, 저장·이동·삭제·다운로드 버튼은 작은 작업 버튼으로 배치한다.

## 수행 내용

- 업로드 결과 화면과 검색 수정 팝업에서 JSON 편집 영역을 제거했다.
- 요약, 목적, 핵심 메시지, 5개 키워드 범주, 저장 경로를 텍스트 입력으로 제공했다.
- `/output/` 루트는 `displayArchivePath`를 통해 입력 화면에 표시하지 않도록 유지했다.
- `POST /api/v1/documents/{file_id}/recommend-folder`를 추가했다. 수정된 요약·목적·메시지·키워드와 폴더 트리의 `output` 하위 경로를 받아 추천 후보를 계산/AI 요청에 전달한다.
- 업로드 및 검색 수정 화면에 `추천경로` 버튼과 추천 후보 적용 UI를 연결했다.
- 검색 수정 팝업의 작업 버튼을 `DB반영`, `경로변경`, `다운로드`, `파일삭제`로 축소 배치했다.

## 변경한 파일

- `app/schemas.py`
- `app/api.py`
- `static/index.html`
- `tests/test_api.py`
- `walkthrough/Gharam/20260725_46_editable_text_fields_folder_recommendation.md`

## 테스트 방법과 결과

프론트 JavaScript를 추출해 `node --check`로 검사했고, `python -m pytest tests -q` 결과는 `22 passed, 2 warnings`이다. `git diff --check`도 통과했다.

## 남아 있는 문제

추천 엔진은 기존 LLM 연동과 규칙 기반 fallback을 함께 사용한다. 운영 환경에서는 폴더 목록이 많을 때 목록 크기 제한과 추천 근거 표시를 추가할 수 있다. 기존 무관 변경 파일은 보존했다.
