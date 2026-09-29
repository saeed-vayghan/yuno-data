---
name: challenge-me
description: Run an interview session to stress-test your plan. This session compares the plan with the existing domain model, refines terminology, and updates the glossary and ADRs inline. Use this when the user wants to stress-test a plan.
---

This workflow guides you through a relentless interview session with the user. The goal is to stress-test their plan against the project's codebase, domain language, and architectural decisions.

---

## 🎯 Core Objectives

1. **Test the Plan**: Question every aspect of the plan until both you and the user share a clear, deep understanding.
2. **Review Step-by-Step**: Walk down each branch of the design. Resolve decisions and their dependencies one-by-one.
3. **Ask One at a Time**: Ask questions one by one. Always wait for the user's feedback before asking the next question.
4. **Suggest Answers**: For every question you ask, provide your recommended answer or option.
5. **Inspect the Code First**: Before asking the user a question, check if you can answer it yourself by exploring the codebase.

---

## 🧠 Domain Awareness & File Structure

Look for existing documentation in the following directories. Only create these files and folders lazily (when you have content to write).

- **For Single-Context Projects**:
  - Domain glossary: `artifacts/{project_id}/docs/CONTEXT.md`
  - Architecture Decision Records: `artifacts/{project_id}/docs/adr/`
- **For Multi-Context Projects**:
  - Context map: `artifacts/{project_id}/docs/CONTEXT-MAP.md` (shows where each context file lives)
  - System-wide decisions: `artifacts/{project_id}/docs/adr/`
  - Sub-context glossary: `src/{context_directory}/CONTEXT.md`

---

## ⚡ Active Grilling Guidelines

Apply these rules during the session:

### 1. Match Against the Glossary
If the user uses a term that conflicts with `CONTEXT.md`, call it out immediately.
> *Example:* "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which one is correct?"

### 2. Clarify Vague Terms
When the user uses vague or overloaded terms, suggest a precise, canonical term.
> *Example:* "You mentioned 'account'—do you mean the Customer or the User? Those are different concepts in this system."

### 3. Stress-Test with Scenarios
When discussing relationships between concepts, probe edge cases with specific scenarios.
> *Example:* "What happens if a user submits a payment at the exact moment their subscription is paused?"

### 4. Cross-Reference with Code
Verify if the code matches the user's assumptions. Highlight contradictions.
> *Example:* "The code allows canceling complete Orders, but you mentioned partial cancellation is possible. Which behavior should we implement?"

### 5. Update the Glossary Inline
As soon as a term is resolved, update `CONTEXT.md` immediately. 
- Do **not** wait until the end of the session.
- Follow the template format in [.mitra/templates/CONTEXT-FORMAT.md](../../../templates/CONTEXT-FORMAT.md).
- Do **not** include implementation details or specs in `CONTEXT.md`. It must remain a pure glossary.

### 6. Create ADRs Sparingly
Only suggest creating an Architecture Decision Record (ADR) if all three conditions are met:
1. **Hard to reverse**: Changing the decision later will be expensive.
2. **Surprising without context**: A future developer might wonder why we designed it this way.
3. **A real trade-off**: There were valid alternatives, and we picked this one for specific reasons.

If any of these three conditions are not met, do not create an ADR. Follow the template format in [.mitra/templates/ADR-FORMAT.md](../../../templates/ADR-FORMAT.md).

---

## ✅ Session End

End when every branch of the plan is resolved or the user stops. Close with a short summary: decisions made, glossary terms and ADRs added or changed, and questions still open.