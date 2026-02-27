# Architecture diagrams

## High level architecture

```text
                 ┌──────────────────────────────────────────────┐
                 │               Web App (JS)                   │
                 │  MediaPipe Hands (browser)                   │
                 │  Gesture state machine + confidence          │
                 │  Ring buffer: last ~1s frames                │
                 │  UI overlay + event log view                 │
                 └───────────────┬──────────────────────────────┘
                                 │
                 proposes intent │  POST /execute
                 and decides     │  { intent, event_id }
                 whether to      v
                 verify          ┌──────────────────────────────┐
                                 │      Action Executor (PY)    │
                                 │   FastAPI on localhost       │
                                 │   Reads actions.yaml         │
                                 │   Sends OS key events        │
                                 │   Linux GNOME X11: xdotool   │
                                 │   macOS: osascript or Quartz │
                                 │   Logs JSONL per action      │
                                 └──────────────────────────────┘

                                 │  only for ambiguous cases
                                 │  POST /verify
                                 │  { proposed_intent, frames[], landmark_summary, event_id }
                                 v
                 ┌──────────────────────────────────────────────┐
                 │           Cosmos Verifier (PY)               │
                 │   FastAPI on DGX Spark                       │
                 │   Validates strict JSON schema               │
                 │   Logs JSONL per verification                │
                 └───────────────┬──────────────────────────────┘
                                 │
                                 │  OpenAI compatible HTTP call
                                 │  /v1/chat/completions
                                 v
                 ┌──────────────────────────────────────────────┐
                 │      Cosmos Reason 2 NIM (DGX Spark)          │
                 │   Model inference service                     │
                 │   Returns strict JSON: intentional or not     │
                 └──────────────────────────────────────────────┘
```

## Runtime decision flow

```text
Runtime decision flow

Web App detects candidate gesture
        │
        ├─ if local_confidence >= HIGH:
        │        execute immediately via Action Executor
        │        POST /execute { intent, event_id }
        │
        ├─ if LOW < local_confidence < HIGH:
        │        ambiguous policy applies
        │        POST /verify { proposed_intent, frames[], landmark_summary, event_id }
        │        Cosmos Verifier validates schema and calls Cosmos Reason 2 NIM
        │        if intentional and final_intent != NONE:
        │             execute via Action Executor
        │             POST /execute { intent, event_id }
        │        else:
        │             do not execute
        │
        └─ if local_confidence <= LOW:
                 ignore
```

## Deployment modes

```text
Deployment modes

Mode 1: Split deployment (preferred)
Mac Air: Web App + Action Executor  ───────network──────>  DGX: Verifier + Cosmos Reason 2 NIM
- Web runs MediaPipe and local heuristic confidence gating.
- Executor runs locally to press OS keys.
- Ambiguous cases call Verifier on DGX.
- Verifier calls Cosmos Reason 2 NIM via OpenAI compatible HTTP /v1/chat/completions.

Mode 2: All on DGX Spark (single box)
DGX Spark: Web App + Action Executor + Verifier + Cosmos Reason 2 NIM
- Useful for benchmarking and debugging.
- Web may still be accessed remotely, but all services execute on the same host.

Notes
- Current verifier implementation may use stub logic, but the target architecture includes the Cosmos Reason 2 NIM call.
- Keep HTTP boundaries between Web, Verifier, and Executor the same in both modes.
```

## Option 2 placeholder

```text
Teacher-student future path
- Student: local gesture proposer in web runtime
- Teacher: Cosmos Verifier calling Cosmos Reason 2 NIM for ambiguous / sampled events
- Output: strict JSON labels logged for periodic retraining
```
