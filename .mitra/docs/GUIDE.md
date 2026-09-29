# Mitra Features & User Guide

Welcome to **Mitra**, a multi-agent AI full-lifecycle system. This guide provides a detailed walkthrough of the system's capabilities, repository layout, developer guidelines, and a real-world example project to demonstrate how to leverage the collective intelligence of our agent roster.

---

## 🌟 Core Features

### 1. The Agent Roster
Six specialized agents ready to tackle different aspects of your project.

| Agent | Icon | Role | Focus | ID |
| :--- | :--- | :--- | :--- | :--- |
| **Mitra** | 🎼 | Orchestrator | Guidance, Routing, Party Host | `mitra-orchestrator` |
| **Sina** | 📊 | Analyst | Requirements & Strategy | `mitra-analyst` |
| **Zal** | 👑 | Manager | Planning & Task Breakdown | `mitra-manager` |
| **Jamshid** | 🏛️ | Architect | Systems, Database, Cloud | `mitra-architect` |
| **Mani** | 🎨 | Designer | UI/UX, Design Systems | `mitra-designer` |
| **Kaveh** | ⚡ | Engineer | Specs, Security, APIs | `mitra-engineer` |

### 2. Global Memory System
All agents share a unified memory system.

*   **`*save`**: Persists your current context, including the topic (e.g., `crypto-tasker`), key decisions, and artifacts.
*   **`*load`**: Instantly restores the session variables so you can pick up exactly where you left off.

#### Memory Protocols
*   **State Path**: `artifacts/{project_id}/{agent}/memory/state-{version}-{topic}-{yyyy-mm-dd}.json`
*   **Schema**:
    ```json
    {
      "timestamp": "ISO-8601",
      "context": { "topic": "...", "summary": "..." },
      "artifacts": [ { "type": "PRD", "path": "artifacts/..." } ]
    }
    ```
*   **Rule**: Never modify the `memory-manager` logic without testing the JSON read/write cycle.

> [!IMPORTANT]
> **MANDATORY MEMORY PROTOCOL**
> When asked to "save state", "persist context", or "remember this", agents **MUST** execute the `memory-manager` workflow defined in their `.toml` or `.agent` file.
> - **DO NOT** create ad-hoc markdown files like `MEMORY.md`.
> - **DO NOT** summarize in chat only.

---

## 📂 Repository Layout

*   **`.agents/workflows/`**: [SOURCE OF TRUTH] The master XML definitions for all agents. **Edit these first.**
*   **`.claude/commands/`**: Claude CLI interfaces. *Must mirror the Source of Truth.*
*   **`.mitra/agents/{agent}/`**: Agent-specific support files (persona, workflows).
*   **`artifacts/`**: The strictly designated output folder for all agent artifacts.
*   **`artifacts/{project_id}/{agent}/memory/`**: The designated folder for session persistence.