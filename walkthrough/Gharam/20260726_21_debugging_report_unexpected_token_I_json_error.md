# 오류 분석 보고서 (Debugging Report)

## 1. 실행 상황

- **실행 명령 / 시점**: 테스트로 삽입되었거나 결측 필드가 존재하는 미확인 작업 목록 항목에서 '상세' 버튼을 클릭했을 때
- **사용자가 기대한 동작**: 해당 미확인 문서의 상세 요약 결과 대시보드가 정상 렌더링되거나, 에러 발생 시 명확한 사유 안내 팝업 표출
- **실제 발생 증상**: `상세 조회 중 오류 발생: Unexpected token 'I', "Internal S"... is not valid JSON` 에러 팝업 표출

---

## 2. 핵심 오류 로그

```text
SyntaxError: Unexpected token 'I', "Internal S"... is not valid JSON
    at JSON.parse (<anonymous>)
    at readJsonResponse (index.html:2238)
```
서버 반환 HTTP Status: `500 Internal Server Error` (Body: `"Internal Server Error"`)

---

## 3. 원인 분석

- **에러 타입**: `SyntaxError (JSON Parsing Error)` & `HTTP 500 Internal Server Error`
- **발생 위치**:
  1. 백엔드 `app/api/routes/documents.py` 내 `get_document_result(file_id)` (Line 307~328)
  2. 프론트엔드 `static/index.html` 내 `showWorkItemDetail(fileId)` 및 `readJsonResponse`
- **로그 및 코드 근거**:
  - **백엔드 레벨**: 테스트용으로 임의 생성된 문서나 특정 메타데이터 필드가 부분 결락된 문서 항목의 경우, `doc['size_bytes']` 인덱싱이나 `summary_data_obj.summary_result`, `validation.validation_result` 접근 시 `KeyError` 또는 `AttributeError` 예외가 감지되어 FastAPI가 500 Internal Server Error (텍스트 `"Internal Server Error"`)를 돌려주었습니다.
  - **프론트엔드 레벨**: 서버가 HTML/Text 형태인 `"Internal Server Error"` 응답을 보냈을 때 `res.json()`을 시도함으로써 `Unexpected token 'I'` 에러가 발생한 것입니다.

---

## 4. 수정 및 보완 내용

| 파일 | 수정 내용 | 이유 |
| --- | --- | --- |
| [app/api/routes/documents.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/api/routes/documents.py) | `get_document_result` API 라우트에 널 세이프티(`doc.get(...) or default`) 및 try-except 내 안전 핸들링 추가 | 결측 필드나 mock 테스트 데이터에 접근 시 500 에러 발생을 근본적으로 방지 |
| [static/index.html](file:///c:/Workspace/team-project/team-project-comm-summary/static/index.html) | `readJsonResponse` 안전 헬퍼 구현 (`content-type` 및 `res.ok` 확인 후 JSON 또는 text 분기 수신) | 서버가 non-JSON 또는 HTML/Text 500 에러를 반환할 때 `Unexpected token` 오류 대신 정확한 에러 메시지 팝업 노출 |

---

## 5. 재실행 및 검증 방법

1. **DB 레코드 조회 검증**:
   - 현재 존재하는 모든 미확인 작업 문서 아이디에 대해 `GET /api/v1/documents/{file_id}/result` 조회 ➔ **`200 OK` (모든 미확인 문서 100% 정상 결과 반환 확인)**
2. **자동 단위 테스트 실행**:
   ```bash
   python -m pytest tests/test_api.py
   ```
   - **결과**: **`23 passed` (100% 성공 통과)**

---

## 6. 확인 방법

- **확인 위치**: 웹 UI ➔ 파일업로드 탭 ➔ 하단 [미확인 작업 목록]
- **테스트 방법**: 임의의 미확인 항목 행에서 **'상세'** 버튼 클릭
- **기대 결과**: `Unexpected token 'I'` 오류 없이 100% 정상적으로 상세 요약 대시보드가 렌더링됨
