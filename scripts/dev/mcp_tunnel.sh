#!/usr/bin/env bash
# Background ngrok tunnel for the Gemini demo.
# Only /mcp is forwarded; the reserved hostname is research.sharedoxygen.com.
# Stops ngrok processes that hold that hostname. Leaves other ngrok agents alone.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PUBLIC_URL="${MCP_PUBLIC_URL:-https://research.sharedoxygen.com}"
LOCAL_PORT="${MCP_LOCAL_PORT:-8010}"
POLICY_FILE="${MCP_POLICY_FILE:-$ROOT_DIR/deploy/ngrok/indoc-mcp-policy.yml}"
PID_FILE="${TMP_DIR:-$ROOT_DIR/tmp}/ngrok.pid"
LOG_FILE="${TMP_DIR:-$ROOT_DIR/tmp}/ngrok.out"

holder_pids() {
  ps -ax -o pid= -o command= | awk -v url="$PUBLIC_URL" '
    $0 ~ /[n]grok/ && index($0, url) { print $1 }
  '
}

cmd_stop() {
  mkdir -p "$(dirname "$PID_FILE")"
  if [ -f "$PID_FILE" ]; then
    pid="$(tr -d '[:space:]' <"$PID_FILE" || true)"
    if [ -n "${pid:-}" ]; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
  local pids
  pids="$(holder_pids || true)"
  if [ -n "$pids" ]; then
    echo "Releasing $PUBLIC_URL (ngrok pid $pids)"
    # shellcheck disable=SC2086
    kill -TERM $pids 2>/dev/null || true
    sleep 1
    pids="$(holder_pids || true)"
    if [ -n "$pids" ]; then
      # shellcheck disable=SC2086
      kill -KILL $pids 2>/dev/null || true
      sleep 1
    fi
  fi
}

wait_ready() {
  local i code body
  for i in $(seq 1 30); do
    if [ -f "$PID_FILE" ] && ! kill -0 "$(tr -d '[:space:]' <"$PID_FILE")" 2>/dev/null; then
      if [ -z "$(holder_pids || true)" ]; then
        echo "ngrok exited" >&2
        tail -n 40 "$LOG_FILE" >&2 || true
        return 1
      fi
    fi
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:${LOCAL_PORT}/healthz" || true)"
    if [ "$code" = "200" ]; then
      body="$(curl -s --max-time 8 -X POST "$PUBLIC_URL/mcp" \
        -H 'content-type: application/json' \
        -H 'accept: application/json, text/event-stream' \
        -d '{}' || true)"
      case "$body" in
        *'"error":"unauthorized"'*|*'"error": "unauthorized"'*)
          return 0
          ;;
      esac
    fi
    if [ -f "$LOG_FILE" ] && grep -q 'ERR_NGROK_334' "$LOG_FILE"; then
      echo "ngrok refused $PUBLIC_URL (ERR_NGROK_334)" >&2
      return 1
    fi
    sleep 1
  done
  echo "MCP tunnel did not become ready" >&2
  tail -n 40 "$LOG_FILE" >&2 || true
  return 1
}

cmd_start() {
  [ -f "$POLICY_FILE" ] || { echo "Missing $POLICY_FILE" >&2; exit 1; }
  command -v ngrok >/dev/null || { echo "ngrok is not on PATH" >&2; exit 1; }
  local attempt
  for attempt in 1 2 3; do
    cmd_stop
    sleep 1
    mkdir -p "$(dirname "$PID_FILE")"
    : >"$LOG_FILE"
    nohup ngrok http "$LOCAL_PORT" \
      --url "$PUBLIC_URL" \
      --traffic-policy-file "$POLICY_FILE" \
      >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    if wait_ready; then
      echo "MCP tunnel ready at $PUBLIC_URL/mcp"
      return 0
    fi
    if [ -f "$LOG_FILE" ] && grep -q 'ERR_NGROK_334' "$LOG_FILE"; then
      echo "Hostname still claimed; retry $attempt" >&2
      continue
    fi
    exit 1
  done
  echo "Could not bind $PUBLIC_URL" >&2
  exit 1
}

cmd_check() {
  local health mcp_body edge api ui
  health="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${LOCAL_PORT}/healthz" || true)"
  [ "$health" = "200" ] || { echo "local MCP /healthz=$health" >&2; exit 1; }
  edge="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$PUBLIC_URL/healthz" || true)"
  [ "$edge" = "404" ] || { echo "public /healthz expected 404, got $edge" >&2; exit 1; }
  mcp_body="$(curl -s --max-time 10 -X POST "$PUBLIC_URL/mcp" \
    -H 'content-type: application/json' \
    -H 'accept: application/json, text/event-stream' \
    -d '{}' || true)"
  case "$mcp_body" in
    *unauthorized*) ;;
    *) echo "public /mcp did not reject an anonymous call: $mcp_body" >&2; exit 1 ;;
  esac
  api="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${DEV_API_PORT:-8001}/health" || true)"
  ui="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${DEV_FE_PORT:-5193}/" || true)"
  [ "$api" = "200" ] || { echo "local API /health=$api" >&2; exit 1; }
  [ "$ui" = "200" ] || { echo "local frontend / =$ui" >&2; exit 1; }
  echo "ok api=$api frontend=$ui mcp=$health edge_healthz=$edge mcp_auth=rejected"
}

case "${1:-}" in
  stop) cmd_stop ;;
  start) cmd_start ;;
  check) cmd_check ;;
  *)
    echo "usage: $0 {start|stop|check}" >&2
    exit 1
    ;;
esac
