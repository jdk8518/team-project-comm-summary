# 작업 완료 보고서

## 작업 지시사항 원문

> [docpler/docpler-python](https://github.com/docpler/docpler-python)의 문서를 검토하여 HWP 텍스트 추출 기능에 반영하라.

## 사용 AI 모델

상세 모델 ID 확인 불가

## 작업 수행 시간

- 작업 시작 시간: 2026-07-25 20:15:00 +09:00
- 작업 완료 시간: 2026-07-25 20:28:00 +09:00
- 총 작업 수행 시간: 780초
- 토큰 정보: 현재 세션에서 조회할 수 없음

## 수행 내용

공식 문서가 안내하는 `pip install docpler` 및 `from docpler.hwp import convert; convert("document.hwp")` 사용법을 확인하고, HWP v5 바이너리 입력은 docpler를 우선 호출하도록 파서를 변경했다. 임시 HWP 파일을 안전하게 생성·삭제하며, 변환 결과가 비어 있거나 변환 중 예외가 발생하면 바이너리 문자열 fallback 대신 명시적인 `DocumentParsingError`를 반환한다.

HWPX 입력은 ZIP 컨테이너 유효성을 먼저 확인한 뒤 `HwpxDocument.open(...).export_text()`를 사용하도록 수정했다. python-hwpx가 특정 기능을 읽지 못하는 경우에만 유효한 ZIP XML fallback을 사용하며, 손상된 HWPX를 ZIP 바이트 텍스트로 잘못 통과시키지 않는다.

`requirements.txt`에 `docpler>=1.0.5`를 추가하고 README에 HWP/HWPX 처리 경로를 기록했다. 공식 저장소는 docpler가 `hwpcli`로 이름이 변경되었고 docpler 패키지는 추가 업데이트를 받지 않는다고 안내하므로, 향후 hwpcli 전환을 별도 검토 대상으로 남겼다.

## 변경한 파일

- `app/parsers.py`
- `requirements.txt`
- `README.md`
- `tests/test_parsers.py`
- `walkthrough/Gharam/20260725_38_integrate_docpler_hwp_text_extraction.md`

## 입력과 출력

입력은 HWP v5 바이너리 또는 HWPX ZIP 문서다. 출력은 docpler가 반환한 Markdown 텍스트, python-hwpx가 반환한 HWPX 텍스트, 또는 파싱 실패 시 사용자에게 전달 가능한 `DocumentParsingError`다.

## 테스트 방법과 결과

현재 Python 3.12.10 환경에서 `python -m py_compile app/parsers.py`와 `python -m pytest tests -q`를 실행했다. 결과는 `21 passed, 2 warnings`이다. 경고는 Starlette TestClient의 httpx deprecation과 docpler 패키지 rename 안내다. 실제 공식 사용법으로 샘플 HWP도 실행했으며, 샘플 파일이 유효하지 않아 docpler의 Compound file 오류가 발생하는 것을 확인했다.

## 다른 기능과 연결할 부분

문서 업로드 API는 기존 `extract_text_from_file()`를 그대로 사용하므로 HWP 업로드도 docpler 변환 결과를 AI 분석·요약·검증 파이프라인으로 전달한다. 변환 실패는 422 파싱 오류로 API 예외 처리기에 연결된다.

## 공통 구조에 미치는 영향

문서 파서와 의존성·회귀 테스트만 변경했으며 AI, DB, 아카이빙 구조는 변경하지 않았다. 임시 파일은 `NamedTemporaryFile`로 관리하고 변환 후 항상 삭제한다.

## 남아 있는 문제

공식 저장소가 docpler의 후속 패키지로 `hwpcli`를 안내하므로 장기적으로 의존성을 hwpcli로 교체할지 검토해야 한다. 저장소의 샘플 HWP/HWPX 파일은 실제 정상 문서가 아니어서 성공적인 실문서 추출 fixture로 사용할 수 없다. 비민감한 정상 HWP fixture를 별도로 확보해야 한다.
