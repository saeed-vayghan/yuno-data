---
name: backend-dev-rules
description: Rules and best practices for writing secure, maintainable, reliable Python backend. Use when authoring or reviewing backend TS — services, APIs, policies, sinks, DB access, tests. Covers functional-core/thin-shell design, effect injection, security-by-structure, reliability patterns, constants-vs-config, KISS + simple types, DRY/utilities, comments, and logic-first testing.
---

# Backend Development Rules (Python, this repo)

These are the rules for backend code in the repo root. They are not generic advice —
each one is demonstrated by existing code here, cited so you can copy the pattern. When a
plan or an instruction conflicts with a rule, **say so and challenge it** (see §11) rather
than silently following it.

**The one-line creed:** *pure functions decide, thin classes/callers do; validate once at the
edge into honest types; enforce authority and fail-closed in the structure itself; make cleanup
idempotent and artifacts atomic; keep it simple; test the decisions and invariants — not the
line count; and verify on the running system before calling it done.*

---

## 1. Functional core, thin imperative/class shell

Most logic is **pure functions**. A **class** is legitimate only when it owns *stateful* or
*effectful identity*.

- **Use a class for:** a resource with a lifecycle/handle (`FileSink` owns a file + rotation
  state — `shared/telemetry-file/index.ts`; `WarmPool` owns the in-memory registry —
  `orchestrator/core/scheduling/warmpool.ts`; a DB wrapper owns a connection), or a typed error
  carrier (`HttpError` — `orchestrator/core/auth/errors.ts`). That is the whole list.
- **Everything else is a pure function:** validation (`resolveNature`), derivation
  (`computeBootFingerprint`, `decideTerminalAction` — `shared/execution/derive.ts`), policy
  (`selectExpiredRuns`, `withinPinnedCeiling`). Input data → output data,
  no side effects.
- **The test you got it right:** the pure function is unit-testable *without mocks* — no DB, no
  fs, no clock. If a "pure" function needs a mock to test, its effect wasn't pushed to the edge.

## 2. Push effects to the boundary; inject them, don't import them

`orchestrator/core/network/live-vms.ts` is the model: `liveVmRowOf(record, ctx)` is pure and
receives the per-tenant policy LOOKUP (`ctx.policyOf`), the config defaults and the heartbeat cadence
as arguments; the *caller* (`network/policy-plane.ts`) resolves them from the DB and config. (The old
model, `core/provisioning/disk-budget.ts`, was deleted at T-121.)

- A function that both *decides* and *does* is two functions glued together. Split them:
  `decideX(state) → action`, then a thin caller performs the action.
- **Time is an effect.** Take `now: number` / `nowMs` as a parameter for anything
  time-dependent (the reaper selectors and `core/scheduling/vm-view.ts` do — that's why they
  test on macOS without a live clock).
- **Config is an effect** (I/O + environment): read it once at the boundary and thread plain
  values down — `resolveNature(declared, config.execution, config.limits.max_storage_mib)`. Pure
  functions never read `config.yaml`.

## 3. Make illegal states unrepresentable; validate once at the edge

- Model results as **discriminated unions**, not `{ ok?, error? }` with both optional.
  `resolveNature` returns `{ ok: true; nature } | { ok: false; error }` — the compiler forces the
  check.
- **Parse untrusted input once**, at the HTTP/vsock boundary, into a trusted internal type.
  Downstream assumes soundness (the `runs` filter allowlist; tenant scoping enforced in SQL,
  never re-derived from a client field).
- **Closed unions catch typos at compile time.** `EventId = KnownEventId | \`x-${string}\``
  (`shared/contract/index.ts`) turns a mistyped event id into a build error. Use this for any
  fixed vocabulary.

## 4. Security is structural, not a check you remember to add

