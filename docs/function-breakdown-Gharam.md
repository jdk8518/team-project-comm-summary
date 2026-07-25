<<<<<<< HEAD
# AI 문서 분석 시스템 기능 분해표 (Gharam)

본 문서는 `./docs/requirements-Gharam.md` 요구사항 정의서를 바탕으로 `vibe-frame-kit`의 `function-breakdown` 표준 템플릿 서식에 맞추어 AI 문서 분석 시스템의 세부 기능을 단위별로 분해하고 명세한 문서입니다.

---

## 1. 프로젝트 정보

| 항목 | 내용 |
| --- | --- |
| **프로젝트명** | AI Agent를 활용한 회의록, 업무보고, 공문자료 등을 이용한 문서 분석 시스템 구축 |
| **기준 문서** | `./docs/requirements-Gharam.md` |
| **작성일** | 2026-07-25 |

---

## 2. 기능 분해표

| 대분류 | 세부 기능 | 입력 | 처리 | 출력 | 구현 우선순위 | 관련 Agent/API |
| --- | --- | --- | --- | --- | --- | --- |
| **문서 입력** | 파일 업로드 & 유효성 검증 | 단일 문서 파일 (PDF, HWPX, DOCX, TXT, HWP, PPTX / 최대 50MB) | 확장자/MIME 대조, 50MB 용량 체크, 빈파일/암호화 유효성 검증, 임시 저장 | File ID (`file_id`), 임시 경로, 메타데이터 | 높음 (P1) | `POST /api/v1/documents/upload` (API) |
| **텍스트 추출** | 문서 텍스트 파싱 & 구조화 | `file_id`, 임시 파일 경로, 포맷 | 포맷별 파서 (`python-hwpx` 등), 공백/줄바꿈 정제, Heading/Table 구분 분리 | 정제 텍스트 (`raw_cleaned_text`), 구조화 객체 | 높음 (P1) | `POST /api/v1/documents/{file_id}/extract` (API) |
| **AI 문서 분석** | 메타데이터 & 핵심 요소 분석 | `file_id`, `raw_cleaned_text` | 날짜/수치 정규식 파싱(일반코드) + 중심주제/목적/3~4단구조/핵심문장/NER 파싱(AI) | 9대 필수 결과 항목 JSON (`analysis_data`) | 높음 (P1) | `POST /api/v1/documents/{file_id}/analyze` (Agent) |
| **핵심 내용 요약** | 팩트 기반 3단 요약문 생성 | `raw_cleaned_text`, `document_subject`, `core_structure` | short doc 사전 체크(일반코드) + 3~5줄 개요/구조별 요약 + Fact-Checker(AI) | 3단 요약 리포트 객체 (`summary_result`) | 높음 (P1) | `POST /api/v1/documents/{file_id}/summarize` (Agent) |
| **검증 결과 제공** | 필수 항목 누락 & 상충 탐지 | 원문 텍스트, 키워드, 검증후보, 요약 객체 | 필수 항목 누락 파이썬 Null 체크 + 본문-표 수치/일자 상충 LLM 대조 + 뱃지 부여 | 검증 상태 뱃지, 누락/상충 리포트, 근거 링크 | 높음 (P1) | `POST /api/v1/documents/{file_id}/verify` (Agent/API) |
| **화면 출력** | 분석 결과 시각화 & 대조 뷰 | 통합 결과 조회 DTO | 데이터 수신 및 UI 카드, 개체 뱃지, 검증 경고 컴포넌트 바인딩 | 웹 UI 분석 리포트 화면 | 높음 (P1) | `GET /api/v1/documents/{file_id}/result` (API) |

---

## 3. API 기능 목록 (⚙️ 일반 코드 구현)

| 기능 | Endpoint 후보 | 설명 | 우선순위 |
| --- | --- | --- | --- |
| **문서 업로드 API** | `POST /api/v1/documents/upload` | 단일 파일 수신, 확장자/용량/유효성 검증 및 임시 저장 후 File ID 반환 | 높음 (P1) |
| **텍스트 추출 API** | `POST /api/v1/documents/{file_id}/extract` | 확장자별 파서 기반 텍스트 정제 및 구조화(제목/문단/표) 추출 | 높음 (P1) |
| **통합 결과 조회 API** | `GET /api/v1/documents/{file_id}/result` | 분석·요약·검증이 완료된 리포트 데이터를 통합 바인딩하여 반환 | 높음 (P1) |
| **분석 상태 조회 API** | `GET /api/v1/documents/{file_id}/status` | 문서 분석 파이프라인 진행 상태 (Processing/Completed/Failed) 폴링 조회 | 높음 (P1) |

---

