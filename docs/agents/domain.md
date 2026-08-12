# Domain docs

This document explains how engineering skills should consume the repository's domain documentation when exploring the codebase.

## Before exploring

- Read `CONTEXT.md` at the repository root when it exists.
- If a root `CONTEXT-MAP.md` exists, use it to find and read each context relevant to the task.
- Read architecture decision records under `docs/adr/` that affect the area being changed.

If these files do not exist, proceed without reporting their absence. The `/domain-modeling` skill, reached through `/grill-with-docs` and `/improve-codebase-architecture`, creates them lazily when terminology or decisions are resolved.

## File structure

This is a single-context repository:

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
└── application source directories
```

`CONTEXT.md` and `docs/adr/` do not need to exist until the project has domain terminology or architecture decisions worth recording.

## Use the glossary's vocabulary

When an output names a domain concept in an issue title, refactoring proposal, hypothesis, or test name, use the term defined in `CONTEXT.md`. Do not drift to synonyms that the glossary explicitly avoids.

If a needed concept is absent from the glossary, reconsider whether the term belongs to the project. If it represents a real gap, record it for `/domain-modeling`.

## Flag ADR conflicts

If proposed work contradicts an existing architecture decision record, report the conflict explicitly instead of silently overriding the decision.
