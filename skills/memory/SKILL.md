---
name: memory
description: Keeps the project's memory so that nothing is lost, shortened or rewritten. Records the owner's multiple-choice answers word for word, guards the logs against loss, moves closed rows to volumes verbatim, keeps a reference map, backs up the transcript before a compaction and gives the resume context after it, and optionally keeps a private journal and a light copy for a claude.ai Project. Use after each answer of the owner to a multiple-choice question, at the end of each step, before a long task, after a compaction, and once per milestone for the completeness review.
---

# Keep the project's memory

Principle: **nothing disappears, everything can be found, every loss shows.** The committed repository is the source;
everything else is derived from it or appended to it.

Tool: `python3 "<this skill's base directory>/scripts/yd_memory.py" <command>` (on Windows, `py -3` instead of
`python3`), run from the project root. Settings: `docs/memory/config.json`, written by `setup` at the standard and
strict levels (`init` writes the default). **Light level** (no config): only `docs/state.md` and the resume hook exist;
say so and stop.

## 1. After each answer of the owner to a multiple-choice question (at once, before going on)
1. `qa`: the question, its options and the answer, word for word, appended to `docs/questions_answers.md`. Without a
   path it reads the newest transcript of this project (`--all`: every one). A question still waiting for its answer is
   left for the next run. A possible secret or IP address holds the entry back: re-read it, then `--accept <call id>`.
2. A row in the requests log (skill `log`) that points to `docs/questions_answers.md`; the decision written where it
   belongs (plan, decision record).
3. Update `docs/state.md` if the next actions change.

## 2. Before a long task, and whenever something runs in the background
Write in `docs/state.md` what is running, how to check its result and the next three actions. After a compaction, the
resume reads that file, not the conversation.

## 3. After a compaction
The `SessionStart` hook already put the resume context in the conversation (state, open rows, last answers); otherwise
run `resume`. Then re-read each file it names before acting, search the rest with `grep` and `docs/memory/map/`, and
never guess a lost detail: when backups are enabled, the transcript from before the compaction is in the backup folder
of the config (outside the repository).

## 4. At the end of each step (with `close-step`)
Before the step's commit:
1. `move`: closed rows of the logs from past months go to their volume (`docs/memory/volumes/<log>/<YYYY-MM>.md`),
   and the oldest entries of the state file's update log go to `docs/memory/state_history.md` once the state passes
   its line budget. Moved verbatim; the command refuses if the lines before and after are not the same.
2. `map`: regenerates `docs/memory/map/` (where each id is defined, who cites it, open rows, ids defined nowhere).
3. `guard --update`: records what is new in `docs/memory/conservation.json`, and refuses a loss (a protected cell
   changed, an append-only line gone, an id written nowhere) unless declared with `--accept "reason"`. **Never accept
   by reflex**: re-read each loss and undo it if it was not intended.
4. `check`: fails on a loss, a missing conservation register or an out-of-date map, and lists what is waiting to be
   moved. `close-step` runs it at every step end; to run it in the project's own CI too, copy the script into the
   project (for example `tools/yd_memory.py`) and refresh that copy after a plugin update.

After the step's commit:
5. Private journal, if enabled: `journal --all`. It appends the owner's messages and answers, word for word, to a file
   outside the repository, each message once. A possible secret or IP address stops the writing: re-read that
   message, then rerun with `--accept <id>`.
6. claude.ai Project copy, if enabled: `sync` prepares the changed documents as they are in the last commit (never the
   working tree) in a new `upload_<commit>` folder, with `project_manifest.md`; it refuses to run until its folder is
   ignored by git. The owner uploads them, or a Claude
   session with access to the Project does, smallest growth first. Then run `sync --done`. Remove a document from the
   Project only with the owner's "yes".

## 5. Volumes
A log keeps its open rows and recent closed rows. Older closed rows live in volumes, moved verbatim by the script, never
retyped, summarised or shortened. To withdraw a row, write it in its state column; never edit a protected column (the
owner's words, a finding, a question).

## 6. Completeness review (once per milestone, and on request)
- Requests still `⏳` whose work is done: set them to `✅` with the proof.
- Decisions without a follow-up in the plan.
- References to an id defined nowhere (`docs/memory/map/README.md`).
- Open findings without a valid target.
- State file and update log up to date.

## Never
- Rewrite a memory file from memory, or from a tool output that may be truncated: use an exact replacement or the
  script.
- Keep a decision, a question, a failed run or the state of a running task only in the conversation.
- Shorten or "clean up" a log, the state or a document to save space: move, never cut.
