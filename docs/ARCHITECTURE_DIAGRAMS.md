# Architecture Diagrams

## High-level architecture

```text
                 ┌──────────────────────────────────────────────┐
                 │               Web App (JS)                   │
                 │  MediaPipe Hands (browser, 30+ fps)          │
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
                                 │   FastAPI on localhost:8787  │
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
                 │   FastAPI on port 8788                       │
                 │   Validates strict JSON schema               │
                 │   Logs JSONL per verification                │
                 └───────────────┬──────────────────────────────┘
                                 │
                                 │  OpenAI compatible HTTP call
                                 │  /v1/chat/completions
                                 v
                 ┌──────────────────────────────────────────────┐
                 │      Cosmos Reason 2 NIM (DGX Spark)         │
                 │   Model inference service                    │
                 │   Returns strict JSON: intentional or not    │
                 └──────────────────────────────────────────────┘
```

## Confidence-gated runtime flow

This is the target decision logic once real confidence scores are available. Currently simplified to Safe Mode on/off toggle.

```text
Gesture Detected
  → local_confidence computed
        │
        ├── confidence ≥ 0.85 (HIGH)
        │     │
        │     └── Execute immediately via POST /execute
        │         Log: policy_path = "high_confidence_direct"
        │
        ├── 0.50 ≤ confidence < 0.85 (MEDIUM)
        │     │
        │     └── Call POST /verify with evidence window
        │           │
        │           ├── Cosmos approves (intentional=true, final_intent≠NONE)
        │           │     └── Execute via POST /execute
        │           │         Log: policy_path = "safe_mode_verified"
        │           │
        │           ├── Cosmos rejects (intentional=false OR final_intent=NONE)
        │           │     └── Do NOT execute
        │           │         Log: policy_path = "verifier_reject"
        │           │
        │           └── Timeout (no response within configured ms)
        │                 └── Do NOT execute
        │                     Log: policy_path = "verifier_timeout"
        │
        └── confidence < 0.50 (LOW)
              │
              └── Ignore entirely — no proposal, no Cosmos call
                  Log: (not logged, below detection threshold)
```

## Current runtime flow (Safe Mode toggle)

This is what the code actually implements today:

```text
Proposal Created (event_id)
        │
        v
Safe Mode ON?
  │ yes                          │ no
  v                              v
Call /verify                 Call /execute
  │                              │
  ├── timeout                    │
  │     └── Stop                 v
  │         Log: verifier_timeout   Execute
  │                              Log: unsafe_direct
  ├── response received
  │     │
  │     ├── intentional=true AND final_intent≠NONE
  │     │     └── Call /execute
  │     │         Log: safe_mode_verified
  │     │
  │     └── intentional=false OR final_intent=NONE
  │           └── Stop
  │               Log: verifier_reject
  │
  └── error
        └── Stop
            Log: verifier_error
```

## Deployment modes

### DGX-only mode (primary)

```text
┌─────────────────────── DGX Spark ───────────────────────┐
│                                                          │
│  USB Webcam                                              │
│      │                                                   │
│      v                                                   │
│  Chromium Browser                                        │
│  ┌──────────────┐                                       │
│  │  Web App      │──POST /execute──→ Executor (:8787)   │
│  │  :5173        │                   │                   │
│  │  MediaPipe JS │                   └──→ xdotool       │
│  │               │                       → GNOME desktop│
│  │               │──POST /verify──→ Verifier (:8788)    │
│  └──────────────┘                   │                   │
│                                      └──→ Cosmos NIM    │
│                                          (localhost)     │
└──────────────────────────────────────────────────────────┘
```

### Mac + DGX mode (development)

```text
┌──────── MacBook Air ────────┐    ┌────── DGX Spark ──────┐
│                              │    │                        │
│  Built-in Webcam             │    │                        │
│      │                       │    │                        │
│      v                       │    │                        │
│  Chrome Browser              │    │                        │
│  ┌──────────────┐           │    │                        │
│  │  Web App      │──execute──│──→ │ (not needed)          │
│  │  :5173        │  :8787    │    │                        │
│  │  MediaPipe JS │  local    │    │                        │
│  │               │──verify───│──→ │ Verifier (:8788) ──→  │
│  └──────────────┘           │    │   Cosmos NIM           │
│                              │    │   (localhost on DGX)   │
│  Executor (:8787)            │    │                        │
│  └──→ osascript              │    │                        │
│      → macOS desktop         │    │                        │
└──────────────────────────────┘    └────────────────────────┘
```

**Requirement:** Web app verifier URL must be configurable to point at DGX IP instead of localhost.

### Stub mode (offline development)

Same layout as either mode above, but verifier uses `stub_logic.py` (always approve or force-reject) instead of calling Cosmos NIM. No DGX Spark required.

## Option 2: Teacher-Student Loop (placeholder — to be filled when implemented)

```text
┌─────────────────── Runtime Loop ───────────────────────┐
│                                                         │
│  Gesture Detected → Local Confidence (student model)    │
│       │                                                 │
│       ├── HIGH → Execute directly                       │
│       │                                                 │
│       ├── MEDIUM → Cosmos Verifier (teacher) ──┐       │
│       │       │                                 │       │
│       │       ├── Approved → Execute            │       │
│       │       └── Rejected → Block              │       │
│       │                                         │       │
│       └── LOW → Ignore                          │       │
│                                                 │       │
│  All events logged to JSONL ◄───────────────────┘       │
│                                                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        v
┌─────────────── Periodic Training ──────────────────────┐
│                                                         │
│  1. Extract features + Cosmos labels from JSONL         │
│  2. Train lightweight student classifier                │
│  3. Evaluate on frozen calibration set                  │
│  4. If improved AND no regression → deploy new student  │
│  5. Student provides better confidence scores           │
│  6. Fewer cases fall in MEDIUM band                     │
│  7. Fewer Cosmos calls needed over time                 │
│                                                         │
│  Cosmos teaches → Student learns → System improves      │
│  Cosmos is never fine-tuned — only the student trains   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
