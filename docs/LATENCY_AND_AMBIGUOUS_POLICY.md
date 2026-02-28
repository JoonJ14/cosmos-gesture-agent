# Latency and Ambiguous Case Policy

## Measured latency: Cosmos Reason 2 on DGX Spark GB10

Latency was measured on 2026-02-27 using vLLM v0.16.0 serving nvidia/Cosmos-Reason2-8B
at bfloat16 on the GB10 (sm_121a, CUDA 13.0, ~14 tok/s warm). Full results in
`data/cosmos_latency_tests.md`.

| Scenario | Latency |
|----------|---------|
| Text only (warm) | 3.4s |
| 1 frame + verify prompt | 5.8s |
| 4 frames + verify prompt | 7.0s |
| 8 frames + verify prompt | 8.4s |
| Stub (no Cosmos) | 19ms |

**Conclusion:** 5.8–8.4s round-trip rules out synchronous verification in the live
gesture path. A user who swipes their hand will wait 7 seconds before seeing any
desktop action — this is not acceptable for a gesture control system.

## Policy modes

### 1) Async verification (default mode)

The live gesture path executes immediately based on local confidence. Cosmos
verification runs in the background after execution and its output is logged.

```
Gesture detected → local_confidence computed
    │
    ├── confidence ≥ HIGH threshold → Execute immediately
    │       → Queue async Cosmos verification
    │       → Log Cosmos result when it arrives (~7s later)
    │
    ├── MEDIUM ≤ confidence < HIGH  → Execute immediately
    │       → Queue async Cosmos verification
    │       → Log Cosmos result when it arrives
    │
    └── confidence < LOW threshold  → Ignore (no execution, no Cosmos call)

Async verification (background, after execution):
    → Send frames + landmarks to verifier → Cosmos NIM
    → Log result to JSONL: intentional, final_intent, reason_category, rationale
    → If Cosmos disagrees with local decision → log as disagreement
    → Disagreements become training signal for Option 2 teacher-student loop
```

**Why async:** The user gets immediate feedback. Cosmos correctness improves the
system over time without being in the hot path.

**Logging field:** `policy_path = async_verified` (Cosmos result arrived),
`policy_path = async_queued` (Cosmos not yet responded when event closed).

### 2) Safe Mode (synchronous, opt-in for demo)

Safe Mode is a demo-only option that blocks execution until Cosmos responds (~7s wait).
It exists to show Cosmos reasoning in real time — the judge can see the rationale appear
before the desktop action fires.

Safe Mode is **not suitable for normal use** due to the 7s latency. It is toggled via
the Safe Mode checkbox in the web UI (default: off in production, on during demo).

```
Gesture detected → local_confidence computed
    │
    ├── confidence ≥ LOW → Call Cosmos verifier (BLOCKS)
    │       │
    │       ├── Cosmos approves (intentional=true, final_intent≠NONE) → Execute
    │       ├── Cosmos rejects (intentional=false or final_intent=NONE) → Do NOT execute, log rejection
    │       └── Cosmos timeout → Do NOT execute, log timeout
    │
    └── confidence < LOW → Ignore
```

**Timeout policy in Safe Mode:** If verifier does not respond within the configured
timeout (default 15s, configurable via UI), the gesture is NOT executed. This prevents
late verification from causing stale actions.

**Logging field:** `policy_path = safe_mode_verified`, `policy_path = safe_mode_rejected`,
`policy_path = safe_mode_timeout`.

### 3) Stub mode (offline development, no DGX)

Verifier uses stub logic (always approve, or force-reject when `force_reject=true`).
Used when DGX Spark is not accessible. Toggle via `NIM_ENABLED` env var on the
verifier service (`NIM_ENABLED=0` = stub, `NIM_ENABLED=1` = real Cosmos call).

## Stale response handling

Each proposal is tracked by `event_id` and lifecycle state.

- Verifier responses are applied only if the event is still current and not superseded.
- If an event transitions to `timeout`, `rejected`, or superseded, any eventual verifier
  response is ignored.
- This prevents late verifier completions from causing stale execution.
- In async mode, a Cosmos response arriving after the event is closed is still logged
  (for training data) but does not trigger any action.

## Debounce and merge behavior

Merge window: **250ms**.

If a proposal arrives within 250ms of the last same-intent proposal and there is an
in-flight verify for that intent:
- no new `event_id` is created
- the existing in-flight `event_id` is reused
- event timestamps are updated (`proposal_last_updated`)
- `merge_count` is incremented and logged

This reduces duplicate verifier calls and event churn. In async mode, only one
background Cosmos call fires per merged event group.

## Superseded event rule

Precedence rule: **newest non-superseded event wins**.

When a newer proposal is accepted as a new event while an older event is verifying,
the older event is marked superseded. Superseded events are treated as non-executable.
If a superseded event later receives verifier output, that response is logged but ignored
for execution purposes (it is still useful as training data).

## Guarantee: no late actions after timeout

`timeout` is terminal.

- After timeout, the web runtime never sends `/execute` for that `event_id`.
- The execution guard also blocks events in `rejected` and superseded states.
- In async mode, the execution has already happened; late Cosmos responses only affect
  the log record, never trigger a second execution.

## Ambiguity handling

In async mode, ambiguity is resolved after the fact: Cosmos labels the event as
intentional or incidental, and the label is stored. Over time, disagreements between
the local model and Cosmos identify the boundary of the local model's reliability and
feed the Option 2 improvement loop.

In Safe Mode, ambiguity is resolved before execution — Cosmos is the gate.

Hard negatives (self-grooming, reaching, conversation gestures) are the primary
source of false positives from the local detector. Cosmos correctly identifies these
from visual context that kinematics alone cannot encode. See `data/cosmos_latency_tests.md`
for measured discrimination accuracy.

## Required instrumentation fields

Each event should be traceable by `event_id` with at least:

- `proposal_start_ts`
- `verifier_request_sent_ts`
- `verifier_response_received_ts` (may be null if async response not yet received)
- `executor_request_sent_ts`
- `executor_response_received_ts`
- `policy_path` (e.g., `async_verified`, `async_queued`, `safe_mode_verified`,
  `safe_mode_rejected`, `safe_mode_timeout`, `stub_approved`, `stale_verifier_response_ignored`)
- `merge_count`
- verifier `latency_ms`
- executor `latency_ms`

These fields support latency analysis, timeout tuning, and disagreement tracking for
Option 2.
