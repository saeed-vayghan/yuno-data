# Workflow: UI Design

General UI design work: new screens, visual refreshes, component design, and design reviews. For narrower jobs the dedicated workflows fit better: `*system` (tokens), `*mockup` (one-screen visual spec), `*flow` (user journeys).

## 1. Gather Context

Check what already exists before designing, so the result stays consistent with it:
- PRD and user stories: `artifacts/{project_id}/analyst/`
- Design system and earlier specs: `artifacts/{project_id}/designer/`
- Frontend architecture: `artifacts/{project_id}/architect/`
- Existing UI code, if any.

Then ask the user only for what is still missing: brand guidelines, target users and devices, platforms (web, iOS, Android, desktop), required accessibility level (default WCAG 2.1 AA), dark mode, and performance constraints.

## 2. Design

Propose a direction and get the user's reaction before detailing it. A complete design covers:
- **Layout & hierarchy**: the primary action on each screen is obvious.
- **Components & states**: default, hover, focus, active, disabled, loading, error, empty.
- **Responsive behaviour** across breakpoints.
- **Motion** only where it communicates state change; respect reduced-motion settings.
- **Dark mode** when in scope: adapted colors, contrast re-checked, shadows replaced where they stop working.

Check the design against `<s name="WCAG 2.1">`, `<s name="Fitts Law">`, `<s name="Hick's Law">`, and `<s name="Gestalt Principles">`. When the user wants something tangible, build an HTML/CSS/JSX prototype.

## 3. Handoff

Write the spec so Kaveh (Engineer) or Jamshid (Architect, frontend) can build it without guessing:
- Component specs in the `<t name="Mockup Spec">` format.
- Tokens used (new tokens go through `*system`).
- Interaction notes and accessibility annotations: contrast, focus order, labels, touch-target sizes.
- Rationale for any non-obvious decision.

Finish with a short summary of what was delivered and what is still open. Report only what was actually produced.

## Deliverables & Storage
- **Deliverable**: A UI Design Specification (layout, typography, color usage, component states, handoff notes).
- **Storage**: Save to `artifacts/{project_id}/designer/` with the `{YYYY-MM-DD}-` filename prefix.
