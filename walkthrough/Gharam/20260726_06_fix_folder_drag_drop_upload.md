# 오류 분석 및 수정 완료 보고서

## 1. 실행 상황

- **실행 기능**: 업로드 카드 드롭존(Dropzone)에 폴더를 드래그 앤 드롭하거나 폴더 업로드를 수행할 때
- **발생 시점**: 폴더를 드롭존으로 끌어다 넣었을 때 내부 파일들의 파이프라인 분석으로 연결되지 않고 0개 파일 처리 또는 오류로 종료됨
- **사용자가 기대한 동작**: 폴더를 드래그 앤 드롭하거나 선택했을 때 폴더 내 모든 지원 파일(`PDF`, `DOCX`, `TXT`, `HWP`, `HWPX`, `PPTX`)이 자동으로 재귀 탐색되어 파일 파이프라인 분석 및 다중파일 작업리스트로 연동되고, 미지원 파일은 하단 처리 불가 리스트로 분류됨

---

## 2. 원인 분석 (Root Cause Analysis)

- **에러 타입**: Drag & Drop Folder Entry Traversal Missing (HTML5 FileSystem API 미비)
- **발생 위치**: `static/index.html` 내 `dropzone.addEventListener('drop', ...)` 이벤트 핸들러 및 `input[type="file"]` 핸들러
- **코드 근거**:
  - 기존 드롭 핸들러:
    ```javascript
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleBatchFileSelect(e.dataTransfer.files);
      }
    });
    ```
  - 브라우저 W3C 사양상, 폴더를 드래그 앤 드롭했을 때 `e.dataTransfer.files` 배열에는 폴더 객체(size: 0, 확장자 없음) 자체만 담기게 됩니다.
  - `handleBatchFileSelect`는 `isFileSupported`(`file.name.endsWith(...)`) 검사를 거치므로, 폴더 객체 자체는 지원 확장자가 없어 미지원 파일로 판정되고 내부 하위 파일들로 접근하지 못하고 종료되었습니다.
- **원인**:
  1. 드롭존에 폴더를 드래그할 경우 `DataTransferItem.webkitGetAsEntry()` 및 `FileSystemDirectoryReader`를 사용한 비동기 재귀 탐색(Recursive Traversal) 로직이 구현되어 있지 않았습니다.
  2. `<input type="file" id="folderInput">`의 `onchange` 이벤트 발생 후 `folderInput.value`가 초기화되지 않아 동일 폴더 재선택 시 이벤트가 발생하지 않는 현상이 있었습니다.

---

## 3. 수정 내용

| 파일 | 수정 내용 | 이유 |
| --- | --- | --- |
| [static/index.html](file:///c:/Workspace/team-project/team-project-comm-summary/static/index.html) | `getFilesFromDataTransferItems()` 및 `traverseFileTree()` 비동기 재귀 탐색 함수 구현 | HTML5 FileSystem API를 사용하여 폴더 드래그 앤 드롭 시 하위 디렉토리 및 모든 파일을 재귀 탐색하기 위함 |
| [static/index.html](file:///c:/Workspace/team-project/team-project-comm-summary/static/index.html) | `dropzone.addEventListener('drop', ...)`을 `e.dataTransfer.items` 비동기 탐색 연동 구조로 개편 | 폴더 드롭 시 내부 모든 파일 리스트를 정상 수집하여 분석 파이프라인으로 연결하기 위함 |
| [static/index.html](file:///c:/Workspace/team-project/team-project-comm-summary/static/index.html) | `handleBatchFileSelect` 처리 종료 시 `fileInput.value = ''; folderInput.value = '';` 초기화 추가 | 파일/폴더 재선택 시 `onchange` 이벤트가 항상 재발화되도록 하기 위함 |

---

## 4. 재실행 방법 및 확인 결과

1. **자동화 테스트 실행**:
   ```bash
   python -m pytest
   ```
   - **결과**: `tests/test_ai_config.py`, `tests/test_api.py`, `tests/test_parsers.py` 전체 26개 테스트 100% 통과 (Pass).

2. **수동 검증 시나리오**:
   - 하위 폴더와 여러 포맷이 포함된 테스트 폴더를 드롭존으로 드래그 앤 드롭.
   - 폴더 내부의 모든 파일들이 재귀 탐색되어 지원 파일은 파이프라인 분석 후 `다중파일 작업리스트`로 들어가고, 미지원 파일은 하단 `처리 불가 파일 리스트`로 정확히 분리 표출됨을 확인.

---

## 5. 같은 오류 방지 방법

- HTML5 Drag & Drop 구현 시 폴더 지원 요구사항이 있는 경우 단순히 `e.dataTransfer.files`에 의존하지 않고 반드시 `webkitGetAsEntry()` / `createReader()` 비동기 재귀 탐색을 적용해야 합니다.
- File Input 요소 사용 시 작업 완료 후 `input.value = ''`로 초기화하여 중복 선택 시의 `onchange` 누락을 방지해야 합니다.
