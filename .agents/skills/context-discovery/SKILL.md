---
name: context-discovery
description: Establish reliable project context from Git, repository documents, local knowledge, Redmine/RAGFlow/GitLab sources, and explicit user instructions before substantial work.
---

# Context Discovery

## Procedure
1. Inspect Git status, branch, and recent history.
2. Locate current lifecycle documents and Gate status.
3. Identify explicit goals, constraints, stakeholders, in-scope/out-of-scope items.
4. Search current repository docs first.
5. Use company-context MCP for local/external internal sources only when needed.
6. Record conflicts and stale evidence.
7. Produce `docs/00-project-initiation/context-baseline.md` or update it.

## Output
Include:
- current objective
- lifecycle stage
- authoritative sources
- known constraints
- open questions
- conflicts
- blockers
- next recommended Gate