## 4. AI Agent 기능 목록 (🤖 AI Agent / 하이브리드 구현)

| Agent 기능 | 입력 | 처리 | 출력 | 우선순위 |
| --- | --- | --- | --- | --- |
| **문서 구조 & 개체명 분석 Agent** | `raw_cleaned_text` | 중심 주제 도출, 작성 목적 추론, 3~4단 구조 세그멘테이션, 원문 핵심 문장 선택, 인물/부서 NER 추출 | 9대 분석 결과 항목 JSON | 높음 (P1) |
| **Grounded 요약 생성 Agent** | 정제 텍스트, 문서 주체, 핵심 구조 | 3~5줄 전체 개요 요약, 카테고리별 세부 요약, 결론/제안 요약, 2단계 Fact-Checker 검증 | 팩트 검증 완료 3단 요약 객체 | 높음 (P1) |
| **내용 상충 대조 Agent** | 원문 텍스트, 요약문, 키워드 | 본문 텍스트 수치/일자 vs 표(Table Text) 셀 데이터 간 논리적 모순 대조 | 상충 경고 항목 및 "사용자 직접 확인 필요" 태그 | 높음 (P1) |

---

## 5. 후순위 기능 (Post-MVP)

| 기능 | 후순위 이유 | 추후 구현 방향 |
| --- | --- | --- |
| **스캔본 PDF OCR 파싱** | MVP 범위는 디지털 텍스트 포함 문서에 집중하며 OCR 라이브러리 연동 복잡성 배제 | Tesseract / Naver CLOVA OCR 파이프라인 추가 연동 |
| **다중 문서 비교 분석** | 단일 문서 분석 핵심 가치 검증이 선행되어야 함 | 부서A vs 부서B 문서 간 내용 상충 비교 탐지 확장 |
| **결과 리포트 PDF/JSON 다운로드** | 웹 화면 시각화 출력이 우선 제공 사항임 | ReportLab / PDF 변환 엔진을 통한 다운로드 기능 제공 |
| **유저 맞춤형 요약 옵션** | 기본 3단 요약으로 요구사항 수용 가능 | 숏폼/미디엄/롱폼 분량 조절 및 사용자 지정 주제 요약 옵션 |

---

## 6. 추천 구현 순서

| 순서 | 기능 | 이유 |
| --- | --- | --- |
| **1** | **문서 입력 및 텍스트 추출 (`FEAT-01`, `FEAT-02`)** | AI 파이프라인의 기초가 되는 텍스트 파싱 및 파일 관리 인프라 확립 |
| **2** | **AI 문서 분석 Agent (`FEAT-02_ANALYSIS`)** | 요약 및 검증 기능의 입력 데이터가 되는 9대 핵심 구조/개체 데이터 구축 |
| **3** | **AI 핵심 내용 요약 Agent (`FEAT-03`)** | 분석 데이터를 바탕으로 가독성 높은 3단 요약 리포트 생성 파이프라인 구축 |
| **4** | **AI 문서 검증 제공 모듈 (`FEAT-04`)** | 필수 정보 누락 룰 체크 및 본문-표 상충 탐지 리포트 결합 |
| **5** | **분석 결과 화면 출력 UI (`FEAT-05`)** | 전체 통합 조회 DTO 기반의 시각화 리포트 화면 구현 및 통합 검증 |

---

## 7. 기능별 세부 데이터 명세 및 입출력 JSON 규격

### 7.1 문서 입력 기능 (`FEAT-01`)
* **지원 포맷**: PDF (`.pdf`), DOCX (`.docx`), TXT (`.txt`), HWP (`.hwp`), HWPX (`.hwpx`), PPTX (`.pptx`) / 최대 50MB
* **HWPX 수칙**: HWP (v5 바이너리) 파일 수신 시 HWPX 포맷 선행 변환 파이프라인 적용 (`python-hwpx`, Python 3.10+ 사용)
* **응답 DTO (`POST /api/v1/documents/upload`)**:
  ```json
  {
    "success": true,
    "data": {
      "file_id": "doc_12345abc-6789-def0-1234-56789abcdef0",
      "file_path": "temp/uploads/doc_12345abc.pdf",
      "original_filename": "2026_업무보고.pdf",
      "format": "PDF",
      "mime_type": "application/pdf",
      "size_bytes": 1048576,
      "uploaded_at": "2026-07-25T13:11:00Z",
      "status": "VALIDATED"
    }
  }
  ```

---

