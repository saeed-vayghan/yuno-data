### IMPORTANT: This is only for human, if you are an AI agent, or a machine, ignore this file and read AGENTS.md instead.

---

## 🛠️ Developer & Agent Guidelines

### 1. Modifying an Agent
When adding a capability or fixing a bug in an agent's logic:
1.  **Edit XML**: Modify `.agents/workflows/mitra-{agent}.md`.
    *   *Rule*: Update the `<menu>` and `<menu-handlers>` sections together.
2.  **Sync Claude**: Copy updates to `.claude/commands/mitra/{agent}.md`.
    *   *Rule*: Keep each copy's script paths: `./.agents/skills/...` in the Antigravity file, `./.claude/skills/...` in the Claude file.

### 2. Creating a New Workflow
1.  **Create**: New file in `.mitra/agents/{agent}/workflows/{workflow_name}.md`.
2.  **Header**: Include a YAML frontmatter with `description` and `version`.
3.  **Body**: Define the step-by-step process for the agent to follow.
4.  **Link**: Add a handler in the Agent's XML to load this workflow.

### 3. Constraints & Laws
1.  **Unified Context**: All agents must read `config.yaml` to respect `project_id`.
2.  **Output Isolation**: All artifacts must go to `artifacts/{project_id}/`.

### 4. Custom Skills Sync
Custom skills are shared between Antigravity (which uses `.agents/skills/`) and Claude Code (which uses `.claude/skills/`). 
*   **Symlinking**: To ensure compatibility without duplication, directories in `.agents/skills/` are symlinked into `.claude/skills/`.
*   **Creation**: When creating a new skill, create it in `.agents/skills/` and then create a relative symbolic link to it in `.claude/skills/`:
    ```bash
    ln -sfn "../../.agents/skills/<skill-name>" ".claude/skills/<skill-name>"
    ```

