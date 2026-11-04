---
name: story-to-tests
description: Turns a user story or plan step into tests first (one per acceptance criterion and per edge case), then writes the smallest code that passes them, then traces coverage. Use at the start of implementing a user story, a feature or a step of the plan.
---

# Story to tests to code

## 1. Read just enough
- The story: grep its id, read its title and acceptance criteria only.
- Edge cases and test strategy, if the project keeps them: grep the story id or theme.
- Existing coverage (strict level): grep the story id in `docs/traceability.csv`.

## 2. Tests first
- One test per acceptance criterion and per edge case touched, named after the behaviour
  (`reset_token_is_single_use`). Put it in the module that owns the rule: pure domain logic without I/O first, then
  integration, then end-to-end.
- Fake data only. Production data never goes into tests or development.
- Prove each test can fail: run it before the code exists, or mutate one key line afterwards and watch it fail.

## 3. Implement
- The smallest change that makes the tests pass. Errors are handled or typed, never swallowed; no crash shortcuts
  (unchecked unwrap, bare panic, empty catch) outside tests and start-up. Follow the conventions in CLAUDE.md.
- Run format, lint and tests on the touched module first (commands in CLAUDE.md). The full local CI runs at step
  closure (`close-step`).

## 4. Trace (strict level)
One row per covered criterion in `docs/traceability.csv`:
`feature_id,story_id,criterion,test_name,test_file,status`. Status is `partial` until every criterion of the story is
covered, then `covered`.
