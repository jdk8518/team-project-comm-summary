# AGENTS.md

## 1. 프로젝트 개요

- 프로젝트명:AI Agent를 활용한 회의록, 업무보고, 공문자료 등을 이용한  문서 분석 시스템 구축
- 프로젝트 목적:문서를 업로드하면 AI가 핵심 내용을 요약하고 검증 결과를 제공한다.
- 주요 기술: Language: Python 3
            Backend: FastAPI
            AI Workflow: LangChain, LangGraph
            Document Processing: PDF, DOCX, TXT, HWPX, PPTX
            Frontend: 추후 MVP 단계에서 결정
            Database: 초기 단계에서는 사용하지 않음
- 요구사항 문서: `./docs/requirements.md`
- 기능 분해 문서: `./docs/function-breakdown.md`
- MVP 계획 문서: `./docs/MVP-plan.md`

## 2. 작업 시작 순서

1. `./AGENTS.md`를 읽는다.
2. `./README.md`를 읽는다.
3. `./docs/requirements.md`를 읽는다.
4. `./docs/function-breakdown.md`를 읽는다.
5. `./docs/MVP-plan.md`를 읽는다.
6. 현재 브랜치와 `git status`를 확인한다.
7. 담당 기능과 관련된 코드와 테스트를 확인한다.
8. 변경할 파일과 구현 계획을 제시한다.

## 3. 작업 범위

- 요청받은 기능과 직접 관련된 파일만 수정한다.
- 다른 팀원의 변경 사항을 삭제하거나 덮어쓰지 않는다.
- 공통 API, 데이터 모델, 환경변수, 폴더 구조를 임의로 변경하지 않는다.
- 요구사항에 없는 기능을 임의로 추가하지 않는다.
- 구조 변경이 필요하면 이유, 영향 파일, 대안, 테스트 범위를 먼저 보고한다.

## 4. 구현 및 테스트

- 기존 코드 스타일과 구조를 따른다.
- 입력값 검증과 주요 오류 처리를 포함한다.
- 변경 기능과 관련된 테스트를 작성하거나 수정한다.
- 정상 입력과 주요 오류 입력을 확인한다.
- 실행하지 못한 테스트가 있으면 이유를 완료 보고에 남긴다.

## 5. Git 및 PR

- `main`과 `develop`에서 직접 기능을 구현하지 않는다.
- 최신 `develop`에서 작업 브랜치를 생성한다.
- 관계없는 변경을 하나의 Commit에 포함하지 않는다.
- Push 전 `git status`, `git diff`, 테스트 결과를 확인한다.
- 완료된 작업은 PR을 통해 `develop`에 병합한다.
- PR 제목과 본문에 변경 내용, 테스트 결과, 영향 범위를 작성한다.
- 팀 검토 없이 `main`에 병합하지 않는다.
- 강제 Push와 Git 기록 삭제는 임의로 수행하지 않는다.

## 6. 보안

- API Key, 비밀번호, Token을 코드에 작성하지 않는다.
- `.env` 파일을 Commit하지 않는다.
- 개인정보와 인증정보를 로그에 출력하지 않는다.
- 민감정보가 발견되면 작업을 중단하고 노출 범위를 보고한다.

## 7. 완료 보고

- 구현한 내용
- 변경한 파일
- 입력과 출력
- 테스트 방법과 결과
- 다른 기능과 연결할 부분
- 공통 구조에 미치는 영향
- 남아 있는 문제

## 8. 외부 문서 처리: HWPX

HWPX 읽기, 수정, 생성, 검증 기능은 [`python-hwpx`](https://github.com/airmang/python-hwpx)를 사용해 구현합니다. Python 3.10 이상에서 `pip install python-hwpx`로 설치하고, 의존성은 프로젝트의 `requirements.txt` 또는 `pyproject.toml`과 잠금 파일에 명시합니다. 외부 라이브러리의 소스 코드를 이 저장소에 복사하지 않습니다.

`HwpxDocument.open()`으로 원본을 열고, 결과는 예를 들어 `output/report-updated.hwpx`처럼 새 경로에 저장합니다. 개발·테스트 중 사용자 원본을 덮어쓰지 않습니다. HWP(v5 바이너리)는 먼저 HWPX로 변환해야 합니다.

문서 쓰기 후에는 `save_to_path(..., return_report=True)`의 `MutationReport`를 확인하고, 비민감 HWPX 테스트 픽스처로 회귀 테스트를 추가합니다. 테스트는 요청한 내용 변경과 저장 결과의 라이브러리 검증 통과를 모두 확인해야 합니다. 개인정보·기밀·운영 문서는 저장소에 커밋하지 않습니다.
