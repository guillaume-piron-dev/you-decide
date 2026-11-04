# Changelog

## 0.2.2 — 2026-11-04
- PRIVACY.md (the plugin collects and sends nothing), and documentation, support, privacy policy and terms links
  in `plugin.json` for the directory listing.

## 0.2.1 — 2026-11-04
- README: states that `guard.py` names credential files only to block them, and that the tests use fake values
  and make no network call.

## 0.2.0 — 2026-11-04
- The plugin now sits at the repository root, as the Anthropic directory expects; hooks start through small shell
  launchers that pick a working Python (the Microsoft Store `python3` shortcut on Windows is skipped).
- Jurisdictions: `setup` asks where the owner, users, data and hosting are; `compliance` and `decide` use them, with
  official sources for 17 regions and international standards (`skills/compliance/references/regions.md`).
- `displayName`, icon, README section on what the plugin runs, changes and sends, and where it works.

## 0.1.0 — 2026-11-04
- First public version: 9 skills (setup, session, log, decide, story-to-tests, review, close-step, milestone,
  compliance), the `reviewer` subagent, guardrail and state re-injection hooks, three setup levels.
