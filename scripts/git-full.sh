#!/usr/bin/env bash
# git full: resolve WIP → quality gate → promote → verify branch alignment.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

unset GITHUB_TOKEN

WORK_BRANCH="${GIT_WORK_BRANCH:-in-progress}"
COMMIT_MSG="${GIT_FULL_COMMIT_MSG:-wip: auto-commit before promotion}"
RESOLVE=0
SKIP_QUALITY=0
SKIP_COMMIT=0
PROMOTE_BASE_SHA=""
PROMOTE_BASE_SHORT=""
PROMOTE_BASE_LABEL=""
SUMMARY_MAX_COMMITS="${GIT_FULL_SUMMARY_MAX:-40}"

usage() {
  cat <<'EOF'
Usage: scripts/git-full.sh [OPTIONS]

Full promotion pipeline for inDoc:
  1. Preflight (work branch, required promotion branches)
  2. Commit hooks (pre-commit install when .pre-commit-config.yaml exists)
  3. Resolve dirty worktree (auto-commit WIP unless --skip-commit)
  4. make quality (unless --resolve / --skip-quality / GIT_FULL_SKIP_QUALITY=1)
  5. scripts/git-promote.sh (in-progress, development, publish, main + origin)
  6. Verification report + promotion summary (commits and files promoted)

Options:
  --resolve, -resolve   Commit and promote only. Skip make quality.
  --skip-quality        Skip make quality (same effect as --resolve for that step).
  --skip-commit         Fail if the worktree is dirty instead of auto-committing.
  -h, --help            Show this help.

Environment:
  GIT_WORK_BRANCH       Work branch (default: in-progress)
  GIT_FULL_COMMIT_MSG   Auto-commit message (default: wip: auto-commit before promotion)
  GIT_FULL_SKIP_QUALITY=1   Skip quality gate
  GIT_FULL_ARGS         Passed from Makefile (e.g. make git-full GIT_FULL_ARGS="--resolve")
  GIT_FULL_SUMMARY_MAX  Max commits listed in the promotion summary (default: 40)

Also: make git-full | make git-promote (promote only; requires a clean worktree)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resolve | -resolve) RESOLVE=1; shift ;;
    --skip-quality) SKIP_QUALITY=1; shift ;;
    --skip-commit) SKIP_COMMIT=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${GIT_FULL_SKIP_QUALITY:-0}" == "1" ]]; then
  SKIP_QUALITY=1
fi

worktree_dirty() {
  ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]
}

require_branch() {
  local name="$1"
  if ! git show-ref --verify --quiet "refs/heads/${name}"; then
    echo "Missing required branch: ${name}" >&2
    exit 1
  fi
}

print_step() {
  echo ""
  echo "==> $1"
}

capture_promotion_base() {
  PROMOTE_BASE_LABEL="development"
  PROMOTE_BASE_SHA="$(git rev-parse development)"
  PROMOTE_BASE_SHORT="$(git rev-parse --short development)"

  if git remote get-url origin >/dev/null 2>&1; then
    git fetch origin --quiet 2>/dev/null || true
    if git show-ref --verify --quiet refs/remotes/origin/development; then
      PROMOTE_BASE_LABEL="origin/development"
      PROMOTE_BASE_SHA="$(git rev-parse origin/development)"
      PROMOTE_BASE_SHORT="$(git rev-parse --short origin/development)"
    fi
  fi
}

preflight() {
  print_step "Preflight"
  require_branch "${WORK_BRANCH}"
  for b in development publish main; do
    require_branch "$b"
  done
  local current
  current="$(git branch --show-current)"
  if [[ "${current}" != "${WORK_BRANCH}" ]]; then
    echo "Checking out ${WORK_BRANCH} (was on ${current})"
    git checkout "${WORK_BRANCH}"
  fi
  capture_promotion_base
}

ensure_commit_hooks() {
  print_step "Commit hooks (pre-commit install)"
  if [[ ! -f .pre-commit-config.yaml ]]; then
    echo "No .pre-commit-config.yaml — skipping hook install."
    return 0
  fi
  if ! command -v pre-commit >/dev/null 2>&1; then
    echo "pre-commit is required (.pre-commit-config.yaml exists) but is not on PATH." >&2
    exit 1
  fi
  pre-commit install
  if [[ ! -x .git/hooks/pre-commit ]]; then
    echo "pre-commit install did not create an executable .git/hooks/pre-commit" >&2
    exit 1
  fi
  if ! grep -q 'pre-commit' .git/hooks/pre-commit; then
    echo ".git/hooks/pre-commit exists but is not a pre-commit hook" >&2
    exit 1
  fi
  echo "pre-commit hook installed ($(pre-commit --version))"
}

