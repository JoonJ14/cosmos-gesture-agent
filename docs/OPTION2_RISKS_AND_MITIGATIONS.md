# Option 2: Teacher-Student Feedback Loop — Design and Risks

## What Option 2 is

Option 1 (the base system) uses Cosmos as a real-time verification gate for ambiguous gestures. The local gesture detector's rule-based thresholds are static — they don't improve over time.

Option 2 adds a continuous improvement loop where Cosmos acts as a **teacher** that labels ambiguous cases, and a lightweight **student** classifier learns from those labels to gradually improve local detection quality. Over time, the student gets better, fewer cases are ambiguous, and fewer Cosmos calls are needed.

**Important:** We never fine-tune Cosmos. Cosmos is a general reasoning model that already understands human intent from video. Fine-tuning it on a handful of gestures would be overkill, slow, and fragile. Instead, we train a tiny local model (logistic regression or small MLP) on hand landmark features, using Cosmos's structured labels as ground truth.

## The concrete feedback loop

```
1. User performs gesture
2. Local detector proposes intent with confidence score
3. If ambiguous → Cosmos verifies and returns structured label
4. Event is logged to JSONL:
   - landmark features (wrist trajectory, finger extension, palm facing, etc.)
   - proposed intent
   - Cosmos label (final_intent, intentional, reason_category, confidence)
   - execution outcome
5. Periodically (e.g., after 50 new labeled events):
   a. Extract feature vectors and Cosmos labels from JSONL logs
   b. Train a lightweight classifier on landmark features → intentional/not + intent class
   c. Evaluate on a held-out calibration set (must include hard negatives)
   d. If performance improves AND does not regress on calibration set → deploy
   e. Update local confidence model — student now provides better confidence scores
6. With improved confidence, fewer cases fall in the "ambiguous" band → fewer Cosmos calls
```

## What the student model looks like

**Input features (per event):**
- Swipe displacement (% of frame width)
- Swipe duration (seconds)
- Peak velocity of wrist motion
- Handedness consistency (% of frames with same hand label)
- Finger extension count at proposal time
- Palm facing score (z-depth differential)
- Motion smoothness (jerk metric)
- Hand size in frame (bounding box area)

**Output:** Binary (intentional / not intentional) + intent class if intentional

**Model:** Logistic regression or small MLP (< 100 parameters). Must be fast enough to run per-proposal in the browser or in a local Python service.

## Risks and mitigations

### 1. Regression: updated model performs worse on previously-correct cases

**The most serious risk.** You update the model with new data, and it starts misclassifying gestures it used to get right.

**Mitigations:**
- Maintain a **frozen calibration set** of known-correct examples (both positive commands and hard negatives)
- Before deploying any student update, evaluate on the calibration set
- Set a regression threshold: if accuracy drops by > 2% on any category, reject the update
- Keep the previous model version and allow instant rollback
- Version student models: `models/student/v0`, `v1`, etc.

### 2. Label noise from Cosmos

Cosmos is not perfect. Some labels will be wrong, especially for genuinely ambiguous cases.

**Mitigations:**
- Only use labels where Cosmos confidence ≥ 0.75 for training
- Discard labels with `reason_category: unknown` — these are Cosmos expressing uncertainty
- Require multi-frame evidence windows (8–12 frames) to give Cosmos enough context
- Log and periodically review disagreements between Cosmos and local detector

### 3. Class imbalance

In normal usage, most proposals are real commands (user is intentionally gesturing). Hard negatives (accidental motion) are rare unless the user is actively testing them.

**Mitigations:**
- Actively sample: when Cosmos rejects a proposal, always include it in training data (it's a rare but valuable negative example)
- Include the recorded hard negative evaluation set in every training batch
- Use class-weighted loss in the student model

### 4. Distribution shift between users

The student model might learn one user's specific patterns and fail for another user.

**Mitigations:**
- Keep the rule-based detector as a fallback — the student augments thresholds, it doesn't replace the entire pipeline
- If deploying for multiple users, maintain per-user student models or pool data with normalization
- For the competition demo, single-user is fine

### 5. Policy drift between student and teacher

Over time, the student routes fewer cases to Cosmos (because it's more confident). But if the student is wrong about its confidence, it stops getting corrective feedback from Cosmos — a positive feedback loop toward silent failure.

**Mitigations:**
- **Random sampling:** Always send a random 10% of high-confidence events to Cosmos for verification, even when the student is confident. This provides ongoing calibration data.
- **Disagreement dashboards:** Track cases where the student would have decided differently than Cosmos. If the disagreement rate rises, trigger a retraining cycle.
- **Periodic full evaluation:** Re-run the calibration set through both student and teacher and compare.

### 6. Privacy concerns from frame retention

Frames stored for training contain webcam images of the user and their environment.

**Mitigations:**
- Default to storing only landmark features (no raw frames) for training data
- Keep frame retention windows short (delete after Cosmos has labeled them)
- Make frame capture opt-in and configurable
- Document the retention policy clearly

### 7. Schema contract breakage

If the student model or updated pipeline produces outputs that don't match the expected schema, downstream components break silently.

**Mitigations:**
- Student model outputs go through the same confidence-gated routing as before — they just produce better confidence scores
- The verifier response schema (`shared/schema.json`) is enforced at runtime and never changes based on student updates
- Integration tests that validate schema compliance on every code change

## Infrastructure hooks already in Option 1

These are built into the current system specifically to make Option 2 easy to add:

- **JSONL logging everywhere** — every proposal, verification, and execution is logged with shared `event_id`, timestamps, and outcomes
- **Feature-rich event records** — local confidence, proposed intent, Cosmos label, reason category
- **Schema discipline** — strict JSON Schema validation prevents garbage data from entering the training pipeline
- **Stub-able verifier** — the verifier already has a clean interface; swapping between stub, Cosmos, and student-augmented logic is a config change

## When to build Option 2

Build Option 1 first and get a working demo. Option 2 adds value but is not required for a valid competition submission. If time allows after the core demo works:

1. Add feature vector extraction to the JSONL log (landmark features per event)
2. Write a training script that reads the log and fits a logistic regression
3. Add a calibration set of ~20 positive + ~20 hard negative examples
4. Evaluate before/after and document the improvement
5. Add the teacher-student loop diagram to `docs/ARCHITECTURE_DIAGRAMS.md`
