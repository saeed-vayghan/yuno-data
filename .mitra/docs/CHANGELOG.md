### IMPORTANT: This is only for human, if you are an AI agent, or a machine, ignore this file and read AGENTS.md instead.

---

# Changelog

All notable changes to the **Mitra** multi-agent system will be documented in this file.

## [4.1.1] - 2026-09-25

### 🐛 Fixes

- **Workflow Loading**: Antigravity manifests (and two Claude handlers) still called `./.agent/skills/...` after the `.agents/` rename, so workflows never loaded and agents improvised instead. All script paths are fixed.
- **macOS Compatibility**: `load_workflow.sh` and `list_workflows.sh` no longer fail with "bad substitution" on the default macOS bash 3.2.
- **Handler References**: Fixed the `<mplementation-engine>` typo in the Engineer's handlers, and pointed `*challenge-me` at the loaded workflow instead of an undefined `<workflow-challenge-me>` block.
- **Agent Registry**: Triggers now match the real commands (`/mitra:{agent}`), locations point to existing files, and `*develop` replaces the nonexistent `*code`.

### 🛠️ Changes

- **Workflow Rewrite**: Rewrote ten workflows imported from generic subagent prompts (Architect: backend, database, microservices, cloud, frontend; Engineer: api-designer, backend-security, documenter, developer; Designer: ui-designer). Removed references to agents Mitra doesn't have, made-up completion messages, and long keyword lists (~1,500 lines cut); added scope lines between overlapping workflows.
- **Security Audit**: `*security` now covers auditing existing code as well as specifying hardening.
- **Safer Develop Workflow**: The Engineer commits, pushes, or deploys only when the user asks.
- **Personas**: Plain wording instead of all-caps rules; the Orchestrator's New Project Protocol now uses `config.yaml` / `project_id` and routes the PRD to Sina.
- **Consistent Storage & Naming**: All workflows save to `artifacts/{project_id}/{agent}/` with the `{YYYY-MM-DD}-` prefix; the memory manager now defines when to save workflow state.
- **Docs**: Updated `AGENTS.md`, `TREE.md`, `DEVELOPMENT.md`, `GUIDE.md`, and `agent_xml_file.md` for the `.agents/` layout.

---

## [4.1.0] - 2026-08-23

### ✨ New Features

- **New Agent Skills**: Added `policy-report` and `task-report` for E2E test verification, as well as `backend-dev-rules` for backend development guidelines.
- **Architect Challenge Mode**: The Architect agent now supports a new `challenge-me` workflow.
- **New Routine Command**: Added `organize-memory` to routine commands.

### 🛠️ Changes

- **Simplified Routine Commands**: Rewrote `commit.md`, `handoff.md`, and `pr-message.md` using simpler English to improve readability and execution.
- **AGENTS.md Update**: Added a comprehensive summary table listing and explaining all available agent skills.
- **General Configuration Updates**: Synchronized and updated workflows, settings, and registry entries across `.agents`, `.claude`, and `.mitra` directories.

---
    
## [4.0.0] - 2026-06-14

### 🚀 Major Release: AGY Migration & Expanded Skillset

Version 4.0.0 introduces a transition from legacy CLI structures, adding powerful new agent skills and standardizing integration under the new `AGY` command line interface.

### ✨ New Features

- **CLI Standardization & Deprecation**: The legacy `gemini-cli` has been deprecated and replaced by the modern, robust `AGY` CLI toolset.
- **Enhanced Agent Skillset**: Added several specialized agent skills to expand developer capabilities:
  - `caveman`: Terse token-saving communication mode.
  - `code-review`: Automated TypeScript and functional programming code review.
  - `git-guardrails`: Hook integration to prevent destructive git operations.
  - `to-prd`: Synthesizing context into Product Requirement Documents (PRDs).
  - `workflow-loader`: Dynamic loading and execution of Markdown workflows.
  - `zoom-out`: High-level module mapping and architectural overviews.
- **Analyst Challenge Mode**: The Analyst agent now supports the new `challenge-me` workflow to stress-test implementation plans, refine domain glossaries, and align on technical decisions.

### 🛠️ Changes

- **Clean Skill Paths**: Standardized skill directories (removing trailing spaces from paths like `to-prd` and `zoom-out`) and set up symlinks inside `.claude/skills/` for seamless integration.

### ⚠️ Deprecated / Removed

- **gemini-cli**: Officially deprecated in favor of `AGY` CLI.

---

## [3.0.0] - 2026-04-04

### 🚀 Major Release: The "Full-Lifecycle" Update

Version 3.0.0 marks the definitive transition of Mitra from a strategy-only consultancy framework into a **Full-Lifecycle Development Platform**. All "Consultancy-Only" and "No-Code" restrictions have been removed.

### 🆚 V2 vs V3 Comparison

| Feature | **V2.0.0 (Consultancy)** | **V3.0.0 (Full-Lifecycle)** |
| :--- | :--- | :--- |
| **Philosophy** | **Spec-Driven:** "Align before you build." | **Implementation-First:** "We Plan, We Build." |
| **Agent Role** | **Strategy & Planning:** Strictly non-coding. | **Execution & Code:** Planning + Direct Development. |
| **Deliverables** | **Specs & Designs:** Strategy only. | **Production Code:** Filesystem mutation & implementation. |
| **Engine Type** | **Consultancy Engine:** Reviewer/Planner. | **Implementation Engine:** Builder/Partner. |

### ✨ New Features

