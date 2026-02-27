import json
from pathlib import Path
from typing import Tuple

from jsonschema import ValidationError, validate

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "shared" / "schema.json"


def load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_response(payload: dict) -> Tuple[bool, str | None]:
    schema = load_schema()
    try:
        validate(instance=payload, schema=schema)
        return True, None
    except ValidationError as exc:
        return False, exc.message
