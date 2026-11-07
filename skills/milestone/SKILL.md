---
name: milestone
description: Closes a milestone with a full re-verification. Checks every planned step, deferred item and request, reviews the whole milestone, compares with the best comparable products, records measured baselines and writes a hand-off so the next milestone starts in a fresh conversation. Use when the owner says a milestone or phase is finished or asks to close it.
---

# Close a milestone

1. **Plan against reality.** List every step, deferred item and request of the milestone with its proof (file, test,
   commit). Anything not done is done now, or moved by the owner's decision (AskUserQuestion). Never silently.
2. **Whole-milestone review.** Run the `review` skill on the milestone's full range
   (`git diff <milestone-start>...HEAD`). Findings are fixed in the flow.
3. **Compare with the best.** What do the best comparable products or libraries do for this scope? Record the gaps as
   deferred items or decisions, with sourced facts (✅ 🟡 📣 🧠).
4. **Measure.** Run the performance, load or size checks the project defines. Record each number with its date,
   machine and command in `docs/state.md` or a benchmarks file. Never write a number that was not measured.
5. **Security pass.** Dependency audit and secret scan with the project's own tools, offline by default.
6. **Completeness review** (standard and strict): the `memory` skill's review, then its end-of-step commands, and
   the claude.ai Project copy if enabled.
7. **Hand-off.** Update `docs/state.md` so that a fresh session can start from it alone, log the closure in
   `docs/requests_log.md` (standard and strict levels), and recommend starting the next milestone in a new
   conversation.

Light level: steps 1 to 5 and 7 apply to the next actions in `docs/state.md` instead of a plan file, without logs.