- **Enforce authority in the query, not the caller.** Tenant scoping lives inside the SQL
  (`WHERE tenant_id = ?`), so no path can forget it. Identity comes from the channel (the vsock
  socket *is* the VM's identity), never from a client-asserted field.
- **Fail closed.** An invalid nature is rejected at deploy (400) before a VM boots; a quarantined
  image refuses `POST /runs` (409) before boot. Make the unsafe path *unreachable*, not merely
  unlikely.
- **Never trust guest/client-supplied size or identity.** Size caps are re-checked host-side; the
  host stamps `trust: 'guest'` on guest telemetry. Treat every cross-boundary input as hostile.
- **Secrets/keys never enter logs, events, or errors.** Audit events carry ERNs only, asserted by
  a leak-scan test. If you emit structured data, add the test that proves no secret leaks.

## 5. Reliability: idempotent, best-effort where it must be, atomic where it counts

- **Best-effort for observability, strict for correctness.** `FileSink.emit` swallows write
  errors on purpose — *telemetry must never break the thing it instruments*. A slot release is
  the opposite: it is the single lock (`UPDATE … WHERE status='LEASED'`, `changes===1` wins).
  Know which kind each operation is.
- **Idempotent teardown.** `teardownVm` / `releaseJobResources` are safe to call twice (the GC
  monitor and a terminal op can both fire). A double-call must be a no-op, not a corruption.
- **Atomic artifact production.** Content-addressed images build temp → fsync → rename — never a
  half-written file at the real path. Anything another process reads must appear atomically.
- **Guard state transitions.** `PROVISIONING → RUNNING` is `UPDATE … WHERE status='PROVISIONING'`;
  `changes===0` means it was reaped — abort, don't resurrect.

## 6. Constants vs. config — three homes, one decision

**Ask: if this value is wrong, is it a *code bug* or an *operator/deploy choice*?**

- **Code bug → a `constants/` file.** Part of the program's meaning; changing it ships through
  review + tests; must be identical across environments. Status enums (`RUN_STATUS`,
  `DEPLOYMENT_STATUS`), routes (`ENDPOINTS`), messages (`ERROR_MESSAGES`), event ids, protocol op
  names, table names. `RUN_STATUS.PENDING = 'PENDING'` exists so a typo is a compile error.
- **Operator/deploy choice → `config.yaml`.** Legitimately differs per env or is tuned without a
  deploy: `pool_size`, `max_concurrent_vms`, `poll_interval_ms`, timeouts, `wall_cap_multiplier`,
  `deploy.max_image_bytes`, `warm.max_pinned_per_tenant`, all *paths*. Tell: the same binary must
  run correctly with a different value.
- **Platform default that config overrides → both.** A pure/offline package holds a
  `PLATFORM_DEFAULT_*` constant (`PLATFORM_DEFAULT_STORAGE_MIB = 25`); the host derives the
  authoritative value into `config.execution.*` at load and **config wins**. Gotcha: **never
  branch on the constant in orchestrator code** — read the config value; the constant is only the
  offline fallback.

Rules that follow:
1. **No magic literal in a branch or a message — ever.** Move every `'PENDING'`, `60`, path, and
   user-facing string to its home.
2. **Group constants by concern, near their consumer** (`orchestrator/constants/`,
   `cli/src/output/constants.ts`, `admin/constants.ts`) — not one god-file, not scattered.
3. **Config values carry the most operational risk** (they change without review) → they need the
   *most* explanatory comments. Put the *why-this-number* next to the value, as `config.yaml` does
   for `wall_cap_multiplier` ("Must be > 1, else the cap subsumes the silence window").
4. **Validate config at load, fail-closed.** Config is untrusted file input — a bad value stops
   startup with a clear message (admin config throws on missing `db.path`).
5. **Don't config-ify what can't safely vary.** If two deployments differing on this value would
   be *incompatible* rather than merely *tuned*, it's a constant (protocol ops, status enums).

**One-line test:** *would a correct change go through code review (→ `constants/`) or land in an
ops PR without touching logic (→ `config.yaml`)?*

## 7. DRY the rule, not the incident — use utilities, avoid duplication

- **Extract a shared helper the second time you write it**, into the nearest `utils/` or the
  owning module — not a copy-paste. But don't pre-abstract: a helper with one caller and no clear
  second is premature (KISS, §8).
- When you find yourself asserting the same thing two ways, unify the source, don't sync the copies.

## 8. KISS — keep it simple, and keep the types simple

- **Write the boring version.** No clever indirection, no framework where a function does. The
  reviewer should understand a function on first read. Fancy code is a maintenance cost you pay
  forever to save yourself minutes once.
- **Simple, readable TS types.** `interface`s and discriminated unions — *not* conditional/mapped-
  type gymnastics. A type a reader can't grasp at a glance is a liability. Reserve advanced types
  for genuinely reusable infra that earns it (the closed `EventId` union does); everywhere else,
  boring is correct.
- Prefer a plain function + a plain object over a class hierarchy, a generic over a type-level
  computation, an early return over nested conditionals.

## 9. Comments: two audiences, human and machine

The `FileSink` header (`shared/telemetry-file/index.ts`) is the standard:

- **Explain the non-obvious *why*** — the constraint, the race being guarded, the deliberate
  trade-off ("best-effort: never let a transcript-write failure break the caller"). Not *what* the
  line does; the code says that.
- **Keep a machine-readable identifier** on components addressed elsewhere (sinks, events, error
  codes): `machine-readable: telemetry.sink.file`, so tooling/search can join them.
- A comment that restates the code, or narrates your PR ("added this to fix…"), is noise the
  moment it merges. Delete it. Comments are for the next reader, not the reviewer.

## 10. Tests: cover the *decision* and the *invariant*, not the line count

Coverage % measures nothing. **Which logic is asserted** is everything.

- **Unit-test the pure core hard** — it holds the decisions and needs no setup: every branch of
  `resolveNature`, each fingerprint axis flip, `decideTerminalAction`
  across the lifecycle matrix.
- **Test the invariant, not the implementation.** Prefer "*a pinned VM is invisible to all three
  reaper selectors*" (a property that survives refactors) over "this line ran."
- **E2E earns its cost by proving the wiring** units can't: real cold-boot → warm-reuse → eviction,
  a real over-cap 429, the actual G1 race repeated enough to have caught the old timing bug. One
  good E2E through a real seam beats twenty re-asserting unit logic through more layers.
- **A test that needs a heavy mock is a design smell** pointing back at §1/§2 — the effect wasn't
  injected. Fix the seam, don't grow the mock.
- **Assert the observable contract:** DB state, the exact event id (hyphenated `vm.pinned-reused`,
  not the design doc's underscore), the status code — what a consumer actually depends on.

## 11. Challenge the plan

If a plan, ticket, or instruction looks wrong, inconsistent with the code, or in tension with these
rules — **stop and say so**, with the specific reason, before implementing. A plan is a hypothesis,
not a contract. Deviating to honor the plan's *intent* over its *letter* is correct when the code
proves the letter wrong (as with the Plan 04 stamp-all-runs decision); log the deviation and its
why. Silent compliance with a flawed step is the failure mode to avoid.

## 12. "Done" means you watched the running system do it

§10 is about what tests assert. This is about the step after: **an artifact is not evidence.** A
green suite, a clean `tsc`, a commit, and a file on disk all describe what you *wrote*. None of
them observe the deployed thing *working*. Report the difference honestly — never launder "the
code is written" into "the feature runs."

**The incident that produced this rule (2026-08-04, IMPL-03).** The deploy-build queue was
declared BUILT and production-verified on the strength of 2364 green tests and 5 commits. On the
live host it had never queued a single job: `outbox` did not exist, and the relay had been logging
`relation "outbox" does not exist` once a second the whole time. Each rule below is one link in
that chain.

- **A schema change is not applied until you SEE it applied.** The migration was committed and the
  test suite was green, because `makeTestDb` builds the schema by splitting the `.sql` on
  `-- migrate:down` and applying the up half **itself** — it never runs `dbmate`. So the migration
  *runner* had no test at all, and every "green" run proved only that the SQL parses. After any
  migration: query the live DB for the table/column, and confirm the **runner** applied it
  (`schema_migrations`), not just that your tests passed.
- **Restart the service and read its log before claiming anything.** A daemon loads schema,
  config, and wiring at boot; a change that only exists on disk has not run. Restart, then read
  the log **for a window that starts after the restart** — and confirm the process actually
  recycled (compare PID / `ExecMainStartTimestamp`), because a restart that silently no-ops leaves
  you reading the old process's output and calling it verification.
- **Re-run the suite after the LAST commit, not the last one you remember.** A fix landing on the
  branch can flip a test that was pinning the bug it fixed (see §10 characterization tests). Test
  results are only evidence for the tree that produced them.
- **A test that is green because it tested something else is worse than no test.** When a suite
  passes while production is broken, that is a finding: ask which path the test exercised and which
  path production uses. Different paths mean the risk is *unmeasured*, not low.
- **Verifying an installer means running it and checking it changed something.** `is-active`,
  exit 0, and a success line describe the script's *opinion*. Read the state back out of the system
  (the loaded unit, the row, the file) — the outbox unit drifted 10 days behind precisely because
  `systemctl enable --now` is a silent no-op on a running unit while still reporting success.
- **State what you did NOT verify.** "Tests pass; not yet exercised on the live host" is a complete
  and useful report. "Production-verified" when you only ran tests is a false one, and it is the
  claim that stops anyone else from looking.

**One-line test:** *can you name the command whose output you read, after the final change, on the
system you are making the claim about?* If not, you are reporting an artifact — say so.

---

## Quick checklist (paste into a review)

- [ ] Logic is a pure function unless it owns state/effect (§1); effects injected, not imported (§2)
- [ ] Untrusted input validated once at the edge into a discriminated-union result (§3)
- [ ] Authority enforced in the query; fails closed; no secret in logs/events (§4)
- [ ] Cleanup idempotent; artifacts atomic; transitions guarded; best-effort vs strict is deliberate (§5)
- [ ] No magic literals; value placed as constant vs config by the review-vs-ops test; config validated at load (§6)
- [ ] No duplicated rule/policy; shared helper has a real second caller (§7)
- [ ] Simplest version that works; types are interfaces/unions, not type-level tricks (§8)
- [ ] Comments explain *why* + machine-readable tag where addressed elsewhere; no PR narration (§9)
- [ ] Tests assert decisions/invariants/observable contract, not coverage; mocks minimal (§10)
- [ ] Anything off in the plan was challenged, not silently followed (§11)
- [ ] **Verified on the running system after the last commit** (§12): migration seen applied in the
      live DB · service restarted (PID changed) and its post-restart log read · suite re-run on the
      final tree · anything unverified stated as unverified
