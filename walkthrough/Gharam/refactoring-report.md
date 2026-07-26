# MVP 리팩토링 완료 보고서

## 1. 구현한 내용

MVP 코드를 **계층적 모놀리스** 구조로 안전하게 리팩토링했습니다.
vibe-frame-kit의 `refactoring-coach` 원칙(기존 기능/API 계약/테스트 100% 유지)을 엄수하며 진행했습니다.

---

## 2. 변경한 파일

### 신규 생성 (새 레이어 구조)

| 파일 | 역할 |
|------|------|
| `app/api/__init__.py` | API 패키지 초기화 (순환 임포트 방지를 위해 비워둠) |
| `app/api/routes/__init__.py` | Routes 서브패키지 초기화 |
| `app/api/routes/documents.py` | **Router Layer** — 모든 API 엔드포인트 정의 (기존 `app/api.py`의 코드 이동) |
| `app/api/schemas/__init__.py` | Schemas 서브패키지 초기화 |
| `app/api/schemas/document.py` | **Schema Layer** — `app.schemas` re-export 래퍼 |
| `app/agents/__init__.py` | Agents 패키지 초기화 |
| `app/agents/document_agent.py` | **Agent Layer** — LLM 서비스 함수 re-export |
| `app/models/__init__.py` | Models 패키지 초기화 |
| `app/models/document_db.py` | **Model Layer** — SQLite DB 함수 re-export |
| `app/services/__init__.py` | **Services 패키지 초기화** — 모든 서비스 함수 re-export + monkeypatch 호환성 |
| `app/services/_service_impl.py` | Services 실제 구현체 (기존 `app/services.py` 코드 이동) |
| `app/services/parser_service.py` | **Parser Service Layer** — 파서 함수 re-export |
| `app/services/document_service.py` | **Document Service Orchestrator** — AI 파이프라인 오케스트레이터 |
| `app/utils/__init__.py` | Utils 패키지 초기화 |
| `app/utils/file_utils.py` | **Utilities Layer** — 파일명/경로 정제 유틸리티 |

### 수정 (하위 호환성 래퍼 또는 import 경로 수정)

| 파일 | 변경 내용 |
|------|-----------|
| `app/main.py` | `from app.api import router` → `from app.api.routes.documents import router` (순환 임포트 해결) |
| `app/schemas.py` | 원본 Pydantic 정의 유지 (정규 정의 위치 — 순환 임포트 방지) |

### 삭제

| 파일 | 이유 |
|------|------|
| `app/api.py` | `app/api/` 패키지로 전환 (Python 공존 불가) |
| `app/services.py` | `app/services/` 패키지로 전환 (Python 공존 불가) |

---

## 3. 최종 디렉토리 구조

```
app/
├── __init__.py
├── main.py                          # FastAPI 진입점
├── schemas.py                       # Pydantic DTO 정규 정의
├── parsers.py                       # 문서 파서 (6종 포맷)
├── db.py                            # SQLite DB CRUD
├── core/
│   ├── __init__.py
│   └── config.py                    # AI 프로바이더 설정
├── api/                             # Presentation / Router Layer
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── documents.py             # API 엔드포인트 정의
│   └── schemas/
│       ├── __init__.py
│       └── document.py              # Schema re-export 래퍼
├── agents/                          # AI Agent Layer
│   ├── __init__.py
│   └── document_agent.py            # LLM Agent re-export
├── services/                        # Application Service Layer
│   ├── __init__.py                  # 공개 인터페이스 + monkeypatch 호환성
│   ├── _service_impl.py             # AI 분석/요약/검증 실제 구현
│   ├── parser_service.py            # Parser Service re-export
│   └── document_service.py          # Pipeline Orchestrator re-export
├── models/                          # Persistence / DB Model Layer
│   ├── __init__.py
│   └── document_db.py               # DB 함수 re-export
└── utils/                           # Utilities Layer
    ├── __init__.py
    └── file_utils.py                # 파일명/경로 정제 유틸리티
```

