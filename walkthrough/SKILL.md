---
name: walkthrough-reporting
description: Create and maintain approved project walkthrough completion reports and prepare Pull Request summaries from unreflected walkthrough reports. Use whenever a task has finished and Codex must document the work, or when Codex must create or update a Pull Request that should summarize and mark included walkthrough reports.
---

# Walkthrough 완료 보고서

## 승인 요청 설정 (User Approval Setting)

- **`require_user_approval`**: `false` (기본값: `false`)
- 설정값이 `false`인 경우 walkthrough 완료 보고서 작성 및 저장 시 **사용자 승인 절차를 거치지 않고 즉시 작성하여 저장**합니다.
- 설정값이 `true`인 경우에만 저장 전 사용자에게 승인을 요청합니다.

## 저장 전 절차

1. 실제 작업을 시작하기 직전에 현재 시간을 기록한다.
2. 작업을 완료하고 결과를 확인한다.
3. `require_user_approval` 설정값을 확인한다:
   - `false` (기본 설정): **사용자 승인 절차 없이** 보고서 저장 경로(`walkthrough/<브랜치명>/YYYYMMDD_순번_커밋메시지.md`)에 완료 보고서를 즉시 작성 및 저장한다.
   - `true`: 보고서의 저장 경로와 파일명을 제시하고 사용자에게 저장 승인을 요청한 후 명시적 승인 시 저장한다.
4. 저장 직전에 완료 시간을 기록하고 시작 시간과의 차이를 초 단위로 계산한다. (승인 대기 시간이 있는 경우 작업 실행 시간에 포함하지 않음)
5. walkthrough 문서 작성 시에는 자동 커밋을 수행하지 않는다. 커밋 작업은 사용자가 명시적으로 지시할 때만 수행한다.
6. 푸시와 Pull Request 생성은 사용자가 별도로 요청한 경우에만 수행한다.

## 저장 위치와 파일명

- `git branch --show-current` 명령을 통한 브랜치 확인 작업은 `switch`, `commit`, `push`, `pull request` 작업을 수행할 때만 실행한다.
- 그 외의 walkthrough 문서 작성 시에는 매번 브랜치를 다시 확인하지 않고 이전 브랜치 상태를 기억하여 `walkthrough/<기억된 브랜치명>/` 경로를 사용한다.
- 현재 기억된 브랜치가 `Gharam`이면 저장 위치는 `walkthrough/Gharam/`이다.
- 브랜치명이 비어 있는 detached HEAD 상태이면 임의 폴더명을 만들지 말고 사용자에게 저장 경로를 확인받는다.
- 일반 작업 완료 보고서의 파일명은 `YYYYMMDD_순번_커밋메시지.md` 형식을 사용한다.
- Pull Request 생성·갱신·푸시 작업의 완료 보고서는 처음부터 `YYYYMMDD_순번(PR)_커밋메시지.md` 형식을 사용한다. 이 보고서는 해당 PR이 완료된 뒤에 작성되므로, 이후 Pull Request 요약 대상에 포함하지 않는다.
- 같은 날짜에는 기존 파일을 확인하여 `01`부터 `99`까지 순차적으로 번호를 부여한다.
- 기존 보고서를 임의로 덮어쓰거나 삭제하지 않는다.

## Pull Request 반영 절차

Pull Request를 새로 만들거나 기존 Pull Request를 갱신하기 전에 다음 절차를 수행한다.

1. `git branch --show-current`으로 현재 브랜치를 확인하고 `walkthrough/<현재 브랜치명>/`을 찾는다.
2. `YYYYMMDD_순번_커밋메시지.md` 형식이며 순번 뒤에 `(PR)`이 없는 walkthrough 문서를 모두 찾는다. 이미 `(PR)` 표기가 있는 문서와 Pull Request 작업 완료 보고서는 요약 대상에서 제외한다. `SKILL.md`도 대상에서 제외한다.
3. 대상 문서의 `작업 지시사항 원문`을 모두 읽고, 공통 목표·범위·요구를 빠뜨리지 않도록 하나의 서술형 존대말 문단으로 함축한다. 이 문단은 문맥이 자연스럽게 이어져야 하며, 목록으로 나열하지 않는다.
4. 대상 문서의 수행 내용, 변경 파일, 검증 결과, 영향 범위, 남은 작업을 모두 읽고, 실제 완료 내용을 하나의 서술형 존대말 문단으로 함축한다. 이 문단도 문맥의 일관성을 유지하고, 확인하지 않은 사실을 추가하지 않는다.
5. 두 요약 문단의 핵심 키워드를 다시 함축하여 Pull Request 제목을 한 문장의 존대말로 작성한다. 제목은 간단하고 명료한 평문으로 작성하며, Markdown·괄호·불필요한 접두어 없이 핵심 변경 키워드를 포함한다.
6. Pull Request 메시지에는 아래 형식을 사용한다. `작업 지시사항 요약`과 `작업 완료 보고 요약`에는 각각 하나의 서술형 문단만 작성한다. `반영된 walkthrough 문서`에는 최종 파일명만 목록으로 넣는다.

   ```md
   ## 작업 지시사항 요약

   하나의 일관된 서술형 존대말 문단

   ## 작업 완료 보고 요약

   하나의 일관된 서술형 존대말 문단

   ## 반영된 walkthrough 문서

   - YYYYMMDD_순번(PR)_커밋메시지.md
   ```
7. Pull Request 메시지를 보고하고 사용자 승인을 받으면 다음 Pull Request 절차를 수행한다.
8. Pull Request가 성공적으로 생성되거나 갱신된 뒤에만, 반영한 문서의 파일명을 `YYYYMMDD_순번(PR)_커밋메시지.md` 형식으로 변경한다.
9. 이름 변경과 관련된 작업 파일을 커밋하고 원격 브랜치에 푸시하여 Pull Request에 반영한다.
10. Pull Request 생성·갱신·푸시 중 하나라도 실패하면 파일명을 변경하지 않고, 실패 원인을 보고한다.

파일명에서 순번 뒤의 `(PR)` 표기는 해당 walkthrough 문서가 Pull Request 메시지에 요약되어 반영됐음을 뜻한다. 예시는 다음과 같다.

```text
변경 전: 20260723_01_add_claude_framework.md
변경 후: 20260723_01(PR)_add_claude_framework.md
```

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
- `require_user_approval` 설정이 `false`이면 별도 저장 승인 없이 완성된 walkthrough 보고서를 즉시 작성 및 저장한다.
- walkthrough 작성 후 자동 커밋은 절대 수행하지 않으며 사용자의 커밋 명령이 있을 때만 실행한다.
