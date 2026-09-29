# Workflow: User Flow Design

This workflow guides the Designer in mapping out user journeys and interaction flows.

## Protocol
Execute the following steps sequentially. Obtain user confirmation after each major step.

### 1. Goal Definition
**Goal**: What is the user trying to accomplish?
- **Action**: Define the "Happy Path" (e.g., "User Signs Up" or "Checkout").

### 2. Step-by-Step Mapping
**Goal**: Logical sequence.
- **Action**: Create a numbered list of `<t name="User Flow Step">` entries (user action → system response → next state).
    1. User clicks "Sign Up".
    2. System shows Modal.
    3. User enters email...

### 3. Edge Case Discovery
**Goal**: Robustness.
- **Action**: Identify "Unhappy Paths".
    - What if internet fails?
    - What if email is duplicate?
    - What if they click "Cancel"?

### 4. Output Generation
- **Deliverable**: A Mermaid Diagram or bulleted list visualizing the flow.
- **Storage**: Save to `artifacts/{project_id}/designer/` with the `{YYYY-MM-DD}-` filename prefix.
