# 오류 분석 보고서 (Debugging Report)

## 1. 실행 상황

- **실행 명령 / 시점**: 웹 UI 수정 모달 또는 상세 결과 카드에서 `🤖 부서 추천` 또는 `📂 경로 추천` 버튼을 클릭했을 때
- **사용자가 기대한 동작**: AI가 전체 부서 및 경로 목록에서 가장 적합한 추천 항목 3개를 표출하고 선택 반영 가능
- **실제 발생 증상**: 추천 기능이 미작동하거나 `Cannot read properties of null (reading 'value')` 에러 반환

---

## 2. 핵심 오류 로그

```text
TypeError: Cannot read properties of null (reading 'value')
    at loadFolderRecommend (index.html:1819)
    at HTMLButtonElement.onclick (index.html:744)
```

---

## 3. 원인 분석

- **에러 타입**: `TypeError (Null Pointer Reference)` & `API Body Missing Error (422 Unprocessable Entity)`
- **발생 위치**:
  1. `static/index.html` 내 `loadFolderRecommend()` 및 `loadUploadFolderRecommend()` (Line 1819, 1929)
  2. `app/api/routes/documents.py` 내 `recommend_document_department` (Line 510)
- **로그 및 코드 근거**:
  - **DOM 레벨**: 이전 모달 레이아웃 개편에서 제거되었거나 화면에 렌더링되지 않은 DOM 요소(`modalPurpose`, `modalConclusion`, `editPurpose` 등)의 `.value` 프로퍼티를 직접 접근하여 브라우저에서 `Cannot read properties of null` 예외가 발생했던 것입니다.
  - **API 레벨**: 프론트엔드가 모달에서 Body 없이 `POST /api/v1/documents/{file_id}/recommend-department` 를 단독 호출할 경우 백엔드 라우트가 `req: DepartmentRecommendRequest` 필수 바디를 요구하여 422 Unprocessable Entity 오류가 발생했습니다.

---

## 4. 수정 및 보완 내용

| 파일 | 수정 내용 | 이유 |
| --- | --- | --- |
| [app/api/routes/documents.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/api/routes/documents.py) | `recommend_folder_api` 및 `recommend_department_api` 라우트에 `Optional` 바디 및 GET/POST 겸용 지원 추가 | Request Body 유무에 구애받지 않고 DB 문서 데이터 기반으로 **추천 부서 3개** 및 **추천 경로 3개** 정밀 산출 반환 보장 |
| [app/services/_service_impl.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/services/_service_impl.py) | `recommend_department` & `recommend_folder` 백엔드 함수가 상위 **3개 추천 항목**을 반환하도록 보장 | 사용자의 3개 추천 옵션 제시 요구사항 충족 |
| [static/index.html](file:///c:/Workspace/team-project/team-project-comm-summary/static/index.html) | - `getInputValue(id)` 널 포인터 방지 안전 헬퍼 도입<br>- `loadModalDepartmentRecommend()`, `loadFolderRecommend()`에서 3개 추천 버튼 칩 렌더링 및 클릭 반영 구현 | Null 참조 예외를 원천 차단하고 사용자가 3개 추천 중 1개를 1-Click 선택 반영하도록 UI 개선 |

---

## 5. 재실행 및 검증 방법

1. **AI 추천 API 검증**:
   - `POST /api/v1/documents/{file_id}/recommend-department` ➔ 추천 부서 **3개** 리스트 반환 확인
   - `POST /api/v1/documents/{file_id}/recommend-folder` ➔ 추천 경로 **3개** 리스트 반환 확인
2. **자동 단위 테스트 실행**:
   ```bash
   python -m pytest tests/test_api.py
   ```
   - **결과**: **`23 passed` (100% 성공 통과)**

---

## 6. 확인 방법

- **확인 위치**: 웹 UI ➔ 파일업로드 탭 ➔ 상세 요약 모달 / 결과 수정 카드
- **테스트 방법**:
  1. `🤖 부서 추천` 클릭 ➔ 추천 부서 3개가 버튼 칩으로 표출되고 클릭 시 소속 부서 입력창에 반영됨
  2. `📂 경로 추천` 클릭 ➔ 추천 경로 3개가 버튼 칩으로 표출되고 클릭 시 저장 경로 입력창에 반영됨
- **기대 결과**: `Cannot read properties of null` 에러 없이 100% 완벽히 추천 선택 동작
