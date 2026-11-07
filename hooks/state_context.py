#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""You Decide: resume context after a compaction or /clear (SessionStart hook).

With project memory configured (docs/memory/config.json), gives the memory skill's resume text: the state file, the
open rows of the logs and the last questions and answers, after recording any new answer from the transcript.
Without it, gives the first 150 lines of docs/state.md. Prints nothing when neither exists. Standard library only.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

MAX_CHARS = 12_000
MEMORY = Path(__file__).resolve().parents[1] / "skills" / "memory" / "scripts"


def context_for(root: Path, transcript: str | None) -> str:
    if (root / "docs" / "memory" / "config.json").is_file():
        try:
            sys.path.insert(0, str(MEMORY))
            import yd_memory  # type: ignore

            with contextlib.redirect_stdout(io.StringIO()):  # the hook's stdout must hold only its JSON
                cfg = yd_memory.load_config(root)
                return yd_memory.resume_text(root, cfg, Path(transcript) if transcript else None)
        except Exception as error:  # a malformed memory config falls back to the plain state file
            print(f"you-decide: memory resume unavailable ({error})", file=sys.stderr)
    state = root / "docs" / "state.md"
    if not state.is_file():
        return ""
    return "\n".join(state.read_text(encoding="utf-8", errors="replace").splitlines()[:150])


def main() -> int:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        event = json.loads(raw) if raw.strip() else {}
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd())
        body = context_for(root, event.get("transcript_path"))[:MAX_CHARS]
        if not body.strip():
            return 0
        source = event.get("source", "session start")
        context = (f"You Decide: project state re-injected after {source}. Resume from it (skills `session` and "
                   f"`memory`); search other files instead of reading them in full.\n\n{body}")
        sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                            "additionalContext": context}}))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
