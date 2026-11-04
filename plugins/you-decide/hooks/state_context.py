#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""You Decide: re-inject docs/state.md after a compaction or /clear (SessionStart hook).

Prints the first 150 lines of the project's state file as additional context, so that the owner's latest
decisions and next actions survive the summary. Prints nothing if the file does not exist. Standard library only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MAX_LINES = 150
MAX_CHARS = 12_000


def main() -> int:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        event = json.loads(raw) if raw.strip() else {}
        root = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
        state = Path(root) / "docs" / "state.md"
        if not state.is_file():
            return 0
        lines = state.read_text(encoding="utf-8", errors="replace").splitlines()[:MAX_LINES]
        body = "\n".join(lines)[:MAX_CHARS]
        source = event.get("source", "session start")
        context = (f"You Decide: the project state file docs/state.md, re-injected after {source}. "
                   f"Resume from it (skill `session`); search other files instead of reading them in full.\n\n{body}")
        sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                            "additionalContext": context}}))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
