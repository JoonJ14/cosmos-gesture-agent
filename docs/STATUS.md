# Build Status & Session Handoff

## AI agent instructions
- **Read this file at the start of every session before doing anything else**
- **Read `docs/PROJECT_CONTEXT.md` for the full problem framing and design rationale**
- **Read `docs/GESTURE_DETECTION.md` before implementing gesture recognition**
- **Update this file only when the user explicitly asks to update the documents**

## Session handoff note

**Last updated**: 2026-02-27. Initial scaffold complete. Documentation updated to capture full design context.

**Current state**: All three services run and communicate. MediaPipe Hands draws landmarks. The event state machine (merge/supersede/timeout) works. But: no real gesture detection, no real Cosmos call, no real data flowing to verifier.

**Next priority**:
1. Get Cosmos Reason 2 NIM running on DGX Spark and measure latency (blocks everything else)
2. Make verifier URL configurable via env var (enables Mac→DGX workflow)
3. Implement `proposeGestureFromLandmarks()` with real gesture detection
4. Build frame ring buffer and wire real evidence data to verifier
5. Wire real Cosmos NIM call in verifier (replace stub)
6. End-to-end demo: gesture → verify → execute

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

### Critical path — not built yet
- [ ] **Cosmos NIM on DGX Spark** — Cosmos Reason 2 is not running yet. Need to pull/configure the NIM container and confirm it responds to a test request. This is the make-or-break dependency.
- [ ] **Configurable verifier URL** — `web/src/api.js` hardcodes `http://127.0.0.1:8788`. Must be configurable (env/UI) for Mac→DGX workflow.
- [ ] **Gesture recognition** — `web/src/gesture.js:proposeGestureFromLandmarks()` returns `null`. Needs landmark-to-intent classification with the thresholds in `docs/GESTURE_DETECTION.md`: swipe ≥30% frame width in 0.4–0.9s, palm hold ≥0.3s, palm→fist transition, 1.5s cooldown.
- [ ] **Frame ring buffer** — No frame capture exists. Need a circular buffer of ~30 frames (~1s) that can export 8–12 evenly-spaced base64 JPEGs on demand.
- [ ] **Real data to verifier** — Web app sends only hardcoded `local_confidence: 0.7` and no frames/landmarks. Must pass real evidence windows.
- [ ] **Real Cosmos NIM call** — `verifier/verifier/stub_logic.py` is a stub. Replace with actual `/v1/chat/completions` call using the prompt in `docs/COSMOS_PROMPT_AND_SCHEMA.md`.
- [ ] **Real local confidence** — Compute from detection quality, displacement margin, temporal fit (see `docs/GESTURE_DETECTION.md`).

### Post-core / nice-to-have
- [ ] Three-tier confidence routing: HIGH → direct execute, MEDIUM → verify, LOW → ignore
- [ ] Event log UI panel in the browser
- [ ] Evaluation harness for hard negatives (record clips, run Cosmos offline, produce metrics table)
- [ ] Option 2 teacher-student loop implementation
- [ ] Demo video production (under 3 minutes)
- [ ] Final README polish for competition submission

---

## Key files

| File | Role | Status |
|------|------|--------|
| `web/src/gesture.js` | MediaPipe setup + gesture recognition | **TODO: detection returns null** |
| `web/src/main.js` | Event state machine, safe mode, merge/supersede | Done |
| `web/src/api.js` | HTTP client for verifier and executor | **TODO: configurable URLs** |
| `web/src/overlay.js` | Canvas hand landmark drawing | Done |
| `verifier/verifier/main.py` | FastAPI /verify, schema validation, JSONL log | Done |
| `verifier/verifier/stub_logic.py` | Stub verifier (always approve/force reject) | **Replace with Cosmos NIM call** |
| `verifier/verifier/schema_validate.py` | JSON Schema validation | Done |
| `executor/executor/main.py` | FastAPI /execute, xdotool/osascript, JSONL log | Done |
| `executor/actions.yaml` | OS key mappings per intent | Done |
| `shared/schema.json` | Strict verifier response schema | Done |

---

## Documentation index

| Document | Purpose |
|----------|---------|
| `docs/PROJECT_CONTEXT.md` | Problem statement, solution thesis, gestures, hard negatives, platforms, competition context |
| `docs/SYSTEM_ARCHITECTURE.md` | Components, APIs, deployment modes, data flow, logging |
| `docs/GESTURE_DETECTION.md` | Gesture detection algorithm spec with thresholds and state machines |
| `docs/COSMOS_PROMPT_AND_SCHEMA.md` | Cosmos prompt template, schema, API call construction, why-Cosmos framing |
| `docs/LATENCY_AND_AMBIGUOUS_POLICY.md` | Timeout policy, merge/supersede rules, instrumentation |
| `docs/OPTION2_RISKS_AND_MITIGATIONS.md` | Teacher-student loop failure modes and safeguards |
| `docs/ARCHITECTURE_DIAGRAMS.md` | ASCII diagrams for architecture, runtime flow, deployment modes |
| `docs/STATUS.md` | This file — build state, priority, session handoff |

---

## Quick start (3 terminals)

```bash
./scripts/run_executor.sh   # :8787
./scripts/run_verifier.sh   # :8788
./scripts/run_web.sh        # :5173 — open in browser
```

Test: keys `1`–`4` → OPEN_MENU / CLOSE_MENU / SWITCH_RIGHT / SWITCH_LEFT.
Safe Mode ON routes through verifier stub first.

```bash
# Health checks
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8788/health

# Executor dry run
curl -s -X POST http://127.0.0.1:8787/execute \
  -H 'Content-Type: application/json' \
  -d '{"intent":"OPEN_MENU","event_id":"test","dry_run":true,"source":"curl"}'

# Verifier stub
curl -s -X POST http://127.0.0.1:8788/verify \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"test","proposed_intent":"SWITCH_RIGHT","local_confidence":0.73}'
```

---

## Cosmos NIM integration checklist (when ready)

- [ ] Pull Cosmos Reason 2 NIM container on DGX Spark
- [ ] Confirm it starts and responds at `/v1/chat/completions`
- [ ] Test with a single image + text prompt, confirm JSON output
- [ ] Measure inference latency (single frame, 8 frames, 12 frames)
- [ ] Set `COSMOS_NIM_URL` env var in verifier
- [ ] Replace stub logic with real NIM call using prompt from `docs/COSMOS_PROMPT_AND_SCHEMA.md`
- [ ] Validate response against schema, fall back to reject on parse failure
- [ ] Test end-to-end: gesture → verify with Cosmos → execute
