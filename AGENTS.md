---
date created: 2026-04-18
date modified: 2026-07-06
tags: [규칙, 문서관리]
---

# AI Agent 지침

> 이 파일은 모든 AI 도구(Claude, Kiro, Gemini, Copilot 등)가 이 프로젝트를 다룰 때의 기본 지침이다.
> 각 도구의 진입점 파일(CLAUDE.md, .kiro/, .gemini/ 등)은 이 파일을 가리킨다.

본 파일은 진입점이며, 각 영역의 풀 절차, 규약은 산하 SSOT 문서에 둔다. 본 파일은 작게 유지한다.

## 새 세션 시작 시 (필수)

1. 이 파일을 읽는다.
2. [_docs/_worklog/TASK_TREE.md](_docs/_worklog/TASK_TREE.md)와 [_docs/_worklog/STATUS.md](_docs/_worklog/STATUS.md)를 읽는다. TASK_TREE에서 진행 중, 다음 할 일을 파악하고, STATUS 레지스트리에서 감사, 주기 작업의 마지막 수행 시각을 확인한다.
3. 형식 정합성 스크립트를 실행한다 - 워크스페이스 루트에서 `python3 AGENTS/tools/audit.py .` (cf. [AGENTS/tool-environment.md](AGENTS/tool-environment.md) "기계 감사 스크립트"). 보고된 위반은 정리하거나 사용자에게 짚는다. 추가로 STATUS 레지스트리의 에피스테믹 의미 감사 행의 마지막 수행이 12시간 초과면 본 작업 시작 전에 epistemic-auditor 서브에이전트를 호출해 의미 감사(워크로그 최신성, 카테고리 배치 등)를 받는다 (cf. [AGENTS/agent-roles.md](AGENTS/agent-roles.md)). 보고된 위반은 정리하거나 사용자에게 짚은 뒤 STATUS 레지스트리의 해당 행을 새 시각으로 갱신한다.
4. [`_reference/AGENTS.md`](_reference/AGENTS.md)를 읽고 폴더 실제 내용과 대조한다. 인벤토리와 실제가 불일치하거나 `처리 대기`/`사용자 의견 필요` 항목이 있으면 [AGENTS/ingest-workflow.md](AGENTS/ingest-workflow.md) "`_reference/` 폴더 처리" 절차로 진행한다.
5. 작업 범위에 해당하는 `_docs/` 문서를 읽는다 (아래 참조 테이블 기준).
6. 코드 생성/수정 전에는 관련 문서의 기존 결정과 충돌이 없는지 확인한다.

새 정보(사실, 의견, 예측, 결정, 자료)가 세션 중 들어오면 [AGENTS/ingest-workflow.md](AGENTS/ingest-workflow.md)의 표준 시퀀스를 따른다.

## 단위 작업 시작/종료 시 (필수)

단위 작업의 개념(원자 단위 ↔ 트리 노드, 재귀, 조립)은 [AGENTS/unit-task.md](AGENTS/unit-task.md), 운영 프레임(진입/진행/종료, 머지 타입 분기[직접 머지/PR 타입], 재귀 정합화, 끊김 재진입)은 [AGENTS/unit-task-workflow.md](AGENTS/unit-task-workflow.md), PR 타입에 조립되는 상세는 [AGENTS/pr-workflow.md](AGENTS/pr-workflow.md) 참조.

본 진입점에서 강조하는 의무 한 줄: **단위 작업 시작과 종료 시 TASK_TREE 갱신 + 사용자 검토 통과 후 main 머지**. 완료 이력은 git 이력이 담당하며 별도 이력 파일을 두지 않는다. AI 자율 머지 회피. 근거 원리는 [원본 보호 원칙](AGENTS/original-protection-principle.md)이다.

세션 중 새로운 관례, 규칙, 스타일이 합의되었으면 해당 내용이 본 파일 또는 관련 영구 문서에 반영되었는지 확인한다. 긴 세션이거나 큰 변경이 있었던 세션의 종료 전에는 epistemic-auditor 서브에이전트를 호출해 문서 정합성 감사를 받는다 (cf. [AGENTS/agent-roles.md](AGENTS/agent-roles.md)).

