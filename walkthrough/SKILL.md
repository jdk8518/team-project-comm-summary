---
name: walkthrough-reporting
description: Create and maintain approved project walkthrough completion reports. Use whenever a task has finished and Codex must document the work, including the original instruction, verified model information, measured execution time, token-usage availability, changes, and verification results.
---

# Walkthrough 완료 보고서

## 저장 전 절차

1. 실제 작업을 시작하기 직전에 현재 시간을 기록한다.
2. 작업을 완료하고 결과를 확인한다.
3. 보고서의 저장 경로와 파일명을 제시하고 사용자에게 저장 승인을 요청한다.
4. 사용자가 명시적으로 승인한 경우에만 파일을 저장한다.
5. 저장 직전에 완료 시간을 기록하고 시작 시간과의 차이를 초 단위로 계산한다. 사용자 승인 대기 시간은 작업 실행 시간에 포함하지 않는다.

## 저장 위치와 파일명

- 보고서 저장 전에 프로젝트 루트에서 `git branch --show-current`을 실행하여 현재 브랜치명을 확인한다.
- 확인한 브랜치명을 사용하여 프로젝트 루트의 `walkthrough/<현재 브랜치명>/`에 저장한다.
- 현재 브랜치가 `Gharam`이면 저장 위치는 `walkthrough/Gharam/`이다.
- 브랜치명이 비어 있는 detached HEAD 상태이면 임의 폴더명을 만들지 말고 사용자에게 저장 경로를 확인받는다.
- 파일명은 `YYYYMMDD_순번_커밋메시지.md` 형식을 사용한다.
- 같은 날짜에는 기존 파일을 확인하여 `01`부터 `99`까지 순차적으로 번호를 부여한다.
- 기존 보고서를 임의로 덮어쓰거나 삭제하지 않는다.

## 모델과 토큰 기록

- 모델 변경이 있으면 Codex 화면, 스레드 메타데이터, API 응답 등 확인 가능한 근거로 모델명을 확인한다.
- 실제 모델 ID를 확인할 수 없으면 추측하지 않고 `상세 모델 ID 확인 불가`로 기록한다.
- 사용자 지정 모델명과 시스템·API에서 확인한 모델명이 다르면 각각 구분해 기록한다.
- API 응답의 `usage` 등 신뢰 가능한 사용량 정보가 있을 때만 토큰 수를 기록한다.
- 현재 세션에서 사용량을 조회할 수 없으면 `이 Codex 세션에서는 도구/API 응답으로 조회할 수 없음`이라고 기록한다.

## 문서 형식

문서 최상단에 사용자의 작업 지시사항을 인용한다. 사용자가 오타 수정을 별도로 요청한 경우에는 수정된 문구를 사용한다. 그 아래에 모델, 작업 시간, 토큰 정보를 기록한다.

```md
# 작업 완료 보고서

## 작업 지시사항 원문

> 사용자 작업 지시사항

## 사용 AI 모델

모델명 또는 확인 불가

## 작업 수행 시간

- 작업 시작 시간: YYYY-MM-DD HH:MM:SS +09:00
- 작업 완료 시간: YYYY-MM-DD HH:MM:SS +09:00
- 총 작업 수행 시간: N초
- 소모 토큰: 확인값 또는 확인 불가 사유
```

이후 수행 내용, 변경 파일, 입력·출력, 테스트·검증 결과, 다른 기능과의 연결, 공통 구조 영향, 남은 문제를 실제 수행 사실만으로 작성한다.

## 작성 원칙

- 테스트하지 않은 항목을 완료로 기록하지 않는다.
- API 키, 토큰, 비밀번호, 개인정보, 민감한 원문 내용을 기록하지 않는다.
- 관련 파일과 검증 결과를 명확히 적는다.
- 새 walkthrough 보고서 자체도 완료 작업으로 취급하고, 저장 전 사용자 승인을 다시 요청한다.
