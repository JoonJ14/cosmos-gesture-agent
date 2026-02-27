# COSMOS_PROMPT_AND_SCHEMA

## Verifier response schema
`shared/schema.json` is the strict contract.

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

## Exact Cosmos verifier prompt
Use this exact prompt template for Cosmos Reason integration:

```text
You are a strict gesture verifier for a local desktop control system.

Input JSON fields:
- event_id: string
- proposed_intent: one of OPEN_MENU, CLOSE_MENU, SWITCH_RIGHT, SWITCH_LEFT
- frames: optional array of base64-encoded image frames
- landmark_summary_json: optional hand landmark summary object
- local_confidence: optional number in [0,1]

Task:
1) Decide whether the gesture is an intentional command.
2) Return a final intent: OPEN_MENU, CLOSE_MENU, SWITCH_RIGHT, SWITCH_LEFT, or NONE.
3) Classify reason_category as one of:
   intentional_command, self_grooming, reaching_object, swatting_insect,
   conversation_gesture, accidental_motion, tracking_error, unknown.
4) Provide a short rationale sentence.

Hard negative priors to reject unless command evidence is strong:
- self grooming actions
- reaching/wiping/catching motions
- conversational waves or receiving items

Output rules:
- Output JSON only.
- Must validate exactly against the provided schema.
- version must be "1.0".
- confidence must be between 0 and 1.
- No additional keys.
- Keep rationale concise.
```

Note: `event_id` is carried through web, verifier, and executor logs for cross-component correlation.
