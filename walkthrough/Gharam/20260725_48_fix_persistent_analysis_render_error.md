# 작업 완료 보고서

## 오류 증상

AI 문서 분석 요청 후 계속 `Cannot set properties of null (setting 'textContent')`가 발생하고, 화면에는 서버 연결 오류로 표시되었다.

## 원인 분석

분석 결과 UI가 텍스트 입력 중심으로 개편되면서 기존 표시용 DOM ID가 일부 제거되었는데, `renderResult()`가 과거 `resPurpose`, `resConclusion`, `resKey*` 요소를 갱신하던 코드가 남아 있었다. 또한 브라우저가 이전 HTML/인라인 JS를 재사용할 경우 수정 전 코드가 계속 실행될 수 있었다.

## 수정 내용

- 분석 결과 렌더러에서 제거된 DOM 참조를 정리했다.
- `setDomText`, `setDomValue`, `setDomStyle`, `readDomValue` 헬퍼를 추가해 누락 요소가 있어도 분석 요청 전체가 중단되지 않도록 방어했다.
- 목적·메시지·키워드는 현재 편집 입력 필드에 반영하도록 유지했다.
- `/` 및 HTML 응답에 `Cache-Control: no-store`를 설정해 오래된 인라인 JS 재사용을 방지했다.

## 검증 결과

- `node --check` JavaScript 문법 검사 통과
- 대시보드 캐시 헤더 테스트 통과
- `python -m pytest tests -q`: `23 passed, 2 warnings`
- 변경 파일 `git diff --check` 통과

## 변경 파일

- `static/index.html`
- `app/main.py`
- `tests/test_api.py`
- `walkthrough/Gharam/20260725_48_fix_persistent_analysis_render_error.md`

기존 무관 변경 파일은 보존했다.
