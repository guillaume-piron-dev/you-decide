---
name: compliance
description: Handles a legal or regulatory question (privacy, consumer law, AI rules, sector rules, licensing) without ever giving personalised legal advice. Finds primary sources, writes a stand-alone question an expert can answer, proposes a position marked as unconfirmed, and keeps a single question file. Use when a task touches law, regulation or licensing, or when a message to a lawyer, regulator or authority must be prepared.
---

# Legal and regulatory questions

## Principles
- Claude is not a lawyer. It finds the sources, writes the question and proposes a position. Only a lawyer, the
  regulator or the competent body settles what is marked EXPERT REQUIRED. Never present a position as settled.
- Read primary sources (official journals, legislation databases, regulator guidance) before citing them. If
  automatic access is blocked, ask the owner to open the page instead of citing from memory.
- Tags: ✅ primary source read · 🟡 secondary source · 🧠 unverified.

## One file: `docs/compliance_questions.md`
- Search first: `grep -n "^### Q-" docs/compliance_questions.md`, then a keyword. Read only the matching entry.
- States: `SETTLED`, `DECIDED` (by the owner), `TO VALIDATE ❓`, `EXPERT REQUIRED ❓`.
- New question: next id (`grep -o "Q-[0-9]*" docs/compliance_questions.md | sort -V | tail -1`), entry under its
  theme: `### Q-nn — Title`, then **State**, **Facts** (sourced), **Position**, **Question** (a stand-alone text that
  an expert understands without knowing the project: context, legal texts, numbered questions, what we plan, the answer
  we expect), **Channel** (free channel first, then paid recourse), **Before sending**, **Affects** (decisions,
  stories).
- Update the summary table at the top of the file. Other documents cite `Q-nn`; they never copy the entry.

## Sending
Claude sends nothing. It prepares the text; the owner sends it from their own account, after Claude has re-read every
primary source cited.

Light or standard level (no question file): answer in the conversation with sources and the same caution, and offer to
create the file.
