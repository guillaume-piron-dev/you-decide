# CLAUDE.md — {{project_name}}

Read by Claude Code at every session. Keep it under 200 lines: procedures live in the You Decide skills, rules for
specific paths in `.claude/rules/`.

**Method level**: {{level}} · **Owner** (author and decision-maker): {{owner}}

## 1. Owner's rules (non-negotiable)
1. **Language**: answer in {{answer_language}}. Code, identifiers and code comments in {{code_language}}.
2. **Tone**: direct, technical, no filler.
3. **Naming**: {{naming_rules}}
4. **Secrets**: never show, log or commit API keys, tokens, passwords or personal data. Secrets only through
   environment variables or a secret manager. No secret exists in the project folder, even in an ignored file:
   permission rules and hooks are a second barrier, not the first.
5. **Network**: send nothing over the network (push, publish, upload, data-sending request, install from an unlisted
   source) without the owner's explicit "yes".
6. **Deletion**: always ask before deleting a file, folder, branch or data.
7. **Irreversible actions**: always ask (destructive migrations, history rewrite, production changes, real emails).
8. **New dependency or service**: only after the screen of the `decide` skill and the owner's "yes".
9. **Always state the path** of every file created or modified.
{{extra_owner_rules}}

## 2. Red lines of the project
<!-- Rules that must never be broken: legal, safety, privacy, contractual. The reviewer checks every diff against
them. Write them in the owner's words. Delete this section if there are none. -->
{{red_lines}}

## 3. Authorship and AI use
- The owner is the author and decision-maker: architecture, choices, validation of every merge. Claude proposes, the
  owner validates. No large batches of unreviewed code.
- Every significant AI contribution is logged in `docs/ai_usage.md`; commits carry `AI-Assisted: yes`. <!-- level: strict -->

## 4. Stack and decisions
{{stack_summary}}
- Decision records: `docs/decisions/` (skill `decide`). No choice that is costly to reverse is made without one. <!-- level: standard -->

## 5. Commands
| Purpose | Command |
|---|---|
| Build | {{build_cmd}} |
| Test | {{test_cmd}} |
| Lint | {{lint_cmd}} |
| Format | {{format_cmd}} |
| Local CI, before every commit | {{ci_cmd}} |

## 6. Code conventions
{{conventions}}
- Every feature ships with tests; acceptance criteria become tests (skill `story-to-tests`).
- Fix the code rather than suppress a lint rule.
- Commits: {{commit_convention}}

## 7. Data and security
- Fake data only in development and tests. Production data never leaves production: no database copy, backup, log,
  trace or extract.
- An exploited vulnerability is reported to the owner immediately.

## 8. Working method
0. Start or resume with `/you-decide:session`: read `docs/state.md` only, search the rest.
1. Log every new request of the owner in their words before working (skill `log`); flag contradictions. <!-- level: standard -->
2. Propose a short plan (files, risks, tests, approvals needed) **before** writing code. One session = one task.
3. Small verifiable steps; run the tests; show the result.
4. Any legal, security or scope doubt: stop and ask.
5. Review findings are fixed in the step where they are found. No step closes on an open finding.
6. Facts are sourced: ✅ primary source read · 🟡 secondary · 📣 vendor claim · 🧠 unverified · ❓ open question.
7. Questions to the owner: multiple-choice when possible, recommended option first, research done beforehand.
8. Close a step with `/you-decide:close-step`, a milestone with `/you-decide:milestone`.

## 9. Where to find what
- Current state, the only file read in full when resuming: `docs/state.md`
- Requests log: `docs/requests_log.md` · findings log: `docs/findings_log.md` <!-- level: standard -->
- Decisions: `docs/decisions/` · plan: `docs/plan.md` <!-- level: standard -->
{{project_map}}
