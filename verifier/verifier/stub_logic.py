from typing import Literal

Intent = Literal["OPEN_MENU", "CLOSE_MENU", "SWITCH_RIGHT", "SWITCH_LEFT"]


def build_stub_response(event_id: str, proposed_intent: Intent, force_reject: bool = False) -> dict:
    _ = event_id

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

    return {
        "version": "1.0",
        "proposed_intent": proposed_intent,
        "final_intent": proposed_intent,
        "intentional": True,
        "confidence": 0.9,
        "reason_category": "intentional_command",
        "rationale": "Gesture appears to be an intentional command.",
    }
