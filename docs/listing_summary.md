# You Decide

A human-gated development method for Claude Code: the owner decides, Claude executes. Ten skills cover the whole
loop (setup, session, log, decide, story-to-tests, review, close-step, milestone, compliance, memory), a `reviewer` subagent
reviews each diff independently, and hooks ask for the owner's "yes" before network sends or irreversible commands,
block secrets written to files and re-inject the state file after a compaction. Start with `/you-decide:setup` in
your project. Full documentation, levels, guardrails, regional adaptation and limits: see the README at the root of the repository.

## Install

```
/plugin marketplace add guillaume-piron-dev/you-decide
/plugin install you-decide@you-decide
```
