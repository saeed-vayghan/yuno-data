# Workflow: Competitive Analysis

This workflow guides the Analyst in performing a structured competitive analysis.

## Protocol
Execute the following steps sequentially. Obtain user confirmation after each major step.

### 1. Identify Competitors
**Goal**: List 3-5 key competitors.
- **Action**: Ask the user for known competitors or perform a search to identify them.
- **Output**: A bulleted list of competitors with 1-line descriptions.
- **Tools**: Web search, when the harness provides it.

### 2. Feature & Gap Analysis
**Goal**: Compare feature sets.
- **Action**: For each competitor, identify:
    - Key Features (What they do well).
    - Weaknesses (What users complain about).
    - Pricing Model (if relevant).
- **Template**: Use a standardized matrix (markdown table).

### 3. SWOT Synthesis
**Goal**: Strategic alignment.
- **Action**: Create a SWOT analysis for the USER'S product in relation to these competitors.
    - **Strengths**: Where can we win?
    - **Weaknesses**: Where are we vulnerable?
    - **Opportunities**: What gaps exist in the market?
    - **Threats**: What are competitors launching?

### 4. Strategic Recommendations
**Goal**: Actionable advice.
- **Action**: Recommend 3 specific features or modifications to gain a competitive edge.
- **Deliverable**: A "Strategic Brief" markdown file.
- **Storage**: Save to `artifacts/{project_id}/analyst/` with the `{YYYY-MM-DD}-` filename prefix.
