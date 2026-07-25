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
