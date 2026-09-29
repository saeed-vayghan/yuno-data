# Workflow: UI Mockup Creation

This workflow guides the Designer in creating high-fidelity visual mockups.

## Protocol
Execute the following steps sequentially. Obtain user confirmation after each major step.

### 1. Requirement & Wireframe Check
**Goal**: Validate inputs.
- **Action**: Confirm we have the "Wireframes" or "User Stories" for this screen.
- **Check**: Are the content requirements clear?

### 2. Visual Layout
**Goal**: Apply the design system.
- **Action**: Describe the screen layout using the defined Design System components.
    - Header/Footer placement.
    - Grid alignment (Columns, Gutters).
    - Visual hierarchy (What is the primary action?).

### 3. Interactive Elements
**Goal**: Define behavior.
- **Action**: Specify how elements react to user input.
    - Hover states.
    - Loading states.
    - Error messages.

### 4. Output Generation
- **Deliverable**: A "Visual Spec" markdown file (use `<t name="Mockup Spec">` per component), detailed enough for Kaveh (Engineer) to implement without guessing.
- **Storage**: Save to `artifacts/{project_id}/designer/` with the `{YYYY-MM-DD}-` filename prefix.
