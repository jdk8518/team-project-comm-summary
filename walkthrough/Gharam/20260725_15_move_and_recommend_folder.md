# 리팩토링 결과 — 파일 저장 경로 수정 및 추천

## 1. 리팩토링 목표

- **개선 문제**: 검색 후 상세 모달에서 파일 저장 경로를 수정할 수 없었고, 추천 경로도 고정 문자열이었음
- **유지한 기존 기능**: 12단계 MVP 전체 API 경로·Request/Response 형식·오류 메시지 100% 유지

---

## 2. 변경 전 문제점

| # | 문제 | 위치 |
|:---:|:---|:---|
| ① | 모달에 저장 경로 표시·수정 UI 없음 | `static/index.html` |
| ② | 파일 경로 변경 시 물리 파일 이동 로직 없음 | `app/db.py` |
| ③ | 파일 경로 변경 API 없음 | `app/api.py` |
| ④ | 추천 경로가 고정 문자열 (`output/archive/디지털혁신팀/`) | `app/db.py` |

---

## 3. 변경 내용

| 파일 | 변경 내용 | 이유 |
|:---|:---|:---|
| [app/schemas.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/schemas.py) | `MoveFileRequest`, `MoveFileResponse`, `FolderRecommendItem`, `FolderRecommendResponse` DTO 추가 | 이동·추천 API 입출력 정의 |
| [app/db.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/db.py) | `move_document_file()` — shutil.move 기반 물리 파일 이동 + DB 경로 갱신 | 경로 변경 핵심 로직 |
| [app/db.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/db.py) | `get_existing_archive_folders()` — `output/archive/` 하위 실존 폴더 목록 반환 | 추천 알고리즘 입력 데이터 |
| [app/services.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/services.py) | `recommend_folder()` — 키워드 교집합 기반 폴더 추천 (규칙 기반, LLM 미사용) | 추천 서비스 로직 분리 |
| [app/api.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/api.py) | `PUT /{file_id}/folder` — 파일 이동 엔드포인트 추가 | |
| [app/api.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/api.py) | `GET /{file_id}/recommend-folder` — 폴더 추천 엔드포인트 추가 | |
| [static/index.html](file:///c:/Workspace/team-project/team-project-comm-summary/static/index.html) | 모달에 저장 경로 입력 필드 + [🔍 경로 추천] 버튼 + [📂 경로 변경 및 파일 이동] 버튼 추가 | UI 연동 |
| [tests/test_api.py](file:///c:/Workspace/team-project/team-project-comm-summary/tests/test_api.py) | `test_move_document_folder`, `test_recommend_folder_returns_list`, `test_move_nonexistent_document` 추가 | 신규 기능 검증 |

---

## 4. 새 기능 처리 흐름

### 파일 저장 경로 수정

```
[검색 탭] 문서 카드 클릭
  └─ openSummaryModal() → GET /{file_id}/result
       └─ 모달 표시 (저장 경로 필드에 현재 saved_folder 값 자동 입력)
            └─ 사용자가 경로 수정 후 [📂 경로 변경 및 파일 이동] 클릭
                 └─ submitModalMove() → PUT /{file_id}/folder
                      └─ db.move_document_file()
                           ├─ os.makedirs(new_folder, exist_ok=True)
                           ├─ shutil.move(old_path, new_path)
                           └─ DB archived_path / saved_folder 업데이트
```

### 저장 경로 추천

```
[🔍 경로 추천] 클릭
  └─ loadFolderRecommend() → GET /{file_id}/recommend-folder
       └─ db.get_existing_archive_folders()  ← output/archive/ 실존 폴더 스캔
       └─ services.recommend_folder(folders, keywords)
            └─ 키워드(조직명·개념어) ∩ 폴더명 교집합 점수 계산
            └─ 상위 3개 반환
       └─ 추천 버튼 클릭 시 경로 입력 필드에 자동 입력
```

---

## 5. 기존 기능 유지 확인

- ✅ 기존 API 경로 (`/analyze`, `/save`, `/search`, `/summary`, `/download`, `/delete`) 전부 유지
- ✅ Request/Response DTO 형식 변경 없음
- ✅ 오류 메시지 형식 유지

---

## 6. 테스트 결과

```
tests/test_api.py::test_full_12step_mvp_pipeline         PASSED
tests/test_api.py::test_unsupported_file_extension        PASSED
tests/test_api.py::test_empty_file_content                PASSED
tests/test_api.py::test_delete_nonexistent_document       PASSED
tests/test_api.py::test_move_document_folder              PASSED  ← 신규
tests/test_api.py::test_recommend_folder_returns_list     PASSED  ← 신규
tests/test_api.py::test_move_nonexistent_document         PASSED  ← 신규

7 passed in 3.34s
```

---

## 7. 수동 확인 기준

- [ ] `uvicorn app.main:app --reload` 정상 실행
- [ ] Swagger(`/docs`)에 `PUT /{file_id}/folder`, `GET /{file_id}/recommend-folder` 표시
- [ ] 검색 모달에서 저장 경로 필드가 현재 경로로 자동 입력되는가?
- [ ] [🔍 경로 추천] 클릭 → 추천 경로 목록이 표시되고 클릭 시 필드에 적용되는가?
- [ ] [📂 경로 변경 및 파일 이동] 클릭 → 파일이 새 경로로 이동되는가?
- [ ] 존재하지 않는 경로도 폴더가 자동 생성되는가?
