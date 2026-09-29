# Workflow: Design System Creation

This workflow guides the Designer in establishing or extending a cohesive design system.

## Protocol
Execute the following steps sequentially. Obtain user confirmation after each major step.

### 1. Foundation Definition
**Goal**: Establish base values.
- **Action**: Define:
    - **Color Palette**: Primary, Secondary, Feedback, Neutral.
    - **Typography**: Headings, Body, Monospace (Font family, scale).
    - **Spacing**: Grid system, padding/margin scale (e.g., 4px baseline).
    - **Radius & Shadows**: Border radius and elevation levels.

### 2. Component Architecture
**Goal**: Define reusable UI elements.
- **Action**: Specify core components (Buttons, Inputs, Cards, Modals).
    - **States**: Default, Hover, Active, Disabled, Error.
    - **Variants**: Primary, Secondary, Ghost, Outline.

### 3. Token Standardization
**Goal**: Ensure consistency.
- **Action**: Create a "Tokens" map (JSON/CSS Variables) in the `<t name="Design Token">` format.
    - `color-primary-500`
    - `spacing-md`
    - `font-size-xl`

### 4. Output Generation
- **Deliverable**: A `design-tokens.json` or `variables.css` file.
- **Storage**: Save to `artifacts/{project_id}/designer/` with the `{YYYY-MM-DD}-` filename prefix.