### 7.2 문서 텍스트 추출 기능 (`FEAT-02`)
* **파서 구성**: `pdfplumber` (PDF), `python-docx` (DOCX), `chardet` (TXT), `python-hwpx` (`HwpxDocument.open()`), `python-pptx` (PPTX)
* **응답 DTO (`POST /api/v1/documents/{file_id}/extract`)**:
  ```json
  {
    "success": true,
    "data": {
      "file_id": "doc_12345abc-6789-def0-1234-56789abcdef0",
      "metadata": {
        "original_filename": "2026_업무보고.pdf",
        "format": "PDF",
        "extracted_char_count": 3450,
        "section_count": 3,
        "is_analyzable": true
      },
      "structured_content": {
        "title": "2026년 상반기 부서별 주요 업무보고",
        "sections": [
          {
            "section_id": 1,
            "section_title": "1. 추진 배경 및 목적",
            "content": "본 보고서는 2026년 상반기 부서별 주요 성과를 점검하고...",
            "content_type": "paragraph"
          }
        ]
      },
      "raw_cleaned_text": "2026년 상반기 부서별 주요 업무보고\n\n1. 추진 배경 및 목적..."
    }
  }
  ```

---

### 7.3 AI 문서 분석 기능 (`FEAT-02_ANALYSIS`) - 9대 필수 항목
* **하이브리드 역할 분담**:
  - **⚙️ 일반 코드 (Rule/Regex)**: 날짜/수치 정규식 파싱, 단순 미기재 Null Check (`"원문 미기재 (확인 필요)"`), 원문 위치 매핑
  - **🤖 AI Agent (LLM)**: 문서 주체(중심주제 1문장), 작성 목적 추론, 3~4단 구조 세그멘테이션, 원문 핵심 문장 선택(Verbatim 3~5개), 인물/부서 NER
* **응답 DTO (`POST /api/v1/documents/{file_id}/analyze`)**:
  ```json
  {
    "success": true,
    "data": {
      "file_id": "doc_12345abc-6789-def0-1234-56789abcdef0",
      "analysis_status": "WARNING",
      "document_subject": "AI Agent 기반 문서 분석 시스템 구축 및 상반기 성과 보고",
      "document_purpose": "DECISION_AND_REPORT",
      "core_structure": [
        {
          "category": "추진 배경 및 목적",
          "section_id": 1,
          "content_summary": "문서 검토 시간 단축 및 인적 오류 방지를 위한 AI 분석 시스템 구축"
        }
      ],
      "key_sentences": [
        {
          "sentence_id": 1,
          "section_id": 1,
          "text": "업무 현장에서는 회의록, 업무보고, 공문자료를 빠르게 검토해야 하며 인적 오류를 최소화해야 한다."
        }
      ],
      "key_keywords": {
        "persons": ["홍길동 팀장", "김철수 수석"],
        "organizations": ["디지털혁신팀", "AI개발팀"],
        "schedules": ["2026-08-31"],
        "metrics": ["예산 집행률 85%"],
        "concepts": ["AI Agent", "FastAPI", "HWPX 파싱"]
      },
      "verification_candidates": [
        {
          "candidate_id": "VER-01",
          "type": "MISSING_INFO",
          "target": "시범 적용 결과 보고 일정",
          "display_tag": "원문 미기재 (확인 필요)",
          "evidence": "3절: 시범 적용 후 피드백 수집 예정"
        }
      ],
      "evidence_grounding": [
        {
          "entity_or_item": "MVP 구축 기한",
          "section_id": 3,
          "original_sentence": "오는 2026년 8월 31일까지 MVP 구축을 완료할 예정이다."
        }
      ]
    }
  }
  ```

---

### 7.4 핵심 내용 요약 생성 기능 (`FEAT-03`)
* **요약 구조**: 1단 전체 개요 요약 (3~5줄) + 2단 핵심 구조별 요약 + 3단 결론/제안 요약
* **응답 DTO (`POST /api/v1/documents/{file_id}/summarize`)**:
  ```json
  {
    "success": true,
    "data": {
      "file_id": "doc_12345abc-6789-def0-1234-56789abcdef0",
      "summary_result": {
        "overview_summary": [
          "2026년 상반기 디지털혁신팀은 AI 기반 문서 분석 시스템 구축 계획을 수립함.",
          "오는 2026년 8월 31일까지 MVP 구축을 완료하고 현업 부서에 시범 적용할 예정임."
        ],
        "core_structure_summaries": [
          {
            "category": "추진 배경 및 목적",
            "summary_points": ["부서별 긴급 회의록 및 공문자료 검토 시간 단축 필요성 증대"],
            "source_section_ids": [1]
          }
        ],
        "conclusion_and_proposals": {
          "core_message": "AI 문서 분석 시스템 도입을 통해 검토 시간을 대폭 줄임.",
          "action_items": ["MVP 구축 기한 준수"]
        }
      }
    }
  }
  ```