print_promotion_summary() {
  print_step "Promotion summary"
  local tip tip_short commit_count hidden_count
  tip="$(git rev-parse HEAD)"
  tip_short="$(git rev-parse --short HEAD)"

  if [[ -z "${PROMOTE_BASE_SHA}" ]]; then
    echo "Baseline unknown — could not compare against ${PROMOTE_BASE_LABEL:-development}."
    return 0
  fi

  echo "Baseline: ${PROMOTE_BASE_LABEL} @ ${PROMOTE_BASE_SHORT}"
  echo "Promoted tip: ${WORK_BRANCH} @ ${tip_short}"
  echo ""

  if [[ "${PROMOTE_BASE_SHA}" == "${tip}" ]]; then
    echo "No new commits since last promotion (${PROMOTE_BASE_LABEL} already at ${tip_short})."
    return 0
  fi

  commit_count="$(git rev-list --count "${PROMOTE_BASE_SHA}..${tip}" 2>/dev/null || echo 0)"
  echo "Promoted ${commit_count} commit(s): ${PROMOTE_BASE_SHORT}..${tip_short}"
  echo ""
  echo "Commits:"
  if [[ "${commit_count}" -le "${SUMMARY_MAX_COMMITS}" ]]; then
    git log --oneline "${PROMOTE_BASE_SHA}..${tip}"
  else
    git log --oneline -"${SUMMARY_MAX_COMMITS}" "${PROMOTE_BASE_SHA}..${tip}"
    hidden_count=$((commit_count - SUMMARY_MAX_COMMITS))
    echo "... and ${hidden_count} more commit(s) (set GIT_FULL_SUMMARY_MAX to raise cap)"
  fi
  echo ""
  echo "Files changed:"
  git diff --stat "${PROMOTE_BASE_SHA}..${tip}"
}

resolve_wip() {
  print_step "Resolve worktree"
  if ! worktree_dirty; then
    echo "Worktree clean — no correction commit needed."
    return 0
  fi
  if [[ "${SKIP_COMMIT}" -eq 1 ]]; then
    echo "Worktree is dirty and --skip-commit was set." >&2
    git status -sb >&2
    exit 1
  fi
  echo "Dirty worktree detected — creating correction commit:"
  git status -sb
  git add -A
  if git diff --cached --quiet; then
    echo "Nothing to commit after git add -A." >&2
    exit 1
  fi
  git commit -m "${COMMIT_MSG}"
  echo "Correction commit: $(git rev-parse --short HEAD) — ${COMMIT_MSG}"
}

run_quality() {
  if [[ "${RESOLVE}" -eq 1 || "${SKIP_QUALITY}" -eq 1 ]]; then
    print_step "Quality gate (skipped)"
    if [[ "${RESOLVE}" -eq 1 ]]; then
      echo "Skipped because --resolve was set (commit + promote only)."
    else
      echo "Skipped because --skip-quality was set."
    fi
    return 0
  fi
  print_step "Quality gate (make quality)"
  make quality
}

verify_alignment() {
  print_step "Verification"
  local tip local_dev local_pub local_main
  tip="$(git rev-parse --short HEAD)"
  local_dev="$(git rev-parse --short development)"
  local_pub="$(git rev-parse --short publish)"
  local_main="$(git rev-parse --short main)"

  echo "HEAD (${WORK_BRANCH}): ${tip}"
  echo ""
  printf "%-14s %-10s %-10s %s\n" "Branch" "Local" "Origin" "Synced"
  printf "%-14s %-10s %-10s %s\n" "------" "-----" "------" "------"

  local synced_all=1
  for b in development publish main "${WORK_BRANCH}"; do
    local local_sha remote_sha mark
    local_sha="$(git rev-parse --short "${b}")"
    if git show-ref --verify --quiet "refs/remotes/origin/${b}"; then
      remote_sha="$(git rev-parse --short "origin/${b}")"
      if [[ "${local_sha}" == "${remote_sha}" ]]; then
        mark="yes"
      else
        mark="NO"
        synced_all=0
      fi
    else
      remote_sha="—"
      mark="no origin"
      synced_all=0
    fi
    printf "%-14s %-10s %-10s %s\n" "${b}" "${local_sha}" "${remote_sha}" "${mark}"
  done

  echo ""
  if worktree_dirty; then
    echo "Worktree: DIRTY (unexpected after git full)" >&2
    git status -sb
    exit 1
  fi
  echo "Worktree: clean"

  if [[ "${local_dev}" == "${tip}" && "${local_pub}" == "${tip}" && "${local_main}" == "${tip}" ]]; then
    echo "Local promotion chain: aligned at ${tip}"
  else
    echo "Local promotion chain: MISALIGNED (expected all == ${tip}; got development=${local_dev} publish=${local_pub} main=${local_main})" >&2
    exit 1
  fi

  if git remote get-url origin >/dev/null 2>&1; then
    if [[ "${synced_all}" -eq 1 ]]; then
      echo "Origin branches (development, publish, main, ${WORK_BRANCH}): synced"
    else
      echo "Origin branches: NOT fully synced" >&2
      exit 1
    fi
  else
    echo "No origin remote — local branches updated only."
  fi

  echo ""
  echo "git-full complete: ${tip} (${WORK_BRANCH}, development, publish, main aligned)"
}

preflight
ensure_commit_hooks
resolve_wip
run_quality
"$(dirname "$0")/git-promote.sh"
print_promotion_summary
verify_alignment
