---
date created: 2026-04-18
date modified: 2026-04-18
tags: [readme, 소개]
---

[한국어](README.md) | English

# Epistemic Workspace Scaffold

A workspace scaffold that partitions documentation by epistemic category. Prevents the loss of higher-level context when humans and AI work together.

## The problem this workspace addresses

In AI collaboration, verbal comprehension ability appears to strongly shape work outcomes. Good outcomes come from good instructions, and good instructions come from well-organized context documentation. When tacit knowledge and meta-cognition are not properly recorded, intent and direction fail to reach the concrete-level documents and designs below them. Actual workers — human or AI — often end up moving without a clear sense of why. And writing ability varies widely between individuals.

This scaffold is an attempt to address that gap through structure. Examples of describing a system by slicing it into layers include the Zachman Framework, Domain-Driven Design, Architecture Decision Records, Aristotle's Four Causes, and Popper's Three Worlds. This scaffold chooses four categories suited to LLM collaboration and classifies design documents accordingly. In the course of organizing their writing, workers also come to clarify their own thinking.

- What exists
- How the world is
- Why we decided this way
- How we build it

If harness engineering is the approach of drawing fences at the boundary between normal and abnormal to contain problems, this scaffold is designed to delegate more to workers so they can pursue the right goal themselves. It aims to be a framework that captures even high-level context in documentation without omission, while allowing only the needed parts to be retrieved efficiently.

## Directory structure

```
(workspace-root)/
├── _docs/             ← Knowledge not expressible in code
│   ├── _worklog/          ← Work status, history
│   ├── _ontology/         ← Domain concepts
│   ├── _knowledge/        ← External facts
│   ├── _strategy/         ← Decisions and rationale
│   └── _architecture/     ← Design specifications
└── _implementation/   ← Implementation code
    ├── backend/
    └── web/
```

The `_` prefix marks the fixed skeleton of the workspace. Items without the prefix are content that arises and changes over the project's lifetime.

## Core principles

- Distinguish speculation from what is settled: do not write undiscussed content as if it were decided. When an AI agent lacks the necessary information, it asks the human rather than filling in arbitrarily.
- Small documents + INDEX: read the index first and open only what is needed. Saves tokens; also less taxing for humans to read.
- No duplication / SSOT: keep the same fact in one place; other documents link to it.
- Single entry point AGENTS.md: tool-specific auto-loaded files (Claude, Gemini, Copilot, Kiro, etc.) contain only pointers; the body of the guidance lives in AGENTS.md alone.
- Division of labor between documentation and code: `_docs/` holds only what cannot be expressed in code. Interfaces, types, and error contracts are specified by the code itself.

## How to use

1. Rename the workspace folder to match your project.
2. Follow the "Workspace initial setup" checklist in `_docs/_worklog/TASK_TREE.md`.
3. Adjust AGENTS.md to your project's requirements as needed.

## Further reading

- [AGENTS/workspace-and-project-structure.md](AGENTS/workspace-and-project-structure.md) — Structural rationale
- [AGENTS/how-to-separate-docs-folders.md](AGENTS/how-to-separate-docs-folders.md) — Criteria for separating `_docs/` subfolders
