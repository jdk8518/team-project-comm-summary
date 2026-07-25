# 작업 완료 보고서

## 작업 지시사항 원문

> HWP 파일을 HWPX로 변환하는 라이브러리의 작동상태를 점검하라.

## 사용 AI 모델

상세 모델 ID 확인 불가

## 작업 수행 시간

- 작업 시작 시간: 2026-07-25 20:00:00 +09:00
- 작업 완료 시간: 2026-07-25 20:12:00 +09:00
- 총 작업 수행 시간: 720초
- 토큰 정보: 현재 세션에서 조회할 수 없음

## 수행 내용

현재 의존성에 선언된 `python-hwpx>=0.1.0`을 실제 Python 3.12.10 환경에서 확인한 결과 설치 버전은 `3.6.0`이며 `from hwpx import HwpxDocument` import는 정상이다. `HwpxDocument`에는 `open`, `export_text`, `save_to_path` 등 HWPX 문서 API는 있지만 HWP(v5 바이너리)를 HWPX로 변환하는 converter API는 없다.

현재 `app/parsers.py`의 `.hwp` 경로는 HWP를 임시 `.hwpx` 파일로 저장한 뒤 `HwpxDocument.open()`에 직접 전달한다. HWP v5 파일은 OLE Compound File 시그니처(`D0 CF 11 E0 ...`)이므로 HWPX ZIP으로 열 수 없고, 해당 시도가 실패하면 ZIP XML 파싱과 바이너리 문자열 정제 fallback으로 진행한다. 샘플 HWP를 실제 실행한 결과 `UnicodeEncodeError`가 발생하거나, UTF-8 출력 기준으로 `ࡱ` 및 공백 중심의 526자 문자열이 반환되어 유효한 문서 텍스트 추출로 볼 수 없었다. 즉 현재 HWP→HWPX 변환은 작동하지 않는다.

샘플 `.hwpx` 파일도 시그니처는 `PK`였지만 표준 `zipfile.ZipFile` 검사에서 `BadZipFile: File is not a zip file`이 발생했다. 파서 fallback은 ZIP 바이트 자체를 텍스트로 반환해 4,504~4,562자 결과를 정상 텍스트처럼 통과시키는 문제도 확인됐다. 샘플 파일 자체의 손상 여부와 파서의 유효성 검증 누락을 분리해서 처리해야 한다.

## 변경한 파일

- `walkthrough/Gharam/20260725_37_check_hwp_to_hwpx_library_status.md`

코드 수정은 하지 않았다. 이번 요청은 작동상태 점검이므로, 기존 구현과 샘플 파일을 보존했다.

## 입력과 출력

입력은 `sample/range_sample_1.hwp`, `sample/range_sample_2.hwp`, `sample/range_sample_1.hwpx`, `sample/range_sample_2.hwpx`와 현재 `app/parsers.py` 구현이다. 출력은 라이브러리 import 상태, HWP 변환 API 제공 여부, 샘플별 파싱 결과와 실패 원인이다.

## 테스트 방법과 결과

`python-hwpx` 버전과 `HwpxDocument` 공개 메서드를 조회했다. HWPX 샘플은 `zipfile.ZipFile`로 컨테이너 검사를 실행했고 두 파일 모두 `BadZipFile`이었다. HWP/HWPX 샘플은 `extract_text_from_file()`로 직접 실행했다. HWP는 유효하지 않은 바이너리 텍스트가 반환됐고, HWPX는 ZIP 내부 텍스트가 아닌 ZIP 바이트 문자열이 반환됐다.

## 다른 기능과 연결할 부분

현재 API의 HWP 업로드 경로는 `extract_text_from_file()` 결과를 그대로 AI 분석으로 전달한다. 따라서 변환기 없이 HWP를 허용하면 바이너리 잔여 문자열이 분석·요약·검증 단계로 유입될 수 있다.

## 공통 구조에 미치는 영향

이번 점검에서는 공통 코드와 의존성을 변경하지 않았다. 변환 기능을 구현하려면 별도의 HWP v5 변환 도구(예: Windows 한글 설치 기반 자동화 또는 검증된 외부 변환 서비스)를 선택하고, 변환 산출물을 새 `.hwpx` 경로에 저장한 뒤 `HwpxDocument.open()`으로 검증하는 구조가 필요하다.

## 남아 있는 문제 및 수정안

`python-hwpx`만으로는 HWP→HWPX 변환을 해결할 수 없다. 우선 HWP 파일의 OLE 시그니처를 감지해 현재 HWPX 파서에 직접 전달하지 말고 명시적인 “HWP 변환기 미설정” 오류를 반환해야 한다. 실제 HWP 지원을 유지하려면 별도 변환기를 도입하고, 변환 후 `HwpxDocument.open()` 및 `validate()` 검증, 비민감 HWP/HWPX fixture 회귀 테스트를 추가해야 한다. 손상된 HWPX는 ZIP 유효성 검사를 통과하지 못하면 분석 전에 거부해야 한다.
