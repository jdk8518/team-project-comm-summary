# 작업 완료 보고서

## 작업 지시사항 원문

> AI 프로바이더를 `openai`, `google`, `deepseek`에서 사용할 수 있도록 수정하고, AI 프로바이더·API 키·모델을 `.env`에서 설정하라.

## 사용 AI 모델

상세 모델 ID 확인 불가

## 작업 수행 시간

- 작업 시작 시간: 2026-07-25 19:46:00 +09:00
- 작업 완료 시간: 2026-07-25 19:56:00 +09:00
- 총 작업 수행 시간: 600초
- 토큰 정보: 현재 세션에서 조회할 수 없음

## 수행 내용

AI 설정을 `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL` 세 환경변수로 통일했다. 지원 프로바이더는 `openai`, `google`, `deepseek`, 테스트용 `mock`이며, 모델을 생략하면 프로바이더별 기본 모델을 사용한다. 기존 `OPENAI_API_KEY`와 `OPENAI_MODEL` fallback은 제거해 `.env` 설정 경로가 명확해졌다.

OpenAI 호출은 공통 OpenAI 호환 클라이언트로 정리하고, DeepSeek는 `https://api.deepseek.com` base URL을 사용하는 별도 분기로 연결했다. Google은 Gemini `generateContent` API를 `google` 프로바이더 이름으로 호출하며 시스템 지시문과 JSON 응답 설정을 전달한다. 세 프로바이더의 실패·빈 응답·JSON 오류는 기존 AI 오류 메시지 흐름으로 전달된다.

`.env.example`과 README에 설정 예시와 지원 프로바이더를 갱신했다. 실제 `.env`의 API 키 값은 확인하거나 출력하지 않았다. 테스트에서는 `tests/conftest.py`의 자동 fixture로 외부 API 호출을 차단하고, 프로바이더별 환경 설정과 호출 디스패치를 별도 회귀 테스트로 검증했다.

## 변경한 파일

- `.env.example`
- `README.md`
- `app/core/config.py`
- `app/services.py`
- `tests/conftest.py`
- `tests/test_ai_config.py`
- `walkthrough/Gharam/20260725_36_add_openai_google_deepseek_env_config.md`

## 입력과 출력

입력은 `.env`의 `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`과 문서 분석 프롬프트다. 출력은 선택된 프로바이더의 JSON 분석 결과 또는 안전한 오류 메시지다.

## 테스트 방법과 결과

`python -m py_compile app/core/config.py app/services.py`가 통과했다. `python -m pytest tests -q` 결과는 `18 passed, 1 warning`이다. 경고는 Starlette TestClient의 httpx 관련 deprecation warning이며 기능 실패는 아니다. `git diff --check`도 통과했다.

## 다른 기능과 연결할 부분

기존 분석·요약·검증 서비스는 공통 `_call_llm_api`를 통해 프로바이더를 선택하므로 세 기능 모두 동일한 `.env` 설정을 사용한다. 폴더 추천도 같은 호출 계층을 사용해 선택된 AI 프로바이더를 따른다.

## 공통 구조에 미치는 영향

설정 모듈과 공통 AI 호출 계층만 확장했으며 API 응답 스키마와 문서 처리 흐름은 유지했다. 테스트 실행 시 외부 API가 호출되지 않도록 테스트 환경만 `mock`으로 격리했다.

## 남아 있는 문제

실제 OpenAI·Google·DeepSeek 계정의 네트워크 응답은 보안상 키를 출력하지 않고, 테스트에서도 외부 호출을 차단했으므로 여기서 검증하지 않았다. 운영 실행 전 `.env`에 올바른 프로바이더별 키와 모델을 설정해야 한다. 기존 무관 문서 변경은 보존했다.
