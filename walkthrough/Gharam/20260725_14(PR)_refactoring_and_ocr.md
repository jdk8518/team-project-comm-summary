# 리팩토링 결과

## 1. 리팩토링 목표

- **개선하려는 문제**: 환경 변수 읽기 중복, AI API 호출 코드 중복, 이미지 전용 PDF OCR 미지원
- **유지해야 할 기존 기능**: 전체 12단계 MVP 파이프라인 API·Request/Response·오류 메시지

---

## 2. 변경 전 문제점 (refactoring-coach 진단)

| # | 문제 유형 | 위치 | 구체적 내용 |
|:---:|:---|:---|:---|
| ① | 환경 변수 중복 | `services.py` | `os.getenv("AI_PROVIDER")` 등 동일 읽기 코드가 3개 함수에 반복 |
| ② | AI API 호출 중복 | `services.py` | OpenAI·Gemini 호출 패턴이 `analysis`, `summarization`, `validation` 함수에 각각 중복 |
| ③ | OCR 미지원 | `parsers.py` | 이미지 전용 PDF는 텍스트 추출 → 422 오류로 종료; OCR 폴백 없음 |
| ④ | 함수가 너무 긴 경우 | `parsers.py` | `extract_text_from_file()` 한 함수 안에 5가지 형식 분기가 혼재 |

---

## 3. 변경 내용

| 파일 | 변경 내용 | 이유 |
|:---|:---|:---|
| **[NEW] app/core/config.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/core/config.py)** | `AIConfig` 데이터 클래스, `get_ai_config()`, `is_api_key_valid()` 추가 | 환경 변수 읽기를 한 곳에서 관리 |
| **[NEW] app/core/\_\_init\_\_.py** | 패키지 초기화 | `app.core` 모듈 임포트 지원 |
| **[MODIFY] [app/services.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/services.py)** | 공통 `_call_llm_api()`, `_call_openai()`, `_call_gemini()` 분리; 각 서비스 함수를 `_build_*_prompt()` / `_parse_*_response()` / `_*_fallback()`으로 역할 분리 | AI 호출 중복 제거, 가독성 개선 |
| **[MODIFY] [app/parsers.py](file:///c:/Workspace/team-project/team-project-comm-summary/app/parsers.py)** | 형식별 파서를 `_extract_txt/pdf/docx/hwp/pptx()` 독립 함수로 분리; `_ocr_pdf_fallback()` 추가; `_clean_text()` / `_make_section()` 분리 | OCR 지원, 함수 크기 감소 |
| **[MODIFY] [requirements.txt](file:///c:/Workspace/team-project/team-project-comm-summary/requirements.txt)** | `pytesseract>=0.3.10`, `Pillow>=10.0.0` 추가 | OCR 의존성 명시 |

---

## 4. OCR 처리 흐름 (신규 기능)

```
PDF 업로드
  └─ PyMuPDF 텍스트 추출
        ├─ 텍스트 ≥ 20자  →  기존 분석 파이프라인 진행
        └─ 텍스트 < 20자 (이미지 전용 PDF)
              └─ pytesseract OCR 폴백
                    ├─ OCR 성공  →  분석 파이프라인 진행
                    └─ pytesseract 미설치 / OCR 실패  →  422 오류
```

> [!IMPORTANT]
> `pytesseract`는 Python 패키지 외에 **Tesseract OCR 엔진**이 시스템에 설치되어 있어야 합니다.
> - Windows: https://github.com/UB-Mannheim/tesseract/wiki 에서 설치 후 PATH 등록
> - 한국어 지원: `tesseract-ocr-kor` 언어팩 설치 필요

---

## 5. 기존 기능 유지 확인

- ✅ **API 경로**: `POST /api/v1/documents/analyze`, `DELETE /api/v1/documents/{file_id}` 등 전부 유지
- ✅ **Request/Response 형식**: 모든 Pydantic DTO (`IntegratedResultResponse`, `SearchResponse` 등) 유지
- ✅ **실행 명령**: `uvicorn app.main:app --reload` 유지
- ✅ **오류 메시지**: `DocumentParsingError` 메시지 형식 유지

---

## 6. 테스트 결과

```bash
python -m pytest tests/test_api.py -v
```

```
tests/test_api.py::test_full_12step_mvp_pipeline      PASSED
tests/test_api.py::test_unsupported_file_extension     PASSED
tests/test_api.py::test_empty_file_content             PASSED
tests/test_api.py::test_delete_nonexistent_document    PASSED

4 passed in 2.52s
```

---

## 7. 수동 확인 기준

- [ ] 서버가 `uvicorn app.main:app --reload`로 정상 실행되는가?
- [ ] Swagger(`http://127.0.0.1:8000/docs`)에서 전체 API 목록이 표시되는가?
- [ ] TXT 파일 업로드 → 12단계 파이프라인이 정상 동작하는가?
- [ ] 이미지 전용 PDF 업로드 시 OCR 결과가 분석에 활용되는가?
- [ ] 잘못된 확장자(xlsx) 업로드 시 400 오류가 반환되는가?

---

## 8. 주의사항 또는 후속 작업

- Tesseract OCR 엔진이 시스템에 설치되지 않으면 이미지 PDF는 기존과 동일하게 422로 처리됨 (기존 기능 미훼손)
- OCR 결과 품질은 이미지 해상도 및 Tesseract 언어팩 설치 여부에 따라 달라짐
- `pytesseract` 설치 후 OCR 결과 단위 테스트 추가 권장
