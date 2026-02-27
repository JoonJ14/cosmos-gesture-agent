# Latency and Ambiguous Case Policy

## Critical dependency: Cosmos Reason 2 latency on DGX Spark

The entire demo architecture depends on how fast Cosmos responds. This has NOT been measured yet.

- **If < 300ms round-trip:** Live gating is viable for every ambiguous case. The user feels a slight delay but it's acceptable for "medium confidence" gestures.
- **If 300–500ms:** Live gating works but only for the ambiguous band. High-confidence gestures must execute directly.
- **If > 500ms:** Live gating feels sluggish. Lean toward executing locally and using Cosmos for offline evaluation/labeling only. The demo story shifts from "Cosmos gates actions" to "Cosmos improves the system over time."

**First priority when DGX Spark is available:** Run Cosmos Reason 2 NIM, send a test request with 8 base64 frames, and measure latency. This determines the demo architecture.

## Policy modes

### 1) Synchronous verification
- Every proposal blocks on verifier response.
- Executor is called only when verifier returns `intentional=true` and `final_intent != NONE`.
- Highest safety, higher latency.

### 2) Offline periodic labeling
- Runtime can execute from local proposer policy.
- Sampled events and ambiguous events are sent to teacher verifier offline.
- Used for model improvement and policy calibration, not immediate gating.

### 3) Default hybrid policy (current target)
- Safe Mode ON: synchronous verifier gate with timeout.
- If verifier timeout occurs, do **not** execute.
- Log `policy_path=verifier_timeout`.
- If verifier rejects (`final_intent=NONE` or `intentional=false`), do not execute.
- Safe Mode OFF: direct execution path (for controlled testing only).

## stale response handling
- Each proposal is tracked by `event_id` and lifecycle state.
- Verifier responses are applied only if the event is still current and not superseded.
- If an event transitions to `timeout`, `rejected`, or superseded, any eventual verifier response is ignored.
- This prevents late verifier completions from causing stale execution.

## debounce and merge behavior
- Merge window: `250ms`.
- If a proposal arrives within `250ms` of the last same-intent proposal and there is an in-flight verify for that intent:
  - no new `event_id` is created
  - the existing in-flight `event_id` is reused
  - event timestamps are updated (`proposal_last_updated`)
  - `merge_count` is incremented and logged
- This reduces duplicate verifier calls and event churn.

## superseded event rule
- Precedence rule: **newest non-superseded event wins**.
- When a newer proposal is accepted as a new event while an older event is verifying, the older event is marked superseded.
- Superseded events are treated as non-executable.
- If a superseded event later receives verifier output, that response is ignored.

## guarantee: no late actions after timeout
- `timeout` is terminal.
- After timeout, the web runtime never sends `/execute` for that `event_id`.
- The execution guard also blocks events in `rejected` and superseded states.
- Result: no late action is triggered by verifier responses that arrive after timeout.

## Ambiguity handling
Treat low-confidence or context-ambiguous actions as reject/hold paths by default. This is critical for hard negatives such as grooming, reaching, and conversation gestures.

## Required instrumentation fields
Each event should be traceable by `event_id` with at least:
- `proposal_start_ts`
- `verifier_request_sent_ts`
- `verifier_response_received_ts`
- `executor_request_sent_ts`
- `executor_response_received_ts`
- `policy_path` (e.g., `safe_mode_verified`, `verifier_reject`, `verifier_timeout`, `unsafe_direct`, `stale_verifier_response_ignored`)
- `merge_count`
- verifier `latency_ms`
- executor `latency_ms`

These fields support latency budgets, timeout tuning, and disagreement analysis for Option 2.
