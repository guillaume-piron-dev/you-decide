---
name: decide
description: Turns a structural choice into a sourced decision that the owner makes. Researches the options first, screens every service or dependency, asks a 2–4 option multiple-choice question, then writes the decision record. Use before choosing an architecture, a library, a service, a data model, a hosting provider or anything costly to reverse, or when the user asks "which one should we use".
---

# Decide: the owner decides, Claude prepares

## 1. Research before proposing
- Read official documentation, changelogs, licenses, security advisories and maintenance activity. Tag every fact:
  ✅ primary source read · 🟡 secondary source · 📣 vendor claim · 🧠 unverified · ❓ open question.
- Never invent a mechanism, delay, workaround or default that the owner has not decided. Present it as an option.

## 2. Screen every service, tool or dependency (answers written down)
1. Where does the data go, and under which jurisdiction? Compare with the project's jurisdictions in CLAUDE.md.
2. Who operates it, and under which law? (A company subject to a foreign law stays subject to it wherever it hosts.)
3. License, and is it compatible with the project's license?
4. Cost now and at scale. Free until the end of development?
5. Can we reasonably do it ourselves, and at what cost?

Also: maintenance (last release, open security issues), lock-in and exit path.
One unfavourable answer: do not propose the option, or propose it and say so plainly.

## 3. Ask
- One AskUserQuestion with 2–4 options. Put your recommendation first, marked "(Recommended)". Give each option its
  main trade-off in one line. The question must make sense on its own.
- If the choice is cheap to reverse, say so and propose a default instead of asking.

## 4. Record
- `docs/decisions/NNNN_short_title.md` from `docs/decisions/0000_template.md`: context, options with sourced facts,
  the decision **taken by the owner** with its date, consequences, and what would make us revisit it.
  Next number: `ls docs/decisions | sort | tail -1`.
- Log the owner's answer in `docs/requests_log.md` (skill `log`). Update `docs/state.md` if the next actions change.
- Light level (no `docs/decisions/`): write the decision as one dated line in `docs/state.md`.