---

### 7.5 문서 검증 결과 제공 기능 (`FEAT-04`)
* **검증 상태 뱃지 부여 조건**:
  - `정상`: 누락 0건 AND 상충 0건
  - `누락 탐지`: 필수 정보 누락 1건 이상 (⚙️ 일반 코드 처리)
  - `상충 가능성`: 본문-표 수치/일자 불일치 1건 이상 (🤖 AI Agent 대조)
  - `확인 필요`: AI 검증 결과의 판단 불확실 시 (`"사용자 직접 확인 필요"` 태그 부여)
* **응답 DTO (`POST /api/v1/documents/{file_id}/verify`)**:
  ```json
  {
    "success": true,
    "data": {
      "file_id": "doc_12345abc-6789-def0-1234-56789abcdef0",
      "verification_summary": {
        "status_badge": "확인 필요",
        "total_warnings_count": 2,
        "missing_items_count": 1,
        "conflict_items_count": 1
      },
      "missing_items": [
        {
          "missing_id": "MIS-01",
          "field_name": "후속 조치 보고 기한",
          "display_tag": "원문 미기재 (확인 필요)",
          "recommendation": "시범 적용 후속 보고 일정을 확인하십시오."
        }
      ],
      "conflict_items": [
        {
          "conflict_id": "CNF-01",
          "conflict_type": "VALUE_MISMATCH",
          "description": "본문 텍스트와 표 텍스트 간 금액 불일치",
          "uncertainty_tag": "사용자 직접 확인 필요",
          "recommendation": "원문 표 2행과 본문 2절 금액을 수동 대조하십시오."
        }
      ]
    }
  }
  ```

---

### 7.6 분석 결과 화면 출력 기능 (`FEAT-05`)
* **역할**: `GET /api/v1/documents/{file_id}/result` 단일 엔드포인트 통합 DTO 바인딩 및 시각화 UI 렌더링 (**⚙️ 100% 일반 코드**)
* **통합 Response DTO**:
  ```json
  {
    "success": true,
    "data": {
      "file_id": "doc_12345abc-6789-def0-1234-56789abcdef0",
      "status": "COMPLETED",
      "document_info": {
        "original_filename": "2026_상반기_업무보고.pdf",
        "format": "PDF",
        "size_formatted": "1.0 MB"
      },
      "analysis_data": {
        "analysis_status": "WARNING",
        "document_subject": "AI Agent 기반 문서 분석 시스템 구축 및 상반기 성과 보고",
        "key_keywords": {
          "persons": ["홍길동 팀장"],
          "schedules": ["2026-08-31"]
        }
      },
      "summary_data": {
        "overview": ["2026년 상반기 부서별 성과 점검 및 AI 문서 분석 시스템 구축 승인"]
      },
      "verification_data": {
        "status_badge": "확인 필요",
        "warning_count": 2
      }
    }
  }
  ```

---
=======
# AI 기반 문서 분석 및 요약 시스템 기능 분해 명세서 (Function Breakdown)

본 문서는 `vibe-frame-kit`의 **Function Breakdown Skill & Template** 기준을 엄격히 적용하여 `./docs/requirements-Gharam.md` 요구사항 정의서를 실행 가능한 세부 기능 단위로 분해하고, 입력/출력 데이터, 처리 로직, AI Agent 역할, API 엔드포인트 및 구현 순서를 정돈한 표준 설계 명세서입니다.

---

## 1. 프로젝트 개요 및 기능 분류 체계

### 1.1. 시스템 목적
문서(PDF, DOCX, TXT, HWP, HWPX, PPTX)를 입력받아 텍스트 파싱, AI 기반 핵심 분석(주제, 목적, 구조, 키워드, 검증후보), 과장 없는 3단 핵심 요약, 검증 신뢰도 점수(0~100점) 산출, 통합 대시보드 화면 출력, 규칙 기반 파일 아카이빙 및 DB 요약 검색/1-Click 다운로드를 자동화함.

### 1.2. 대분류 파이프라인 구조
```text
[FEAT-01] 문서 입력 및 3단계 유효성 검증
   ↓ (document_id, file Payload)
[FEAT-02] 6종 포맷 텍스트 추출 및 정제 (Text Normalization)
   ↓ (extracted_content JSON)
[FEAT-03] AI 기반 문서 8대 핵심 구조 분석 (DocumentAnalysisAgent)
   ↓ (analysis_result JSON)
[FEAT-04] AI 핵심 내용 3단 요약 생성 (DocumentSummarizerAgent)
   ↓ (summary_report JSON)
[FEAT-05] AI 문서 검증 & 신뢰도 점수 산출 (DocumentValidationAgent)
   ↓ (validation_result JSON)
[FEAT-06] 분석 결과 통합 대시보드 화면 출력 (One-Page Integrated View)
   ↓ (archiving_info & DB Record)
[FEAT-07] DB 요약 다각도 검색 및 원본 파일 1-Click 다운로드
```

