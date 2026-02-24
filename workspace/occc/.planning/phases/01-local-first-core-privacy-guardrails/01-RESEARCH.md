# Phase 1: Local-First Core & Privacy Guardrails - Research

**Researched:** 2026-02-24
**Domain:** Local-first privacy controls, consent gating, transport security, and data minimization
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Remote AI Opt-In UX
- Remote inference is offered only when local confidence is low.
- Consent is scoped per workspace/project (not global-only and not per-request).
- If user denies remote inference, Nexus-Sync returns a local-only result and explicitly notes remote could improve the output.
- Users can revoke or change consent from a central Privacy Settings surface with one-click revoke.

### Data Visibility & User Trust Signals
- Product includes a dedicated Privacy Center plus lightweight inline badges.
- Default provenance on generated summaries/answers includes source links, timestamps, and connector label.
- Remote inference events are visible in a filterable audit log.
- Any response that used remote inference must show an explicit badge and short reason.

### Claude's Discretion
- Exact UI wording and visual style for consent prompts, badges, and Privacy Center layout.
- Threshold logic used to determine "local confidence is low".
- Final filter taxonomy for the audit log.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRIV-01 | Raw content processing and embeddings run locally by default. | Default policy engine set to `LOCAL_ONLY`; local embed/index pipeline is the normal path; remote path cannot be selected unless explicit workspace consent exists. |
| PRIV-02 | Any remote inference path must use encrypted transit and explicit opt-in. | Project-scoped consent state + revocation UX; remote client hard-enforces HTTPS and certificate validation; all remote events logged with reason and timestamp. |
| PRIV-03 | System stores only minimum metadata required for retrieval and linking. | Data classification matrix + allowlist schema; metadata-first persistence; avoid raw payload retention except explicit, policy-bounded debug snapshots. |
</phase_requirements>

## Summary
Phase 1 should be planned as a policy and enforcement phase, not a model-quality phase. The key deliverable is a hard gate that makes local processing the invariant, with remote inference disabled by default and only reachable through explicit per-project opt-in.

Plan this phase around four implementation seams: processing policy, consent state, secure remote transport, and audit/provenance visibility. If these are isolated behind interfaces now, later phases (connectors/summaries/linking) can consume privacy-safe defaults automatically instead of duplicating checks.

Data minimization should be encoded in storage contracts early (what fields are allowed, retained, and queryable), otherwise retention creep will happen as features ship.

**Primary recommendation:** Implement a single Privacy Guard module that all inference/embedding calls go through, and make bypass impossible by construction.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tauri | v2 | Desktop app security boundary + capabilities | Capability-based permissions align with least-privilege local-first desktop model. |
| Rust `reqwest` | 0.12.x | Remote HTTP client for opt-in inference | Supports HTTPS-only and certificate validation controls in one client surface. |
| SQLite | 3.x (WAL mode) | Local metadata/audit persistence | Reliable embedded store with WAL for concurrent read/write and crash resilience. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `keyring` crate | current stable | OS credential vault storage for tokens/keys | Store remote provider credentials and encryption keys without plaintext files. |
| `sqlcipher` | 4.x | Encrypt sensitive local DB data at rest | Use when local threat model requires encrypted DB files beyond OS-level disk encryption. |
| `tracing` ecosystem | current stable | Structured, redactable local audit/event logs | Use for consistent remote-use evidence and troubleshooting without leaking content. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite + optional SQLCipher | Plain SQLite only | Simpler ops, weaker at-rest protection for sensitive local artifacts. |
| Tauri capability gating | App-level custom flags only | Faster initially, but easier to bypass and harder to audit. |
| Reqwest HTTPS-only policy | Ad-hoc URL checks | More fragile, higher chance of accidental insecure transport. |

**Installation:**
```bash
# Planning phase only: no mandatory package install required yet.
# Capture dependency decisions in implementation tasks before coding.
```

