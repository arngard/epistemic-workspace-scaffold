---
date created: 2026-04-18
date modified: 2026-10-26
tags: [architecture]
---

@AGENTS/epistemic-rules.md

# 설계 명세 디스크립터

최종 설계 명세를 두는 폴더다.

디스크립터에 파일별 안내 표를 두는 폴더이므로 파일별 설명과 "언제 읽는가" 트리거를 명시한다 (ref: [AGENTS/epistemic-rules/folder-structure.md](../../AGENTS/epistemic-rules/folder-structure.md) "폴더 구조와 디스크립터"). 설계 명세는 구현 시 전체가 함께 참조되어 서로를 지지하는 정보다 - 존재를 모르면 위반 구현이 나온다.

## 파일별 안내

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [core-constraints.md](core-constraints.md) | 핵심 제약. 스캐폴드 상태 - 제약 목록 작성 필요 | 설계 결정, 구현 착수 전 |
| [conventions.md](conventions.md) | 프로젝트 고유 코드, 빌드 규약의 자리 (현재는 Git 규약 포인터만). 워크스페이스 공통 규약은 [epistemic-rules.md](../../AGENTS/epistemic-rules.md) 참조 | 코드 작성, 빌드 설정 시 |
| [sample-spec.md](sample-spec.md) | 설계 명세 문서의 위치와 형식을 보여주는 튜토리얼용 샘플. 실제 작성 시 삭제하거나 교체한다 | 첫 명세 작성 시 |