---

## 2. FEAT-01: 문서 입력 및 유효성 검증 기능 분해

### 2.1. 기능 개요
지원 포맷(PDF, DOCX, TXT, HWP, HWPX, PPTX) 단일 문서 1건을 안전하게 수신하여 파일 메타정보 표시, 3단계(형식·크기·내용) 검증을 수행하고 `document_id`를 발급하여 텍스트 추출 파이프라인으로 전달함.

### 2.2. 세부 기능 분해 표

| 구분 | 세부 기능명 | 기능 설명 | 입력 데이터 | 출력 데이터 | 우선순위 / 비고 |
|---|---|---|---|---|---|
| **화면 (UI)** | 파일 선택 및 Dropzone UI | 탐색기 선택 또는 드래그 앤 드롭으로 단일 문서 선택 | 문서 파일 (File) | 선택된 파일 객체 | High (MVP) |
| **화면 (UI)** | 파일 메타정보 렌더링 | 선택 파일의 파일명, 포맷 확장자, 용량(KB/MB) 표시 | 파일 객체 (File) | 메타정보 UI 렌더링 | High (MVP) |
| **화면 (UI)** | 3단계 검증 상태 표시 | 검증 진행 및 통과/에러 메시지 알림 토스트 출력 | 검증 결과 객체 | 검증 알림 UI | High (MVP) |
| **API** | 문서 업로드 API | 단일 파일 수신, 유효성 검증 및 식별자 발급 | `multipart/form-data` | `200 OK` (Payload) / `4xx Error` | High (MVP) |
| **처리 (Logic)** | 1차: 파일 형식 검증 | 확장자 및 Magic Bytes 기반 미지원 포맷 차단 | 업로드 파일 | 검증 통과 여부 (Bool) | High (MVP) |
| **처리 (Logic)** | 2차: 파일 크기 검증 | 단일 파일 용량이 50MB 이하인지 확인 | 파일 크기 (bytes) | 검증 통과 여부 (Bool) | High (MVP) |
| **처리 (Logic)** | 3차: 문서 내용 검증 | 파싱 전 파일 손상, 암호화 및 빈 문서(0자) 감지 | 파일 스트림 / 파서 | 검증 통과 여부 (Bool) | High (MVP) |
| **오류 처리** | 미지원/용량초과 예외 | 50MB 초과, 미지원 확장자, 빈 문서 입력 시 거부 | 에러 조건 발생 | `400/413/422 Error` | High (MVP) |

### 2.3. API Endpoint 명세
- `POST /api/v1/documents/upload`
  - **Request**: `file` (binary), `document_type_hint` (optional)
  - **Response (200 OK)**:
    ```json
    {
      "success": true,
      "data": {
        "document_id": "doc_20260725_001",
        "filename": "2026_부서업무보고.pdf",
        "file_extension": "pdf",
        "file_size_bytes": 1048576,
        "validation_status": "PASSED"
      }
    }
    ```

---

## 3. FEAT-02: 문서 텍스트 추출 및 정제 기능 분해

### 3.1. 기능 개요
검증 통과된 문서 ID와 스트림을 전달받아 6종 포맷별 전용 파서(PyMuPDF, `python-docx`, `python-hwpx`, `python-pptx` 등)를 통해 Raw 텍스트를 파싱하고 공백 정제(Normalization)를 거쳐 표준 JSON 구조로 변환함.

### 3.2. 세부 기능 분해 표

| 구분 | 세부 기능명 | 기능 설명 | 입력 데이터 | 출력 데이터 | 우선순위 / 비고 |
|---|---|---|---|---|---|
| **처리 (Logic)** | ExtractorFactory 팩토리 | 확장자에 따른 전용 텍스트 파서 객체 동적 생성 | 파일 확장자 | Parser Instance | High (MVP) |
| **처리 (Logic)** | 6종 포맷 텍스트 추출 | PDF, DOCX, TXT, HWP/HWPX, PPTX 텍스트 파싱 | 파일 스트림 | Raw Text & Page Info | High (MVP) |
| **처리 (Logic)** | Text Normalizer | 불필요 공백 정제, 3개 이상 줄바꿈(`\n\n\n+`) 축소 | Raw Text | Cleaned Text | High (MVP) |
| **처리 (Logic)** | 기본 구조 태깅 | Heading, Paragraph, List 단위 섹션 배열 구성 | Cleaned Text | Section Array | High (MVP) |
| **처리 (Logic)** | 텍스트 품질 검증 | 추출 텍스트 20자 미만 또는 스캔본 이미지 감지 | Cleaned Text | Is Analyzable (Bool) | High (MVP) |
| **오류 처리** | 이미지전용/손상 예외 | 스캔 이미지 PDF/HWP 또는 손상 파일 시 알림 | 파싱 에러/0자 | `IMAGE_ONLY_DOCUMENT` | High (MVP) |

