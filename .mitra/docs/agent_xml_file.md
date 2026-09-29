# Mitra Agent Configuration Guide

This document defines the schema and purpose of the XML-based configuration files used to define Mitra Agents (e.g., `.agents/workflows/mitra-analyst.md`).
By understanding these tags, you can customize agent behavior, create new agents, or modify existing workflows.

## 🧬 Anatomy of an Agent

Every agent is defined within a root `<agent>` tag which acts as the container for its entire brain.

```xml
<agent id="unique-id" name="DisplayName" title="Role Title" icon="📊">
  <!-- Components go here -->
</agent>
```

---

## 🚀 1. Activation & Startup (`<activation>`)
This block runs **automatically** when the agent is first loaded. It sets up the environment and state.

```xml
<activation critical="MANDATORY">
  <step n="1">Load persona...</step>
  <step n="2">Load config...</step>
</activation>
```

| Tag | Purpose |
| :--- | :--- |
| **`<activation>`** | The sequence of commands executed at boot time. |
| **`<step n="x">`** | An individual instruction. The agent executes these sequentially. Used to load memory, create folders, and greet the user. |

---

## 🎮 2. Menu System (`<menu>` & `<menu-handlers>`)
This defines the primary user interface. Instead of a free-form chat, the agent presents structured options.

### The Display (`<menu>`)
Defines what the user *sees*.
```xml
<menu>
  <item cmd="*brainstorm">[1] Brainstorm Project</item>
</menu>
```

### The Logic (`<menu-handlers>`)
Defines what *happens* when an option is selected.
```xml
<menu-handlers>
  <handler cmd="*brainstorm">
    Action: Initiate the <brainstorm-protocol>...
  </handler>
</menu-handlers>
```

| Tag | Attributes | Purpose |
| :--- | :--- | :--- |
| **`<item>`** | `cmd` (Trigger ID) | Displays a clickable/selectable option to the user. |
| **`<handler>`** | `cmd` (Matching ID) | The code block that executes when the corresponding item is picked. Connects the UI to the Logic. |

---

## 🧠 3. System Instructions (`<system-instructions>`)
This is the "Kernel" of the agent. It defines **HOW** the agent performs complex tasks. It contains named "Protocols" and "Engines".

### Protocols (Interactive Skills)
Self-contained sub-routines for specific interactive tasks (e.g., brainstorming, debugging).

```xml
<brainstorm-protocol>
  <trigger>When user selects brainstorm...</trigger>
  <flow>
    1. Ask Topic.
    2. Generate Ideas.
    3. Loop.
  </flow>
</brainstorm-protocol>
```

### Workflow Engines (File Runners)
Meta-rules for executing *external* markdown workflow files.

```xml
<workflow-engine>
  <rule>When executing a file...</rule>
  <logic>
    1. Read-Execute-Loop (Pause after every step).
    2. No skipping.
  </logic>
</workflow-engine>
```

| Tag | Purpose |
| :--- | :--- |
| **`<trigger>`** | The "If" condition. When this condition is met, the protocol starts. |
| **`<flow>`** | The "Then" sequence. A numbered algorithm the agent follows step-by-step. |
| **`<rule>`** | Defines the scope of an engine (e.g., "Only when running PRD workflows"). |
| **`<logic>`** | The axiom rules the agent must obey during execution (e.g., "Never use YOLO mode"). |

---

## 🧰 4. Embedded Resources (`<resources>`)
A local database of "Knowledge" or "Tools" the agent can reference without hallucinating.

```xml
<resources>
  <templates>
    <t name="User Story">As a [User], I want to [Action]...</t>
  </templates>
  <standards>
    <s name="INVEST">Independent, Negotiable, Valuable...</s>
  </standards>
</resources>
```

| Tag | Purpose | Usage in Workflows |
| :--- | :--- | :--- |
| **`<resources>`** | Container for all embedded knowledge. | N/A |
| **`<templates>`** | Container for text formats. | Use `<t name="Template Name">` in instructions. |
| **`<standards>`** | Container for quality rules. | Use `<s name="Standard Name">` in instructions. |
| **`<t>` / `<s>`** | Individual definitions. | The agent expands these tags at runtime. |

### 🔗 Linking Resources in Workflows
You can explicitly force the agent to use these resources in your `.md` workflow files:

> "Draft a user story using the `<t name="User Story">` format and verify it meets `<s name="INVEST">` criteria."

This creates a rigid contract: The workflow demands the standard, and the configuration provides the definition.

---

## ⚡ Customization Rules

1.  **Tag Naming**: Tags like `<brainstorm-protocol>` or `<workflow-prd>` are **custom namespaces**. You can rename them (e.g., `<idea-machine>`) as long as you update both the **Definition** (in system instructions) and the **Call** (in the menu handler).
2.  **Extensibility**: You can add new sections anywhere inside `<agent>`. For example, a `<knowledge-base>` section could be added if needed, as long as you instruct the agent on how to use it.
3.  **Strictness**: Using XML tags forces the LLM to pay higher attention to structure than plain text. Keep the syntax valid to maintain high adherence.
