# PROJECT_CONTEXT

## Summary
`cosmos-gesture-agent` is a real-time webcam gesture agent for local desktop control. The browser detects hands and proposes intent quickly. A verifier service (Cosmos Reason integration target) confirms intent and rejects non-command motions. The executor performs OS key actions.

## Gesture set in scope
- `OPEN_MENU`: open palm with five fingers extended and spread, held deliberately.
- `CLOSE_MENU`: open palm transitions into a deliberate closed fist.
- `SWITCH_RIGHT`: right hand swipe from right to left.
- `SWITCH_LEFT`: left hand swipe from left to right.

## Supported platforms
- Linux GNOME X11 (`xdotool` available).
- macOS (System Events via `osascript`, Accessibility permission required).

## Cosmos role
Cosmos Reason acts as the verifier that receives context for a proposed intent and returns strict structured JSON with:
- intent acceptance or rejection
- confidence and rationale
- reason category for policy and analytics

Current implementation uses a strict-schema stub verifier and keeps API boundaries unchanged so Cosmos can be integrated later without architecture changes.

## Hard negatives for evaluation
These scenarios should be rejected by the verifier during future model validation and policy tuning:
- Self grooming: scratch head, scratch nose, rub eye.
- Reaching: wipe monitor, reach to side while head turned, catch a fly.
- Conversation: turn and wave while talking, receive an item from someone.

## Option 2 plan: teacher-student feedback loop
Option 2 trains a fast local student classifier with Cosmos as teacher:
- Student proposes low-latency intent.
- Teacher (Cosmos verifier) labels uncertain/ambiguous cases.
- Logged events and outcomes become periodic training data.
- Student model improves online behavior while verifier remains safety gate.

This repo includes instrumentation and schema discipline needed to evolve into that loop.