### 3.3. API Endpoint 명세
- `POST /api/v1/documents/extract`
  - **Response (200 OK)**: `extracted_content` (full_cleaned_text, sections, metadata) 반환.

---

## 4. FEAT-03: AI 기반 문서 8대 핵심 구조 분석 기능 분해

### 4.1. 기능 개요
정제 텍스트 JSON을 입력받아 `DocumentAnalysisAgent`가 원문 기반 8대 핵심 항목(문서 주체, 목적, 핵심 구조, 핵심 문장, 주요 키워드 5종, 검증 후보, 분석 상태, 근거 정보)을 분석하고 근거 인덱스를 매핑함.

### 4.2. 세부 기능 분해 표

| 구분 | 세부 기능명 | 기능 설명 | 입력 데이터 | 출력 데이터 | 우선순위 / 비고 |
|---|---|---|---|---|---|
| **AI Agent** | 1. 문서 주체 추론 | 문서 전체 대표 중심 주제(`document_subject`) 추론 | `full_cleaned_text` | `document_subject` | High (MVP) |
| **AI Agent** | 2. 문서 목적 분류 | 작성 의도(`document_purpose`: 제안/결정/전달) 분류 | `full_cleaned_text` | `document_purpose` | High (MVP) |
| **AI Agent** | 3. 핵심 구조 파싱 | 배경, 주요 내용, 결론/요구사항 3단 구조 추출 | `sections` 배열 | `core_structure` | High (MVP) |
| **AI Agent** | 4. 핵심 문장 추출 | 원문에서 대표 핵심 문장 3~5개 직접 선택 | `full_cleaned_text` | `key_sentences` 리스트 | High (MVP) |
| **AI Agent** | 5. 주요 키워드 추출 | 인물, 기관, 일정, 수치, 개념 5대 범주 키워드 파싱 | `full_cleaned_text` | `key_keywords` 5종 | High (MVP) |
| **AI Agent** | 6. 검증 후보 식별 | 모호한 표현, 특이 조건, 정밀 수치, 상충 후보 스크리닝 | `full_cleaned_text` | `verification_candidates` | High (MVP) |
| **처리 (Logic)**| 7. 분석 상태 산출 | 8대 필드 및 Grounding 점수 기반 `SUCCESS/WARNING` 판정 | Agent Output | `analysis_status` | High (MVP) |
| **처리 (Logic)**| 8. 근거 정보 매핑 | 추출 항목별 원문 구절(`evidence_text`) 1:1 매핑 | 분석 결과 항목 | `grounding_evidences` | High (MVP) |
| **오류 처리** | Grounding 실패 재시도 | 환각 감지 또는 Citation 미존재 시 최대 3회 Retry | Grounding Score < 80 | Retry Prompt / Fallback | High (MVP) |

### 4.3. API Endpoint 명세
- `POST /api/v1/documents/analyze` -> 재정의된 8대 분석 결과 JSON 반환.

---

## 5. FEAT-04: AI 핵심 내용 3단 요약 생성 기능 분해

### 5.1. 기능 개요
원문과 분석 결과를 수신하여 `DocumentSummarizerAgent`가 원문의 뉘앙스(제안/검토의 확정 표기 금지)를 100% 보존하며 개요(한 줄 요약+태그), 세부 구조 요약, 결론/향후계획의 3단 리포트를 생성함.

### 5.2. 세부 기능 분해 표

| 구분 | 세부 기능명 | 기능 설명 | 입력 데이터 | 출력 데이터 | 우선순위 / 비고 |
|---|---|---|---|---|---|
| **AI Agent** | Part 1. 개요 요약 생성 | 한 줄 요약(`one_line_summary`) 및 태그 5~7개 생성 | `full_cleaned_text` | `overview` 객체 | High (MVP) |
| **AI Agent** | Part 2. 세부 요약 생성 | 배경/목적, 현황/내용, 결정/요구사항별 세부 요약 | `structured_context` | `contextual_summary` | High (MVP) |
| **AI Agent** | Part 3. 결론 요약 생성 | 최종 결론, 제안 및 향후 추진 일정/액션아이템 요약 | `conclusion` | `conclusion_and_next_steps` | High (MVP) |
| **처리 (Logic)** | 뉘앙스 왜곡 검증 | '검토 중' 표현이 '확정'으로 변곡되었는지 룰 기반 체크 | 요약 결과 JSON | Nuance Valid (Bool) | High (MVP) |
| **오류 처리** | 요약 지연/실패 예외 | 30초 타임아웃 또는 API 에러 시 3회 재시도 처리 | 타임아웃/에러 | `504 Gateway Timeout` | High (MVP) |

