# 작업 완료 보고서

## 작업 지시사항 원문

> vibe-frame-kit의 refactoring-coach 기준을 참조해서 현재 MVP 코드를 리팩토링하라.
>
> AI 분석·요약·검증 응답 오류 표시, 현재 폴더 기반 AI 저장 폴더 추천, DB 상태와 접속 API 검토, `YYYY-MM-DD_원본파일명(순번)` 파일명과 중복 순번 증가 규칙을 반영한다.

## 사용 AI 모델

상세 모델 ID 확인 불가

## 작업 수행 시간

- 작업 시작 시간: 2026-07-25 19:10:00 +09:00
- 작업 완료 시간: 2026-07-25 19:39:56 +09:00
- 총 작업 수행 시간: 1796초
- 토큰 정보: 현재 세션에서 조회할 수 없음

## 수행 내용

AI 호출 공통 계층이 API 키 누락, HTTP 오류, 빈 응답, JSON 구조 오류를 구분해 오류 메시지를 반환하도록 수정했다. 분석·요약·검증 결과 모델에 `error_message`를 추가하고, 규칙 기반 대체 결과가 생성되더라도 오류 상태를 유지하도록 했다. 통합 분석 응답은 세 단계 중 하나라도 오류가 있으면 `ERROR` 상태를 반환하며, 프론트엔드는 결과 화면 상단에 단계별 오류 메시지를 표시한다.

문서 분석 시 `output` 아래 실제로 존재하는 폴더 목록과 분석 키워드를 폴더 추천 프롬프트에 전달하도록 변경했다. AI 응답은 후보 목록에 있는 경로만 허용하고, AI를 사용할 수 없는 경우 기존 점수 기반 추천으로 안전하게 대체한다.

MVP DB가 인메모리 저장소라는 사실을 명시적으로 확인할 수 있도록 `/api/v1/documents/health/db`를 추가했다. 이 API는 연결 가능 여부, 현재 레코드 수, 영속성 여부와 SQLite/PostgreSQL 전환 권고를 반환한다. 현재 검색·저장·이동·삭제 API는 기존 인메모리 동작을 유지한다.

파일 저장 시 요청받은 파일명을 그대로 사용하지 않고 원본 파일명에서 확장자를 보존해 `YYYY-MM-DD_원본파일명(순번).확장자`를 서버에서 생성한다. 같은 날짜·원본명·폴더에 파일이 있으면 순번을 1부터 증가시키며, 파일은 배타적 생성 모드로 저장해 덮어쓰기를 방지한다. 업로드 화면의 파일명 입력은 읽기 전용으로 표시한다.

## 변경한 파일

- `app/services.py`
- `app/db.py`
- `app/api.py`
- `app/schemas.py`
- `static/index.html`
- `tests/test_api.py`
- `walkthrough/Gharam/20260725_34_refactor_ai_db_filename_rules.md`

## 입력과 출력

입력은 업로드 문서, 분석 키워드, `output` 하위의 기존 폴더 목록, 저장 요청이다. 출력은 AI 단계별 오류가 포함된 통합 분석 결과, 후보 폴더 중 선택된 추천 경로, DB 상태 응답, 규칙을 적용한 고유 아카이빙 파일 경로다.

## 테스트 방법과 결과

`node -e`로 `static/index.html`의 JavaScript 문법을 검사했으며 `JavaScript syntax OK`를 확인했다. `git diff --check -- app/services.py app/db.py app/api.py app/schemas.py static/index.html tests/test_api.py`도 공백 오류 없이 완료됐다. `tests/test_api.py`에는 DB 상태 API와 동일 원본 파일의 순번 증가 회귀 테스트를 추가했다.

`python -m pytest tests/test_api.py -v`와 `python -m py_compile app/services.py app/db.py app/api.py app/schemas.py`는 실행을 시도했으나, 현재 환경의 pyenv에 전역 또는 로컬 Python 버전이 설정되지 않아 실행하지 못했다(`No global/local python version has been set yet`).

## 다른 기능과 연결할 부분

분석 화면은 `error_message`를 사용해 오류를 표시하고, 저장 화면은 서버가 생성한 최종 파일명을 그대로 보여준다. 폴더 추천 API와 파일 저장 API는 동일한 `output` 루트 정규화 규칙을 공유한다. DB 상태 API는 운영 환경에서 영속 저장소로 교체할 때 연결 확인 지점으로 사용할 수 있다.

## 공통 구조에 미치는 영향

기존 FastAPI 라우터와 인메모리 MVP DB 구조를 유지하면서 응답 스키마에 선택적 오류 필드를 추가했다. 저장 파일명 생성은 DB 모듈의 공통 함수로 분리했으며, 기존 저장·검색·이동·삭제 흐름의 경로 루트 규칙과 충돌하지 않는다.

## 남아 있는 문제

현재 DB는 여전히 프로세스 메모리에만 저장되므로 서버 재시작 후 자료가 유지되지 않는다. 상태 API에 이 한계와 SQLite/PostgreSQL 전환 권고를 명시했지만, 실제 영속 DB 마이그레이션은 별도 작업이 필요하다. Python 실행 환경을 설정한 뒤 전체 API 회귀 테스트를 다시 실행해야 한다. 기존 작업과 무관한 `docs/문서 요약 시스템 구축_1차 과제 관련_Doc(Ver 0.22) copy.txt` 변경은 보존했으며 이번 작업에 포함하지 않았다.