## 문서 변경 시 (필수)

- 모듈/의존성 변경 -> [_docs/_architecture/AGENTS.md](_docs/_architecture/AGENTS.md) 먼저 업데이트
- 문서/구조 규약 변경 -> 해당 관심사의 규약 문서([AGENTS/document-units.md](AGENTS/document-units.md), [AGENTS/folder-structure.md](AGENTS/folder-structure.md), [AGENTS/document-temporality.md](AGENTS/document-temporality.md), [AGENTS/writing-style.md](AGENTS/writing-style.md))를 먼저 업데이트. 프로젝트 코딩 규약이면 [_docs/_architecture/conventions.md](_docs/_architecture/conventions.md).
- 문서 간 정합성 확인을 항상 수행한다 (특히 cross-reference 되는 섹션 번호).
- 문서나 주석을 수정한 경우, "문서 작성 스타일" 섹션의 규칙을 위배하는 것이 없는지 검토한다.
- 폴더를 신설할 때는 그 폴더의 디스크립터(`AGENTS.md`)를 같은 커밋에 동반한다. 규범 폴더의 디스크립터는 파일별 설명과 읽기 트리거를 유지한다 (cf. [AGENTS/folder-structure.md](AGENTS/folder-structure.md) "폴더 구조와 디스크립터").
- 절차 문서나 폴더를 신설할 때는 첫 실체 1건을 같은 단위 작업에 포함한다. 사양만 있고 실체 0건인 상태는 추측으로 채운 결과로 본다.
- 폴더/파일 이동 또는 리네임은 연쇄 갱신을 요구한다. 절차는 [`AGENTS/folder-structure.md` "폴더, 파일 이동 시 연쇄 갱신"](AGENTS/folder-structure.md) 참조.

## 작업 수행 원칙

단위 작업 하나를 어떻게 대하는가의 토대 원칙. 전체 SSOT와 근거는 [AGENTS/working-principles.md](AGENTS/working-principles.md).

- 넘겨짚지 않는다: 가정을 명시하고 불확실하면 물어 확인한다. 해석이 갈리면 말없이 하나를 고르지 않는다.
- 단순함 우선: 문제를 푸는 최소한으로 만든다. 요청되지 않은 확장을 얹지 않는다.
- 외과적 변경: 바뀐 모든 줄이 요청에 직결되어야 한다. 인접 영역을 덤으로 고치지 않는다.
- 목표 주도: 착수 전 검증 가능한 성공 기준을 정한다. 큰 목표는 작업 트리로 재귀 세분한다.
- 기억보다 실제 상태: 도구 한 번으로 검증되는 것을 기억으로 단언하지 않는다. 다른 에이전트와 어긋나면 자기 기억을 먼저 의심한다.

코드 작업에는 [AGENTS/coding-guidelines.md](AGENTS/coding-guidelines.md)가 추가로 적용된다.

## 문서 작성 스타일

진입자가 첫 화면에서 봐야 할 핵심 항목만 본 절에 둔다. 그 외 규약은 관심사별 SSOT 문서에 둔다: 문서 단위와 SSOT 원칙(1관심사, 분량, 중복 금지, 이름 안정성)은 [`AGENTS/document-units.md`](AGENTS/document-units.md), 문서 시간성은 [`AGENTS/document-temporality.md`](AGENTS/document-temporality.md), 문장, 서술 수준 규칙(코드 블록 절제, 표준 표현, 출처 표기, 자체 완결성, 태그 중복 회피, 도구 전용 파일 예외, ASCII 부호)은 [`AGENTS/writing-style.md`](AGENTS/writing-style.md).

