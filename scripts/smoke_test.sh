#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXECUTOR_LOG_PATH="$ROOT_DIR/executor/logs/executor_events.jsonl"
VERIFIER_LOG_PATH="$ROOT_DIR/verifier/logs/verifier_events.jsonl"
EXECUTOR_RUN_LOG="$ROOT_DIR/logs/smoke_executor_run.log"
VERIFIER_RUN_LOG="$ROOT_DIR/logs/smoke_verifier_run.log"

EXECUTOR_EVENT_ID="evt-smoke-exec-001"
VERIFIER_EVENT_ID="evt-smoke-verify-001"

EXECUTOR_PID=""
VERIFIER_PID=""

stop_services() {
  set +e

  if [[ -n "$EXECUTOR_PID" ]] && kill -0 "$EXECUTOR_PID" 2>/dev/null; then
    kill "$EXECUTOR_PID" 2>/dev/null || true
  fi
  if [[ -n "$VERIFIER_PID" ]] && kill -0 "$VERIFIER_PID" 2>/dev/null; then
    kill "$VERIFIER_PID" 2>/dev/null || true
  fi

  pkill -f "uvicorn executor.main:app --host 127.0.0.1 --port 8787 --reload" 2>/dev/null || true
  pkill -f "uvicorn verifier.main:app --host 127.0.0.1 --port 8788 --reload" 2>/dev/null || true

  if [[ -n "$EXECUTOR_PID" ]]; then
    wait "$EXECUTOR_PID" 2>/dev/null || true
  fi
  if [[ -n "$VERIFIER_PID" ]]; then
    wait "$VERIFIER_PID" 2>/dev/null || true
  fi
}

wait_for_health() {
  local url="$1"
  local name="$2"

  for _ in $(seq 1 180); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for ${name} health endpoint: ${url}" >&2
  return 1
}

trap stop_services EXIT

mkdir -p "$ROOT_DIR/logs"

"$ROOT_DIR/scripts/run_executor.sh" >"$EXECUTOR_RUN_LOG" 2>&1 &
EXECUTOR_PID=$!

"$ROOT_DIR/scripts/run_verifier.sh" >"$VERIFIER_RUN_LOG" 2>&1 &
VERIFIER_PID=$!

wait_for_health "http://127.0.0.1:8787/health" "executor"
wait_for_health "http://127.0.0.1:8788/health" "verifier"

echo "Executor /health:"
curl -fsS "http://127.0.0.1:8787/health"
echo

echo "Executor /execute dry_run:true:"
curl -fsS -X POST "http://127.0.0.1:8787/execute" \
  -H "Content-Type: application/json" \
  -d "{\"intent\":\"OPEN_MENU\",\"event_id\":\"${EXECUTOR_EVENT_ID}\",\"dry_run\":true,\"source\":\"smoke_test\"}"
echo

echo "Verifier /health:"
curl -fsS "http://127.0.0.1:8788/health"
echo

echo "Verifier /verify:"
curl -fsS -X POST "http://127.0.0.1:8788/verify" \
  -H "Content-Type: application/json" \
  -d "{\"event_id\":\"${VERIFIER_EVENT_ID}\",\"proposed_intent\":\"OPEN_MENU\"}"
echo

stop_services
trap - EXIT

if [[ ! -s "$EXECUTOR_LOG_PATH" ]]; then
  echo "Missing or empty executor log: $EXECUTOR_LOG_PATH" >&2
  exit 1
fi

if [[ ! -s "$VERIFIER_LOG_PATH" ]]; then
  echo "Missing or empty verifier log: $VERIFIER_LOG_PATH" >&2
  exit 1
fi

echo "Last 3 lines: $EXECUTOR_LOG_PATH"
tail -n 3 "$EXECUTOR_LOG_PATH"

echo "Last 3 lines: $VERIFIER_LOG_PATH"
tail -n 3 "$VERIFIER_LOG_PATH"
