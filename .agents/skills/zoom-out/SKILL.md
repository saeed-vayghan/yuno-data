---
name: zoom-out
description: Tell the agent to zoom out and give broader context or a higher-level perspective. Use when you are unfamiliar with a section of code or need to understand how it fits into the bigger picture.
disable-model-invocation: true
---

Use this skill when you need to understand the bigger picture of a specific section of code.

## 🧭 Instructions

1. **Go up a layer of abstraction**: Do not focus on low-level implementation details. Focus on the high-level design instead.
2. **Map the relationships**: Show a clear map or diagram of:
   - All relevant modules.
   - The callers of these modules.
3. **Use the Glossary**: Describe components in the project's **domain glossary** vocabulary (`artifacts/{project_id}/docs/CONTEXT.md` or `src/{context}/CONTEXT.md`) when one exists.