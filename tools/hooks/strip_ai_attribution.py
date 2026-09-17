#!/usr/bin/env python3
"""
commit-msg hook: strip AI-tool attribution trailers from a commit message.

Belt-and-suspenders guard alongside `attribution: {commit: "", pr: ""}` in
.claude/settings.json. Runs on every commit made from this clone, no matter
what tool wrote the message.

Removes lines matching any of:
    Co-Authored-By: Claude ... <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/...
    🤖 Generated with [Claude Code](...)

Wired up two ways:
  - .pre-commit-config.yaml (stage: commit-msg)  ->  pre-commit install --hook-type commit-msg
  - or directly:  cp tools/hooks/strip_ai_attribution.py .git/hooks/commit-msg
"""
import re
import sys

TRAILER_RE = re.compile(
    rb"^[ \t]*("
    rb"Co-Authored-By:[ \t]*Claude\b.*"
    rb"|Claude-Session:.*"
    rb"|.*Generated with \[Claude Code\].*"
    rb"|.*noreply@anthropic\.com.*"
    rb")[ \t]*\r?\n?",
    re.IGNORECASE | re.MULTILINE,
)


def clean(message: bytes) -> bytes:
    cleaned = TRAILER_RE.sub(b"", message)
    cleaned = re.sub(rb"\n{3,}", b"\n\n", cleaned)
    return cleaned.rstrip(b" \t\r\n") + b"\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: strip_ai_attribution.py <commit-msg-file>", file=sys.stderr)
        return 2
    path = argv[1]
    with open(path, "rb") as f:
        original = f.read()
    cleaned = clean(original)
    if cleaned != original:
        with open(path, "wb") as f:
            f.write(cleaned)
        print("commit-msg: stripped AI attribution trailer(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
