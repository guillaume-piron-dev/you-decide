# SPDX-License-Identifier: Apache-2.0
"""Tests for the memory skill's script and hooks. Run: python3 -m unittest discover -s tests -v"""
from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "memory" / "scripts" / "yd_memory.py"
FAKE_GH = "ghp" + "_" + "Z9y8X7w6" * 5
THIS_MONTH = datetime.now().strftime("%Y-%m")

REQUESTS = f"""# Requests log

| Date time | Owner's words | State and handling |
|---|---|---|
| 2026-01-05 10:00 | "Add the export button" | ✅ docs/plan.md |
| 2026-01-06 11:00 | "Keep every answer word for word" | ⏳ |
| {THIS_MONTH}-01 09:00 | "Write the guide" | ✅ docs/guide.md |
"""
FINDINGS = """# Findings log

| ID | Review (date, scope) | Severity | Finding | Handling | State | Target | Proof |
|---|---|---|---|---|---|---|---|
| F-1-1 | 2026-01-07 step 1 | minor | Missing test for empty input | fixed | done | 1 | tests/a.py |
| F-1-2 | 2026-01-07 step 1 | important | Timeout not bounded | action | open | 2 | plan |
"""


def ask_call(call_id: str, stamp: str, answers: dict | None, text: str) -> list[dict]:
    use = {"type": "assistant", "timestamp": stamp, "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": call_id, "name": "AskUserQuestion", "input": {"questions": [
            {"question": "Which database?", "header": "Database", "multiSelect": False,
             "options": [{"label": "SQLite", "description": "local file"}, {"label": "PostgreSQL"}]},
            {"question": "Which checks?", "header": "Checks", "multiSelect": True,
             "options": [{"label": "Lint"}, {"label": "Tests"}]},
            {"question": "Name?", "header": "Name", "multiSelect": False,
             "options": [{"label": "alpha"}, {"label": "beta"}]}]}}]}}
    result = {"type": "user", "timestamp": stamp, "uuid": f"u-{call_id}", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": call_id, "content": text}]}}
    if answers is not None:
        result["toolUseResult"] = {"answers": answers}
    return [use, result]


def owner(uid: str, stamp: str, text, **extra) -> dict:
    return {"type": "user", "uuid": uid, "timestamp": stamp, "message": {"role": "user", "content": text}, **extra}


class Project:
    def __init__(self, level: str = "standard", name: str = "proj"):
        self.tmp = Path(tempfile.mkdtemp())
        self.root, self.home = self.tmp / name, self.tmp / "home"
        (self.root / "docs").mkdir(parents=True)
        self.home.mkdir()
        self.run("init", "--level", level)

    def env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        env.update({"HOME": str(self.home), "USERPROFILE": str(self.home), "PYTHONIOENCODING": "utf-8"})
        return env

    def run(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root, input=stdin.encode("utf-8"),
                              capture_output=True, env=self.env(), timeout=60)

    def out(self, result: subprocess.CompletedProcess) -> str:
        return result.stdout.decode("utf-8") + result.stderr.decode("utf-8")

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def read(self, name: str) -> str:
        return (self.root / name).read_text(encoding="utf-8")

    def config(self, **changes) -> None:
        path = self.root / "docs" / "memory" / "config.json"
        cfg = json.loads(path.read_text(encoding="utf-8"))
        for key, value in changes.items():
            cfg[key] = value
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    def transcript(self, entries: list[dict], name: str = "t.jsonl") -> Path:
        path = self.tmp / name
        path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
        return path

    def cleanup(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()

    def tearDown(self):
        self.p.cleanup()

    def test_init_then_check_passes_on_an_empty_project(self):
        self.assertTrue((self.p.root / "docs/memory/config.json").is_file())
        self.p.run("map")
        result = self.p.run("check")
        self.assertEqual(result.returncode, 0, self.p.out(result))

    def test_qa_records_questions_options_and_answers_once(self):
        t = self.p.transcript(ask_call("toolu_1", "2026-11-07T10:00:00Z",
                                       {"Which database?": "SQLite", "Which checks?": ["Lint", "Tests"],
                                        "Name?": "gamma, my own"}, "Your questions have been answered: ..."))
        self.assertEqual(self.p.run("qa", str(t)).returncode, 0)
        text = self.p.read("docs/questions_answers.md")
        self.assertIn('"Which database?"', text)
        self.assertIn('- "SQLite": local file', text)
        self.assertIn('**Answer**: "SQLite"', text)
        self.assertIn('**Answers**: "Lint"; "Tests"', text)
        self.assertIn('**Answer written by the owner**: "gamma, my own"', text)
        self.assertIn("nothing new", self.p.out(self.p.run("qa", str(t))))
        self.assertEqual(text, self.p.read("docs/questions_answers.md"))
        self.assertEqual(self.p.run("qa", str(t), "--check").returncode, 0)
        t2 = self.p.transcript(ask_call("toolu_2", "2026-11-07T11:00:00Z", None,
                                        'Your questions have been answered: "Which database?"="PostgreSQL". '
                                        "You can now continue."), "t2.jsonl")
        self.assertEqual(self.p.run("qa", str(t2), "--check").returncode, 1)
        self.p.run("qa", str(t2))
        self.assertIn('**Answer**: "PostgreSQL"', self.p.read("docs/questions_answers.md"))

    def test_qa_finds_the_newest_transcript_of_the_project(self):
        folder = self.p.home / ".claude" / "projects" / "elsewhere"
        folder.mkdir(parents=True)
        entries = [{"type": "system", "cwd": str(self.p.root.resolve())}] + ask_call(
            "toolu_9", "2026-11-07T10:00:00Z", {"Which database?": "SQLite"}, "questions have been answered")
        (folder / "s.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
        result = self.p.run("qa")
        self.assertEqual(result.returncode, 0, self.p.out(result))
        self.assertIn("toolu_9", self.p.read("docs/questions_answers.md"))

    def test_guard_refuses_a_changed_owner_word_unless_accepted(self):
        self.p.write("docs/requests_log.md", REQUESTS)
        self.assertEqual(self.p.run("guard", "--update").returncode, 0)
        changed = REQUESTS.replace("⏳ |", "✅ done |").replace('"Add the export button"', '~~"Add the export button"~~')
        self.p.write("docs/requests_log.md", changed)
        self.assertEqual(self.p.run("guard").returncode, 0, "a state change or a strike is not a loss")
        self.p.write("docs/requests_log.md", changed.replace("word for word", "roughly"))
        result = self.p.run("guard")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Keep every answer word for word", self.p.out(result))
        self.assertEqual(self.p.run("guard", "--update").returncode, 1)
        self.assertEqual(self.p.run("guard", "--update", "--accept", "owner reworded it").returncode, 0)
        register = json.loads(self.p.read("docs/memory/conservation.json"))
        self.assertEqual(register["accepted"][0]["reason"], "owner reworded it")
        self.assertEqual(self.p.run("guard").returncode, 0)

    def test_guard_sees_an_id_written_nowhere_and_a_lost_append_only_line(self):
        self.p.write("docs/findings_log.md", FINDINGS)
        self.p.write("docs/questions_answers.md", "# Q\n\nfirst line\n")
        self.p.run("guard", "--update")
        self.p.write("docs/findings_log.md", FINDINGS.replace(FINDINGS.splitlines()[-1] + "\n", ""))
        self.p.write("docs/questions_answers.md", "# Q\n")
        out = self.p.out(self.p.run("guard"))
        self.assertIn("F-1-2", out)
        self.assertIn("first line", out)

    def test_move_sends_only_old_closed_rows_to_volumes_and_guard_still_passes(self):
        self.p.write("docs/requests_log.md", REQUESTS)
        self.p.write("docs/findings_log.md", FINDINGS)
        self.p.run("guard", "--update")
        dry = self.p.run("move", "--dry-run")
        self.assertIn("would move", self.p.out(dry))
        self.assertEqual(self.p.read("docs/requests_log.md"), REQUESTS)
        self.assertEqual(self.p.run("move").returncode, 0)
        log = self.p.read("docs/requests_log.md")
        self.assertNotIn("export button", log)
        self.assertIn("word for word", log)
        self.assertIn("Write the guide", log)
        volume = self.p.read("docs/memory/volumes/requests/2026-01.md")
        self.assertIn('| 2026-01-05 10:00 | "Add the export button" | ✅ docs/plan.md |', volume)
        self.assertIn("| Date time | Owner's words | State and handling |", volume)
        self.assertIn("F-1-1", self.p.read("docs/memory/volumes/findings/2026-01.md"))
        self.assertIn("F-1-2", self.p.read("docs/findings_log.md"))
        self.assertEqual(self.p.run("guard").returncode, 0, self.p.out(self.p.run("guard")))

    def test_move_keeps_the_state_file_within_its_budget_and_the_newest_entry(self):
        cfg_state = {"path": "docs/state.md", "max_lines": 12, "log_heading": "## Update log",
                     "history": "docs/memory/state_history.md"}
        self.p.config(state=cfg_state)
        entries = "\n".join(f"- 2026-11-{day:02d}: step {day} closed\n  detail {day}" for day in range(10, 0, -1))
        state = f"# Current state\n\n## Next three actions\n1. a\n\n## Update log\n{entries}\n"
        self.p.write("docs/state.md", state)
        self.assertEqual(self.p.run("move").returncode, 0)
        kept = self.p.read("docs/state.md")
        self.assertLessEqual(len(kept.splitlines()), 12)
        self.assertIn("step 10 closed", kept)
        history = self.p.read("docs/memory/state_history.md")
        self.assertIn("step 1 closed", history)
        self.assertIn("  detail 1", history)
        moved = [line for line in state.splitlines() if line.strip()]
        self.assertEqual(sorted(moved), sorted(line for line in (kept + history).splitlines()
                                               if line.strip() and line in moved))

    def test_map_finds_definitions_citations_and_dangling_ids(self):
        self.p.write("docs/decisions/0001_store.md", "# D-0001 — Store data in SQLite\n\nBecause.\n")
        self.p.write("docs/findings_log.md", FINDINGS)
        self.p.write("docs/state.md", "# State\n\nSee D-0001 and F-1-2, and D-0099.\n")
        self.assertEqual(self.p.run("map").returncode, 0)
        ids = self.p.read("docs/memory/map/ids.md")
        self.assertIn("| D-0001 | docs/decisions/0001_store.md | Store data in SQLite | docs/state.md |", ids)
        self.assertIn("| F-1-2 | docs/findings_log.md |", ids)
        readme = self.p.read("docs/memory/map/README.md")
        self.assertIn("D-0099: cited in docs/state.md", readme)
        self.assertIn("Timeout not bounded", self.p.read("docs/memory/map/open.md"))
        self.assertEqual(self.p.run("map", "--check").returncode, 0)
        self.p.write("docs/state.md", "# State\n\nSee D-0001.\n")
        self.assertEqual(self.p.run("map", "--check").returncode, 1)
        self.assertEqual(self.p.run("check").returncode, 1)

    def test_resume_gives_state_open_rows_and_last_answers_within_budget(self):
        self.p.write("docs/state.md", "# State\n\n## Next three actions\n1. ship the guide\n")
        self.p.write("docs/requests_log.md", REQUESTS)
        t = self.p.transcript(ask_call("toolu_5", "2026-11-07T10:00:00Z", {"Which database?": "SQLite"},
                                       "questions have been answered"))
        result = self.p.run("resume", "--transcript", str(t))
        text = self.p.out(result)
        self.assertIn("ship the guide", text)
        self.assertIn("Keep every answer word for word", text)
        self.assertIn("Which database?", text)
        self.assertLessEqual(len(result.stdout), 9200)

    def test_precompact_hook_backs_up_without_overwriting_and_records_answers(self):
        self.p.config(transcript_backup={"enabled": True, "dir": "~/.you-decide/transcripts/{project}"})
        t = self.p.transcript(ask_call("toolu_7", "2026-11-07T10:00:00Z", {"Which database?": "SQLite"},
                                       "questions have been answered"))
        event = json.dumps({"transcript_path": str(t), "session_id": "abc", "trigger": "auto",
                            "cwd": str(self.p.root)})
        for _ in range(2):
            self.assertEqual(self.p.run("hook-precompact", stdin=event).returncode, 0)
        backups = sorted((self.p.home / ".you-decide" / "transcripts").glob("proj-*/abc-*.jsonl.gz"))
        self.assertEqual(len(backups), 2)
        with gzip.open(backups[0], "rt", encoding="utf-8") as packed:
            self.assertIn("toolu_7", packed.read())
        self.assertIn("toolu_7", self.p.read("docs/questions_answers.md"))

    def test_precompact_hook_does_nothing_without_config(self):
        (self.p.root / "docs/memory/config.json").unlink()
        t = self.p.transcript([owner("u1", "2026-11-07T10:00:00Z", "hello")])
        event = json.dumps({"transcript_path": str(t), "session_id": "abc", "cwd": str(self.p.root)})
        result = self.p.run("hook-precompact", stdin=event)
        self.assertEqual((result.returncode, result.stdout), (0, b""))
        self.assertFalse((self.p.home / ".you-decide").exists())

    def test_journal_keeps_only_the_owners_words_outside_the_repository(self):
        self.p.config(journal={"enabled": True, "path": "~/journal/{project}.md"})
        entries = [
            owner("u1", "2026-11-07T10:00:00Z", "Ship it today<system-reminder>clock 10:00</system-reminder>"),
            owner("u2", "2026-11-07T10:01:00Z", "Prompt written by Claude for a subagent", isSidechain=True),
            owner("u3", "2026-11-07T10:02:00Z", "Caveat injected by the app", isMeta=True),
            owner("u4", "2026-11-07T10:03:00Z",
                  "<command-name>/you-decide:setup</command-name><command-args>strict</command-args>"),
        ] + ask_call("toolu_8", "2026-11-07T10:04:00Z", {"Which database?": "SQLite"}, "questions have been answered")
        t = self.p.transcript(entries)
        self.assertEqual(self.p.run("journal", str(t)).returncode, 0)
        journal_file = next((self.p.home / "journal").glob("proj-*.md"))
        text = journal_file.read_text(encoding="utf-8")
        self.assertIn("Ship it today", text)
        self.assertNotIn("clock 10:00", text)
        self.assertNotIn("subagent", text)
        self.assertNotIn("injected", text)
        self.assertIn("/you-decide:setup strict", text)
        self.assertIn("Which database? → SQLite", text)
        self.assertIn("nothing new", self.p.out(self.p.run("journal", str(t))))
        risky = self.p.transcript([owner("u9", "2026-11-07T11:00:00Z", f"my token is {FAKE_GH}")], "r.jsonl")
        self.assertEqual(self.p.run("journal", str(risky)).returncode, 1)
        self.assertNotIn("my token", journal_file.read_text(encoding="utf-8"))
        self.assertEqual(self.p.run("journal", str(risky), "--accept", "u9").returncode, 0)
        self.p.config(journal={"enabled": True, "path": "docs/journal.md"})
        result = self.p.run("journal", str(t))
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside the repository", self.p.out(result))

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_sync_prepares_only_changed_documents_from_the_commit(self):
        self.p.config(project_sync={"enabled": True, "out": ".you-decide/project_sync",
                                    "files": ["CLAUDE.md", "docs/state.md", "docs/décisions/*.md"]})
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "init", "-q"], cwd=self.p.root, check=True)
        refused = self.p.run("sync")
        self.assertEqual(refused.returncode, 1)
        self.assertIn(".gitignore", self.p.out(refused))
        self.p.write(".gitignore", ".you-decide/\n")
        self.p.write("CLAUDE.md", "# Rules\n")
        self.p.write("docs/state.md", "# State\n")
        self.p.write("docs/décisions/d.md", "# D-0001 — x\n")
        subprocess.run(git + ["add", "-A"], cwd=self.p.root, check=True)
        subprocess.run(git + ["commit", "-qm", "one"], cwd=self.p.root, check=True)
        first = self.p.run("sync")
        self.assertEqual(first.returncode, 0, self.p.out(first))
        uploads = list((self.p.root / ".you-decide/project_sync").glob("upload_*"))
        names = sorted(p.name for p in uploads[0].iterdir())
        self.assertEqual(names, ["CLAUDE.md", "docs__décisions__d.md", "docs__state.md", "project_manifest.md"])
        self.assertFalse(any(".you-decide" in line for line in subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.p.root, capture_output=True, text=True).stdout.splitlines()))
        self.assertEqual(self.p.run("sync", "--done").returncode, 0)
        self.p.write("docs/state.md", "# State\n\nmore\n")
        self.p.write("docs/state_uncommitted_change_is_ignored.md", "x")
        (self.p.root / "CLAUDE.md").unlink()
        subprocess.run(git + ["add", "-A"], cwd=self.p.root, check=True)
        subprocess.run(git + ["commit", "-qm", "two"], cwd=self.p.root, check=True)
        out = self.p.out(self.p.run("sync"))
        self.assertIn("docs__state.md", out)
        self.assertNotIn("docs__décisions__d.md", out)
        self.assertIn("CLAUDE.md is in the Project but no longer selected", out)


