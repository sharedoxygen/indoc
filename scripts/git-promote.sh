#!/usr/bin/env bash
# Point development, publish, main, and in-progress at the work tip (same SHA).
# Prefers fast-forward. If a branch history diverged, resets that ref and
# force-with-lease pushes so the promotion branches match.
# in-progress is pushed because it is this repo's GitHub default branch.
# Unsets GITHUB_TOKEN so gh/osxkeychain credentials win over invalid env tokens.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

unset GITHUB_TOKEN

WORK_BRANCH="${GIT_WORK_BRANCH:-in-progress}"

if ! git show-ref --verify --quiet "refs/heads/${WORK_BRANCH}"; then
  echo "Missing work branch: ${WORK_BRANCH}" >&2
  exit 1
fi

TIP="$(git rev-parse "${WORK_BRANCH}")"
TIP_SHORT="$(git rev-parse --short "${TIP}")"

echo "Align promotion branches to ${WORK_BRANCH} @ ${TIP_SHORT}"

current="$(git branch --show-current)"
if [[ "${current}" != "${WORK_BRANCH}" ]]; then
  git checkout "${WORK_BRANCH}"
fi

for b in development publish main; do
  if ! git show-ref --verify --quiet "refs/heads/${b}"; then
    echo "Missing required branch: ${b}" >&2
    exit 1
  fi
  git update-ref "refs/heads/${b}" "${TIP}"
  echo "  ${b} → ${TIP_SHORT}"
done

push_ref() {
  local branch="$1"
  if git rev-parse --verify "origin/${branch}" >/dev/null 2>&1 \
    && git merge-base --is-ancestor "origin/${branch}" "${TIP}" 2>/dev/null; then
    git push origin "${TIP}:refs/heads/${branch}"
  else
    echo "  ${branch}: history diverged — force-with-lease to match ${TIP_SHORT}"
    git push --force-with-lease="${branch}:origin/${branch}" origin "${TIP}:refs/heads/${branch}"
  fi
}

if git remote get-url origin >/dev/null 2>&1; then
  echo "Pushing aligned tips to origin…"
  git fetch origin
  for b in development publish main "${WORK_BRANCH}"; do
    push_ref "$b"
  done
  git fetch origin
  for b in development publish main "${WORK_BRANCH}"; do
    git update-ref "refs/heads/${b}" "$(git rev-parse "origin/${b}")"
  done
else
  echo "No origin remote; local branches updated only." >&2
fi

echo "git-promote complete: ${TIP_SHORT} (${WORK_BRANCH}, development, publish, main aligned)"