- 볼드, 이탤릭, 이모지 등 서식/기호 강조는 강한 경고/금지/주의 사항에만 사용한다. 나열, 제목, 항목 라벨, 일반 개념어, 장식에는 쓰지 않는다. 남발하면 진짜 강조가 필요할 때의 진정성을 잃는다.
- 문서 간 참조는 마크다운 링크로 작성한다. `[표시 텍스트](상대경로)` 형식.
- 참고 자료/출처 표기는 `cf.` (비교/참고)와 `ref.` (출처/근거)를 사용한다.
- 약어가 처음 등장할 때는 풀어쓴 원문을 병기한다. 예: `SSOT(single source of truth)`, `ADR(Architecture Decision Record)`. 원문이 외국어이고 한국어 설명이 추가로 필요하면 세미콜론으로 덧붙인다. 예: `KAI(Korea Aerospace Industries; 한국항공우주산업)`. 이후 같은 문서 내에서는 약어만 사용한다.
- 약어와 줄임말을 구분한다. 약어(acronym; 단어 첫 글자를 모아 만든 형태: SSOT, ADR, API 등)는 허용. **줄임말(truncation; 단어 중간을 잘라낸 형태: feature -> feat, configuration -> config, repository -> repo 등)은 피하고 공식 형태(full form)를 그대로 사용한다.** 줄임말 남발은 입문자 진입 비용을 높이고 검색, 일치성을 떨어뜨린다. 일반 도메인에 완전히 정착해 공식 형태처럼 통용되는 경우(예: `docs` 폴더명, `dev` 환경명)는 예외다. 그 경우 본 워크스페이스에서 표준 사용 형태를 명시한다.
- 모든 .md 파일에 YAML front matter를 붙인다. 필수 필드: `date created`, `date modified`, `tags`. 날짜 형식은 `yyyy-MM-dd`. `tags`의 첫 항목은 소속 카테고리. `_docs/` 4범주 직속 문서는 폴더명에서 언더스코어를 뗀 값(ontology, knowledge, strategy, architecture)을 쓰며 감사 스크립트가 검사한다. 하위 폴더 문서에는 강제하지 않는다.
- **추측으로 문서를 채우지 않는다.** 논의되지 않은 내용을 확정된 것처럼 적지 않는다.
- 사실과 의견, 의견의 주체를 분명히 구분한다. 근거 있는 사실, 작성자 본인의 판단, 타인/외부의 판단은 서술 형태를 달리한다. 의견에는 주체를 명시한다 (예: "`@아릉`의 판단", "Klaviyo 팀의 설계", "AI 제안"). 의견을 사실인 양 서술하거나 주체를 흐리면 이후 결정의 근거 추적이 깨진다.

## 폴더 디스크립터 사용 규칙

모든 폴더는 디스크립터(`AGENTS.md`)를 가진다. 규약 SSOT는 [AGENTS/folder-structure.md](AGENTS/folder-structure.md) "폴더 구조와 디스크립터"이며, 아래는 진입자용 요지다.

- 읽기: 폴더 디스크립터를 먼저 읽고 그 서브트리의 목적, 로컬 규칙, 행동 유발 항목을 파악한 뒤, 필요한 문서만 선택적으로 연다. "어떤 문서가 존재하는가"의 SSOT는 파일시스템 자체이므로 디스크립터에 인벤토리 표를 강제하지 않는다.
- 쓰기: 내용에 맞는 기존 문서에 추가하거나, 구체적인 제목의 새 파일을 만든다. 규범 폴더면 디스크립터의 파일별 안내에 새 파일의 설명과 읽기 트리거를 등재한다.
- 제목 규칙: 파일명은 내용을 특정할 수 있어야 한다. 포괄적 이름은 금지. 자기설명적 파일명이 참조 폴더의 기본 인덱스 기능을 대신한다.
- 폴더 직속 항목이 많아지면 하위 폴더로 분화한다. 분화 임계는 감사 스크립트가 검출한다.

## 경계 (하지 말 것)

데이터 안전 관련 항목(`main` 직접 커밋, `_docs/` 대폭 재편)의 근거 원리는 [원본 보호 원칙](AGENTS/original-protection-principle.md)이다.

