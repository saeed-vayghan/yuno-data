# Workflow: Sprint Planning

This workflow guides the Manager in defining the scope for the next iteration.

## Protocol
Execute the following steps sequentially. Obtain user confirmation after each major step.

### 1. Backlog Review
**Goal**: Prioritization.
- **Action**: Review open tickets from the latest task breakdown in `artifacts/{project_id}/manager/`.
- **Selection**: Ask the user: "What is the primary goal for this Sprint?" (e.g., "MVP Launch", "User Auth").

### 2. Capacity Check
**Goal**: Feasibility.
- **Action**: Estimate the complexity of selected tasks. (S/M/L or Points).
- **Check**: Is this realistic for the sprint's timeframe? Flag risks.

### 3. Sprint Goal Definition
**Goal**: Focus.
- **Action**: Write a single sentence describing the Sprint outcome.
    - Example: "By the end of this sprint, a user will be able to sign up and view their profile."

### 4. Output Generation
- **Deliverable**: A `{YYYY-MM-DD}-sprint-plan.md` file in the `<t name="Sprint Plan">` format (Goal, Selected Tasks, Capacity, Risks).
- **Storage**: Save to `artifacts/{project_id}/manager/` with the `{YYYY-MM-DD}-` filename prefix.
