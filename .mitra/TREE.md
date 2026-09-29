### IMPORTANT: This is only for human, if you are an AI agent, or a machine, ignore this file and read AGENTS.md instead.

---

# Mitra Directory Architecture

This document defines the definitive directory structure for the Mitra multi-agent Full-Lifecycle Development Platform. AI agents MUST reference this tree to locate their personas, workflows, and memory states.

## 🏁 Project Root Structure

```text
/
├── .agents/workflows/      Agent manifests formatted for AntiGravity.
├── .agents/skills/         Shared skills (symlinked into .claude/skills/).
├── .claude/commands/mitra/ Mirror of the agent manifests formatted for Claude.
├── artifacts/       Strictly designated output folder for all agent artifacts.
│   └── {project_id}/       Project-specific output (e.g., upgrade-agents).
│       └── {agent_id}/     Agent-specific project outputs.
│           └── memory/     YAML persona files containing rich session state (*save/*load).
└── .mitra/
    ├── config.yaml         Global configuration (project_id, user_name).
    ├── TREE.md             [THIS FILE] The definitive structure guide.
    ├── docs/               Some Documents.
    ├── templates/          Templates used by agents.
    └── agents/             Configuration and data for specialized agents.
        ├── registry.md     Master list of agent capacities and triggers.
        └── {agent_id}/     Agent-specific directory (e.g., analyst, manager).
            ├── persona.md  Markdown fragment defining the agent's identity.
            └── workflows/  Markdown files defining specialized multi-step tasks.
```

## 🧠 Memory Protocol

-   **Path**: `{project-root}/artifacts/{project_id}/{agent_id}/memory/`
-   **Filename Pattern**: `persona-{yyyy-mm-dd}-{version}.yaml` (e.g. `persona-2026-07-15-01.yaml`; `version` is two-digit, increments if today's file exists)

## 🛠️ Workflow Protocol

-   **Path**: `{project-root}/.mitra/agents/{agent_id}/workflows/`
-   **Execution**: Workflows are loaded dynamically by the `workflow-loader` skill.