## Architecture Patterns

### Recommended Project Structure
```
privacy/
├── policy/                 # local vs remote execution policy and confidence thresholds
├── consent/                # per-project opt-in state, revoke flows, persistence
├── transport/              # remote client factory with HTTPS/cert hardening
├── audit/                  # remote-use event logging, filtering, provenance records
└── minimization/           # storage allowlists, retention and redaction helpers
```

### Pattern 1: Single Privacy Gate for all inference paths
**What:** Route every content-processing and inference request through one guard that resolves execution mode.
**When to use:** Any operation that could use local or remote model execution.
**Example:**
```typescript
// Source: requirements + context contract
type ProcessingMode = 'LOCAL_ONLY' | 'REMOTE_ALLOWED';

interface ConsentStore {
  hasRemoteOptIn(projectId: string): Promise<boolean>;
}

async function resolveMode(projectId: string, localConfidence: number, consent: ConsentStore): Promise<ProcessingMode> {
  const optedIn = await consent.hasRemoteOptIn(projectId);
  if (!optedIn) return 'LOCAL_ONLY';
  return localConfidence < 0.55 ? 'REMOTE_ALLOWED' : 'LOCAL_ONLY';
}
```

### Pattern 2: Hardened remote transport factory
**What:** Build remote clients from one factory that enforces HTTPS and valid certs.
**When to use:** Any outbound request in the remote inference path.
**Example:**
```rust
// Source: reqwest docs (https_only + cert validation controls)
let client = reqwest::Client::builder()
    .https_only(true)
    .build()?;
```

### Pattern 3: Metadata allowlist before persistence
**What:** Persist only retrieval/linking-required metadata and references.
**When to use:** Every ingestion/processing write path.
**Example:**
```typescript
const ALLOWED_FIELDS = ['source_id', 'thread_id', 'timestamp', 'connector', 'entity_type'] as const;
```

### Anti-Patterns to Avoid
- **Split privacy checks across features:** creates bypass risk and inconsistent user guarantees.
- **Global-only consent:** violates locked decision requiring workspace/project scope.
- **Storing raw payloads by default:** conflicts with PRIV-03 and expands breach surface.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TLS correctness | Custom cert/HTTPS logic | `reqwest` TLS defaults + `https_only(true)` | Mature libraries handle edge cases and verification behavior safely. |
| Secret storage | Homegrown encrypted file format | OS keychain via `keyring` | Avoids key-management mistakes and plaintext exposure. |
| Desktop permission model | Custom permission matrix | Tauri v2 capability permissions | Built-in least-privilege mechanism with clearer auditability. |

**Key insight:** Privacy failures usually come from inconsistent enforcement boundaries, not missing cryptography primitives.

## Common Pitfalls

### Pitfall 1: Remote path reachable without explicit consent
**What goes wrong:** Feature code calls remote inference directly when local confidence is low.
**Why it happens:** No central gate; convenience shortcuts appear over time.
**How to avoid:** Enforce a single privacy gateway and ban direct remote client usage.
**Warning signs:** Remote calls appear in logs for projects without opt-in records.

### Pitfall 2: Insecure transport regressions
**What goes wrong:** HTTP endpoints or invalid cert acceptance slip into config/debug flows.
**Why it happens:** Environment-specific overrides bypass production settings.
**How to avoid:** Enforce HTTPS-only in client factory and block insecure overrides in release builds.
**Warning signs:** Non-HTTPS URLs accepted, or `danger_accept_invalid_certs` enabled.

### Pitfall 3: Data-retention creep
**What goes wrong:** Extra raw fields are stored “temporarily” and never removed.
**Why it happens:** No schema-level allowlist/review gate.
**How to avoid:** Add a storage classification policy and fail writes for disallowed fields.
**Warning signs:** Tables/files include raw body text where only IDs/timestamps are needed.

