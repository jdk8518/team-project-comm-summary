# AI 기반 문서 분석 및 요약 시스템 기능 분해 명세서

본 문서는 `docs/requirements-Gharam.md`와 현재 FastAPI 구현을 기준으로 MVP 기능과 API를 단일 기준으로 정리합니다.

## 1. 프로젝트 기준

| 항목 | 기준 |
|---|---|
| 지원 형식 | PDF, DOCX, TXT, HWP, HWPX, PPTX |
| 파일 크기 | 파일당 최대 50MB |
| 저장소 | `ARCHIVE_ROOT` 하위 SQLite DB(`documents.db`) 및 원본·Markdown 파일 |
| AI 호출 | OpenAI SDK 기반 provider adapter |
| HWP/HWPX | HWP는 `docpler`, HWPX는 `python-hwpx` |
| OCR | PDF 추출 텍스트가 20자 미만일 때 Tesseract 기반 선택적 폴백 |

## 2. MVP 기능 분해

| ID | 기능 | 입력 | 처리 | 출력 | 실제 API |
|---|---|---|---|---|---|
| FEAT-01 | 문서 입력 및 유효성 검증 | 단일 또는 다중 파일 | 확장자, 파일당 50MB, 빈 파일·파싱 가능 여부 검증 | 분석 가능 여부 또는 오류 | `POST /api/v1/documents/analyze`, `POST /api/v1/documents/analyze-auto` |
| FEAT-02 | 텍스트 추출 및 정제 | 검증된 파일 | 포맷별 파싱, 공백 정제, PDF 텍스트 부족 시 선택적 OCR 폴백 | 정제 원문 텍스트와 구조 | 분석 API 내부 처리 |
| FEAT-03 | AI 문서 분석 | 정제 원문 | 주제, 목적, 핵심 구조, 핵심 문장, 키워드, 검증 후보 추출 | 분석 결과 | 분석 API 내부 처리 |
| FEAT-04 | AI 핵심 요약 | 원문 및 분석 결과 | 3단 요약과 핵심 태그 생성 | 요약 결과 | 분석 API 내부 처리 |
| FEAT-05 | AI 검증 | 원문 및 요약 결과 | 원문-요약 대조, 신뢰도와 사람 검토 항목 생성 | 검증 결과 | 분석 API 내부 처리 |
| FEAT-06 | 결과 대시보드 및 저장 | 통합 분석 결과, 사용자 수정값 | 결과 조회, 원본·요약 저장, 결과 수정 | 통합 결과와 저장 상태 | `GET /{file_id}/result`, `POST /{file_id}/save`, `PUT /{file_id}/summary`, `PUT /{file_id}/results` |
| FEAT-07 | DB 검색·파일 관리 | 검색 조건 또는 파일 ID | SQLite 검색, 다운로드, 이동, 삭제, 부서·폴더 조회 | 검색 결과 또는 파일 스트림 | `GET /search`, `GET /{file_id}/download`, `PUT /{file_id}/folder`, `DELETE /{file_id}` |

모든 API 경로는 `/api/v1/documents` 접두사를 사용합니다.

## 3. 입력·예외 처리

| 구분 | 기준 | 처리 |
|---|---|---|
| 미지원 형식 | 6종 외 확장자 | 4xx 오류와 지원 형식 안내 |
| 용량 초과 | 파일당 50MB 초과 | 해당 파일 거부; 다중 처리에서는 다른 파일을 계속 처리 |
| 텍스트 부족 | 정제 텍스트 20자 미만 | PDF는 OCR 폴백 시도; 실패 시 422 오류 |
| OCR 환경 미설치 | `pytesseract` 또는 Tesseract 실행 파일·언어 데이터 미설치 | OCR 결과 없음으로 처리하고 텍스트 추출 오류 안내 |
| AI 호출 실패 | provider 오류 또는 비정상 응답 | 문서 단위 실패 처리; 다중 처리의 다른 파일은 계속 진행 |

## 4. 단일·다중 처리 흐름

### 4.1 단일 문서 분석

1. `POST /analyze`로 파일을 수신한다.
2. 유효성 검증, 텍스트 추출·OCR 폴백, AI 분석·요약·검증을 순서대로 수행한다.
3. 통합 결과와 추천 파일명·폴더를 반환한다.
4. 사용자가 검토 후 `POST /{file_id}/save` 또는 수정 API로 저장한다.

### 4.2 다중 문서 자동 처리

1. 파일별로 `POST /analyze-auto`를 호출한다.
2. 각 파일을 독립적으로 분석한 뒤 SQLite와 아카이브에 `user_confirmed=false` 상태로 저장한다.
3. `GET /unconfirmed`으로 작업 목록을 조회하고, `PUT /{file_id}/confirm` 또는 `POST /batch-confirm`으로 확정한다.
4. 필요하면 `POST /batch-delete`로 작업 목록의 파일을 삭제한다.

## 5. API 목록

| 목적 | 메서드와 경로 |
|---|---|
| DB 상태 | `GET /health/db` |
| 단일 분석 | `POST /analyze` |
| 다중 자동 분석 | `POST /analyze-auto` |
| 미확정 목록 | `GET /unconfirmed` |
| 확정 저장 | `PUT /{file_id}/confirm`, `POST /batch-confirm` |
| 일괄 삭제 | `POST /batch-delete` |
| 수동 저장·수정 | `POST /{file_id}/save`, `PUT /{file_id}/summary`, `PUT /{file_id}/results` |
| 조회·검색 | `GET /{file_id}/result`, `GET /search`, `GET /departments`, `GET /folder-tree` |
| 파일 관리 | `GET /{file_id}/download`, `GET /{file_id}/markdown`, `PUT /{file_id}/folder`, `DELETE /{file_id}` |
| 폴더 추천 | `GET /{file_id}/recommend-folder`, `POST /{file_id}/recommend-folder` |

## 6. MVP 제외 범위

- OCR 결과 보정, 외부 OCR 서비스 연동, 이미지·표 중심 문서의 고도화 OCR
- 다중 문서 간 비교 분석
- PDF·JSON 형태의 분석 리포트 내보내기
- 고도화된 사용자 권한 관리, 통계 대시보드, 외부 그룹웨어 연동

## 7. 검증 기준

- 문서에 정의된 API가 `app/api/routes/documents.py`의 라우트와 일치한다.
- 단일 분석과 다중 자동 처리 모두 파일당 50MB·6개 형식·텍스트 추출 오류 정책을 따른다.
- OCR은 선택적 폴백이며, OCR 환경이 없는 경우에도 오류가 명확히 반환된다.
- SQLite 저장·검색·다운로드·삭제 흐름은 관련 자동 테스트와 수동 확인 절차로 검증한다.
