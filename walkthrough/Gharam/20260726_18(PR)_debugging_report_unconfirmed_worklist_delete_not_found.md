# 오류 분석 보고서 (Debugging Report)

## 1. 실행 상황

- **실행 명령 / 시점**: 웹 UI의 [미확인 작업 목록] 테이블 또는 API (`DELETE /api/v1/documents/{file_id}`)를 통해 미확인 작업 문서 삭제 요청 시
- **사용자가 기대한 동작**: 미확인 문서가 정상 삭제되거나, 원본 미존재 시 확인 팝업 후 DB 데이터(레코드)가 삭제됨
- **실제 발생 증상**: UI 및 API에서 `'삭제 실패: 문서를 찾을 수 없습니다.'` (`404 NOT_FOUND`) 오류 메시지가 반환됨

---

## 2. 핵심 오류 로그 및 응답

```json
{
  "detail": "문서를 찾을 수 없습니다."
}
```
HTTP Status Code: `404 Not Found`

---

## 3. 원인 분석

- **에러 타입**: `HTTPException (404 Not Found)`
- **발생 위치**: `app/db.py` 의 `delete_document_from_db(file_id)` 진입부
- **로그 및 코드 근거**:
  `delete_document_from_db` 함수 진입 시 문서의 존재 여부를 인메모리 딕셔너리 캐시(`document_db`)로만 단순 조회했습니다:
  ```python
  # 기존 결함 코드
  def get_document_by_id(file_id: str) -> Optional[Dict[str, Any]]:
      return document_db.get(file_id)  # SQLite DB 조회를 하지 않고 인메모리 dict만 참조
  ```
- **근본 원인**:
  서버 재시작 후나 메모리 캐시(`document_db`)에서 해당 `file_id`가 팝(pop)되어 제거된 상태에서는 SQLite DB (`documents.db`) 테이블에 해당 문서 정보가 정상 보관되어 있더라도 `document_db.get(file_id)`가 `None`을 반환했습니다.
  이로 인해 `delete_document_from_db` 함수가 SQLite DB 조회를 시도하지 못하고 조기에 `"문서를 찾을 수 없습니다."` 404 에러를 일으킨 것입니다.

---

## 4. 수정 내용

| 파일 | 수정 내용 | 이유 |
| --- | --- | --- |
| [app/db.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/db.py) | `get_document_by_id(file_id)` 함수가 인메모리 캐시(`document_db`)에 없을 경우, SQLite DB (`documents.db`)에서 `SELECT * FROM documents WHERE file_id = ?` 로 자동 조회 및 캐싱하여 반환하도록 수정 | 인메모리 캐시 미존재 시에도 SQLite DB 레코드를 정상 참조하여 동기화 삭제를 보장하기 위함 |
| [tests/test_api.py](file:///c:/Workspace/team-project/team-project-comm-summary/tests/test_api.py) | `test_delete_document_from_db_when_not_in_memory_cache` 단위 테스트 추가 | 메모리 캐시에 없는 상태에서 삭제 요청 시 정상 작동함을 검증 |

---

## 5. 재실행 방법

백엔드 서버 재실행 및 테스트:
```bash
python -m pytest tests/test_api.py
```

Swagger API 확인:
```text
http://127.0.0.1:8000/docs#/documents/delete_document_api_v1_documents__file_id__delete
```

---

## 6. 확인 방법

- **확인할 명령 / URL**: `DELETE /api/v1/documents/{file_id}`
- **테스트 케이스**:
  1. 서버 재시작 후 미확인 작업 목록에서 임의의 문서 삭제 시도
  2. 인메모리 `document_db` 캐시를 비운 뒤 삭제 시도
- **기대 결과**: 상태 코드 `200 OK` 및 `{"success": true, "message": "문서 doc_... 가 성공적으로 삭제되었습니다."}` 응답 반환

---

## 7. 같은 오류 방지 방법

- 인메모리 딕셔너리 캐시(`document_db`)를 조회할 때는 반드시 데이터베이스(SQLite DB)와의 동기화 조회(Fallback Query)를 지원하도록 설계해야 합니다.
- API 단에서 404 에러가 발생할 경우 캐시 유무와 실재 영구 저장소(DB) 데이터를 모두 확인했는지 점검하십시오.
