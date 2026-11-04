---
name: setup
description: Sets up the You Decide method in a repository. Detects the stack, interviews the owner with multiple-choice questions, then writes a CLAUDE.md under 200 lines, the state and log files and a permissions file at the level the owner picks (light, standard or strict). Use when the user runs /you-decide:setup or asks to set up, bootstrap or adopt this method in a project.
disable-model-invocation: true
---

# Set up the method in this project

Principle: **the owner decides, Claude executes.** Nothing is written before the owner approves the plan (step 4).
Answer in the owner's language. Templates are in the `templates/` folder of this skill's base directory.

## 1. Look before asking (read-only)
- Detect the stack from manifests: `package.json`, `pnpm-workspace.yaml`, `Cargo.toml`, `pyproject.toml`,
  `requirements*.txt`, `go.mod`, `pom.xml`, `build.gradle*`, `*.csproj`, `composer.json`, `Gemfile`, `pubspec.yaml`,
  `Makefile`, `justfile`; CI files (`.github/workflows/`, `.gitlab-ci.yml`); lint and format configs; test folders.
- Derive the real build, test, lint, format and CI commands from these files. **Never invent a command**: if none is
  found, ask.
- Existing `CLAUDE.md`, `AGENTS.md` or `.claude/`: you will propose additions and show a diff, never overwrite.
- Note the platform (Windows, macOS, Linux) for the permission templates.

## 2. Interview (AskUserQuestion, recommended option first, at most 2 rounds of up to 4 questions)
Round 1:
1. **Level**
   - Light: prototype, script, experiment. `CLAUDE.md` + `docs/state.md` only.
   - Standard: a product in progress. Adds the requests log, findings log and decision records.
   - Strict: regulated, sensitive or critical work. Adds the AI usage log, traceability matrix and compliance
     question file.
2. **Languages**: language of answers and documentation; language of code identifiers and comments.
3. **Guardrails**: which actions always need the owner's "yes": network sends (push, publish, upload, data-sending
   HTTP), deletions, irreversible actions (destructive migrations, history rewrite, production), new dependencies or
   services, web searches and fetches. Recommended: all. Each "no" removes the matching rules from the `ask` lists of
   the permission templates; the `deny` lists and the plugin's hooks stay as they are.
4. **Red lines**: does the project have rules that must never be broken (legal, safety, privacy, contractual)?
   If yes, collect them in round 2, in the owner's own words.

Round 2, only for what is still unknown: naming conventions, commit convention (Conventional Commits, sign-off,
`AI-Assisted` trailer), the plan or roadmap file, a short map of the main folders.

## 3. Show the plan
List every file to create or modify with its path, and the commands that will go into CLAUDE.md.

| File | Light | Standard | Strict |
|---|---|---|---|
| `CLAUDE.md` (from `templates/CLAUDE.md`) | ✓ | ✓ | ✓ |
| `docs/state.md` | ✓ | ✓ | ✓ |
| `.claude/settings.json` permissions (merged) | ✓ | ✓ | ✓ |
| `docs/requests_log.md` |  | ✓ | ✓ |
| `docs/findings_log.md` |  | ✓ | ✓ |
| `docs/plan.md` (if the project has no plan yet) |  | ✓ | ✓ |
| `docs/decisions/0000_template.md` |  | ✓ | ✓ |
| `docs/ai_usage.md` |  |  | ✓ |
| `docs/traceability.csv` |  |  | ✓ |
| `docs/compliance_questions.md` |  |  | ✓ |

## 4. Ask approval, then write
- One AskUserQuestion: Approve / Change something / Cancel.
- Fill the templates. `CLAUDE.md` goes to the project root, `decision_template.md` to
  `docs/decisions/0000_template.md`, `settings.json` to `.claude/settings.json`, every other template to `docs/`.
  If the project already has a roadmap, point to it instead of creating `docs/plan.md`, and replace that path in
  CLAUDE.md and `docs/state.md` (the skills find the plan through `docs/state.md`).
- Level markers in the CLAUDE.md template: keep a line ending with `<!-- level: standard -->` only at the standard
  and strict levels, and a line ending with `<!-- level: strict -->` only at the strict level; then remove the
  markers themselves. Remove the sections that do not apply to the chosen level. **No `{{placeholder}}` may
  remain**: check with `grep -rn "{{" CLAUDE.md docs/`.
- `.claude/settings.json`: start from `templates/settings.json`; on Windows also merge the rules of
  `templates/settings.powershell.json`. Add the project's own build, test, lint and format commands to `allow`.
  If the file exists, merge lists (union), keep every existing entry, **never loosen a `deny`**, and show the diff.
- Keep `CLAUDE.md` under 200 lines (`wc -l CLAUDE.md`). Procedures belong in skills; rules that only matter for some
  paths go in `.claude/rules/` with `paths:` frontmatter.
- If `.gitignore` lacks `.env` and `.env.*` (except examples), propose adding them. The `deny` rules also hide
  `.env.example` from Claude: if the project needs one, suggest naming it `env.example`.

## 5. Report
Every created or modified file with its path, the level chosen, and the four commands to remember:
`/you-decide:session` (start or resume), `/you-decide:decide` (before a costly choice),
`/you-decide:close-step` (finish a step), `/you-decide:milestone` (close a milestone).
Remind the owner that hooks and permissions are guardrails, not a security guarantee: secrets must never be in the
project folder.
