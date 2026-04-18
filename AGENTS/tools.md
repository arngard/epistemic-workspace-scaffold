---
date created: 2026-04-18
date modified: 2026-04-18
tags: [agents, 도구, 환경, IDE]
---

# 도구/환경 정보

## 도구별 자동 참조 파일

각 AI 도구는 프로젝트 루트에서 고유 경로의 파일을 자동으로 참조한다. 모든 진입점 파일은 루트의 [AGENTS.md](../AGENTS.md)를 가리킨다.

| 도구 | 진입점 파일 | 비고 |
|------|------------|------|
| Claude Code | [CLAUDE.md](../CLAUDE.md) | Anthropic CLI/IDE. 세션 시작 시 자동 로드. |
| GitHub Copilot | [.github/copilot-instructions.md](../.github/copilot-instructions.md) | VS Code/JetBrains Copilot이 자동 로드. |
| Gemini (Android Studio) | [.gemini/styleguide.md](../.gemini/styleguide.md) | Android Studio 통합 Gemini가 자동 로드. |
| Kiro | `.kiro/` 디렉토리 | AWS의 VS Code 기반 AI IDE. spec-driven development 지원. 디렉토리 세팅은 도구 자체가 수행. |
| Cursor | `.cursor/rules/` 또는 `.cursorrules` | 현 스캐폴드는 진입점을 포함하지 않는다. Cursor를 사용하는 경우 별도 설정한다. |

## 진입점 유지 원칙

- 진입점 파일은 "[AGENTS.md](../AGENTS.md)를 읽으라"는 포인터 역할만 한다. 지침 자체를 진입점에 적지 않는다. 중복·불일치 방지.
- 새로운 도구가 추가되면: 해당 도구의 자동 참조 경로에 진입점 파일을 만들고, 이 표에 등록한다.