### 5.3. API Endpoint 명세
- `POST /api/v1/documents/summarize` -> 3단 요약 JSON 반환.

---

## 6. FEAT-05: AI 문서 검증 & 신뢰도 점수 산출 기능 분해

### 6.1. 기능 개요
원문과 요약문을 교차 대조하여 NLI 함의, 수치 정확도, 근거 매핑률을 종합한 **검증 신뢰도 점수(`0~100점`)**를 산출하고, 80점 미만 경고 태그 및 사람이 눈으로 확인해야 할 **4대 필수 검토 리스트**를 생성함.

### 6.2. 세부 기능 분해 표

| 구분 | 세부 기능명 | 기능 설명 | 입력 데이터 | 출력 데이터 | 우선순위 / 비고 |
|---|---|---|---|---|---|
| **AI Processing**| NLI 문맥 일치성 검증 | 원문 대비 요약문 Entailment/Neutral/Contradiction 분류 | 원문 & 요약문 | NLI Score (0~100) | High (MVP) |
| **처리 (Logic)** | 수치/기한 100% 대조 | 예산, 수량, 날짜 등 수치 표기 1:1 대조 및 불일치 감지 | 원문 & 요약문 수치 | Numerical Score | High (MVP) |
| **처리 (Logic)** | 신뢰도 점수 엔진 | $(S_{NLI} \times 0.4) + (S_{Num} \times 0.35) + (S_{Cit} \times 0.25)$ 계산 | 3대 평가점수 | `confidence_score` | High (MVP) |
| **처리 (Logic)** | 4대 인간 검토 리스트 | 메타데이터, 정밀수치, 특이조건, 경고항목 체크리스트 | 분석/요약 결과 | `human_review_items` | High (MVP) |
| **오류 처리** | 검증 지연 예외 | NLI 엔진 지연 시 기본 80점 산출 및 수동확인 표출 | Validation Error | `VALIDATION_WARNING` | High (MVP) |

### 6.3. API Endpoint 명세
- `POST /api/v1/documents/validate` -> 신뢰도 점수 및 4대 인간 검토 체크리스트 JSON 반환.

---

## 7. FEAT-06: 분석 결과 통합 대시보드 화면 출력 기능 분해

### 7.1. 기능 개요
분석/요약/검증 결과를 사용자가 한 화면(One-Page Dashboard)에서 탐색할 수 있도록 메타데이터, 저장 예정 파일명/경로, 3단 요약, 신뢰도 배지, 대화형 체크박스 및 원본 다운로드 버튼을 렌더링함.

### 7.2. 세부 기능 분해 표

| 구분 | 세부 기능명 | 기능 설명 | 입력 데이터 | 출력 데이터 | 우선순위 / 비고 |
|---|---|---|---|---|---|
| **화면 (UI)** | 메타데이터 카드 UI | 문서 제목, 작성일, 시행일, 소속부서 카드 출력 | `metadata_header` | 메타데이터 UI | High (MVP) |
| **화면 (UI)** | 파일 아카이빙 카드 UI | 규칙 적용 **변경 예정 파일명** 및 **저장 폴더 경로** 표시 | `archiving_info` | 아카이빙 정보 UI | High (MVP) |
| **화면 (UI)** | 요약 & 신뢰도 UI | 한 줄 요약, 태그, 3단 요약 + 92.5점 신뢰도 배지 출력 | `summary_content` | 요약 대시보드 UI | High (MVP) |
| **화면 (UI)** | 원문 근거 모달 UI | `[원문근거보기]` 클릭 시 원문 해당 단락 하이라이트 | `evidence_citations` | 근거 대조 모달 | High (MVP) |
| **화면 (UI)** | 인간 검토 체크박스 | 4대 필수 검토 항목 사용자가 눈으로 직접 체크 | `human_review_items` | 대화형 체크박스 | High (MVP) |
| **화면 (UI)** | 원본 다운로드 버튼 | `[📥 1-Click 원본 파일 다운로드]` 실행 액션 | `document_id` | 파일 다운로드 실행 | High (MVP) |

