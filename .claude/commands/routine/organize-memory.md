---
description: Synchronize and manage agent memory between Mitra artifacts and local Claude snapshots
---

### 🧠 Agent Memory Management Protocol

**Objective:**
Ensure that Mitra agents autonomously manage their memory, maintaining a clear separation between the agent's internal source of truth and the project-level Claude memory snapshots.

**Memory Locations & Definitions:**
1. **Mitra Memory (Source of Truth):** 
   - Managed via the agent's specific memory workflow/skill.
   - Stored in the dedicated `artifacts/` directory for the specific agent (e.g., the Engineer agent's artifact directory).
2. **Claude Memory (Snapshot):** 
   - A localized project memory snapshot.
   - Stored and retrieved exclusively from the `.claude/` directory at the project root.

**Execution Workflow:**
When an agent receives a command or prompt, it must execute the following steps in order:
1. **Update Mitra Memory (Primary):** First, ensure that the agent's specific Mitra memory in the `artifacts/` directory is fully updated and accurate, as this serves as the definitive source of truth.
2. **Sync Claude Memory (Secondary):** Only after the Mitra memory is secured, update or retrieve the corresponding snapshot memory in the root `.claude/` directory to keep the project-level context aligned.
