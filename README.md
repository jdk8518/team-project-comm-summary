# 문서 분석 MVP

문서 한 개를 업로드하면 OpenAI로 본문을 분석·요약·검증하고, 검토 완료 후 Markdown 결과를 유형별 폴더에 저장합니다.

## 지원 형식

PDF, DOC, DOCX, HWP, HWPX, PPT, PPTX, TXT, JPG, JPEG, PNG, TIFF. DOC·HWP·PPT는 로컬에 LibreOffice가 설치되어 있어야 변환·분석할 수 있습니다. 이미지와 텍스트 추출이 불가능한 스캔 PDF는 Tesseract OCR의 한국어(`kor`)·영어(`eng`) 언어 데이터를 사용합니다.

Windows에서 이미지 OCR 또는 스캔 PDF OCR을 사용하려면 Tesseract와 Poppler를 별도로 설치하고, 두 실행 파일 경로를 `PATH`에 추가해야 합니다. OCR 엔진 또는 언어 데이터가 없으면 추출 요청은 안전한 오류 메시지로 종료되며 원본 파일은 수정하지 않습니다.

### 스캔 PDF OCR 준비(Windows)

스캔 PDF는 텍스트 레이어가 없어 Poppler로 페이지 이미지를 만들고 Tesseract로 텍스트를 읽습니다. Poppler와 Tesseract(한국어 언어 데이터 `kor` 포함)를 설치한 뒤, 각 설치 경로의 `Library\\bin` 또는 `bin` 폴더를 Windows `PATH`에 추가하세요. 새 PowerShell 창에서 아래 명령이 성공해야 합니다.

```powershell
pdftoppm -v
tesseract --list-langs
```

두 번째 명령의 출력에 `kor`가 없으면 Tesseract 한국어 언어 데이터를 추가로 설치해야 합니다. 설치 후 Uvicorn 서버를 다시 시작하고 스캔 PDF를 다시 업로드하세요. 텍스트를 선택·복사할 수 있는 일반 PDF는 OCR 도구 없이 처리됩니다.

CMD에서는 `tesseract --list-langs`가 성공하지만 Uvicorn에서만 OCR 오류가 나면, 실행 중인 서버가 다른 PATH를 사용 중인 경우입니다. `.env`에 실행 파일과 언어 데이터 경로를 직접 지정한 뒤 서버를 재시작하세요.

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSDATA_DIR=C:\Users\user-id\AppData\Local\Tesseract-OCR\tessdata
```

## 실행 방법

> 이 저장소는 FastAPI 기반 Python 프로젝트입니다. `package.json`과 Node 의존성을 사용하지 않으므로 `npm install`을 실행하지 않습니다. 의존성 설치에는 아래의 `pip install -r requirements.txt` 명령을 사용합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 열고, Swagger UI는 `http://127.0.0.1:8000/docs`에서 확인합니다. `.env`에 `OPENAI_API_KEY`를 반드시 설정해야 하며, 키가 없거나 OpenAI 호출에 실패하면 분석 결과를 대체 생성하지 않고 오류를 안내합니다.

`app/web/index.html`을 탐색기에서 직접 열면(`file:///...`) API 요청이 차단되어 `Failed to fetch`가 발생합니다. 반드시 Uvicorn을 실행한 뒤 위의 `http://127.0.0.1:8000` 주소로 접속하세요.

분석 결과는 최종 확인 후 `other_docs/meeting`, `other_docs/official document`, `other_docs/report`, `other_docs/announcement`에 Markdown으로 저장됩니다. `기타(예외)`는 자동 확정하지 않으며, 검토·승인된 경우에만 `other_docs/others`에 저장합니다. 원본 파일은 변경하지 않습니다.

## Swagger UI 확인

`http://127.0.0.1:8000/docs`에서 다음 순서로 확인합니다.

1. `GET /api/v1/documents/folder`에 문서 폴더 경로를 입력해 지원 문서의 이름·형식·크기·수정일을 조회합니다.
2. `POST /api/v1/documents/extract`에 단일 문서를 업로드합니다.
3. 반환된 `document_id`로 `POST /api/v1/documents/{document_id}/analyze`를 호출합니다. 기본 카테고리는 회의록·공문·보고서·공고문입니다.
4. 검토 후 `POST /api/v1/documents/{document_id}/save`에 문서특성, 기준일, 두 확인값을 입력해 결과 Markdown을 저장합니다.

## 테스트

```powershell
python -m pytest
```

API 키와 `.env` 파일은 커밋하지 마세요.