### 7.3. API Endpoint 명세
- `GET /api/v1/documents/{document_id}/report` -> 통합 대시보드 JSON 반환.

---

## 8. FEAT-07: DB 요약 검색 및 원본 파일 다운로드 기능 분해

### 8.1. 기능 개요
아카이빙된 요약 내역을 DB에서 키워드, 부서, 기간, 문서 유형별로 검색하고, 결과 목록에서 요약 미리보기 모달 및 원본 파일 1-Click 다운로드 스트림을 제공함.

### 8.2. 세부 기능 분해 표

| 구분 | 세부 기능명 | 기능 설명 | 입력 데이터 | 출력 데이터 | 우선순위 / 비고 |
|---|---|---|---|---|---|
| **화면 (UI)** | DB 검색 바 & 필터 | 키워드 검색어, 소속부서, 기간, 문서 유형 선택 UI | 검색 조건 | Query Params | High (MVP) |
| **화면 (UI)** | 검색 결과 목록 리스트 | 검색된 문서 카드리스트, 요약 1줄, 신뢰도 점수 표시 | `search_results` | 목록 카드리스트 UI | High (MVP) |
| **화면 (UI)** | 요약 미리보기 모달 | 검색 항목 클릭 시 분석/요약 팝업 렌더링 | `document_id` | 미리보기 모달 | High (MVP) |
| **API** | DB 요약 검색 API | 조건별 Indexed DB Query 수행 및 페이징 응답 | Query Params | `200 OK` (Result List) | High (MVP) |
| **API** | 원본 파일 다운로드 API | 지정된 문서의 원본 파일 바이너리 스트림 반환 | `document_id` | File Binary Stream | High (MVP) |
| **오류 처리** | 검색결과없음 / 누락 | 검색 조건 미부합 또는 물리 파일 누락 시 알림 | 0건 / 파일 없음 | `200 Empty` / `404 Error` | High (MVP) |

### 8.3. API Endpoint 명세
- `GET /api/v1/documents/search?keyword=AI&department=AI개발팀&page=1&size=10`
- `GET /api/v1/documents/{document_id}/download` (`Content-Disposition` 파일 다운로드)

---

## 9. 전체 파이프라인 데이터 계약 및 상태 전이 명세 (Pipeline State Contract)

### 9.1. 문서 처리 상태 전이표 (State Transition)

```text
[UPLOADED] ──(Extract Success)──> [EXTRACTED] ──(Analyze Success)──> [ANALYZED]
    │                                │                                │
 (Error)                          (Error)                          (Error)
    ▼                                ▼                                ▼
[UPLOAD_FAILED]                 [EXTRACT_FAILED]                [ANALYSIS_FAILED]

[ANALYZED] ──(Summarize Success)─> [SUMMARIZED] ──(Validate Success)─> [VALIDATED] ──(Save)──> [ARCHIVED]
                                       │                                   │
                                    (Error)                             (Error)
                                       ▼                                   ▼
                            [SUMMARIZE_FAILED]                  [VALIDATION_WARNING]
```

### 9.2. 파이프라인 차단 규칙 (Short-Circuiting Rules)
1. 선행 단계 상태가 성공(`UPLOADED`, `EXTRACTED`, `ANALYZED`, `SUMMARIZED`)이 아닌 경우 후속 AI Agent 및 API 호출을 즉시 차단하고 에러 응답을 반환함.
2. 예외 발생 시 파이프라인은 해당 `document_id` 세션을 에러 상태로 변경하고 이전 단계까지 생성된 텍스트 및 기본 메타데이터만 보존함.

---

## 10. 추천 구현 순서 (Implementation Order Plan)

```text
Phase 1 (기반 파이프라인 구축):
  Step 1. FEAT-01 문서 입력 API & 3단계 유효성 검증 모듈 구현
  Step 2. FEAT-02 6종 포맷(PyMuPDF, python-docx, python-hwpx, python-pptx) 파서 구현

Phase 2 (AI Processing & Agent 구축):
  Step 3. FEAT-03 DocumentAnalysisAgent 8대 핵심 구조 분석 모듈 구현
  Step 4. FEAT-04 DocumentSummarizerAgent 3단 요약 생성 모듈 구현
  Step 5. FEAT-05 DocumentValidationAgent 신뢰도 점수 및 4대 검토 리스트 엔진 구현

Phase 3 (Dashboard & DB Search 구축):
  Step 6. FEAT-06 통합 대시보드 화면 출력 API 및 프론트엔드 UI 연동
  Step 7. FEAT-07 DB 요약 검색 API 및 1-Click 원본 파일 다운로드 스트림 구현
```
>>>>>>> 5e19089 (기능분해)
