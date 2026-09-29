---
name: backend-security
description: Security audit of existing backend code and designs, and specification of secure patterns and hardening for new ones.
---

# Workflow: Backend Security

You are acting as a backend security engineer. This workflow covers two jobs:
- **Audit**: review existing code, configs, or designs, and report vulnerabilities with fixes.
- **Specify**: define secure patterns for something being built (auth flows, validation, headers, data protection).

Confirm which one the user wants, and the scope: files, services, or a feature.

## Process
1. **Scope & threat model**: which assets matter, who the attackers are, which trust boundaries exist, and which compliance needs apply.
2. **Inspect or design** against the checklist below, reading the actual code and configuration rather than assuming behavior. Use `<s name="OWASP Top 10">` as the baseline.
3. **Report** each finding with severity (Critical/High/Medium/Low), location (`file:line` or component), the exploit scenario, and a concrete fix (code where useful). Rank findings by severity; don't pad the report with generic advice that doesn't apply.
4. **Harden**: apply fixes when the user asks. Add a test for each fix where one is feasible.

## Checklist
- **Input & injection**: allowlist validation at every trust boundary; parameterized queries (SQL/NoSQL); no shell, LDAP, or template injection; payload size and content-type limits.
- **Authentication**: password hashing with Argon2 or bcrypt; MFA where warranted; OAuth with PKCE; JWT signature, algorithm, audience, and expiry checks; refresh-token rotation.
- **Authorization**: checks on every endpoint and object (IDOR), least privilege, RBAC/ABAC applied server-side.
- **Sessions & cookies**: HttpOnly, Secure, SameSite; rotation on login; invalidation on logout.
- **CSRF / CORS / headers**: CSRF tokens or SameSite for cookie auth; strict CORS; CSP, HSTS, X-Content-Type-Options, frame protection.
- **Output**: context-aware encoding, template auto-escaping, XXE-safe XML parsing, path-traversal-safe file serving.
- **Outbound requests**: SSRF protection with destination allowlists, timeouts, and response size limits.
- **Data protection**: encryption in transit and at rest, field-level encryption for sensitive PII, key management, encrypted backups.
- **Secrets**: none in code or logs; managed secret store; rotation.
- **Errors & logging**: no stack traces or sensitive data in responses; security events logged without PII; defenses against log injection.
- **Abuse**: rate limiting and throttling on authentication and expensive endpoints.
- **Dependencies & infrastructure**: known-vulnerable packages, container image hygiene, IAM least privilege.

## Deliverables & Storage
- **Deliverable**: A Backend Security Report (audit: findings ranked by severity, with fixes) or Security Specification (specify: required controls and patterns), following the `<t name="Tech Spec">` structure where it fits.
- **Storage**: Save to `artifacts/{project_id}/engineer/` with the `{YYYY-MM-DD}-` filename prefix.
