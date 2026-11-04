---
name: close-step
description: Closes a step or task. Gets the local CI green, closes the step's findings, logs traceability and AI usage, updates the state file, makes a local commit and sends a short report to the owner. Use when a step's code is written and tested, or when the user says "commit", "close the step", "wrap up", "finish".
---

# Close a step

## 1. Local CI
Run the CI command written in CLAUDE.md, offline by default. On failure, fix the cause: never disable a check, never
add a lint suppression to make it pass. Read only the last lines of the output.

## 2. Findings of the step (standard and strict levels)
Grep the open findings that target this step in `docs/findings_log.md`. All are fixed and closed before the commit,
or moved to the sub-step that writes the code they depend on, with the reason written. **No step closes on an open
finding.** If no review was done for this step, run the `review` skill first.

## 3. Traceability and AI usage (strict level)
- One row per covered criterion in `docs/traceability.csv` (format in `story-to-tests`).
- One row appended to `docs/ai_usage.md` **without reading the file**:
  `| date | tool and model; what was verified (build, lint, tests, human review) | files | contribution | human decision or change | follow-up |`

## 4. State
Update `docs/state.md`: current step, the next three actions, what the owner must decide, date. Keep it under 150
lines; whatever leaves it must already be written elsewhere (plan, logs, decisions).

## 5. Local commit
- Commit convention from CLAUDE.md; body in factual bullets; findings cited by id; trailers as configured
  (for example `AI-Assisted: yes`, and `Signed-off-by` through `git commit -s`).
- `git add` only the step's files: never scratch files, build output, secrets or real data.
- Write the message to a UTF-8 file and run `git commit -F <file>`. Check with `git log -1 --format=%s`.
- **Never push** without the owner's explicit "yes" at that moment. Never `--amend`, `reset` or `rebase` without them.

## 6. Report
Short: what is done, the path of every created or modified file, the CI result, what the owner must decide.
Standard and strict levels: tick the request in `docs/requests_log.md` (skill `log`).
