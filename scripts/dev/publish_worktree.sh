#!/usr/bin/env bash
# Ensure a local git worktree for refs/heads/publish (saas build source).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
WORKTREE_DIR="${PUBLISH_WORKTREE:-$ROOT_DIR/.worktrees/publish}"
BRANCH="${PUBLISH_BRANCH:-publish}"

die() { echo "ERROR: $*" >&2; exit 1; }

cmd="${1:-ensure}"

case "$cmd" in
  path)
    echo "$WORKTREE_DIR"
    ;;
  sha)
    git -C "$ROOT_DIR" rev-parse "refs/heads/$BRANCH"
    ;;
  ensure)
    git -C "$ROOT_DIR" show-ref --verify --quiet "refs/heads/$BRANCH" \
      || die "local branch '$BRANCH' does not exist (refs/heads/$BRANCH)"

    mkdir -p "$(dirname "$WORKTREE_DIR")"

    if [ -d "$WORKTREE_DIR/.git" ] || [ -f "$WORKTREE_DIR/.git" ]; then
      current="$(git -C "$WORKTREE_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
      if [ "$current" != "$BRANCH" ]; then
        die "worktree at $WORKTREE_DIR is on '$current', expected '$BRANCH' (remove it and retry)"
      fi
      # Sync worktree files to current local publish tip (shared ref; no primary checkout).
      git -C "$WORKTREE_DIR" reset --hard "refs/heads/$BRANCH" >/dev/null
    else
      if [ -e "$WORKTREE_DIR" ] && [ -n "$(ls -A "$WORKTREE_DIR" 2>/dev/null || true)" ]; then
        die "path exists but is not a git worktree: $WORKTREE_DIR"
      fi
      rm -rf "$WORKTREE_DIR"
      git -C "$ROOT_DIR" worktree add "$WORKTREE_DIR" "$BRANCH"
    fi

    current="$(git -C "$WORKTREE_DIR" rev-parse --abbrev-ref HEAD)"
    [ "$current" = "$BRANCH" ] || die "worktree HEAD is '$current', expected '$BRANCH'"

    sha="$(git -C "$WORKTREE_DIR" rev-parse HEAD)"
    echo "$WORKTREE_DIR"
    echo "PUBLISH_SHA=$sha" >&2
    ;;
  *)
    die "usage: $0 {ensure|path|sha}"
    ;;
esac
