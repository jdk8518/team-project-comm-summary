# 오류 분석 및 수정 완료 보고서

## 1. 실행 상황

- **실행 기능**: 폴더 전체 선택 업로드(`webkitdirectory`) 또는 드롭존을 통한 폴더 업로드 기능
- **발생 시점**: 폴더에서 업로드된 파일의 HTTP 전송 시 헤더에 상대 경로(예: `"folder/sub/sample.pdf"`)가 포함될 때
- **사용자가 기대한 동작**: 브라우저에서 폴더 내 수신된 모든 파일들이 서버에 전송되어 정상 파이프라인 분석이 진행되고 저장되는 동작

---

## 2. 원인 분석 (Root Cause Analysis)

- **에러 타입**: `FileNotFoundError: [Errno 2] No such file or directory` (서버 500 오류)
- **발생 위치**: `app/api.py` 내 `analyze_document` 엔드포인트 Line 46-57
- **코드 근거**:
  ```python
  filename = file.filename or "unknown.pdf"
  temp_path = os.path.join("temp/uploads", f"{file_id}_{filename}")
  with open(temp_path, "wb") as f:
      f.write(file_bytes)
  ```
- **원인**:
  1. 브라우저에서 폴더를 업로드할 때 HTTP Multipart Form 데이터에 포함되는 `file.filename`은 `"my_folder/sub_dir/doc.pdf"`와 같은 **상대 디렉토리 경로**를 포함할 수 있습니다.
  2. 서버 백엔드가 이를 정제(`os.path.basename`)하지 않고 바로 `os.path.join("temp/uploads", f"doc_xxx_my_folder/sub_dir/doc.pdf")`와 같이 결합함에 따라, 아직 생성되지 않은 하위 임시 폴더 경로를 참조하게 되어 `FileNotFoundError` (Internal Server Error 500)가 발생하였습니다.
  3. 이로 인해 프론트엔드의 `fetch('/api/v1/documents/analyze-auto')` 요청이 500 서버 에러로 응답되어 서버가 업로드된 파일 저장을 정상적으로 수행하지 못하고 실패 처리되었습니다.

---

## 3. 수정 내용

| 파일 | 수정 내용 | 이유 |
| --- | --- | --- |
| [app/api.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/api.py) | `raw_filename = file.filename` 수신 후 `filename = os.path.basename(raw_filename.replace("\\", "/"))` 안전 정제 로직 적용 | 브라우저의 상대 폴더 경로 전송 시에도 순수 파일명만 추출하여 `temp/uploads` 경로 결합 시 `FileNotFoundError` 500 에러 차단 |
| [tests/test_api.py](file:///c:/Workspace/team-project/team-project-comm-summary/tests/test_api.py) | `test_folder_relative_path_filename_upload` 단위 테스트 신설 | 폴더 업로드 시 상대 경로 파일명(`my_folder/sub/nested_doc.txt`) 전송 건에 대해 서버 수신 및 파이프라인 분석 정상 처리 검증 |

---

## 4. 재실행 방법 및 검증 결과

1. **자동화 테스트 실행**:
   ```bash
   python -m pytest
   ```
   - **결과**: `tests/test_ai_config.py`, `tests/test_api.py`, `tests/test_parsers.py` 전체 27개 테스트 100% 통과 (`27 passed`).

2. **수동 검증 시나리오**:
   - 폴더 내 깊은 계층 구조(예: `A_folder/B_sub/report.pdf`)를 가진 테스트 폴더를 선택 업로드.
   - 서버가 `FileNotFoundError` 없이 바이너리 데이터를 수신하고 정상 파이프라인 분석 후 DB 및 원문 파일 보관에 성공함을 확인.

---

## 5. 같은 오류 방지 방법

- `UploadFile.filename`은 사용자 브라우저 환경 및 업로드 방식(`webkitdirectory`)에 따라 상대 디렉토리 경로가 포함될 수 있으므로, 서버에 로컬 임시 파일로 작성하거나 DB에 기록할 때는 항상 `os.path.basename()`으로 파일명만 정제하여 사용해야 합니다.
