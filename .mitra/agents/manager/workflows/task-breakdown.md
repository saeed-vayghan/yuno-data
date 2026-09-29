# Workflow: Task Breakdown

This workflow guides the Manager in breaking down high-level features into estimable tickets.

## Protocol
Execute the following steps sequentially. Obtain user confirmation after each major step.

### 1. Feature Analysis
**Goal**: Understand the detailed requirement.
- **Action**: Read the PRD or Feature Request.
- **Verification**: Check `<s name="DoR">` — do we have the User Story and Acceptance Criteria? If not, send the user to Sina (`/mitra:analyst`) first.

### 2. Micro-Tasking
**Goal**: Granularity.
- **Action**: Break the feature into tasks that take < 1 day.
- **Example**:
    - Feature: "Login Page"
    - Tasks:
        1. Design Login Mockup (Designer)
        2. Define Auth API Spec (Engineer)
        3. Define User Schema (Architect)

### 3. Ticket Generation
**Goal**: Structured output.
- **Action**: Create a `<t name="Task Card">` for each task.
    - **Title**: Actionable verb (e.g., "Design...", "Spec...", "Map...").
    - **Description**: Link to requirements.
    - **Deliverable**: Expected output filename, `{YYYY-MM-DD}-<kebab-case-name>-<version>.<ext>` (e.g., `2026-01-29-design-login-mockup-01.svg`).

### 4. Output Generation
- **Deliverable**: A markdown table of tickets.
- **Storage**: Save to `artifacts/{project_id}/manager/` with the `{YYYY-MM-DD}-` filename prefix.
