# Workflow: Memory Manager

This workflow enables the Manager to save and restore rich session state, including context, artifact links, and future steps.

## Protocols

### 1. Save State (`*save`)
**Trigger**: User runs `*save` or asks to "save memory".

**Steps**:
1.  **Deep Capture**: Analyze the current session to extract:
    -   `project_id` & `user_name`
    -   `current_topic`: What was being worked on (e.g., "Sprint 1 Planning").
    -   `session_summary`: A 1-2 sentence overview of achievements.
    -   `artifacts`: Scan `artifacts/{project_id}/manager/` for any files created/modified in this session.
    -   `key_decisions`: List explicit user choices (e.g., "Sprint: 2 weeks", "Priority: Core Auth").
    -   `next_steps`: 2-3 actionable bullet points for the next session.
2.  **Generate Filename**:
    - **Persona State**: `persona-{yyyy-mm-dd}-{version}.yaml`
    - **Workflow State**: `workflow-{yyyy-mm-dd}-{version}.yaml`
    - `version`: Two digits starting with `01`. Increment if today's file exists (e.g., `01`, `02`).
    - Use **Workflow State** when saving from inside an active workflow (e.g. mid-PRD); `{workflow-id}` is that workflow's filename without `.md`. Otherwise use **Persona State**.
3.  **Construct YAML**:
    ```yaml
    timestamp: "{ISO-8601}"
    agent: "mitra-manager"
    project_id: "{project_id}"
    user_name: "{user_name}"
    context:
      topic: "{current_topic}"
      status: "in-progress"
      last_deliverable: "{most_recent_artifact_filename}"
      session_summary: "{session_summary}"
      key_decisions:
        - "Decision 1"
        - "Decision 2"
      next_steps:
        - "Step 1"
        - "Step 2"
    artifacts:
      - type: "Project Plan"
        path: "artifacts/{project_id}/manager/{filename}.md"
        description: "Sprint Plan for X"
    ```
4.  **Write**: 
    - For Persona: Save to `artifacts/{project_id}/manager/memory/{persona_filename}`.
    - For Workflow: Save to `artifacts/{project_id}/manager/memory/{workflow-id}/{workflow_filename}`.
5.  **Confirm**: "Session saved as `{filename}`. You can restore this later with `*load`."

### 2. Load State (`*load`)
**Trigger**: User runs `*load` or asks to "restore memory".

**Steps**:
1.  **List**: Scan `artifacts/{project_id}/manager/memory/` (and subfolders) for available YAML files.
    -   `[1] persona-2026-01-09-01.yaml` (Topic: Sprint Planning)
2.  **Select**: Ask user to pick a number.
3.  **Read**: Load the content of the selected YAML file.
4.  **Inject**: Update current session variables (`project_id`, `topic`) with the loaded data.
5.  **Resume**:
    -   **Recap**: "Welcome back. Last time, we worked on **{topic}**. {session_summary}"
    -   **Context**: "We made these key decisions: {key_decisions}."
    -   **Prompt**: "Our next steps were: {next_steps}. Shall we proceed?"
