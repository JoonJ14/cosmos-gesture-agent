# Build Status & Session Handoff

## AI agent instructions
- **Read this file at the start of every session before doing anything else**
- **Read `docs/PROJECT_CONTEXT.md` for the full problem framing and design rationale**
- **Read `docs/GESTURE_DETECTION.md` before implementing gesture recognition**
- **Update this file only when the user explicitly asks to update the documents**

## Session handoff note

**Last updated**: 2026-02-27. Cosmos Reason 2 is running on DGX Spark. Discrimination
test passed (3/3). Architecture shifted to async verification based on measured latency.

**Current state**: Cosmos Reason 2 serves at `http://localhost:8000` via vLLM. The
verifier service (`:8788`) calls it with `NIM_ENABLED=1`. Discrimination tests show
correct accept/reject with valid schema output. Latency is 5.8–8.4s per call — too
slow for live gating, so the architecture is now async-first. Still no real gesture
detection in the web app, no frame ring buffer, no real data flowing from browser to
verifier.

**Next priority:**
1. Implement `proposeGestureFromLandmarks()` in `web/src/gesture.js` with real swipe/hold detection
2. Build the frame ring buffer in `web/src/main.js` — circular buffer of ~30 frames, export 4–8 evenly-spaced JPEGs
3. Wire real evidence (frames + landmark summary + local_confidence) to the verifier POST
4. Implement async verification path in the web app state machine
5. End-to-end demo: gesture → execute immediately → Cosmos verifies async → log result

---

## Build checklist

### Done — scaffold
- [x] Web app: MediaPipe Hands running in browser, canvas overlay, Safe Mode toggle, verifier timeout input
- [x] Event state machine: PROPOSED → VERIFYING → APPROVED → EXECUTED with merge/supersede/timeout
- [x] Verifier service (FastAPI :8788) — stub logic, schema validation, JSONL logging
- [x] Executor service (FastAPI :8787) — xdotool (Linux) / osascript (macOS), JSONL logging
- [x] `shared/schema.json` — strict 7-field verifier response contract
- [x] `executor/actions.yaml` — OS key mappings (linux/macos)
- [x] Shell scripts: `run_executor.sh`, `run_verifier.sh`, `run_web.sh`
- [x] Smoke test: `scripts/smoke_test.sh`
- [x] Design docs capturing full architecture, prompt, schema, latency policy, Option 2 risks
- [x] Keyboard test stubs (keys 1–4) for triggering intents without gesture detection

### Done — Cosmos NIM integration
- [x] **Cosmos Reason 2 running on DGX Spark** — vLLM v0.16.0, localhost:8000, model nvidia/cosmos-reason2-8b
- [x] **Verifier URL configurable** — `?verifier=http://dgx-ip:8788` query param + UI text input
- [x] **Verifier nim_logic.py** — real Cosmos call, code fence stripping, missing-field check, env-configurable
- [x] **NIM_ENABLED toggle** — `NIM_ENABLED=1` routes to Cosmos; `NIM_ENABLED=0` uses stub (19ms)
- [x] **Discrimination test passed** — 3/3 correct (intentional swipe ACCEPT, head scratch REJECT, conversation wave REJECT)
- [x] **Latency measured and documented** — 5.8–8.4s; see `data/cosmos_latency_tests.md`
- [x] **Architecture decision made** — async verification is default; Safe Mode retained for demo

### Critical path — not built yet
- [ ] **Gesture recognition** — `web/src/gesture.js:proposeGestureFromLandmarks()` returns `null`.
  Needs landmark-to-intent classification with the thresholds in `docs/GESTURE_DETECTION.md`:
  swipe ≥30% frame width in 0.4–0.9s, palm hold ≥0.3s, palm→fist transition, 1.5s cooldown.
- [ ] **Frame ring buffer** — No frame capture exists. Need a circular buffer of ~30 frames
  (~1s) that can export 4–8 evenly-spaced base64 JPEGs on demand. Quality=50 JPEG, ~8 KB/frame.
- [ ] **Real data to verifier** — Web app sends only hardcoded `local_confidence: 0.7` and no
  frames/landmarks. Must pass real evidence windows.
