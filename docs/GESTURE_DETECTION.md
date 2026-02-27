# Gesture Detection Specification

This document specifies the gesture detection algorithm for `web/src/gesture.js:proposeGestureFromLandmarks()`. It is the implementation reference for the local perception layer.

## Overview

MediaPipe Hands provides 21 landmarks per hand, per frame, plus handedness (Left/Right) and detection confidence. The gesture detection logic tracks these landmarks over time using a state machine to classify temporal motion patterns into intent proposals.

## Input from MediaPipe

Each frame callback receives:
- `multiHandLandmarks[]` — array of hands, each with 21 normalized landmarks (x, y, z in [0, 1])
- `multiHandedness[]` — array of `{label: "Left"|"Right", score: float}`

Key landmarks used:
- **Wrist** (landmark 0) — primary position tracker for swipe detection
- **Middle finger MCP** (landmark 9) — secondary position reference
- **Fingertips** (landmarks 4, 8, 12, 16, 20) — for finger extension detection
- **Finger MCPs** (landmarks 2, 5, 9, 13, 17) — for palm facing / finger extension comparison

## Gesture definitions

### SWITCH_RIGHT

- **Trigger hand:** Right hand
- **Motion:** Wrist x-coordinate decreases (hand moves right→left in camera view) by ≥30% of frame width
- **Time window:** 0.4–0.9 seconds from start of motion to completion
- **Optional filter:** Four or more fingers extended (flat hand, not a fist) to reduce false positives
- **Cooldown:** 1.5 seconds after any successful execution

### SWITCH_LEFT

- **Trigger hand:** Left hand
- **Motion:** Wrist x-coordinate increases (hand moves left→right in camera view) by ≥30% of frame width
- **Time window:** 0.4–0.9 seconds from start of motion to completion
- **Optional filter:** Four or more fingers extended
- **Cooldown:** 1.5 seconds after any successful execution

### OPEN_MENU

- **Trigger hand:** Either hand
- **Pose:** Palm facing camera, all five fingers extended and spread
- **Hold duration:** ≥0.3 seconds of stable open palm pose
- **Motion constraint:** Hand should be mostly stationary (wrist displacement < 5% frame width during hold)
- **Cooldown:** 1.5 seconds after any successful execution

### CLOSE_MENU

- **Trigger hand:** Either hand
- **Pose transition:** Hand transitions from open palm (fingers extended) to closed fist (fingers curled)
- **Time window:** Transition completes within 0.3–0.8 seconds
- **Requirement:** Must see at least 3 frames of open palm before fist is detected
- **Cooldown:** 1.5 seconds after any successful execution

## Detection algorithm

### Finger extension detection

A finger is considered "extended" when the fingertip y-coordinate is above (less than, since y increases downward) the corresponding MCP joint, adjusted for hand orientation:

```
finger_extended = (fingertip.y < finger_mcp.y)  // simplified; needs palm orientation correction
```

For the thumb, use x-axis distance from the wrist instead (thumb extends laterally).

**Palm facing detection:** When the palm faces the camera, the z-coordinates of the fingertips are closer to the camera (lower z) than the wrist. Combine with finger extension to detect open palm.

### Swipe detection state machine

Track per-hand state over a sliding time window:

```
States: IDLE → TRACKING → PROPOSED

IDLE:
  - Hand appears and is tracked for ≥3 consecutive frames
  - Record initial wrist position and timestamp
  - Transition to TRACKING

TRACKING:
  - Each frame, compute cumulative x-displacement from initial position
  - If displacement ≥ 30% frame width AND elapsed time is 0.4–0.9s:
    → Transition to PROPOSED, emit intent proposal
  - If elapsed time > 0.9s without threshold:
    → Reset to IDLE
  - If hand lost:
    → Reset to IDLE

PROPOSED:
  - Intent emitted, enter cooldown
  - After cooldown (1.5s), return to IDLE
```

### Open palm detection state machine

```
States: IDLE → PALM_DETECTED → HOLDING → PROPOSED

IDLE:
  - Each frame, check if all 5 fingers extended AND palm facing camera
  - If yes: record timestamp, transition to PALM_DETECTED

PALM_DETECTED / HOLDING:
  - Continue checking open palm pose each frame
  - Track wrist stability (must stay within 5% frame width of initial position)
  - If pose held for ≥ 0.3s: transition to PROPOSED, emit OPEN_MENU
  - If pose breaks: reset to IDLE

PROPOSED:
  - Enter cooldown, return to IDLE after 1.5s
```

### Close menu detection

```
States: IDLE → OPEN_SEEN → CLOSING → PROPOSED

IDLE:
  - Detect open palm (same criteria as OPEN_MENU)
  - If open palm seen for ≥ 3 frames: transition to OPEN_SEEN, record timestamp

OPEN_SEEN:
  - Monitor finger extension count each frame
  - If extension count drops to ≤ 1 (fist) within 0.3–0.8s of OPEN_SEEN start:
    → Transition to PROPOSED, emit CLOSE_MENU
  - If > 0.8s without fist: reset to IDLE
  - If hand lost: reset to IDLE
```

## Local confidence scoring

Each proposal should include a local confidence score (0 to 1) based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| MediaPipe detection confidence | 0.25 | Raw confidence from MediaPipe hand detection |
| Displacement margin | 0.25 | How far past the 30% threshold the swipe went (for swipe gestures) |
| Temporal fit | 0.20 | How well the timing matches the expected window (centered = higher) |
| Pose stability | 0.15 | Consistency of finger extension / palm facing across frames in the window |
| Hand size / distance | 0.15 | Larger hand in frame (closer to camera) = more reliable landmarks |

This score feeds the confidence-gated routing:
- **HIGH (≥ 0.85):** Execute directly
- **MEDIUM (0.5–0.85):** Send to Cosmos for verification
- **LOW (< 0.5):** Ignore

## Ring buffer for evidence windows

The web app should maintain a circular buffer of recent frames:

- **Buffer size:** ~30 frames (~1 second at 30 fps)
- **Storage format:** Each entry stores the video frame as a `canvas.toDataURL('image/jpeg', 0.7)` base64 string, plus the corresponding landmarks and timestamp
- **On proposal:** Extract 8–12 evenly-spaced frames from the buffer covering the gesture window
- **Purpose:** Sent to the verifier as the evidence for Cosmos to reason about

## Global cooldown

After any intent is executed (or rejected by verifier), no new proposals are accepted for 1.5 seconds. This prevents:
- Repeated triggers from a single gesture
- Rapid accidental triggering during hand repositioning after a gesture

## Edge cases to handle

- **Both hands visible:** Each hand tracks independently. A right-hand swipe and left-hand palm are separate state machines.
- **Hand switching:** If handedness flips between frames (MediaPipe inconsistency), require 3+ consistent frames before accepting handedness.
- **Small hands / far from camera:** If the hand bounding box is very small (e.g., landmarks span < 5% of frame), ignore — landmark accuracy drops significantly at distance.
- **Rapid hand entry/exit:** Don't trigger swipe when a hand enters the frame from the side — require hand to be tracked for ≥3 frames before starting swipe detection.
