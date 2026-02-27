# SYSTEM_ARCHITECTURE

## Components
1. **Web app (`web/`)**
- Captures webcam stream.
- Runs MediaPipe Hands for landmarks.
- Produces intent proposal (currently keyboard-triggered stub).
- Enforces runtime policy:
  - Safe Mode ON: call verifier before executor.
  - Safe Mode OFF: direct executor call.
- Emits structured timing logs in browser console with shared `event_id`.

2. **Verifier service (`verifier/`)**
- HTTP API: receives `event_id` and proposed intent.
- Returns strict JSON that must validate against `shared/schema.json`.
- Current behavior: deterministic stub with optional forced reject path.
- Writes JSONL logs for observability and schema-validity tracking.

3. **Executor service (`executor/`)**
- HTTP API: receives final intent and event metadata.
- Loads key mappings from `actions.yaml` by OS and intent.
- Executes key injection:
  - Linux GNOME X11: `xdotool key <combo>`
  - macOS: `osascript` (System Events)
- Writes JSONL logs with latency and execution outcome.

4. **Shared contract (`shared/schema.json`)**
- Single strict schema for verifier response.
- Used by verifier runtime validation and downstream integrations.

## API contracts
### Verifier API
- `GET /health` -> `{ "status": "ok" }`
- `POST /verify`
  - Request:
    - `event_id` (required)
    - `proposed_intent` (required)
    - `frames` (optional)
    - `landmark_summary_json` (optional)
    - `local_confidence` (optional)
    - `force_reject` (optional test flag)
  - Response: strict schema object (`shared/schema.json`).

### Executor API
- `GET /health` -> `{ "status": "ok" }`
- `POST /execute`
  - Request:
    - `intent` (required)
    - `event_id` (optional; generated if missing)
    - `dry_run` (optional, default `false`)
    - `source` (optional, default `web`)
  - Response:
    - `ok`, `executed`, `intent`, `event_id`, `key_combo`, `detail`

## Deployment modes
- **Local all-in-one**: web + verifier + executor on a single workstation.
- **Split services**: web on one machine, verifier/executor on another host, connected via HTTP.
- **Future edge/cloud hybrid**: local proposal + cloud verifier + local executor.

## Logging and observability
All components correlate by shared `event_id`:
- Web console structured timing object.
- Verifier JSONL: request time, latency, schema validity, response payload.
- Executor JSONL: mapping used, execution result, OS, latency.

## Runtime decision logic
Decision path (verifier-first, timeout behavior, fallback policy) is defined in:
- `docs/LATENCY_AND_AMBIGUOUS_POLICY.md`
