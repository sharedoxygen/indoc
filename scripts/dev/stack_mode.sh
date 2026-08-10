#!/usr/bin/env bash
# Exclusive stack mode lock + liveness helpers for make dev / make saas.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TMP_DIR="${TMP_DIR:-$ROOT_DIR/tmp}"
LOCK_FILE="${STACK_MODE_FILE:-$TMP_DIR/stack.mode}"
DEV_API_PORT="${DEV_API_PORT:-8001}"
SAAS_API_PORT="${SAAS_API_PORT:-8011}"
DOCKER_BIN="${DOCKER_BIN:-docker}"

die() { echo "ERROR: $*" >&2; exit 1; }

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -nP >/dev/null 2>&1
  else
    nc -z localhost "$port" >/dev/null 2>&1
  fi
}

pidfile_alive() {
  local f="$1"
  [ -f "$f" ] || return 1
  local pid
  pid="$(tr -d '[:space:]' <"$f" || true)"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null
}

saas_containers_live() {
  "$DOCKER_BIN" ps --format '{{.Names}}' 2>/dev/null | grep -qE '^indoc-(backend|celery-worker)$'
}

dev_live() {
  pidfile_alive "$TMP_DIR/backend.pid" && return 0
  pidfile_alive "$TMP_DIR/frontend.pid" && return 0
  # Dev API port owned by a local listener (not saas).
  if port_in_use "$DEV_API_PORT" && ! saas_containers_live; then
    return 0
  fi
  return 1
}

saas_live() {
  saas_containers_live && return 0
  if port_in_use "$SAAS_API_PORT"; then
    return 0
  fi
  return 1
}

read_mode() {
  if [ -f "$LOCK_FILE" ]; then
    # shellcheck disable=SC1090
    . "$LOCK_FILE"
    echo "${MODE:-}"
  fi
}

write_mode() {
  local mode="$1"
  local sha="${2:-}"
  mkdir -p "$TMP_DIR"
  cat >"$LOCK_FILE" <<EOF
MODE=$mode
SHA=$sha
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
DEV_API_PORT=$DEV_API_PORT
SAAS_API_PORT=$SAAS_API_PORT
EOF
}

clear_mode() {
  rm -f "$LOCK_FILE"
}

assert_can_start() {
  local want="$1"
  local locked
  locked="$(read_mode || true)"

  if [ "$want" = "dev" ]; then
    if saas_live; then
      die "saas stack is running (API :$SAAS_API_PORT / indoc containers). Run: make stop"
    fi
    if [ "$locked" = "saas" ]; then
      echo "WARNING: stale stack.mode=saas (containers not live); clearing" >&2
      clear_mode
    fi
    if port_in_use "$DEV_API_PORT"; then
      die "dev API port :$DEV_API_PORT already in use. Run: make stop"
    fi
  elif [ "$want" = "saas" ]; then
    if dev_live; then
      die "dev stack is running (API :$DEV_API_PORT). Run: make stop"
    fi
    if [ "$locked" = "dev" ]; then
      echo "WARNING: stale stack.mode=dev (processes not live); clearing" >&2
      clear_mode
    fi
    if port_in_use "$SAAS_API_PORT"; then
      die "saas API port :$SAAS_API_PORT already in use. Run: make stop"
    fi
    if saas_live; then
      die "saas containers already running. Run: make stop"
    fi
  else
    die "assert_can_start: unknown mode '$want'"
  fi
}

detect_mode() {
  if saas_live; then
    echo "saas"
  elif dev_live; then
    echo "dev"
  else
    locked="$(read_mode || true)"
    if [ -n "$locked" ]; then
      echo "stale:$locked"
    else
      echo "none"
    fi
  fi
}

cmd="${1:-}"
case "$cmd" in
  assert-can-start) assert_can_start "${2:-}" ;;
  write) write_mode "${2:-}" "${3:-}" ;;
  clear) clear_mode ;;
  read) read_mode; echo ;;
  detect) detect_mode ;;
  dev-live) dev_live ;;
  saas-live) saas_live ;;
  *)
    die "usage: $0 {assert-can-start|write|clear|read|detect|dev-live|saas-live} ..."
    ;;
esac
