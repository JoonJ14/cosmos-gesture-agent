# Cosmos Gesture Agent

**A real-time webcam gesture agent with VLM-based intent verification — solving the false positive problem in continuous spatial tracking.**

> NVIDIA Cosmos Cookoff 2026 Submission

## The Problem

Gesture-based computer interaction has a fundamental unsolved problem: **false positives from incidental motion.**

On a touchscreen, physical contact IS the intent signal. But in webcam-based spatial tracking, the system watches your hands continuously — and a head scratch looks identical to a swipe, a conversational wave triggers workspace switches, reaching for your coffee fires a pull gesture.

Traditional approaches attack this with geometric constraints: velocity thresholds, activation zones, displacement guards, cooldown timers. These help incrementally, but hit a ceiling because **many intentional commands and incidental motions are kinematically identical.** A deliberate swipe and a conversational hand wave have the same trajectory and velocity profile. The difference isn't in the motion — it's in the *context and intent* behind it.

## The Solution: Cosmos Reason 2 as Intent Verifier

Instead of engineering increasingly complex geometric rules, we use **NVIDIA Cosmos Reason 2** — a vision-language model — to reason about whether a detected gesture was intentional.

The architecture follows the **Event Reviewer pattern:**

1. **Fast local perception** — MediaPipe Hands in the browser detects hand landmarks at 30+ fps and classifies gesture candidates using a state machine
2. **Intelligent verification** — Ambiguous cases are sent to Cosmos Reason 2 with a short evidence clip (~8–12 frames). Cosmos sees the full visual context: body posture, gaze direction, scene, whether the motion is purposeful or casual
3. **Action execution** — Only verified intentional commands trigger OS actions (workspace switching, Mission Control)

Cosmos earns its role by solving what heuristics fundamentally cannot: distinguishing a deliberate lateral swipe from someone scratching their head, catching a fly, or waving during conversation.

## Architecture

```
┌───────────────────────────────────────────────┐
│               Web App (JS, :5173)             │
│  MediaPipe Hands · Gesture state machine      │
│  Ring buffer · Confidence scoring · Overlay   │
└──────────────┬────────────────────────────────┘
               │
     ┌─────────┴──────────┐
     │                    │
     v                    v
┌──────────────┐   ┌───────────────────────┐
│ Executor     │   │ Cosmos Verifier       │
│ (PY, :8787)  │   │ (PY, :8788)           │
│ xdotool /    │   │ Calls Cosmos Reason 2 │
│ osascript    │   │ NIM on DGX Spark      │
└──────────────┘   └───────────────────────┘
```

**Decision flow:** High-confidence gestures execute directly. Ambiguous cases go to Cosmos first. Low-confidence signals are ignored. See [Architecture Diagrams](docs/ARCHITECTURE_DIAGRAMS.md) for full details.

## Gestures

| Intent | Gesture | Action (Linux / macOS) |
|--------|---------|------------------------|
| `OPEN_MENU` | Open palm, five fingers spread, held ~0.3s | Super key / Ctrl+Up (Mission Control) |
| `CLOSE_MENU` | Open palm → closed fist transition | Escape |
| `SWITCH_RIGHT` | Right hand swipes right→left | Ctrl+Right / Ctrl+Right |
| `SWITCH_LEFT` | Left hand swipes left→right | Ctrl+Left / Ctrl+Left |

## Why Cosmos Is Necessary (Not Optional)

We demonstrate Cosmos's value with **8 hard negative scenarios** — motions that a landmark-based detector proposes as gestures, but Cosmos correctly rejects:

| Category | Scenario | Why heuristics fail |
|----------|----------|---------------------|
| Self-grooming | Scratch head, scratch nose, rub eye | Same hand trajectory as a swipe |
| Reaching | Wipe monitor, reach to side, catch a fly | Same displacement and velocity |
| Conversation | Wave while talking, receive item from someone | Same hand shape and motion |

**Key metric:** False positive rate on hard negatives — baseline (local only) vs. with Cosmos verification.

## Quick Start

Three terminals from repo root:

```bash
./scripts/run_executor.sh   # Port 8787 — OS key injection
./scripts/run_verifier.sh   # Port 8788 — Cosmos verification (stub for now)
./scripts/run_web.sh        # Port 5173 — open in browser
```

Open `http://127.0.0.1:5173`, allow webcam access. Press keys `1`–`4` to test intent proposals. Toggle **Safe Mode** to route through the verifier.

### Platform requirements

**Linux (DGX Spark / Ubuntu):**
- GNOME X11 desktop
- `sudo apt install xdotool`

**macOS:**
- Enable Accessibility permission for Terminal: System Settings → Privacy & Security → Accessibility
- Uses `osascript` for key injection

## Hardware

- **DGX Spark** (Grace Blackwell GB10, 128GB unified, Ubuntu 24.04 arm64) — Cosmos inference
- **MacBook Air** (Apple Silicon) — development and secondary demo platform
- USB webcam on DGX Spark; built-in camera on Mac

## Stretch Goal: Teacher-Student Feedback Loop

The system logs every proposal, verification, and execution as structured JSONL. This enables a continuous improvement loop where Cosmos acts as a **teacher** labeling ambiguous cases, and a lightweight local **student** classifier trains on those labels to improve over time — gradually reducing Cosmos calls while maintaining accuracy.

See [Option 2 Design & Risks](docs/OPTION2_RISKS_AND_MITIGATIONS.md) for the full design, failure modes, and safeguards.

## Beyond Desktop Gestures

Desktop gesture control is a proof of concept. The core architecture — **VLM-based intent verification on top of continuous spatial tracking** — applies to any domain where false positives from incidental motion are the bottleneck:

- Robotics safety (command vs. normal worker motion)
- Automotive gesture controls (driver commands vs. passenger conversation)
- Smart home / IoT (control gestures vs. stretching)
- AR/VR spatial input (commands vs. natural hand motion)
- Industrial operations and retail kiosks

## Documentation

| Document | Purpose |
|----------|---------|
| [Project Context](docs/PROJECT_CONTEXT.md) | Problem statement, solution thesis, competition framing |
| [System Architecture](docs/SYSTEM_ARCHITECTURE.md) | Components, APIs, deployment modes, data flow |
| [Gesture Detection](docs/GESTURE_DETECTION.md) | Detection algorithm, thresholds, state machines |
| [Cosmos Prompt & Schema](docs/COSMOS_PROMPT_AND_SCHEMA.md) | Prompt template, JSON schema, integration guide |
| [Latency Policy](docs/LATENCY_AND_AMBIGUOUS_POLICY.md) | Timeout, merge/supersede, instrumentation |
| [Option 2 Risks](docs/OPTION2_RISKS_AND_MITIGATIONS.md) | Teacher-student loop design and safeguards |
| [Architecture Diagrams](docs/ARCHITECTURE_DIAGRAMS.md) | Visual diagrams for all system flows |
| [Build Status](docs/STATUS.md) | Current state, priorities, session handoff |

## License

Apache 2.0
