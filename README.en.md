---
date created: 2026-04-18
date modified: 2026-07-06
tags: [소개]
---

[한국어](README.md) | English

# Epistemic Workspace Scaffold

A workspace scaffold that partitions documentation by epistemic category. Keeps higher-level intent and rationale from getting lost when humans and AI work together. Design documents are classified into four categories.

- Ontology: What exists
- Knowledge: How the world is
- Strategy: Why we decided this way
- Architecture: How we build it

For the rationale, see [AGENTS/why-epistemic-workspace.md](AGENTS/why-epistemic-workspace.md) (Korean); for operating guidance and principles, the single entry point [AGENTS.md](AGENTS.md).

## Directory structure

```
(workspace-root)/
├── _docs/             <- Knowledge not expressible in code
│   ├── _ontology/         <- Domain concepts
│   ├── _knowledge/        <- External facts
│   ├── _strategy/         <- Decisions and rationale
│   ├── _architecture/     <- Design specifications
│   └── _worklog/          <- Work status, history
├── _reference/        <- Immutable raw materials dumped by the user
└── _implementation/   <- Implementation code
    ├── backend/
    └── web/
```

## How to use

There are three ways to obtain the scaffold: GitHub fork, plain copy (clone or template), or clone and connect the original as an `upstream` remote (choose this to keep pulling parent improvements - `git fetch upstream && git merge upstream/main`). Switching between these later is cumbersome, so record the chosen approach and its rationale as a decision document.

After obtaining it, rename the workspace folder to match your project, follow the "Workspace initial setup" checklist in `_docs/_worklog/TASK_TREE.md`, and adjust AGENTS.md to your project's requirements.

## Further reading

- [AGENTS/why-epistemic-workspace.md](AGENTS/why-epistemic-workspace.md) - Design philosophy and rationale (Korean)
- [AGENTS/workspace-and-project-structure.md](AGENTS/workspace-and-project-structure.md) - Structural rationale
- [AGENTS/how-to-separate-docs-folders.md](AGENTS/how-to-separate-docs-folders.md) - Criteria for separating `_docs/` subfolders
