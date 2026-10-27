---
date created: 2026-04-18
date modified: 2026-10-27
tags: [소개]
description: 스캐폴드 소개의 영어판
---

[한국어](README.md) | English

# Epistemic Workspace Scaffold

A workspace scaffold that partitions documentation by epistemic category. Keeps higher-level intent and rationale from getting lost when humans and AI work together. Design documents are classified into four categories.

- Ontology: What exists in our domain
- Knowledge: How the world is
- Strategy: Why we decided to do it this way
- Architecture: What we build and how

For the rationale, see [AGENTS/epistemic-rules/why-epistemic-workspace.md](AGENTS/epistemic-rules/why-epistemic-workspace.md) (Korean); for operating guidance and principles, the single entry point [AGENTS.md](AGENTS.md).

## Directory structure

```
(workspace-root)/
├── AGENTS/               <- Agent operating norms (entry point: AGENTS.md)
├── worklog.md            <- Parent document: X.md introduces the same-name folder X/ (likewise below)
├── worklog/              <- Work status
├── reference.md
├── reference/            <- Immutable raw materials dumped by the user
├── epistemic-structure.md
├── epistemic-structure/  <- Knowledge not expressible in code
│   ├── ontology.md           <- Parent document: X.md introduces the same-name folder X/ (likewise below)
│   ├── ontology/             <- Domain concepts
│   ├── knowledge.md
│   ├── knowledge/            <- External facts
│   ├── strategy.md
│   ├── strategy/             <- Decisions and rationale
│   ├── architecture.md
│   └── architecture/         <- Design specifications
├── implementation.md
└── implementation/       <- Implementation projects (one subfolder per project)
    ├── <project-A>/
    └── <project-B>/
```

## How to use

There are two ways to obtain the scaffold.

- Staying connected to upstream: receive the scaffold history through a GitHub fork or a clone, and connect the original as the `upstream` remote. For a clone, run `git remote rename origin upstream` and add your own repository as `origin`. For a fork, add `git remote add upstream https://github.com/arngard/epistemic-workspace-scaffold.git`. Pull upstream improvements with `git fetch upstream && git merge upstream/main`.
- Without history: create a repository from the GitHub template, or copy the files into an existing project. Without the scaffold history, you cannot merge upstream improvements.

If you received the scaffold history, the `upstream` connection is not optional; it is the starting state. Audits use it to tell upstream commits from your own. Record the chosen approach and its rationale as a decision document.

After obtaining it, before your first commit, connect the pre-commit hook once per clone (command in [tools.md](AGENTS/epistemic-rules/tools.md) "색인 생성 스크립트"). Then rename the workspace folder to match your project, follow the "Workspace initial setup" checklist in `worklog/TASK_TREE.md`, and specialize the workspace identity section ("이 워크스페이스의 정체") of AGENTS.md for your project. To change other inherited assets, follow [AGENTS/epistemic-rules/instance-specialization.md](AGENTS/epistemic-rules/instance-specialization.md).

## Further reading

- see: [AGENTS/epistemic-rules/why-epistemic-workspace.md](AGENTS/epistemic-rules/why-epistemic-workspace.md) - Design philosophy and rationale (Korean)
- see: [AGENTS/epistemic-rules/workspace-and-project-structure.md](AGENTS/epistemic-rules/workspace-and-project-structure.md) - Structural rationale
- see: [epistemic-structure/AGENTS/epistemic-rules.md](epistemic-structure/AGENTS/epistemic-rules.md) "판별 규칙" - Criteria for separating `epistemic-structure/` subfolders
