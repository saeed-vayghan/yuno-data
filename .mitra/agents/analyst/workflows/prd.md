# Workflow: Product Requirements Document (PRD) Creation

This workflow guides the Analyst in creating a comprehensive PRD.

## Phase 1: Context & Problem Definition
1.  **Ingest Context**: Ask the user for any existing background info, similar apps, or specific problem statements.
2.  **Define Problem**: Clearly articulate the "What" and "Why".
    *   *Output*: A clear Problem Statement.
3.  **Identify Goals**: List the core business and user goals.
    *   *Output*: Key Success Metrics (Use `<t name="Success Metric (KPI)">`).
    *   *Standard*: Ensure goals are `<s name="SMART">`.

## Phase 2: User Analysis
4.  **Identify Users**: List primary and secondary user personas.
5.  **User Stories**: Draft high-level user stories for the core flow.
    *   *Format*: Use `<t name="User Story">`.
    *   *Quality Check*: Verify they meet `<s name="INVEST">` criteria.

## Phase 3: Functional Requirements
6.  **Core Features**: List the mandatory features (Must-Haves).
    *   *Standard*: Define `<s name="AC">` (Acceptance Criteria) for key features.
7.  **Nice-to-Haves**: List secondary features (Should-Haves).
8.  **Flow Definition**: Describe the critical user journey step-by-step.

## Phase 4: Non-Functional Requirements
9.  **Technical Constraints**: Platform (Web/Mobile), Tech Stack preferences (if any).
10. **Performance & Security**: Speed, data privacy, and reliability requirements.

## Phase 5: Deliverable Generation
11. **Draft PRD**: Compile all findings into a structured markdown document.
12. **Review**: Present the draft to the user for feedback.
13. **Finalize**: 
    - **Deliverable**: A structured Product Requirements Document (PRD).
    - **Storage**: Save to `artifacts/{project_id}/analyst/` with the `{YYYY-MM-DD}-` filename prefix.
