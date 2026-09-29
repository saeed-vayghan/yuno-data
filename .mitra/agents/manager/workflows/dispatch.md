# Workflow: Task Dispatch

This workflow guides the Manager in assigning planned tasks to the correct agents.

## Protocol
Execute the following steps sequentially. Obtain user confirmation after each major step.

### 1. Skill Mapping
**Goal**: Right Agent for the Right Task.
- **Action**: Review the latest Sprint Plan in `artifacts/{project_id}/manager/`.
- **Map**:
    - Visual/UI -> **Designer** (Mani)
    - Architecture/DB/Cloud -> **Architect** (Jamshid)
    - API/Security/Docs -> **Engineer** (Kaveh)
    - Analysis/PRD -> **Analyst** (Sina)

### 2. Dependency Analysis
**Goal**: Order of Operations.
- **Action**: Identify blockers.
    - "Can Kaveh write the API spec before Jamshid defines the Schema?" (No).
- **Typical sequence** (adjust to the actual dependencies):
    1. Architect (Schema)
    2. Engineer (API Spec)
    3. Designer (Mockup)

### 3. Command Generation
**Goal**: Execution validation.
- **Action**: Generate the sequence of commands for the User.
    - `Step 1: /mitra:architect (Topic: User Schema)`
    - `Step 2: /mitra:engineer (Topic: Auth API)`

### 4. Output Generation
- **Deliverable**: A "Dispatch Plan" identifying who does what and in which order.
- **Storage**: Save to `artifacts/{project_id}/manager/` with the `{YYYY-MM-DD}-` filename prefix.
