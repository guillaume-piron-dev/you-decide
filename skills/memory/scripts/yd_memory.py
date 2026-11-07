#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""You Decide project memory: nothing disappears, everything can be found, every loss shows.

Standard library only, no network access. Settings come from `docs/memory/config.json` in the project (`init` writes
the default). The committed repository is the source of truth; everything here is derived from it or appended to it.
Files outside the project (transcript backups, the private journal) are written only when the config enables them.

Commands:
  init [--level standard|strict] [--force]       write the default config
  qa [TRANSCRIPT ...] [--all] [--check] [--accept ID ...]   append answered multiple-choice questions, word for word
  guard [--update [--accept REASON]]             conservation register: nothing lost, shortened or rewritten
  move [--dry-run]                               move closed rows and old state entries to volumes, verbatim, verified
  map [--check]                                  reference map: where each id is defined, who cites it, what is open
  resume [--transcript PATH]                     short context to resume work after a compaction
  journal [TRANSCRIPT ...] [--all] [--dry-run] [--accept ID ...]   the owner's messages, word for word, outside the
                                                 repository
  sync [--rev REV] [--done]                      lightweight copy of chosen documents for a claude.ai Project
  check                                          guard + map check + pending moves, for the local CI
  hook-precompact                                hook entry point (JSON on stdin): backup, then qa and journal
Without TRANSCRIPT, `qa` and `journal` read the newest Claude Code transcript of this project (every one with --all).
"""
from __future__ import annotations

import argparse
import contextlib
import fnmatch
import glob
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path("docs") / "memory" / "config.json"
DEFAULT_CONFIG: dict = {
    "version": 1,
    "docs": ["CLAUDE.md", "docs/**/*.md"],
    "state": {"path": "docs/state.md", "max_lines": 150, "log_heading": "## Update log",
              "history": "docs/memory/state_history.md"},
    "qa_log": "docs/questions_answers.md",
    "tables": [
        {"name": "requests", "path": "docs/requests_log.md", "protected": [0, 1],
         "closed": {"column": 2, "pattern": "✅"}},
        {"name": "findings", "path": "docs/findings_log.md", "protected": [0, 1, 2, 3],
         "closed": {"column": 5, "pattern": "^done$"}},
    ],
    "append_only": ["docs/questions_answers.md", "docs/memory/state_history.md", "docs/ai_usage.md"],
    "ids": {"finding": r"F-[A-Za-z0-9./]+-\d+", "question": r"Q-\d+", "decision": r"D-\d{4}"},
    "volumes_dir": "docs/memory/volumes",
    "map_dir": "docs/memory/map",
    "conservation": "docs/memory/conservation.json",
    "transcript_backup": {"enabled": False, "dir": "~/.you-decide/transcripts/{project}"},
    "journal": {"enabled": False, "path": "~/.you-decide/journal/{project}.md"},
    "project_sync": {"enabled": False, "out": ".you-decide/project_sync",
                     "files": ["CLAUDE.md", "docs/state.md", "docs/plan.md", "docs/decisions/*.md",
                               "docs/questions_answers.md", "docs/memory/map/*.md"]},
    "strict_moves": False,
}
RESUME_BUDGET = 9000
SECRETS_FALLBACK = [r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\bAKIA[0-9A-Z]{16}\b", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",
                    r"\bsk-[A-Za-z0-9_\-]{30,}", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"]
IPV4 = re.compile(r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w.])")


# ---------------------------------------------------------------- basics
class MemoryError_(Exception):
    """A refusal that the command reports and exits with code 1."""


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def find_root(start: Path | None = None) -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    here = Path(env if env else (start or Path.cwd())).resolve()
    for candidate in (here, *here.parents):
        if (candidate / CONFIG).is_file():
            return candidate
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return here


def merged(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        out[key] = merged(base[key], value) if isinstance(value, dict) and isinstance(base.get(key), dict) else value
    return out


def load_config(root: Path) -> dict | None:
    path = root / CONFIG
    if not path.is_file():
        return None
    try:
        data = json.loads(read(path))
    except json.JSONDecodeError as error:
        raise MemoryError_(f"{CONFIG.as_posix()} is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise MemoryError_(f"{CONFIG.as_posix()} must hold a JSON object")
    return merged(DEFAULT_CONFIG, data)


def read(path: Path) -> str:
    """A file's text with CRLF read as LF, for parsing only (rewrites keep the file's own line ending)."""
    if not path.is_file():
        return ""
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read().replace("\r\n", "\n")


def write(path: Path, text: str, eol: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\n", eol) if eol != "\n" else text)


def digest(text: str) -> str:
    return hashlib.sha256(text.rstrip().encode("utf-8")).hexdigest()[:16]


def project_name(root: Path) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", root.name) or "project"
    return f"{base}-{hashlib.sha256(str(root.resolve()).encode('utf-8')).hexdigest()[:6]}"


def outside_path(template: str, root: Path) -> Path:
    path = Path(os.path.expanduser(template.replace("{project}", project_name(root))))
    return path if path.is_absolute() else root / path


def local_time(stamp: str) -> str:
    """An ISO instant (UTC) shown in the machine's local time, with its offset."""
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return stamp
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    local = moment.astimezone()
    offset = local.strftime("%z")
    return f"{local:%Y-%m-%d %H:%M} (UTC{offset[:3]}:{offset[3:]})"


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def lines_of(text: str) -> list[str]:
    """Lines split on \\n only: never on U+2028, U+0085 or form feeds, which can sit inside a table cell."""
    lines = text.split("\n")
    return lines[:-1] if lines and lines[-1] == "" else lines