-   **Full-Lifecycle Enablement**: Agents are now authorized to generate production-grade code, unit tests, and reference implementations.
-   **Implementation Engine**: Rebranded core logic from "Consultancy" to "Implementation" to better reflect the new execution-oriented behavior.
-   **Execution Mode**: Replaced "Consultancy Mode" with "Execution Mode" in all system-wide documentation (`README.md`, `GUIDE.md`, etc.).
-   **10x Developer Skill**: Introduced a new, language-agnostic `developer.md` workflow for high-performance software engineering and direct implementation.

### 🛠️ Changes

-   **Persona Refactoring**: Updated all 6 core agent personas to include the new "Execution & Implementation" policy.
-   **Workflow Synchronization**: Synchronized 20+ workflows across Source XML, AGY TOML, and Claude MD to remove non-implementation directives.
-   **Registry Update**: Updated the Agent Registry to reflect development capabilities and implementation focuses.
-   **Terminology Migration**: Final sweep to replace "Consultancy" with "Full-Lifecycle Implementation" across the entire repository.

### ⚠️ Deprecated / Removed

-   **Non-Implementation Policy**: Removed the strict policy forbidding agents from writing implementation code.
-   **No-Code Directives**: Excised all "No Code" and "No Filesystem Mutation" rules from agent profiles.

## [2.2.0] - 2026-04-04

### 🏗️ Standardized Architecture Update

This update finalizes the transition to a centralized, YAML-based memory architecture and enforces strict agent-namespacing for all system outputs.

### ✨ New Features

-   **YAML-Based Persistence**: Migration from JSON to YAML for all session state files, improving readability and tool-compatibility.

### 🛠️ Changes

-   **Agent-Namespaced Artifacts**: Updated all agent personas and 15+ workflows to strictly save files in `{project_root}/artifacts/{project_id}/{agent-id}/`.
-   **Uniform Deliverable Rules**: Implemented a standardized "Deliverables & Storage" footer across all non-memory-manager workflows to ensure protocol compliance.
-   **Memory Manager Synchronization**: All 6 core agent memory managers now use an identical YAML schema and scanning protocol.

---

## [2.1.0] - 2026-04-04

### 📦 Centralized Memory Update

This update relocates all agent session memories from agent-specific directories to a project-isolated structure under `artifacts/`.

### ✨ New Features

-   **Project-Isolated Memory**: Session state files are now stored in `artifacts/{project_id}/{agent_id}/memory/`.
-   **Clean Agent Dirs**: Removed memory storage from `.mitra/agents/` to keep core agent definitions separate from session data.

### 🛠️ Changes

-   **Memory Protocol**: Updated `AGENTS.md` and `TREE.md` with the new State Path pattern.
-   **Workflow Synchronization**: Updated all 6 `memory-manager` workflows and mirrored CLI configurations (Claude/AGY).
-   **Activation Logic**: Enhanced agent startup to automatically create memory subdirectories within the project artifacts folder.

---

## [2.0.0] - 2026-01-09

### 🚀 Major Release: The "Memory & Structure" Update

Version 2.0.0 introduces a comprehensive overhaul of the agent architecture, establishing a strict "Source of Truth" via XML workflows and enabling long-term persistence through the new Memory System.

### 🆚 V1 vs V2 Comparison

| Feature | **V1.0.0 (Legacy)** | **V2.0.0 (Current)** |
| :--- | :--- | :--- |
| **Agent Logic** | Scattered across CLI configs | **Centralized** in `.agent/workflows/*.md` (XML) |
| **Consistency** | AGY/Claude often drifted | **Synchronized** (XML -> TOML/MD) |
| **Persistence** | None (Amnesic sessions) | **Memory System** (`*save`/`*load`) |
| **Scope** | Ambiguous (Some coding) | **Strict Consultancy** (Specs/Plans only) |
| **Orchestrator** | Routing only | **Routing + Help + Context** |
| **Storage** | Root or random folders | **Structured**: `artifacts/{project_id}/` |

### ✨ New Features

-   **Memory System (Global)**: All 6 agents can now `*save` their session state to JSON and `*load` it later to resume work.
    -   Schema includes: `session_summary`, `key_decisions`, `next_steps`, and `artifacts`.
-   **XML Source of Truth**: Agent behaviors are now defined once in `.agent/workflows/` and propagated to all CLI platforms.
-   **Orchestrator Help**: Added `[0] Help & Guidance` (`*help`) to the Orchestrator for interactive tutorials and validiation.
-   **Agent Registry**: A centralized `.mitra/agents/registry.md` now acts as the capabilities catalog.

### 🛠️ Changes

-   **Folder Structure**:
    -   Added `.mitra/agents/{agent}/memory/` for state tables.
    -   Standardized workflow paths to `.mitra/agents/{agent}/workflows/`.
-   **CLI Configuration**:
    -   AGY `.toml` files are now strictly generated from the XML source.
    -   Claude `.md` files are now strictly generated from the XML source.
-   **Documentation**:
    -   Updated `AGENTS.md` to be an operational manual.

### ⚠️ Deprecated / Removed

-   **Legacy Configs**: Removed standalone/divergent configuration files that did not match the `.agent` XML definitions.
-   **Git Awareness**: Removed direct Git operation commands from agent personas; agents now rely on the user for version control.

### 🔮 Under Development (What's Next)

-   **Advanced Tool Calling**: Enabling agents to use more sophisticated tools beyond file I/O.
-   **Agent Builder Service**: A meta-agent to help you design and spawn new custom agents.
-   **Workflow Builder Service**: Visual or conversational tool to define complex agent workflows.
-   **MCP Integration**: Native support for Model Context Protocol to connect with external tools.
-   **RAG & CAG Memory**: Implementing Retrieval-Augmented Generation (RAG) and Content-Augmented Generation (CAG) for handling complex, large-scale project memories.
-   **A2A Protocol**: Enabling A2A Protocol for long-running autonomous tasks.
