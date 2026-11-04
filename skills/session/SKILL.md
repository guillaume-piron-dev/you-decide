---
name: session
description: Starts or resumes a work session at the lowest context cost. Reads the state file, logs any new request in the owner's words, reads only what the task touches, then proposes a short plan before any code. Use at the start of every session, after /clear or a compaction, or when the user says "let's resume", "continue", "next", "where are we".
---

# Start or resume a session

Goal: be operational after reading less than ~10,000 tokens. Never read large logs or registers in full.

## Steps
Light level (only CLAUDE.md and `docs/state.md` exist): skip the logs and decision records below; check new requests
against CLAUDE.md and `docs/state.md`, and treat the state file's next actions as the plan.

1. Read `docs/state.md`, the only file read in full. If it is missing, suggest `/you-decide:setup` and stop.
2. New request from the owner? Log it first, in their exact words (skill `log`). Flag any contradiction with an earlier
   request, rule or decision (grep the topic in `docs/requests_log.md` and `docs/decisions/`).
3. Read only what the task touches, by targeted search:
   - the step: grep its id in the plan file named in `docs/state.md`, plus that milestone's deferred items;
   - the user story: grep its id, read its title and acceptance criteria only;
   - open findings for this step: grep `open` and the step id in `docs/findings_log.md`;
   - a decision: grep its id in `docs/decisions/`, read that record.
4. Propose a short plan **before writing code**: files touched, risks, tests, and anything that needs the owner's yes
   (network, new dependency or service, deletion, irreversible action). One session = one task.
5. Any legal, security or scope doubt: stop and ask, with a multiple-choice question when possible.

## Budget
- Use the cheapest model that is good enough for routine steps. Switch to the most capable one for architecture
  decisions or a bug the first one could not solve.
- `/clear` between two tasks. Plan mode before writing code. Subagents only for a wide, isolated read.
- To check a fix, run the test that proves it. Do not re-run a full review.

## Never
- `/clear`, or let a compaction happen, while a decision of the owner is written nowhere. First log it and update
  `docs/state.md`: what is not in a file is lost at `/clear` and can be distorted by a compaction summary.
- Re-read CLAUDE.md, the logs, the plan and the decisions in full after a compaction. Read `docs/state.md`, search
  the rest.
- Start a long run, a download or any network access without the owner's yes.