### Pitfall 4: Trust UI and backend policy diverge
**What goes wrong:** UI claims local-only while backend route used remote.
**Why it happens:** Provenance/audit fields not wired into response contract.
**How to avoid:** Attach mode/reason metadata to every generated response and surface it in badges + Privacy Center.
**Warning signs:** Missing remote-use badge for responses that triggered remote audit events.

## Code Examples

Verified patterns from official sources:

### Enforce HTTPS-only remote requests
```rust
// Source: https://docs.rs/reqwest/latest/reqwest/struct.ClientBuilder.html
let client = reqwest::Client::builder()
    .https_only(true)
    .build()?;
```

### Keep certificate validation enabled
```rust
// Source: https://docs.rs/reqwest/latest/reqwest/struct.ClientBuilder.html
let client = reqwest::Client::builder()
    .danger_accept_invalid_certs(false)
    .build()?;
```

### SQLite WAL for reliable local concurrent access
```sql
-- Source: https://sqlite.org/wal.html
PRAGMA journal_mode=WAL;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Broad app-level permissions | Capability-scoped desktop permissions (Tauri v2) | Tauri v2 era | Better least-privilege enforcement for local/remote boundaries. |
| Implicit cloud fallback | Explicit per-project remote opt-in + revocation | Privacy-first product patterns (current) | User trust and compliance posture improve; behavior is auditable. |
| Store raw payloads “just in case” | Metadata-first persistence with policy allowlists | Modern privacy-by-design expectations | Reduced breach/compliance surface and lower retention risk. |

**Deprecated/outdated:**
- “Remote by default with optional local mode”: conflicts with this phase’s locked decisions and requirements.
- Accepting invalid TLS certs in non-test paths: creates silent downgrade risk.

## Open Questions

1. **What is the exact confidence threshold strategy for “local confidence is low”?**
   - What we know: Threshold logic is discretionary.
   - What's unclear: Static threshold vs per-feature/per-model calibration.
   - Recommendation: Start with fixed threshold + audit metrics, then tune with real false-positive/false-negative data.

2. **Should any raw payload be retained for debugging?**
   - What we know: PRIV-03 requires minimum metadata only.
   - What's unclear: Whether limited-time encrypted debug snapshots are acceptable.
   - Recommendation: Default to no raw retention; if needed, require explicit diagnostic mode with TTL and user-visible notice.

3. **How granular should audit-log filters be in v1?**
   - What we know: Filter taxonomy is discretionary.
   - What's unclear: Minimum useful dimensions for troubleshooting and trust.
   - Recommendation: Start with `project`, `mode(local/remote)`, `reason`, `time range`, `connector`, then expand only on observed need.

## Sources

### Primary (HIGH confidence)
- Requirements and context docs in-repo:
  - `.planning/phases/01-local-first-core-privacy-guardrails/01-CONTEXT.md`
  - `.planning/REQUIREMENTS.md`
  - `.planning/ROADMAP.md`
  - `.planning/research/STACK.md`
  - `.planning/research/ARCHITECTURE.md`
  - `.planning/research/PITFALLS.md`
- Reqwest API docs (`ClientBuilder`): https://docs.rs/reqwest/latest/reqwest/struct.ClientBuilder.html
- SQLite WAL documentation: https://sqlite.org/wal.html
- Tauri v2 capabilities permissions: https://v2.tauri.app/security/capabilities/

### Secondary (MEDIUM confidence)
- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- OWASP User Privacy Protection Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/User_Privacy_Protection_Cheat_Sheet.html

### Tertiary (LOW confidence)
- SQLCipher landing docs (feature-level confirmation only): https://www.zetetic.net/sqlcipher/

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - aligned with existing project research artifacts and official docs for key controls.
- Architecture: HIGH - directly constrained by locked decisions + requirement mapping.
- Pitfalls: HIGH - corroborated by existing project pitfalls register and OWASP guidance.

**Research date:** 2026-02-24
**Valid until:** 2026-03-26