def eol_of(path: Path) -> str:
    if not path.is_file():
        return "\n"
    with path.open("rb") as handle:
        return "\r\n" if b"\r\n" in handle.read(1 << 16) else "\n"


def append(path: Path, text: str, header: str) -> None:
    """Add text at the end of a file (created with its header); bytes already written are never rewritten."""
    eol = eol_of(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.is_file() and path.stat().st_size > 0
    needs_break = False
    if existing:
        with path.open("rb") as raw:
            raw.seek(-1, os.SEEK_END)
            needs_break = raw.read(1) != b"\n"
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write((eol if needs_break else "") + ((header if not existing else "") + text).replace("\n", eol))


def outside_repository(template: str, root: Path, what: str) -> Path:
    path = outside_path(template, root).resolve()
    top = root.resolve()
    if path == top or top in path.parents:
        raise MemoryError_(f"refused: the {what} must live outside the repository ({path})")
    return path


def known_marks(text: str, kind: str) -> set[str]:
    return set(re.findall(rf"<!-- {kind}: (\S+) -->", text))


def risky(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns) or IPV4.search(text) is not None


def project_transcripts(root: Path) -> list[Path]:
    base = Path.home() / ".claude" / "projects"
    if not base.is_dir():
        return []
    candidates = list((base / re.sub(r"[^A-Za-z0-9]", "-", str(root))).glob("*.jsonl"))
    if not candidates:
        for path in base.glob("*/*.jsonl"):
            with path.open(encoding="utf-8", errors="replace") as lines:
                for _, line in zip(range(30), lines):
                    try:
                        if json.loads(line).get("cwd") == str(root):
                            candidates.append(path)
                            break
                    except (json.JSONDecodeError, AttributeError):
                        continue
    return sorted(candidates, key=lambda p: p.stat().st_mtime)


def hook_capture(root: Path, cfg: dict, event: dict) -> None:
    transcript = Path(event.get("transcript_path") or "")
    if transcript.is_file():
        capture_qa(root, cfg, [transcript])
        if cfg["journal"].get("enabled"):
            journal(root, cfg, [transcript], False, [])


# ---------------------------------------------------------------- tables
def split_row(line: str) -> list[str] | None:
    text = line.strip()
    if len(text) < 2 or not (text.startswith("|") and text.endswith("|")):
        return None
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", text[1:-1])]


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def data_rows(lines: list[str]) -> list[tuple[int, list[str]]]:
    """(index, cells) of every table row that is neither a header nor a separator."""
    rows = []
    for index, line in enumerate(lines):
        cells = split_row(line)
        if cells is None or is_separator(cells):
            continue
        following = split_row(lines[index + 1]) if index + 1 < len(lines) else None
        if following is not None and is_separator(following):
            continue
        rows.append((index, cells))
    return rows


def table_header(lines: list[str]) -> list[str]:
    for index, line in enumerate(lines[:-1]):
        cells, following = split_row(line), split_row(lines[index + 1])
        if cells is not None and following is not None and is_separator(following):
            return [line, lines[index + 1]]
    return []


def volume_files(root: Path, cfg: dict, name: str) -> list[Path]:
    return sorted((root / cfg["volumes_dir"] / name).glob("*.md"))


def family(root: Path, cfg: dict, path: str, name: str) -> list[Path]:
    return [root / path, *volume_files(root, cfg, name)]


def protected_key(cells: list[str], indices: list[int]) -> str | None:
    if max(indices) >= len(cells):
        return None
    return "\x1f".join(cells[i].replace("~~", "").strip() for i in indices)


def is_closed(cells: list[str], closed: dict) -> bool:
    column = closed.get("column", -1)
    return 0 <= column < len(cells) and re.search(closed.get("pattern", "$^"), cells[column]) is not None


# ---------------------------------------------------------------- qa
def open_transcript(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")


def transcript_entries(paths: list[Path]):
    for path in paths:
        with open_transcript(path) as lines:
            for line in lines:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict):
                    yield entry


def result_text(part: dict) -> str:
    text = part.get("content")
    if isinstance(text, list):
        text = "".join(piece.get("text", "") for piece in text if isinstance(piece, dict))
    return text if isinstance(text, str) else ""


ANSWERED = re.compile(r'"((?:[^"]|"(?!=))*)"="((?:[^"]|"(?!, "|\. |$))*)"')


def qa_calls(paths: list[Path]) -> list[dict]:
    found: dict[str, dict] = {}
    replies: dict[str, dict] = {}
    when: dict[str, str] = {}
    for entry in transcript_entries(paths):
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use" and part.get("name") == "AskUserQuestion":
                found.setdefault(part.get("id", ""), {"id": part.get("id", ""), "stamp": entry.get("timestamp", ""),
                                                      "questions": (part.get("input") or {}).get("questions", [])})
            elif part.get("type") == "tool_result" and "questions have been answered" in result_text(part):
                key = part.get("tool_use_id", "")
                structured = entry.get("toolUseResult")
                answers = structured.get("answers") if isinstance(structured, dict) else None
                if isinstance(answers, dict):
                    replies[key] = {q: ", ".join(map(str, a)) if isinstance(a, list) else str(a)
                                    for q, a in answers.items()}
                else:
                    replies[key] = dict(ANSWERED.findall(result_text(part)))
                when[key] = entry.get("timestamp", "")
    calls = sorted(found.values(), key=lambda call: call["stamp"])
    for call in calls:
        call["replies"], call["answered"] = replies.get(call["id"], {}), when.get(call["id"], "")
    return calls


QA_HEADER = """# Questions and answers

Append-only. Every multiple-choice question asked to the owner, with its options and the answer, word for word.
Written by the `memory` skill (`yd_memory.py qa`) from the Claude Code transcript, never retyped. The requests log
points here.
"""


def qa_entry(call: dict) -> str:
    asked = local_time(call["stamp"])
    answered = local_time(call["answered"]) if call["answered"] else ""
    title = asked if not answered or answered == asked else f"{asked}, answered {answered}"
    out = [f"\n## {title}\n", f"<!-- call: {call['id']} -->", ""]
    for number, question in enumerate(call["questions"], start=1):
        out.append(f"**Q{number} — {question.get('header', '')}**: \"{question.get('question', '')}\"")
        out.append("")
        labels = []
        for option in question.get("options", []):
            labels.append(option.get("label", ""))
            description = option.get("description")
            out.append(f"- \"{option.get('label', '')}\"" + (f": {description}" if description else ""))
        reply = call["replies"].get(question.get("question", ""))
        parts = reply.split(", ") if reply and question.get("multiSelect") else []
        if reply is None:
            out.append("- **Answer**: not found in the transcript")
        elif reply in labels:
            out.append(f"- **Answer**: \"{reply}\"")
        elif parts and all(part in labels for part in parts):
            out.append("- **Answers**: " + "; ".join(f"\"{part}\"" for part in parts))
        else:
            out.append(f"- **Answer written by the owner**: \"{reply}\"")
        out.append("")
    return "\n".join(out)


def capture_qa(root: Path, cfg: dict, transcripts: list[Path], check: bool = False,
               accepted: tuple[str, ...] = ()) -> int:
    target = root / cfg["qa_log"]
    known = known_marks(read(target), "call")
    calls = [call for call in qa_calls(transcripts) if call["id"] not in known]
    answered = [call for call in calls if call["answered"]]
    waiting = len(calls) - len(answered)
    if check:
        for call in answered:
            print(f"✗ question missing from {cfg['qa_log']}: {call['stamp']} ({call['id']})")
        return 1 if answered else 0
    patterns = secret_patterns()
    ready, held = [], []
    for call in answered:
        text = qa_entry(call)
        (held if risky(text, patterns) and call["id"] not in accepted else ready).append((call, text))
    for call, _ in held:
        print(f"✗ possible secret or IP address in the question of {local_time(call['stamp'])} (call {call['id']}): "
              f"not written. Re-read it, then rerun with --accept {call['id']}", file=sys.stderr)
    if ready:
        append(target, "".join(text for _, text in ready), QA_HEADER)
    print(f"✓ qa: {len(ready)} question call(s) added to {cfg['qa_log']}" if ready else "✓ qa: nothing new")
    if waiting:
        print(f"• qa: {waiting} question(s) still waiting for an answer; run qa again once answered")
    return 1 if held else 0


def latest_transcript(root: Path) -> Path | None:
    found = project_transcripts(root)
    return found[-1] if found else None


def transcripts_or_latest(root: Path, given: list[Path], every: bool = False) -> list[Path]:
    if given:
        return given
    found = project_transcripts(root)
    if not found:
        raise MemoryError_("no Claude Code transcript found for this project; pass its path")
    return found if every else found[-1:]


# ---------------------------------------------------------------- guard
def snapshot(root: Path, cfg: dict) -> dict:
    tables = {}
    for table in cfg["tables"]:
        counts: Counter = Counter()
        previews: dict = {}
        for path in family(root, cfg, table["path"], table["name"]):
            for _, cells in data_rows(lines_of(read(path))):
                key = protected_key(cells, table["protected"])
                if key is not None:
                    counts[digest(key)] += 1
                    previews[digest(key)] = key.replace("\x1f", " | ")[:100]
        tables[table["name"]] = {k: [counts[k], previews[k]] for k in counts}
    append_only = {}
    for path in cfg["append_only"]:
        counts, previews = Counter(), {}
        for member in family(root, cfg, path, Path(path).stem):
            for line in lines_of(read(member)):
                if line.strip():
                    counts[digest(line)] += 1
                    previews[digest(line)] = line.strip()[:100]
        if counts:
            append_only[path] = {k: [counts[k], previews[k]] for k in counts}
    ids = sorted({match for _, text in documents(root, cfg) for match in all_ids(cfg, text)})
    return {"tables": tables, "append_only": append_only, "ids": ids}


def compare(register: dict, snap: dict) -> tuple[list[str], int]:
    losses, new = [], 0
    for group in ("tables", "append_only"):
        for name, items in register.get(group, {}).items():
            now = snap[group].get(name, {})
            for key, (count, preview) in items.items():
                have = now.get(key, [0])[0]
                if have < count:
                    losses.append(f"{name}: {count - have}× changed or gone: \"{preview}\"")
        for name, items in snap[group].items():
            old = register.get(group, {}).get(name, {})
            new += sum(1 for key, (count, _) in items.items() if count > old.get(key, [0])[0])
    for identifier in sorted(set(register.get("ids", [])) - set(snap["ids"])):
        losses.append(f"id {identifier} is no longer written anywhere")
    new += len(set(snap["ids"]) - set(register.get("ids", [])))
    return losses, new


def guard(root: Path, cfg: dict, update: bool = False, accept: str | None = None) -> int:
    path = root / cfg["conservation"]
    if not path.is_file() and not update:
        print(f"✗ guard: no conservation register ({cfg['conservation']}): run `guard --update` and commit it")
        return 1
    register = json.loads(read(path)) if path.is_file() else {"version": 1, "tables": {}, "append_only": {}, "ids": [],
                                                              "accepted": []}
    snap = snapshot(root, cfg)
    losses, new = compare(register, snap)
    for loss in losses:
        print(f"✗ {loss}")
    if not update:
        if new:
            print(f"• {new} new item(s) not recorded yet: run `guard --update` and commit {cfg['conservation']}")
        print("✗ guard: loss found" if losses else "✓ guard: nothing lost")
        return 1 if losses else 0
    if losses and not accept:
        print("✗ guard: nothing recorded. Re-read each loss; undo it if it is not intended, or declare it with "
              "--accept \"reason\"")
        return 1
    if losses:
        register.setdefault("accepted", []).append({"date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                    "reason": accept, "losses": losses})
    for group in ("tables", "append_only"):
        merged_group = register.setdefault(group, {})
        for name, items in snap[group].items():
            target = merged_group.setdefault(name, {})
            for key, (count, preview) in items.items():
                if count > target.get(key, [0])[0]:
                    target[key] = [count, preview]
        if losses:
            for name, items in list(merged_group.items()):
                now = snap[group].get(name, {})
                for key in list(items):
                    if now.get(key, [0])[0] < items[key][0]:
                        if key in now:
                            items[key][0] = now[key][0]
                        else:
                            del items[key]
    register["ids"] = sorted(set(register.get("ids", [])) | set(snap["ids"])) if not losses else snap["ids"]
    write(path, json.dumps(register, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"✓ guard: {new} new item(s) recorded" + (f", {len(losses)} loss(es) accepted: {accept}" if losses else ""))
    return 0


# ---------------------------------------------------------------- move
def month_of(line: str) -> str | None:
    match = re.search(r"\b(20\d\d)-(0[1-9]|1[0-2])\b", line)
    return f"{match.group(1)}-{match.group(2)}" if match else None


def plan_moves(root: Path, cfg: dict, now: datetime | None = None) -> list[dict]:
    current = (now or datetime.now()).strftime("%Y-%m")
    plans = []
    for table in cfg["tables"]:
        path = root / table["path"]
        lines = lines_of(read(path))
        by_month: dict[str, list[int]] = {}
        for index, cells in data_rows(lines):
            month = month_of(lines[index])
            if month and month < current and is_closed(cells, table.get("closed", {})):
                by_month.setdefault(month, []).append(index)
        if by_month:
            plans.append({"kind": "table", "table": table, "path": path, "by_month": by_month,
                          "volumes": {m: root / cfg["volumes_dir"] / table["name"] / f"{m}.md" for m in by_month}})
    state = cfg["state"]
    path = root / state["path"]
    lines = lines_of(read(path))
    if len(lines) > state["max_lines"]:
        entries = state_entries(lines, state["log_heading"])
        moving, remaining = [], len(lines)
        for start, end in reversed(entries[1:]):
            if remaining <= state["max_lines"]:
                break
            moving.insert(0, (start, end))
            remaining -= end - start
        if moving:
            plans.append({"kind": "state", "path": path, "entries": moving, "volume": root / state["history"]})
    return plans


def state_entries(lines: list[str], heading: str) -> list[tuple[int, int]]:
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading.strip())
    except StopIteration:
        return []
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    starts = [i for i in range(start + 1, end) if re.match(r"^- \d{4}-\d{2}-\d{2}", lines[i])]
    return [(s, starts[n + 1] if n + 1 < len(starts) else end) for n, s in enumerate(starts)]


def apply_move(plan: dict, dry_run: bool) -> str:
    """Apply one file's plan in a single pass; refuse unless every line before is still there after."""
    path = plan["path"]
    lines = lines_of(read(path))
    old_volumes: dict[Path, str] = {}
    new_volumes: dict[Path, str] = {}
    headers: Counter = Counter()
    if plan["kind"] == "table":
        name = plan["table"]["name"]
        header = table_header(lines)
        chosen: set[int] = set()
        for month, indices in sorted(plan["by_month"].items()):
            volume = plan["volumes"][month]
            old = read(volume)
            base = old or (f"# {name} — volume {month}\n\nAppend-only. Rows moved verbatim from "
                           f"`{plan['table']['path']}` by `yd_memory.py move`.\n\n" + "\n".join(header) + "\n")
            if not old:
                headers.update(line for line in lines_of(base) if line.strip())
            new_volumes[volume] = (base + ("" if base.endswith("\n") else "\n")
                                   + "\n".join(lines[i] for i in indices) + "\n")
            old_volumes[volume] = old
            chosen.update(indices)
        what = ", ".join(f"{len(ix)} row(s) of {name} → {month}.md" for month, ix in sorted(plan["by_month"].items()))
    else:
        volume = plan["volume"]
        old = read(volume)
        chosen = {i for start, end in plan["entries"] for i in range(start, end)}
        moved = [lines[i] for i in sorted(chosen)]
        base = old or ("# State history\n\nAppend-only. Older entries of the state file's update log, moved verbatim "
                       "by `yd_memory.py move`, newest first.\n")
        if not old:
            headers.update(line for line in lines_of(base) if line.strip())
        head = lines_of(base)
        cut = next((i for i, line in enumerate(head) if re.match(r"^- \d{4}-\d{2}-\d{2}", line)), len(head))
        spacer = [""] if cut and head[cut - 1].strip() else []
        new_volumes[volume] = "\n".join(head[:cut] + spacer + moved + head[cut:]) + "\n"
        old_volumes[volume] = old
        what = f"{len(plan['entries'])} state entr(y/ies) → {volume.name}"
    kept = [line for i, line in enumerate(lines) if i not in chosen]
    before = Counter(line for line in lines if line.strip())
    after = Counter(line for line in kept if line.strip())
    for text in old_volumes.values():
        before.update(line for line in lines_of(text) if line.strip())
    for text in new_volumes.values():
        after.update(line for line in lines_of(text) if line.strip())
    if before - after or after - before != headers:
        raise MemoryError_(f"move refused for {path.name}: lines would not be the same before and after")
    if not dry_run:
        for volume, text in new_volumes.items():
            write(volume, text, eol_of(volume))
        write(path, "\n".join(kept) + "\n", eol_of(path))
    return what


def move(root: Path, cfg: dict, dry_run: bool = False) -> int:
    plans = plan_moves(root, cfg)
    if not plans:
        print("✓ move: nothing to move")
        return 0
    for plan in plans:
        print(("• would move " if dry_run else "✓ moved ") + apply_move(plan, dry_run))
    return 0


# ---------------------------------------------------------------- map
def documents(root: Path, cfg: dict) -> list[tuple[Path, str]]:
    skip = (root / cfg["map_dir"]).resolve()
    seen, out = set(), []
    for pattern in cfg["docs"]:
        names = glob.glob(os.path.join(glob.escape(str(root)), pattern), recursive=True)
        for name in sorted(names, key=lambda n: rel(root, Path(n).resolve())):
            path = Path(name).resolve()
            if path in seen or not path.is_file() or skip in path.parents:
                continue
            seen.add(path)
            out.append((path, read(path)))
    return out


def all_ids(cfg: dict, text: str) -> set[str]:
    found = set()
    for pattern in cfg["ids"].values():
        found.update(re.findall(rf"(?<![\w-])({pattern})(?![\w-])", text))
    return found


def natural(text: str) -> list:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


def build_map(root: Path, cfg: dict) -> dict[str, str]:
    defined: dict[str, tuple[str, str]] = {}
    cited: dict[str, set[str]] = {}
    for path, text in documents(root, cfg):
        name = rel(root, path)
        for line in lines_of(text):
            heading = re.match(r"^#{1,6}\s+(.*)", line)
            cells = split_row(line)
            for identifier in all_ids(cfg, line):
                title = None
                if heading and re.match(rf"~*{re.escape(identifier)}\b", heading.group(1)):
                    title = re.sub(rf"^~*{re.escape(identifier)}~*\s*[—:-]*\s*", "", heading.group(1))
                elif cells and cells[0].strip("~ ") == identifier:
                    title = next((cell for cell in cells[1:] if cell and not re.fullmatch(r"[\d\-: ,]+", cell)), "")
                if title is not None and identifier not in defined:
                    defined[identifier] = (name, title[:90])
                else:
                    cited.setdefault(identifier, set()).add(name)
    kinds = {kind: [i for i in sorted(set(defined) | set(cited), key=natural) if re.fullmatch(p, i)]
             for kind, p in cfg["ids"].items()}
    lines = ["# Reference ids", "", "Generated by `yd_memory.py map`; never edit by hand.", ""]
    for kind, identifiers in kinds.items():
        if not identifiers:
            continue
        lines += [f"## {kind}", "", "| Id | Defined in | Title | Cited in |", "|---|---|---|---|"]
        for identifier in identifiers:
            where, title = defined.get(identifier, ("—", ""))
            cites = sorted(cited.get(identifier, set()) - {where})
            lines.append(f"| {identifier} | {where} | {title.replace('|', '/')} | "
                         f"{', '.join(cites[:5])}{' …' if len(cites) > 5 else ''} |")
        lines.append("")
    open_lines = ["# Open items", "", "Generated by `yd_memory.py map`; never edit by hand.", ""]
    for table in cfg["tables"]:
        rows = []
        for path in family(root, cfg, table["path"], table["name"]):
            text_lines = lines_of(read(path))
            for _, cells in data_rows(text_lines):
                if not is_closed(cells, table.get("closed", {})):
                    rows.append(f"- {rel(root, path)}: " + " | ".join(c[:120] + ("…" if len(c) > 120 else "")
                                                                        for c in cells))
        open_lines += [f"## {table['name']} ({len(rows)} open)", ""] + (rows or ["- none"]) + [""]
    dangling = sorted(set(cited) - set(defined), key=natural)
    volumes = [rel(root, p) for t in cfg["tables"] for p in volume_files(root, cfg, t["name"])]
    readme = ["# Memory map", "", "Generated by `yd_memory.py map`; never edit by hand. Use it to know where to search "
              "after a compaction, then open the file it names.", "",
              "- `ids.md`: every reference id, where it is defined, its title and who cites it",
              "- `open.md`: open rows of the logs", "", "## Counts", ""]
    readme += [f"- {kind}: {len(ids)}" for kind, ids in kinds.items()] + ["", "## References to an id defined nowhere",
                                                                           ""]
    readme += [f"- {identifier}: cited in {', '.join(sorted(cited[identifier]))}" for identifier in dangling] or [
        "- none"]
    readme += ["", "## Volumes", ""] + ([f"- {v}" for v in volumes] or ["- none"]) + [""]
    return {"README.md": "\n".join(readme), "ids.md": "\n".join(lines), "open.md": "\n".join(open_lines)}


def write_map(root: Path, cfg: dict, check: bool = False) -> int:
    stale = []
    for name, text in build_map(root, cfg).items():
        path = root / cfg["map_dir"] / name
        if read(path) != text:
            stale.append(name)
            if not check:
                write(path, text)
    if check:
        print(f"✗ map out of date ({', '.join(stale)}): run `map`" if stale else "✓ map: up to date")
        return 1 if stale else 0
    print(f"✓ map: {len(stale)} file(s) written" if stale else "✓ map: already up to date")
    return 0


# ---------------------------------------------------------------- resume
def resume_text(root: Path, cfg: dict | None, transcript: Path | None = None) -> str:
    if cfg is None:
        state = lines_of(read(root / "docs" / "state.md"))[:150]
        return "\n".join(state)[:RESUME_BUDGET]
    if transcript is not None and transcript.is_file():
        try:
            capture_qa(root, cfg, [transcript])
        except (OSError, ValueError):
            pass
    parts = ["You Decide resume. Read the files named here before acting; search the rest with grep and "
             f"{cfg['map_dir']}/; never guess a detail lost in the compaction."]
    state_lines = lines_of(read(root / cfg["state"]["path"]))
    parts.append(f"## {cfg['state']['path']} (first lines)\n" + "\n".join(state_lines[:80]))
    for table in cfg["tables"]:
        rows = []
        lines = lines_of(read(root / table["path"]))
        for index, cells in data_rows(lines):
            if not is_closed(cells, table.get("closed", {})):
                rows.append(lines[index][:300])
        if rows:
            parts.append(f"## Open in {table['path']} (last {min(len(rows), 15)} of {len(rows)})\n" + "\n".join(rows[-15:]))
    qa = read(root / cfg["qa_log"]).split("\n## ")[1:]
    if qa:
        parts.append("## Last questions and answers\n" + "\n## ".join(qa[-3:]))
    out = ""
    for part in parts:
        if len(out) + len(part) + 2 <= RESUME_BUDGET:
            out += part + "\n\n"
    return out.rstrip()


# ---------------------------------------------------------------- journal
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
JOURNAL_HEADER = """# Private journal — the owner's messages, word for word

Append-only. Written by `yd_memory.py journal` from Claude Code transcripts. Never in the repository.
"""


def secret_patterns() -> list[str]:
    guard_file = Path(__file__).resolve().parents[3] / "hooks" / "guard.py"
    try:
        sys.path.insert(0, str(guard_file.parent))
        import guard as guard_module  # type: ignore
        return [pattern for pattern, _ in guard_module.DENY_SECRETS]
    except Exception:
        return SECRETS_FALLBACK
    finally:
        if sys.path and sys.path[0] == str(guard_file.parent):
            sys.path.pop(0)


def owner_messages(paths: list[Path]) -> list[dict]:
    messages = []
    for entry in transcript_entries(paths):
        content = (entry.get("message") or {}).get("content")
        if (entry.get("type") != "user" or entry.get("isMeta") or entry.get("isCompactSummary")
                or entry.get("isSidechain")):
            continue
        stamp, uid = entry.get("timestamp", ""), entry.get("uuid", "")
        if isinstance(content, str):
            texts = [content]
        elif isinstance(content, list):
            texts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
            result = entry.get("toolUseResult")
            if isinstance(result, dict) and isinstance(result.get("answers"), dict):
                answers = "\n".join(f"- {q} → {', '.join(map(str, a)) if isinstance(a, list) else a}"
                                    for q, a in result["answers"].items())
                messages.append({"id": uid, "stamp": stamp, "text": "Answers to multiple-choice questions:\n" + answers})
        else:
            continue
        text = REMINDER.sub("", "\n".join(texts)).strip()
        if not text or text.startswith("<local-command-stdout>"):
            continue
        command = re.search(r"<command-name>(.*?)</command-name>", text)
        if command:
            args = re.search(r"<command-args>(.*?)</command-args>", text, re.DOTALL)
            text = (command.group(1) + (" " + args.group(1).strip() if args and args.group(1).strip() else "")).strip()
        messages.append({"id": uid, "stamp": stamp, "text": text})
    return sorted(messages, key=lambda m: m["stamp"])


def journal(root: Path, cfg: dict, transcripts: list[Path], dry_run: bool, accepted: list[str]) -> int:
    if not cfg["journal"].get("enabled"):
        raise MemoryError_("the private journal is not enabled in docs/memory/config.json")
    path = outside_repository(cfg["journal"]["path"], root, "journal")
    known = known_marks(read(path), "msg")
    patterns = secret_patterns()
    fresh, blocked = [], []
    for message in owner_messages(transcripts):
        if message["id"] in known:
            continue
        if risky(message["text"], patterns) and message["id"] not in accepted:
            blocked.append(message)
        fresh.append(message)
    if blocked:
        for message in blocked:
            print(f"✗ possible secret or IP address in the message of {local_time(message['stamp'])} "
                  f"(id {message['id']}): nothing written. Re-read it, then rerun with --accept {message['id']}",
                  file=sys.stderr)
        return 1
    text = "".join(f"\n## {local_time(m['stamp'])}\n<!-- msg: {m['id']} -->\n\n{m['text']}\n" for m in fresh)
    if dry_run:
        print(text or "✓ journal: nothing new")
        return 0
    if fresh:
        append(path, text, JOURNAL_HEADER)
    print(f"✓ journal: {len(fresh)} message(s) added to {path}" if fresh else "✓ journal: nothing new")
    return 0


# ---------------------------------------------------------------- project sync
def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if result.returncode != 0:
        raise MemoryError_(f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def sync(root: Path, cfg: dict, rev: str, done: bool) -> int:
    settings = cfg["project_sync"]
    if not settings.get("enabled"):
        raise MemoryError_("the claude.ai Project copy is not enabled in docs/memory/config.json")
    probe = subprocess.run(["git", "check-ignore", "-q", f"{settings['out'].rstrip('/')}/probe"], cwd=root)
    if probe.returncode != 0:
        raise MemoryError_(f"add {settings['out'].split('/')[0]}/ to .gitignore first: the copy must never be committed")
    out = root / settings["out"]
    manifest_path, pending_path = out / "manifest.json", out / "pending_manifest.json"
    if done:
        if not pending_path.is_file():
            raise MemoryError_("no pending copy: run `sync` first")
        write(manifest_path, read(pending_path))
        print(f"✓ sync: {rel(root, manifest_path)} now records the uploaded copy")
        return 0
    commit = git(root, "rev-parse", rev).decode().strip()
    tracked = [p for p in git(root, "ls-tree", "-r", "-z", "--name-only", commit).decode("utf-8").split("\0") if p]
    chosen = sorted(p for p in tracked if any(fnmatch.fnmatch(p, pattern) for pattern in settings["files"]))
    previous = json.loads(read(manifest_path)).get("files", {}) if manifest_path.is_file() else {}
    files, changed = {}, []
    for path in chosen:
        data = git(root, "show", f"{commit}:{path}")
        sha = hashlib.sha256(data).hexdigest()
        files[path] = {"name": path.replace("/", "__"), "sha256": sha, "bytes": len(data)}
        if previous.get(path, {}).get("sha256") != sha:
            changed.append((len(data) - previous.get(path, {}).get("bytes", 0), path, data))
    removed = sorted(set(previous) - set(files))
    upload = out / f"upload_{commit[:12]}"
    for _, path, data in sorted(changed):
        target = upload / files[path]["name"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    write(pending_path, json.dumps({"commit": commit, "files": files}, indent=1, sort_keys=True) + "\n")
    table = ["# Project copy manifest", "", f"Commit `{commit}`. The repository is the source; this copy is derived.",
             "", "| Document in the Project | Path in the repository | SHA-256 | Bytes |", "|---|---|---|---|"]
    table += [f"| {f['name']} | {p} | {f['sha256'][:16]} | {f['bytes']} |" for p, f in sorted(files.items())]
    if changed or removed:
        write(upload / "project_manifest.md", "\n".join(table) + "\n")
    print(f"✓ sync: {len(changed)} document(s) to upload from {rel(root, upload)} (smallest growth first), "
          f"plus project_manifest.md" if changed else "✓ sync: nothing changed since the last copy")
    for _, path, _ in sorted(changed):
        print(f"  - {files[path]['name']}")
    for path in removed:
        print(f"• {path} is in the Project but no longer selected: remove it only with the owner's yes")
    print("Then run `sync --done` so the next copy compares with this one.")
    return 0


# ---------------------------------------------------------------- hooks and init
def backup_transcript(root: Path, cfg: dict, event: dict) -> Path | None:
    settings = cfg["transcript_backup"]
    source = Path(event.get("transcript_path") or "")
    if not settings.get("enabled") or not source.is_file():
        return None
    folder = outside_repository(settings["dir"], root, "transcript backup folder")
    folder.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(folder).free < 2 * source.stat().st_size:
        print("✗ transcript backup skipped: not enough free disk space", file=sys.stderr)
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session = re.sub(r"[^A-Za-z0-9-]", "_", str(event.get("session_id", "session")))
    target, number = folder / f"{session}-{stamp}.jsonl.gz", 1
    while target.exists():
        number += 1
        target = folder / f"{session}-{stamp}-{number}.jsonl.gz"
    with source.open("rb") as raw, gzip.open(target, "wb") as packed:
        shutil.copyfileobj(raw, packed)
    return target


def hook_precompact() -> int:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        event = json.loads(raw) if raw.strip() else {}
        root = find_root(Path(event["cwd"]) if event.get("cwd") else None)
        cfg = load_config(root)
        if cfg is None:
            return 0
        with contextlib.redirect_stdout(sys.stderr):
            for step in (lambda: backup_transcript(root, cfg, event), lambda: hook_capture(root, cfg, event)):
                try:
                    step()
                except Exception as error:  # one step failing must not stop the other
                    print(f"you-decide memory hook: {error}")
    except Exception as error:  # a hook must never break the session
        print(f"you-decide memory hook: {error}", file=sys.stderr)
    return 0


def init(root: Path, level: str, force: bool) -> int:
    path = root / CONFIG
    if path.is_file() and not force:
        print(f"✓ init: {rel(root, path)} already exists (use --force to replace it)")
        return 0
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if level == "strict":
        config["transcript_backup"]["enabled"] = True
    else:
        config["append_only"] = [p for p in config["append_only"] if p != "docs/ai_usage.md"]
    write(path, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print(f"✓ init: wrote {rel(root, path)} (level {level})")
    if not (root / config["conservation"]).is_file():
        guard(root, load_config(root), update=True)
    return 0


def check(root: Path, cfg: dict) -> int:
    status = guard(root, cfg) | write_map(root, cfg, check=True)
    pending = plan_moves(root, cfg)
    for plan in pending:
        print("• to move: " + apply_move(plan, dry_run=True))
    state_lines = lines_of(read(root / cfg["state"]["path"]))
    if len(state_lines) > cfg["state"]["max_lines"] and not any(p["kind"] == "state" for p in pending):
        print(f"• {cfg['state']['path']} is over its {cfg['state']['max_lines']}-line budget with no movable entry "
              f"under \"{cfg['state']['log_heading']}\"")
    if pending and cfg.get("strict_moves"):
        status = 1
    return status


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--level", choices=["standard", "strict"], default="standard")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("qa")
    p.add_argument("transcripts", nargs="*", type=Path)
    p.add_argument("--check", action="store_true")
    p.add_argument("--all", action="store_true", help="read every transcript of this project")
    p.add_argument("--accept", nargs="*", default=[])
    p = sub.add_parser("guard")
    p.add_argument("--update", action="store_true")
    p.add_argument("--accept")
    p = sub.add_parser("move")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("map")
    p.add_argument("--check", action="store_true")
    p = sub.add_parser("resume")
    p.add_argument("--transcript", type=Path)
    p = sub.add_parser("journal")
    p.add_argument("transcripts", nargs="*", type=Path)
    p.add_argument("--all", action="store_true", help="read every transcript of this project")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--accept", nargs="*", default=[])
    p = sub.add_parser("sync")
    p.add_argument("--rev", default="HEAD")
    p.add_argument("--done", action="store_true")
    sub.add_parser("check")
    sub.add_parser("hook-precompact")
    args = parser.parse_args(argv)
    if args.command == "hook-precompact":
        return hook_precompact()
    root = find_root()
    try:
        if args.command == "init":
            return init(root, args.level, args.force)
        cfg = load_config(root)
        if cfg is None:
            if args.command == "resume":
                print(resume_text(root, None))
                return 0
            raise MemoryError_(f"no {CONFIG.as_posix()} in {root}: run `init` (standard and strict levels only)")
        if args.command == "qa":
            return capture_qa(root, cfg, transcripts_or_latest(root, args.transcripts, args.all), args.check,
                              tuple(args.accept))
        if args.command == "guard":
            return guard(root, cfg, args.update, args.accept)
        if args.command == "move":
            return move(root, cfg, args.dry_run)
        if args.command == "map":
            return write_map(root, cfg, args.check)
        if args.command == "resume":
            print(resume_text(root, cfg, args.transcript))
            return 0
        if args.command == "journal":
            return journal(root, cfg, transcripts_or_latest(root, args.transcripts, args.all), args.dry_run,
                           args.accept)
        if args.command == "sync":
            return sync(root, cfg, args.rev, args.done)
        if args.command == "check":
            return check(root, cfg)
    except MemoryError_ as error:
        print(f"✗ {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
