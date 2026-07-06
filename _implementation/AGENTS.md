---
date created: 2026-04-18
date modified: 2026-07-04
tags: [implementation]
---

# 구현 프로젝트 디스크립터

> 이 워크스페이스에 포함된 구현 프로젝트의 보관 영역. `_implementation/` 하위에 프로젝트마다 한 폴더를 만들고 그 폴더에 실제 소스(또는 서브모듈 등)를 둔다. 한 워크스페이스가 여러 프로젝트를 담을 수 있다 (예: Android/iOS SDK 쌍, 서버/프런트 쌍).
> "어떤 프로젝트가 존재하는가"의 SSOT(single source of truth)는 파일시스템이다 (cf. [AGENTS/folder-structure.md](../AGENTS/folder-structure.md) "폴더 구조와 디스크립터").

## 로컬 규칙

- 프로젝트 폴더 이름은 가급적 해당 프로젝트의 리모트 레포 이름을 고려하여 짓는다.
- 프로젝트별 기술 스택, 빌드 방법 등의 안내는 각 프로젝트 폴더 안의 문서(해당 프로젝트의 README 등)에 둔다.
