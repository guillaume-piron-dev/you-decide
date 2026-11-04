---
name: review
description: Runs one independent, diff-scoped review of a step before its commit (project red lines, security, conventions, test strength) through the reviewer subagent, then fixes every finding in the flow. Use once per step before committing, or at milestone closure. Not after each small fix.
---

# Diff-scoped review

One review per step. It reads the diff, not the whole repository.

1. Delegate to the `reviewer` subagent. It has an independent context: it has not seen the work being produced, so
   the work does not grade itself. Give it:
   - the range to review (`git diff` for uncommitted work, `git diff <base>...HEAD` otherwise);
   - the red lines and conventions sections of CLAUDE.md;
   - the stories or steps touched.
2. It returns findings: severity, file:line, why it matters, suggested fix.
3. Handle **every** finding:
   - on code or a document that exists: fix it now, in this step, whatever its severity, or write a decision with
     the owner;
   - depends on code not written yet: target the sub-step that will write it, where it becomes a mandatory test.
4. Log every finding (skill `log`), fixed ones as `fixed` / `done`.
5. Do not re-run a full review after the fixes. One test or one proof line per finding is enough.

Light level (no findings log): list the findings and their fixes in the step report.
