# Project's documents root is `artifacts/{project_id}/docs/`
if this dir does not exist, create it.

---

# CONTEXT.md Format

Add a well structured context brief here considering below rules.


## Rules

- **Be opinionated.** When multiple words exist for the same concept, pick the best one and list the others as aliases to avoid.
- **Flag conflicts explicitly.** If a term is used ambiguously, call it out in "Flagged ambiguities" with a clear resolution.
- **Keep definitions tight.** One or two sentences max. Define what it IS, not what it does.
- **Show relationships.** Use bold term names and express cardinality where obvious.
- **Only include terms specific to this project's context.** General programming concepts (timeouts, error types, utility patterns) don't belong even if the project uses them extensively. Before adding a term, ask: is this a concept unique to this context, or a general programming concept? Only the former belongs.
- **Group terms under subheadings** when natural clusters emerge. If all terms belong to a single cohesive area, a flat list is fine.
- **Write an example dialogue.** A conversation between a dev and a domain expert that demonstrates how the terms interact naturally and clarifies boundaries between related concepts.

## Single vs multi-context repos

**Single context (most repos):** One `artifacts/{project_id}/docs/CONTEXT.md` at the project's documents root which is `artifacts/{project_id}/docs/`.

**Multiple contexts:** A `artifacts/{project_id}/docs/CONTEXT-MAP.md` at the project's documents root lists the contexts, where they live, and how they relate to each other:


The skill infers which structure applies:

- If `artifacts/{project_id}/docs/CONTEXT-MAP.md` exists, read it to find contexts
- If only a root `artifacts/{project_id}/docs/CONTEXT.md` exists, single context
- If neither exists, create a root `artifacts/{project_id}/docs/CONTEXT.md` lazily when the first term is resolved

When multiple contexts exist, infer which one the current topic relates to. If unclear, ask.