- `main` 브랜치에 직접 커밋하지 않는다. 브랜치 전략은 [AGENTS/branch-strategy.md](AGENTS/branch-strategy.md) 참조.
- `_docs/` 파일을 사람 확인 없이 삭제하거나 대폭 재편하지 않는다.
- 코드나 문서 영역에 공용 태그(`[to:@AGENT: ...]`)가 달려 있으면 그 내용을 하나의 프롬프트와 동등하게 취급하여 먼저 읽고 반영한다. 형식은 [AGENTS/agent-tag-format.md](AGENTS/agent-tag-format.md) 참조. 태그가 없다고 해당 영역을 임의로 수정해도 된다는 뜻은 아니다.
- Git 커밋, 푸시를 명시적 요청 없이 수행하지 않는다. 요청된 범위만 정확히 수행한다: "커밋"을 요청받으면 커밋까지, "푸시"를 요청받으면 푸시까지. 범위를 임의로 확장하거나 축소하지 않는다. 푸시 전에 사용자가 커밋 내용을 확인할 수 있어야 한다.
- PR에 달린 인라인 리뷰 코멘트(사용자, 다른 개발자, 자동 리뷰 봇)에 응답할 때는 **그 코멘트의 스레드 reply**로 단다. 호출 형태, 정정 절차, PR 본문 형식, 속성 할당, 명시적 멘션, AI 시그니처 등 PR 운영 전반 규약은 [AGENTS/pr-workflow.md](AGENTS/pr-workflow.md) 참조.

## 응답 언어

- 문서 작성: 한국어 기본, 평어체(담백한 서술형).
- 코드 주석 및 in-source 문서(kotlindoc, javadoc 등): 한국어.
- 에러 메시지: 첫 대표 문장은 영문, 상세 설명은 한국어.
- 대화: 한국어, 존댓말.
- 금지 표현: 비속어, 욕설, 모욕, 차별적 표현 사용 금지(응답, 문서, 커밋 메시지, PR 본문, 댓글 등). 사용자가 사용하더라도 AI는 정중한 톤을 유지하고 어휘를 모방하지 않는다. 인용, 정정 대상 명시 등 필요시에만 따옴표로 인용 표시.

## 필수 참조 문서

| 문서 | 용도 | 언제 참조하는가 |
|------|------|----------------|
| [_docs/_worklog/TASK_TREE.md](_docs/_worklog/TASK_TREE.md) | 작업 계층 트리 (현재 상태 + 다음 작업 포인터) | 매 세션 시작 시 (최우선), 작업 착수 전 |
| [_docs/_worklog/STATUS.md](_docs/_worklog/STATUS.md) | 감사, 주기 작업 상태 레지스트리 | 매 세션 시작 시 |
| [_docs/_ontology/AGENTS.md](_docs/_ontology/AGENTS.md) | 온톨로지 디스크립터 | 새 용어 도입 전, 도메인 클래스 설계 전, 용어 혼동 시 |
| [_docs/_knowledge/AGENTS.md](_docs/_knowledge/AGENTS.md) | 지식 디스크립터 | 새 세션 시작 시, 문제 해결 시 |
| [_docs/_strategy/AGENTS.md](_docs/_strategy/AGENTS.md) | 전략 디스크립터 | 새 세션 시작 시, 문제 해결 시 |
| [AGENTS/AGENTS.md](AGENTS/AGENTS.md) | 에이전트 지침 디스크립터 | 에이전트 운영 방식 확인 시 |
| [_docs/_architecture/AGENTS.md](_docs/_architecture/AGENTS.md) | 설계 명세 디스크립터 | 새 클래스/모듈 생성 시 |
| [AGENTS/document-units.md](AGENTS/document-units.md) | 문서 단위와 SSOT 규약 | 문서 신설, 분할 판단 시 |
| [AGENTS/folder-structure.md](AGENTS/folder-structure.md) | 폴더 구조, 디스크립터, 연쇄 갱신 규약 | 폴더 구조 변경 시 |
| [AGENTS/document-temporality.md](AGENTS/document-temporality.md) | 문서 시간성 규약 | 날짜 프리픽스 문서 작성, 수정 시 |
| [AGENTS/writing-style.md](AGENTS/writing-style.md) | 일반 문서 작성 스타일 | 모든 문서 작성 시 |
| [AGENTS/unit-task-workflow.md](AGENTS/unit-task-workflow.md) | 단위 작업 운영 흐름 SSOT | 단위 작업 시작, 종료 시 |
| [_reference/AGENTS.md](_reference/AGENTS.md) | raw 자료 인벤토리 + 처리 상태 | 매 세션 시작 시 |

## 핵심 제약

ref. [_docs/_architecture/core-constraints.md](_docs/_architecture/core-constraints.md) 참조.
