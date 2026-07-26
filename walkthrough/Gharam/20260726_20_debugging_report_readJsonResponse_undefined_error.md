# 오류 분석 보고서 (Debugging Report)

## 1. 실행 상황

- **실행 명령 / 시점**: 웹 UI의 [미확인 작업 목록] 테이블 행에서 '상세' 버튼을 클릭했을 때
- **사용자가 기대한 동작**: 해당 미확인 작업 문서의 분석·요약 결과 대시보드 화면이 렌더링되고 화면이 전환됨
- **실제 발생 증상**: `상세 조회 중 오류 발생: readJsonResponse is not defined` 에러 메시지 팝업 표출

---

## 2. 핵심 오류 로그

```text
ReferenceError: readJsonResponse is not defined
    at showWorkItemDetail (index.html:2238)
```

---

## 3. 원인 분석

- **에러 타입**: `JavaScript ReferenceError`
- **발생 위치**: `static/index.html` 내 `showWorkItemDetail(fileId)` 함수 (Line 2238)
- **로그 및 코드 근거**:
  ```javascript
  // (수정 전 코드)
  async function showWorkItemDetail(fileId) {
    try {
      const res = await fetch(`/api/v1/documents/${fileId}/result`);
      const resData = await readJsonResponse(res); // ❌ readJsonResponse 미정의 헬퍼 호출
  ```
- **근본 원인**:
  `fetch()`로 받아온 응답 객체 `res`에 대해 `await res.json()`을 호출해야 하는데, 정작 정의되지 않은 `readJsonResponse` 헬퍼 함수를 호출하여 브라우저에서 `ReferenceError`가 발생한 것입니다.

---

## 4. 수정 및 보완 내용

| 파일 | 수정 내용 | 이유 |
| --- | --- | --- |
| [static/index.html](file:///c:/Workspace/team-project/team-project-comm-summary/static/index.html) | `showWorkItemDetail` 함수 내 `const resData = await readJsonResponse(res);` ➔ `const resData = await res.json();` 로 수정 | `ReferenceError`를 즉시 해결하고 표준 JSON parsing 응답 객체를 수신하도록 조치 |

---

## 5. 재실행 및 검증 방법

1. **기존 미확인 문서 기반 API 테스트**:
   - 기존 미확인 문서 (`doc_9b3b8abf-8539-472b-84da-4a4a07f513d4`)에 대해 `GET /api/v1/documents/{file_id}/result` 조회 ➔ **`200 OK (success: True)`** 반환 확인 (신규 테스트 데이터 입력 없음)
2. **자동 단위 테스트 실행**:
   ```bash
   python -m pytest tests/test_api.py
   ```
   - **결과**: **`23 passed` (100% 성공 통과)**

---

## 6. 확인 방법

- **확인할 UI 위치**: 웹 화면 ➔ 파일업로드 탭 ➔ 하단 [미확인 작업 목록]
- **테스트 케이스**: 임의의 미확인 항목 행에서 **'상세'** 버튼 클릭
- **기대 결과**: 에러 메시지 팝업 없이 `#resultSection` 대시보드 카드로 부드럽게 스크롤 및 전환되며 요약 분석 결과가 정상 출력됨
