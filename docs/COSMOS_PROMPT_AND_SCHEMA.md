# Cosmos Prompt, Schema, and Integration Guide

## Why Cosmos is necessary (not optional)

A landmark-based gesture detector is fast but brittle. It can detect that a hand moved laterally across the frame, but it cannot determine whether that motion was a deliberate command or someone scratching their head. The kinematic features (trajectory, velocity, displacement) are identical in both cases.

Cosmos Reason 2 can look at a short clip and reason about visual context that geometric heuristics cannot encode:
- Is the user facing the screen or turned away talking to someone?
- Is the hand motion directed at the camera or reaching for an object?
- Is the hand in a deliberate command posture or a casual resting position?
- Does the overall scene context suggest the user is issuing a command?

**What makes Cosmos "earn its keep" for judges:**
1. **Cosmos is the arbiter of ambiguity** — it decides on cases where the local detector is uncertain
2. **Cosmos produces structured semantic outputs** — not just yes/no, but reason categories and rationale
3. **Cosmos enables a feedback loop** — its labels become training data for the local model (Option 2)
4. **Show what breaks without Cosmos** — baseline false positive rate on hard negatives vs. with Cosmos gating

## Cosmos Reason 2 technical details

- Based on Qwen3-VL architecture
- Runs on Blackwell GPU (DGX Spark)
- OpenAI-compatible API at `/v1/chat/completions`
- Accepts multimodal input: base64 images interleaved with text
- Apache 2.0 source, NVIDIA Open Model License for weights
- Available as NIM (NVIDIA Inference Microservice) or via transformers/vLLM

## Verifier response schema

`shared/schema.json` is the strict contract. All verifier responses (whether from Cosmos or the stub) must validate against it.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CosmosGestureVerificationResponse",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "version",
    "proposed_intent",
    "final_intent",
    "intentional",
    "confidence",
    "reason_category",
    "rationale"
  ],
  "properties": {
    "version": { "const": "1.0" },
    "proposed_intent": {
      "type": "string",
      "enum": ["OPEN_MENU", "CLOSE_MENU", "SWITCH_RIGHT", "SWITCH_LEFT"]
    },
    "final_intent": {
      "type": "string",
      "enum": ["OPEN_MENU", "CLOSE_MENU", "SWITCH_RIGHT", "SWITCH_LEFT", "NONE"]
    },
    "intentional": { "type": "boolean" },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "reason_category": {
      "type": "string",
      "enum": [
        "intentional_command",
        "self_grooming",
        "reaching_object",
        "swatting_insect",
        "conversation_gesture",
        "accidental_motion",
        "tracking_error",
        "unknown"
      ]
    },
    "rationale": { "type": "string" }
  }
}
```

## Cosmos verifier prompt template

Use this exact system prompt when calling Cosmos Reason 2:

```
You are a strict gesture verifier for a desktop control system that uses webcam hand tracking.

You are given:
- A proposed gesture intent detected by a local hand tracker
- A sequence of video frames showing the moment the gesture was detected
- Optionally, a hand landmark summary with trajectory and pose data

Your task is to determine whether the detected gesture was an INTENTIONAL USER COMMAND directed at the computer, or whether it was incidental human motion that happened to resemble a gesture.

Key distinction: Many normal human activities produce hand motions that are kinematically identical to gesture commands. Scratching your head looks like a swipe. Waving during conversation looks like a dismiss gesture. Reaching for a coffee cup looks like a directional motion. You must use the full visual context — body posture, gaze direction, scene context, motion purposefulness — to determine intent.

Hard negative priors (reject unless strong command evidence):
- Self-grooming: scratching head/face, rubbing eyes, adjusting glasses/hair
- Reaching: grabbing objects, wiping surfaces, catching/swatting
- Conversation: waving while talking, gesticulating, receiving items from others
- Accidental: repositioning hands, stretching, fidgeting

Output rules:
- Output ONLY a JSON object, no other text
- Must validate against the provided schema exactly
- "version" must be "1.0"
- "proposed_intent" must match the proposed intent from the input
- "final_intent" must be one of: OPEN_MENU, CLOSE_MENU, SWITCH_RIGHT, SWITCH_LEFT, NONE
- If not intentional, set final_intent to "NONE"
- "confidence" must be between 0 and 1
- "reason_category" must be one of: intentional_command, self_grooming, reaching_object, swatting_insect, conversation_gesture, accidental_motion, tracking_error, unknown
- "rationale" should be one concise sentence explaining the decision
- When uncertain, err on the side of rejection (set intentional to false)
```

## How to construct the API call

The verifier service constructs the multimodal request like this:

```python
messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT  # the prompt template above
    },
    {
        "role": "user",
        "content": [
            # Include each evidence frame as a base64 image
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}},
            # ... repeat for each of the 8-12 frames ...
            
            # Include the text context
            {"type": "text", "text": json.dumps({
                "proposed_intent": "SWITCH_RIGHT",
                "local_confidence": 0.73,
                "landmark_summary": {
                    "handedness": "Right",
                    "wrist_trajectory_x": [0.72, 0.65, 0.55, 0.43, 0.35],
                    "displacement_pct": 0.37,
                    "duration_s": 0.6,
                    "fingers_extended": 4,
                    "palm_facing_camera": true
                }
            })}
        ]
    }
]

response = httpx.post(
    f"{COSMOS_NIM_URL}/v1/chat/completions",
    json={
        "model": "nvidia/cosmos-reason2",  # confirm exact slug from NIM docs
        "messages": messages,
        "max_tokens": 256,
        "temperature": 0.1  # low temperature for deterministic structured output
    }
)
```

## Schema validation

The verifier MUST validate the parsed JSON against `shared/schema.json` before returning it. If validation fails:
- Log the raw response and the validation error
- Return a conservative reject (intentional=false, final_intent=NONE, reason_category=unknown)
- This prevents malformed model output from causing unintended actions

## What to send Cosmos (evidence window)

- **Frames:** 8–12 JPEG-encoded, base64 frames from the ~1 second window around the gesture event, evenly sampled
- **Landmark summary:** Compact JSON with handedness, wrist trajectory, displacement percentage, timing, finger extension count, palm facing score
- **Local confidence:** The confidence score from the local gesture detector

Sending both frames AND landmarks gives Cosmos visual context for reasoning AND structured data for the kinematic features. The landmark summary helps Cosmos understand what the local detector saw; the frames let it see what the local detector couldn't reason about (body posture, gaze, scene context).

## Environment variable

The Cosmos NIM URL must be configurable:

```bash
export COSMOS_NIM_URL="http://localhost:8000"  # DGX-only mode
# or
export COSMOS_NIM_URL="http://192.168.1.100:8000"  # remote DGX from Mac
```

If `COSMOS_NIM_URL` is not set, the verifier falls back to stub logic.

## Correlation

`event_id` is carried through web app → verifier → executor logs. This allows:
- End-to-end latency computation per event
- Disagreement analysis (local proposed X, Cosmos said Y)
- Option 2 training data construction (pair event features with Cosmos labels)