class ReviewFindingTests(unittest.TestCase):
    """One test per finding of the independent review of 2026-11-07."""

    def setUp(self):
        self.p = Project()

    def tearDown(self):
        self.p.cleanup()

    def test_move_handles_several_past_months_in_one_run(self):
        rows = "\n".join(f"| 2025-0{m}-0{d} 10:00 | \"{name} {m}\" | {state} |"
                         for m in (1, 2, 3) for d, name, state in ((1, "closed", "✅ x"), (2, "open", "⏳")))
        self.p.write("docs/requests_log.md", "# Requests log\n\n| Date time | Owner's words | State and handling |\n"
                                            "|---|---|---|\n" + rows + "\n")
        self.p.run("guard", "--update")
        result = self.p.run("move")
        self.assertEqual(result.returncode, 0, self.p.out(result))
        log = self.p.read("docs/requests_log.md")
        for month in (1, 2, 3):
            self.assertIn(f"open {month}", log)
            self.assertNotIn(f"closed {month}", log)
            volume = self.p.read(f"docs/memory/volumes/requests/2025-0{month}.md")
            self.assertIn(f"closed {month}", volume)
            self.assertNotIn("open", volume.split("|---|---|---|")[1])
        self.assertIn("nothing to move", self.p.out(self.p.run("move")))
        self.assertEqual(self.p.run("guard").returncode, 0)

    def test_an_unanswered_question_waits_for_its_answer(self):
        calls = ask_call("toolu_w", "2026-11-07T10:00:00Z", {"Which database?": "SQLite"},
                         "questions have been answered")
        only_question = self.p.transcript(calls[:1], "q.jsonl")
        out = self.p.out(self.p.run("qa", str(only_question)))
        self.assertIn("waiting for an answer", out)
        self.assertFalse((self.p.root / "docs/questions_answers.md").exists())
        self.p.run("qa", str(self.p.transcript(calls, "full.jsonl")))
        self.assertIn('**Answer**: "SQLite"', self.p.read("docs/questions_answers.md"))

    def test_qa_holds_back_a_possible_secret_until_accepted(self):
        key = "AKIA" + "QWERTYUIOPASDFGH"
        t = self.p.transcript(ask_call("toolu_s", "2026-11-07T10:00:00Z", {"Name?": f"use {key}"},
                                       "questions have been answered"))
        result = self.p.run("qa", str(t))
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.p.root / "docs/questions_answers.md").exists())
        self.assertEqual(self.p.run("qa", str(t), "--accept", "toolu_s").returncode, 0)
        self.assertIn(key, self.p.read("docs/questions_answers.md"))

    def test_a_project_path_with_brackets_is_still_read(self):
        q = Project(name="br[1]")
        try:
            q.write("docs/plan.md", "# Plan\n\nSee D-0001 and Q-1.\n")
            q.run("map")
            self.assertIn("decision: 1", q.read("docs/memory/map/README.md"))
        finally:
            q.cleanup()

    def test_crlf_files_keep_their_line_endings_and_odd_characters(self):
        text = REQUESTS.replace('"Add the export button"', '"Add the\u2028export button"').replace("\n", "\r\n")
        path = self.p.root / "docs" / "requests_log.md"
        path.write_bytes(text.encode("utf-8"))
        self.p.run("guard", "--update")
        self.assertEqual(self.p.run("move").returncode, 0)
        data = path.read_bytes()
        self.assertIn(b"\r\n", data)
        self.assertNotIn(b"\n|", data.replace(b"\r\n", b""))
        volume = self.p.read("docs/memory/volumes/requests/2026-01.md")
        self.assertIn("Add the\u2028export button", volume)
        self.assertEqual(self.p.run("guard").returncode, 0)

    def test_check_fails_when_the_conservation_register_is_missing(self):
        (self.p.root / "docs/memory/conservation.json").unlink()
        result = self.p.run("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no conservation register", self.p.out(result))

    def test_backups_are_off_by_default_and_never_inside_the_repository(self):
        t = self.p.transcript([owner("u1", "2026-11-07T10:00:00Z", "hello")])
        event = json.dumps({"transcript_path": str(t), "session_id": "s", "cwd": str(self.p.root)})
        self.p.run("hook-precompact", stdin=event)
        self.assertFalse((self.p.home / ".you-decide").exists())
        self.p.config(transcript_backup={"enabled": True, "dir": "backups/{project}"})
        result = self.p.run("hook-precompact", stdin=event)
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.p.root / "backups").exists())
        self.assertIn("outside the repository", self.p.out(result))

    def test_a_malformed_config_is_reported_and_the_resume_hook_falls_back(self):
        self.p.write("docs/state.md", "# State\n\n1. keep going\n")
        self.p.write("docs/memory/config.json", "{bad")
        result = self.p.run("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not valid JSON", self.p.out(result))
        self.assertNotIn("Traceback", self.p.out(result))
        event = json.dumps({"source": "compact", "cwd": str(self.p.root)})
        out = subprocess.run([sys.executable, str(ROOT / "hooks" / "state_context.py")], input=event.encode("utf-8"),
                             capture_output=True, env=self.p.env(), timeout=60)
        self.assertIn("keep going", json.loads(out.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"])


class StateHookWithMemoryTests(unittest.TestCase):
    def test_resume_hook_outputs_only_json_with_memory_context(self):
        p = Project()
        try:
            p.write("docs/state.md", "# State\n\n## Next three actions\n1. ship\n")
            p.write("docs/requests_log.md", REQUESTS)
            t = p.transcript(ask_call("toolu_6", "2026-11-07T10:00:00Z", {"Which database?": "SQLite"},
                                      "questions have been answered"))
            event = json.dumps({"source": "compact", "transcript_path": str(t), "cwd": str(p.root)})
            out = subprocess.run([sys.executable, str(ROOT / "hooks" / "state_context.py")],
                                 input=event.encode("utf-8"), capture_output=True, env=p.env(), timeout=60)
            context = json.loads(out.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Keep every answer word for word", context)
            self.assertIn("Which database?", context)
            self.assertIn("toolu_6", p.read("docs/questions_answers.md"))
        finally:
            p.cleanup()


if __name__ == "__main__":
    unittest.main()
