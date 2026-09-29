# Agent Registry

The Mitra agents, their menu commands, and where each is defined. The Orchestrator uses this to route user requests. For detailed information on the system's directory structure, see [`.mitra/TREE.md`](/.mitra/TREE.md).

## Quick Reference

| Agent | Role | Primary Focus | Trigger |
| :--- | :--- | :--- | :--- |
| **Mitra** | Orchestrator | Guidance & Routing | `/mitra:orchestrator` |
| **Zal** | Manager | Planning & Coordination | `/mitra:manager` |
| **Sina** | Analyst | Requirements & Strategy | `/mitra:analyst` |
| **Jamshid** | Architect | Architecture & Infrastructure | `/mitra:architect` |
| **Mani** | Designer | Design & Frontend Logic & UI & UX | `/mitra:designer` |
| **Kaveh** | Engineer | Technical Specification & Implementation | `/mitra:engineer` |

## 🎼 Mitra (Orchestrator)
- **Role**: All-Seeing Guardian & Guide
- **Capabilities**:
    - **Party Mode**: Host collaborative sessions (`*party`).
    - **Help**: Explain the system and which agent to use (`*help`).
    - **Context**: Confirm `project_id` and summarize project status (`*context`).
    - **Routing**: Direct users to the right expert.
    - **Memory**: Save (`*save`) and Load (`*load`) session state; `*save-all` / `*load-all` for every agent at once.
- **Location**: `.claude/commands/mitra/orchestrator.md` (Antigravity: `.agents/workflows/mitra-orchestrator.md`; persona: `.mitra/agents/orchestrator/persona.md`)

## 👑 Zal (Manager)
- **Role**: Wise Visionary & Planner
- **Capabilities**:
    - **Task Breakdown**: Convert features into tickets (`*breakdown`).
    - **Sprint Planning**: Define sprint goals and scope (`*sprint`).
    - **Dispatch**: Assign tasks to specialist agents (`*dispatch`).
    - **Memory**: Save (`*save`) and Load (`*load`) session state.
- **Location**: `.claude/commands/mitra/manager.md` (Antigravity: `.agents/workflows/mitra-manager.md`; persona: `.mitra/agents/manager/persona.md`)

## 📊 Sina (Analyst)
- **Role**: Business Analyst
- **Capabilities**:
    - **Challenge Me**: Interview session that challenges you against the project (`*challenge-me`).
    - **Brainstorming**: Ideation and scope exploration (`*brainstorm`).
    - **Research**: Market and topic research (`*research`).
    - **PRD**: Create Product Requirements Documents (`*prd`).
    - **Competitive Analysis**: Analyze competitors (`*comp`).
    - **Memory**: Save (`*save`) and Load (`*load`) session state.
- **Location**: `.claude/commands/mitra/analyst.md` (Antigravity: `.agents/workflows/mitra-analyst.md`; persona: `.mitra/agents/analyst/persona.md`)

## 🏛️ Jamshid (Architect)
- **Role**: Great Builder
- **Capabilities**:
    - **Backend**: Service architecture — boundaries, communication, resilience (`*backend`).
    - **Frontend**: Architecture (`*frontend`).
    - **Database**: Schema Design (`*database`).
    - **Cloud**: Infrastructure & Deployment (`*cloud`).
    - **Microservices**: Service boundaries (`*microservices`).
    - **Review**: System Audit (`*review`).
    - **Challenge Me**: Dual-agent adversarial review — Jamshid vs Kaveh (`*challenge-me`).
    - **Memory**: Save (`*save`) and Load (`*load`) session state.
- **Location**: `.claude/commands/mitra/architect.md` (Antigravity: `.agents/workflows/mitra-architect.md`; persona: `.mitra/agents/architect/persona.md`)

## 🎨 Mani (Designer)
- **Role**: Master Artist
- **Capabilities**:
    - **UI Design**: General interface design (`*ui`).
    - **Design System**: Tokens and components (`*system`).
    - **Mockups**: Component visual specs (`*mockup`).
    - **User Flows**: Journey mapping (`*flow`).
    - **Audit**: Accessibility & UX review (`*audit`).
    - **Memory**: Save (`*save`) and Load (`*load`) session state.
- **Location**: `.claude/commands/mitra/designer.md` (Antigravity: `.agents/workflows/mitra-designer.md`; persona: `.mitra/agents/designer/persona.md`)

## ⚡ Kaveh (Engineer)
- **Role**: Master Smith & Implementation Expert
- **Capabilities**:
    - **API**: Endpoint-level API contracts (OpenAPI/GraphQL) and their implementation (`*api`).
    - **Security**: Security audit & hardening (`*security`).
    - **Docs**: Technical documentation (`*docs`).
    - **Report**: Technical findings report (`*report`).
    - **Develop**: Feature implementation & testing (`*develop`).
    - **Memory**: Save (`*save`) and Load (`*load`) session state.
- **Location**: `.claude/commands/mitra/engineer.md` (Antigravity: `.agents/workflows/mitra-engineer.md`; persona: `.mitra/agents/engineer/persona.md`)

## 🧠 Memory System (Global)
All Mitra agents are equipped with a standardized **Memory System** to allow persistent sessions.
- **Usage**:
    - **Save State** (`*save`): Captures the current topic, summary, key decisions, and links to created artifacts.
    - **Load State** (`*load`): Lists previous sessions and restores context (variables, project ID) to resume work.
- **Storage**: Sessions are saved in **YAML** format in `artifacts/{project_id}/{agent-id}/memory/`.
    - **Persona State**: `persona-{yyyy-mm-dd}-{version}.yaml`
    - **Workflow State**: `{workflow-id}/workflow-{yyyy-mm-dd}-{version}.yaml`
