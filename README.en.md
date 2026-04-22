---
date created: 2026-04-18
date modified: 2026-04-22
tags: [소개]
---

[한국어](README.md) | English

# Epistemic Workspace Scaffold

A workspace scaffold that partitions documentation by epistemic category. Prevents the loss of higher-level intent and rationale when humans and AI work together.

## The problem this workspace addresses

In human-AI collaboration, it is common to jump into the code-generation-and-revision cycle without first documenting the expected outcomes. But starting this way, trial and error will end up revising the code toward those expectations anyway — and that process is not lean but a waste of tokens. Writing the expectations up front saves iteration time and tokens. Meaning transmission and token economy are not separate problems.

Ultimately, verbal comprehension ability appears to strongly shape work outcomes. Good outcomes come from good understanding, and good understanding comes from well-organized context documentation. When tacit knowledge and meta-cognition are not properly recorded, intent and direction fail to reach concrete-level designs. Actual workers — human or AI — end up moving without a clear sense of why, and this leads to wasteful iterations. Yet writing ability varies widely between individuals.

This scaffold is an attempt to address that gap through structure. Examples of describing a system by slicing it into layers include the Zachman Framework, Domain-Driven Design, Architecture Decision Records, Aristotle's Four Causes, and Popper's Three Worlds. Tailored to the context of collaboration with AI, this scaffold classifies design documents into four categories.

- Ontology: What exists
- Knowledge: How the world is
- Strategy: Why we decided this way
- Architecture: How we build it

If harness engineering is the approach of drawing fences at the boundary between normal and abnormal to contain problems, this scaffold takes the opposite direction. By bounding what is made explicit, it delegates the remaining free zone to workers all the more clearly — with the intent of helping them pursue the right goal. It aims to be a framework that captures even high-level context in documentation without omission, while allowing only the needed parts to be retrieved efficiently.

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
