"""
Real Cosmos Reason 2 NIM call via vLLM OpenAI-compatible API.

Endpoint: COSMOS_NIM_URL env var (default: http://localhost:8000)
Model:    nvidia/cosmos-reason2-8b (served via vLLM)

Latency benchmarks on DGX Spark GB10 (measured 2026-02-27):
  - 1 frame:  ~5.8s   (836 prompt tokens, ~14 tok/s)
  - 4 frames: ~7.3s  (1485 prompt tokens)
  - 8 frames: ~8.4s  (2596 prompt tokens)
"""

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Literal

COSMOS_NIM_URL = os.environ.get("COSMOS_NIM_URL", "http://localhost:8000")
COSMOS_MODEL = os.environ.get("COSMOS_MODEL", "nvidia/cosmos-reason2-8b")

Intent = Literal["OPEN_MENU", "CLOSE_MENU", "SWITCH_RIGHT", "SWITCH_LEFT"]

SYSTEM_PROMPT = """\
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
- Output ONLY a JSON object, no other text, no markdown, no code fences
- "version" must be "1.0"
- "proposed_intent" must match the proposed intent from the input exactly
- "final_intent" must be one of: OPEN_MENU, CLOSE_MENU, SWITCH_RIGHT, SWITCH_LEFT, NONE
- If not intentional, set final_intent to "NONE"
- "intentional" must be a boolean
- "confidence" must be a number between 0 and 1
- "reason_category" must be exactly one of: intentional_command, self_grooming, reaching_object, swatting_insect, conversation_gesture, accidental_motion, tracking_error, unknown
- "rationale" should be one concise sentence explaining the decision
- When uncertain, err on the side of rejection (set intentional to false)\
"""


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences if the model wraps its JSON response."""
    text = text.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


def call_cosmos_nim(
    proposed_intent: Intent,
    frames: list[str] | None = None,
    landmark_summary_json: dict[str, Any] | None = None,
    local_confidence: float | None = None,
    force_reject: bool = False,
) -> dict:
    """
    Call Cosmos Reason 2 via vLLM OpenAI-compatible API and return a response dict
    that validates against shared/schema.json.

    Raises RuntimeError on network failure or unparseable response.
    """
    if force_reject:
        return {
            "version": "1.0",
            "proposed_intent": proposed_intent,
            "final_intent": "NONE",
            "intentional": False,
            "confidence": 0.9,
            "reason_category": "accidental_motion",
            "rationale": "Forced reject is enabled for test validation.",
        }

    context: dict[str, Any] = {"proposed_intent": proposed_intent}
    if local_confidence is not None:
        context["local_confidence"] = local_confidence
    if landmark_summary_json:
        context["landmark_summary"] = landmark_summary_json

    # Build multimodal content: images first, then text context
    content_parts: list[dict] = []
    for frame_b64 in (frames or []):
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"},
        })
    content_parts.append({"type": "text", "text": json.dumps(context)})

    payload = {
        "model": COSMOS_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content_parts},
        ],
        "max_tokens": 256,
        "temperature": 0.1,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{COSMOS_NIM_URL}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cosmos NIM unreachable at {COSMOS_NIM_URL}: {exc}") from exc

    raw = result["choices"][0]["message"]["content"]
    cleaned = _strip_code_fences(raw)

    try:
        response_json = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cosmos NIM returned non-JSON: {raw!r}") from exc

    # Ensure required fields are present (schema_validate will do full validation)
    required = {"version", "proposed_intent", "final_intent", "intentional", "confidence", "reason_category", "rationale"}
    missing = required - response_json.keys()
    if missing:
        raise RuntimeError(f"Cosmos NIM response missing fields {missing}: {response_json}")

    return response_json
