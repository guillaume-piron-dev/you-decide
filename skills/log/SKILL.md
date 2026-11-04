---
name: log
description: Appends to the project logs without reading them in full. Records the owner's requests in their exact words, review findings and deferred items, and marks requests done. Use for every new request from the owner, every finding of a review, every item deferred to a later step, and to tick a handled request.
---

# Keep the logs without re-reading them

Logs are **append-only**: never delete a line. Strike it (`~~…~~` + date) or change its state.
If a log file does not exist, the project runs at the light level: skip that log and say so once.

## Requests: `docs/requests_log.md`
- Row appended at the end of the table: `| YYYY-MM-DD HH:MM | "owner's exact words" | state and handling |`.
  Cut long text with `[…]`; never paraphrase.
- State: `⏳`, then `✅` with the file that proves it.
- Contradiction with an earlier request, rule or decision: write it in the row ("contradicts …") and tell the owner
  **before** working.
- Before every report to the owner, check the open rows that the work touched.

## Findings: `docs/findings_log.md`
- Row: `| ID | Review (date, scope) | Severity | Finding | Handling | State | Target | Proof |`
- ID `F-<step>-<n>`. Last number: `grep -o "F-<step>-[0-9]*" docs/findings_log.md | sort -V | tail -1`.
- Severity: `blocking`, `important`, `minor`, `detail`. Handling: `fixed`, `action`, `research`, `expert` (with the
  question id), `decision`. State: `done` or `open`.
- Target: the smallest sub-step that will write the code the finding depends on. Proof: file:line, test name, or where
  the task is written. Never empty.
- Rule: a finding on code or a document that already exists is fixed in the current step, whatever its severity.

## Deferred items: in the plan file named in `docs/state.md`
- Row `| Milestone | Item | Origin |` at the end of the target milestone's rows. Deferred items are part of that
  milestone's work: `session` and `milestone` read them.

## Append safely
- Insert with a short script that reads the file, inserts before a unique marker (or at the end of the table), and
  writes it back with the same encoding (UTF-8 without BOM) and line endings. Then check with `grep -n` that the line
  is where it should be.
- Windows PowerShell: never pipe text with accents through stdin into git or a file. Write a UTF-8 file first.