- [ ] **Async verification path** — Web app state machine currently blocks on verifier response
  (Safe Mode only). Need a non-blocking path: execute immediately, fire-and-forget verify,
  log result when Cosmos responds.
- [ ] **Real local confidence** — Compute from detection quality, displacement margin,
  temporal fit (see `docs/GESTURE_DETECTION.md`).

### Post-core / nice-to-have
- [ ] Three-tier confidence routing: HIGH → direct execute, MEDIUM → async verify, LOW → ignore
- [ ] Event log UI panel in the browser showing Cosmos rationale when async result arrives
- [ ] Evaluation harness for hard negatives (record clips, run Cosmos offline, produce metrics table)
- [ ] Option 2 teacher-student loop implementation
- [ ] Demo video production (under 3 minutes)
- [ ] Final README polish for competition submission

---

## Key files

| File | Role | Status |
|------|------|--------|
| `web/src/gesture.js` | MediaPipe setup + gesture recognition | **TODO: detection returns null** |
| `web/src/main.js` | Event state machine, safe mode, merge/supersede | Done (needs async path) |
| `web/src/api.js` | HTTP client for verifier and executor | Done (URLs configurable) |
| `web/src/overlay.js` | Canvas hand landmark drawing | Done |
| `verifier/verifier/main.py` | FastAPI /verify, schema validation, JSONL log | Done |
| `verifier/verifier/nim_logic.py` | Real Cosmos NIM call via vLLM | **Done — wired and tested** |
| `verifier/verifier/stub_logic.py` | Stub verifier (always approve/force reject) | Done (kept for NIM_ENABLED=0) |
| `verifier/verifier/schema_validate.py` | JSON Schema validation | Done |
| `executor/executor/main.py` | FastAPI /execute, xdotool/osascript, JSONL log | Done |
| `executor/actions.yaml` | OS key mappings per intent | Done |
| `shared/schema.json` | Strict verifier response schema | Done |
| `data/cosmos_latency_tests.md` | Measured latency + discrimination test results | Done |

---

## Documentation index

| Document | Purpose |
|----------|---------|
| `docs/PROJECT_CONTEXT.md` | Problem statement, solution thesis, gestures, hard negatives, platforms, competition context |
| `docs/SYSTEM_ARCHITECTURE.md` | Components, APIs, deployment modes, data flow, logging |
| `docs/GESTURE_DETECTION.md` | Gesture detection algorithm spec with thresholds and state machines |
| `docs/COSMOS_PROMPT_AND_SCHEMA.md` | Cosmos prompt template, schema, API call construction, why-Cosmos framing |
| `docs/LATENCY_AND_AMBIGUOUS_POLICY.md` | Measured latency, async vs safe-mode policy, merge/supersede rules |
| `docs/OPTION2_RISKS_AND_MITIGATIONS.md` | Teacher-student loop failure modes and safeguards |
| `docs/ARCHITECTURE_DIAGRAMS.md` | ASCII diagrams for architecture, runtime flow, deployment modes |
| `docs/STATUS.md` | This file — build state, priority, session handoff |
| `data/cosmos_latency_tests.md` | Cosmos latency measurements and discrimination test results |

---

## Quick start (3 terminals)

```bash
./scripts/run_executor.sh   # :8787
./scripts/run_verifier.sh   # :8788  (NIM_ENABLED=0 uses stub)
./scripts/run_web.sh        # :5173 — open in browser
```

To use real Cosmos (DGX Spark, vLLM running at localhost:8000):
```bash
NIM_ENABLED=1 COSMOS_NIM_URL=http://localhost:8000 ./scripts/run_verifier.sh
```

Test: keys `1`–`4` → OPEN_MENU / CLOSE_MENU / SWITCH_RIGHT / SWITCH_LEFT.
Safe Mode ON routes through verifier first (blocks ~7s with NIM, 19ms with stub).
Safe Mode OFF executes directly without verifier.

```bash
# Health checks
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8788/health
curl -s http://127.0.0.1:8000/health  # vLLM (DGX only)

# Verifier with real Cosmos (NIM_ENABLED=1 must be set)
curl -s -X POST http://127.0.0.1:8788/verify \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"test","proposed_intent":"SWITCH_RIGHT","local_confidence":0.73}'
```