---

## 4. 입력과 출력

### 연결 흐름 (Request → Response)

```
HTTP Request
    ↓
app/api/routes/documents.py   [Router Layer]
    ↓ validate_file_metadata()
app/parsers.py                [Parser — extract_text, structure_text]
    ↓ run_document_analysis()
app/services/_service_impl.py [Agent/Service Layer — LLM 호출]
    ↓ store / update
app/db.py                     [Model Layer — SQLite CRUD]
    ↑ IntegratedResultData
app/schemas.py                [Schema Layer — Pydantic DTO]
    ↓
HTTP Response (JSON)
```

---

## 5. 테스트 방법과 결과

```bash
python -m pytest -v
```

```
27 passed, 2 warnings in 7.70s
```

- `tests/test_ai_config.py` — 7개 통과 (AI Config, LLM 디스패치, monkeypatch 호환성)
- `tests/test_api.py` — 17개 통과 (12단계 MVP 파이프라인 통합 테스트 포함)
- `tests/test_parsers.py` — 3개 통과 (HWP/HWPX 파서)

---

## 6. 기술적 해결 과제

### 순환 임포트 (Circular Import) 해결

- **문제**: `app/schemas.py` → `app.api.schemas.document` → `app.api.__init__` → `app.api.routes.documents` → `app.schemas` 순환 발생
- **해결**: `app/schemas.py`를 정규 정의 파일로 유지하고, `app/api/schemas/document.py`를 re-export 래퍼로 구성. `app/main.py`에서 `app.api.routes.documents`를 직접 import

### monkeypatch 호환성 해결

- **문제**: `test_ai_config.py`가 `monkeypatch.setattr(services, 'get_ai_config', ...)`를 사용하는데, `_service_impl.py` 내부에서 `get_ai_config`를 직접 import하면 monkeypatch가 무효화됨
- **해결**: `_call_llm_api`와 `_analysis_fallback`에서 `get_ai_config`, `_call_openai`, `_call_google`, `_call_deepseek`를 `import app.services as _svc`를 통한 **late-binding**으로 호출

### Python 모듈 vs 패키지 공존 불가

- **문제**: `app/api.py`와 `app/api/` 디렉토리는 Python에서 동시에 `app.api`로 참조 불가
- **해결**: `app/api.py`, `app/services.py` 삭제 후 동명 패키지로 전환. 코드는 `_service_impl.py`로 이동

---

## 7. 다른 기능과 연결할 부분

- `app/agents/document_agent.py` — 향후 LangGraph 상태 머신 도입 시 이 파일에서 Agent 그래프 정의
- `app/services/document_service.py` — 향후 독립적인 파이프라인 함수로 확장 가능
- `app/models/document_db.py` — 향후 SQLAlchemy ORM 도입 시 Model 클래스 정의 위치
- `app/utils/file_utils.py` — `compute_archiving_paths()` 함수는 `app/db.py`의 아카이빙 로직과 통합 가능

---

## 8. 공통 구조에 미치는 영향

| 항목 | 영향 |
|------|------|
| API 계약 | 변경 없음 (모든 엔드포인트 경로/메서드/스키마 동일) |
| DB 스키마 | 변경 없음 (SQLite 테이블 구조 동일) |
| `.env` 설정 | 변경 없음 (`ARCHIVE_ROOT`, `AI_PROVIDER` 등 동일) |
| 테스트 | 27개 전체 통과 |

---

## 9. 남아 있는 문제

- `docpler` 라이브러리 Deprecation 경고: `pip install hwpcli`로 대체 권장 (기능 동작에는 영향 없음)
- `httpx` → `httpx2` 마이그레이션 권장 경고 (FastAPI TestClient 관련, 기능 영향 없음)
- `app/db.py`는 아직 단일 파일로 유지 중. 향후 `app/models/document_db.py`로 코드를 완전 이동할 수 있음
