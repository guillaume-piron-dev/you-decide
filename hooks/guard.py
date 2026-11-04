#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""You Decide guardrail for Claude Code (PreToolUse hook).

Reads the tool call as JSON on stdin and prints a permission decision as JSON on stdout:
- "ask"  : the owner must say yes (network sends, irreversible or destructive actions, likely secrets);
- "deny" : the call is blocked (a high-confidence secret, a shell command that prints a secret file).
Prints nothing when it has no decision: the normal permission flow then applies.

Pattern-based: it catches the usual commands, not every possible one. It is a guardrail, not a security
guarantee. Standard library only. Any internal error means "no decision"; it never breaks the session.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

PREFIX = "You Decide guard: "
MAX_COMMAND = 20_000
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

# ---------------------------------------------------------------- secrets in text
DENY_SECRETS: list[tuple[str, str]] = [
    (r"-----BEGIN (RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----\s*[A-Za-z0-9+/=\s]{100,}", "a private key"),
    (r"\bAKIA[0-9A-Z]{16}\b", "an AWS access key id"),
    (r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "a GitHub token"),
    (r"\bgithub_pat_[A-Za-z0-9_]{50,}\b", "a GitHub fine-grained token"),
    (r"\bglpat-[A-Za-z0-9_\-]{20,}\b", "a GitLab token"),
    (r"\bsk-ant-[A-Za-z0-9_\-]{20,}", "an Anthropic API key"),
    (r"\bsk-(proj-)?[A-Za-z0-9_\-]{40,}", "an API secret key"),
    (r"\bxox[abprs]-[A-Za-z0-9-]{10,}", "a Slack token"),
    (r"\bAIza[0-9A-Za-z_\-]{35}\b", "a Google API key"),
    (r"\b(sk|rk)_live_[0-9a-zA-Z]{24,}\b", "a Stripe live key"),
]
PLACEHOLDER = re.compile(r"(?i)(example|x{6,}|\.\.\.|<[^>]*>|\*{3,}|0{8,}|your[-_ ]|redacted|dummy|fake|sample)")
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
CREDENTIAL = re.compile(r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret"
                        r"|private[_-]?key)\b[\"']?\s*[:=]\s*[\"']([^\"'\s]{12,})[\"']")
INDIRECT = re.compile(r"(?i)(\$\{|\{\{|%\(|process\.env|os\.environ|getenv)")
KEBAB = re.compile(r"[a-z0-9]+([-_.][a-z0-9]+)+")
LOW_RISK_PATH = re.compile(r"(?i)(^|/)(tests?|__tests__|specs?|fixtures?|testdata|docs?|examples?)(/|$)"
                           r"|\.(md|mdx|rst|txt)$|\.example$|[._](test|spec)\.\w+$|_test\.\w+$")


def secret_in(text: str) -> str | None:
    for pattern, what in DENY_SECRETS:
        for match in re.finditer(pattern, text):
            if not PLACEHOLDER.search(match.group(0)):
                return what
    return None


def looks_random(value: str) -> bool:
    classes = sum([any(c.islower() for c in value), any(c.isupper() for c in value),
                   any(c.isdigit() for c in value), any(not c.isalnum() for c in value)])
    return (len(value) >= 12 and classes >= 3 and not KEBAB.fullmatch(value)
            and not PLACEHOLDER.search(value) and not INDIRECT.search(value))


# ---------------------------------------------------------------- secret files
DENY_FILE = re.compile(r"(?i)^(\.env(\.(?!(example|sample|template|dist|defaults)$)[\w.-]+)?|.+\.(key|p12|pfx|keystore|jks|kdbx)"
                       r"|id_(rsa|dsa|ecdsa|ed25519)|\.git-credentials|\.netrc)$")
ASK_FILE = re.compile(r"(?i)^(.+\.pem|\.npmrc|\.pypirc|credentials(\.json)?|service[-_]?account.*\.json"
                      r"|secrets?\.(json|ya?ml|toml))$")
READERS = {"cat", "type", "get-content", "gc", "less", "more", "head", "tail", "bat", "batcat", "nl", "xxd", "od",
           "hexdump", "base64", "strings", "grep", "egrep", "fgrep", "rg", "ag", "ack", "findstr", "select-string",
           "sls", "sed", "awk", "gawk", "cut", "sort", "uniq", "tac", "jq", "yq", "diff", "cmp", "column"}
MOVERS = {"cp", "copy", "copy-item", "mv", "move", "move-item", "tar", "zip", "7z", "scp", "rsync", "curl", "wget"}


def file_kind(token: str) -> str | None:
    path = token.strip("'\"@<>").rstrip("/")
    name = path.rsplit("/", 1)[-1]
    if not name:
        return None
    if DENY_FILE.match(name):
        return "deny"
    if ASK_FILE.match(name) or path.lower().endswith(".docker/config.json"):
        return "ask"
    return None


# ---------------------------------------------------------------- shell parsing
WRAPPERS = {"sudo", "doas", "time", "nohup", "nice", "command", "exec", "builtin", "xargs"}
RUNNERS = {"npx", "bunx", "pnpx", "exec", "run", "bundle", "uv", "poetry", "pnpm", "yarn", "python", "python3", "py",
           "php", "-m", "-3"}
SHELLS = {"sh", "bash", "zsh", "dash", "fish", "python", "python3", "py", "node", "perl", "ruby", "pwsh", "powershell",
          "iex", "invoke-expression", "cmd"}
DOWNLOADERS = {"curl", "wget", "iwr", "irm", "invoke-webrequest", "invoke-restmethod"}
SQL_CLIENTS = {"psql", "mysql", "mariadb", "sqlite3", "sqlcmd", "duckdb", "cockroach", "clickhouse-client", "mongo",
               "mongosh", "pgcli", "mycli", "litecli"}
DESTRUCTIVE_SQL = re.compile(r"(?i)\b(drop\s+(table|database|schema|view|index|column|role|user)\b|truncate\s+"
                             r"|alter\s+table\s+[\w\"`.]+\s+drop\b|delete\s+from\s+[\w\"`.]+\s*(;|$|[\"'])"
                             r"|dropdatabase\(|\.drop\(\)|deletemany\(\s*\{\s*\}\s*\))")
DESTRUCTIVE_MIGRATION = re.compile(
    r"(?i)^(sqlx\s+migrate\s+revert|diesel\s+(migration\s+(revert|redo)|database\s+reset)|alembic\s+downgrade"
    r"|(rails|rake)\s+db:(drop|reset|rollback|purge|schema:load)|prisma\s+(migrate\s+reset|db\s+push\b.*--(force-reset"
    r"|accept-data-loss))|manage\.py\s+(flush|migrate\s+\S+\s+zero)|artisan\s+(migrate:(fresh|reset|rollback|refresh)"
    r"|db:wipe)|knex\s+migrate:(rollback|down)|sequelize(-cli)?\s+db:(drop|migrate:undo)|typeorm\s+schema:drop"
    r"|dotnet\s+ef\s+database\s+(drop|update\s+0)|goose\s+\S*\s*(down|reset)|migrate\b.*\b(down|drop|force)\b"
    r"|flyway\s+clean|liquibase\s+(rollback|drop-?all))")
DEPLOY_VERBS = {
    "terraform": {"apply", "destroy", "import"}, "pulumi": {"up", "destroy"}, "cdk": {"deploy", "destroy"},
    "kubectl": {"apply", "delete", "replace", "patch", "scale", "rollout", "drain", "edit", "create"},
    "helm": {"install", "upgrade", "uninstall", "rollback"}, "netlify": {"deploy"}, "firebase": {"deploy"},
    "wrangler": {"deploy", "publish", "delete"}, "fly": {"deploy", "destroy"}, "flyctl": {"deploy", "destroy"},
    "railway": {"up"}, "serverless": {"deploy", "remove"}, "sls": {"deploy", "remove"},
    "gcloud": {"deploy", "delete", "create", "update"}, "az": {"create", "delete", "update", "deploy"},
}
PUBLISHERS = {"npm": "publish", "pnpm": "publish", "yarn": "publish", "bun": "publish", "cargo": "publish",
              "twine": "upload", "gem": "push", "poetry": "publish", "uv": "publish", "flit": "publish",
              "hatch": "publish"}
SECRET_VAR = re.compile(r"(?i)\$(\{)?(env:)?\w*(key|token|secret|passw|pwd|credential)\w*")


def tokenize(command: str) -> list[str]:
    text = command.replace("\\", "/")
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars="();<>|&\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return re.findall(r"[;&|<>()\n]+|[^\s;&|<>()]+", text)


def is_separator(token: str) -> bool:
    return bool(token) and all(c in ";&|()\n" for c in token)


def segments(tokens: list[str]) -> list[tuple[str, list[str]]]:
    """Split tokens into (separator before, tokens) pairs; redirections stay inside their segment."""
    result, current, before = [], [], ""
    for token in tokens:
        if is_separator(token):
            if current:
                result.append((before, current))
            current, before = [], token
        else:
            current.append(token)
    if current:
        result.append((before, current))
    return result


def name_of(token: str) -> str:
    name = token.rsplit("/", 1)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def strip_wrappers(tokens: list[str]) -> list[str]:
    i = 0
    while i < len(tokens):
        if re.match(r"^[A-Za-z_]\w*=", tokens[i]):
            i += 1
        elif name_of(tokens[i]) in WRAPPERS and i + 1 < len(tokens):
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 2 if tokens[i] in ("-u", "-g", "-U", "-C", "-D", "-h", "-p", "-r", "-t", "-n") else 1
        elif name_of(tokens[i]) == "env" and any(not re.match(r"^[A-Za-z_]\w*=", t) and not t.startswith("-")
                                                   for t in tokens[i + 1:]):
            i += 1
            while i < len(tokens) and (tokens[i].startswith("-") or re.match(r"^[A-Za-z_]\w*=", tokens[i])):
                i += 1
        else:
            break
    return tokens[i:]


def hosts_all_loopback(args: list[str]) -> bool:
    urls = [a for a in args if "://" in a or re.match(r"^(localhost|127\.|\[::1\]|0\.0\.0\.0)", a)]
    if not urls:
        return False
    for url in urls:
        host = re.sub(r"^\w+://", "", url).split("/")[0].split("@")[-1]
        host = host if host.startswith("[") else host.rsplit(":", 1)[0]
        if not (host in ("localhost", "[::1]", "0.0.0.0") or host.startswith("127.") or host.endswith(".localhost")):
            return False
    return True


def curl_sends(args: list[str]) -> bool:
    takes_value = set("HouXAebcDKmrwxyYzECPQtU")
    for i, arg in enumerate(args):
        if arg in ("--json", "--upload-file", "--form", "--form-string") or arg.startswith("--data"):
            return True
        if arg == "--request" and i + 1 < len(args) and args[i + 1].upper() in MUTATING:
            return True
        if arg.startswith("-") and not arg.startswith("--"):
            for j, char in enumerate(arg[1:], start=1):
                if char in "dFT":
                    return True
                if char == "X":
                    method = arg[j + 1:] or (args[i + 1] if i + 1 < len(args) else "")
                    if method.upper() in MUTATING:
                        return True
                    break
                if char in takes_value:
                    break
    return False


def git_rules(args: list[str]) -> str | None:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env") else 1
    if i >= len(args):
        return None
    sub, rest = args[i].lower(), args[i + 1:]
    flags = set(rest)
    if sub == "push":
        return "git push sends code over the network"
    if sub == "reset" and flags & {"--hard", "--merge", "--keep"}:
        return "git reset discards local changes"
    if sub == "clean" and any(a == "--force" or (a.startswith("-") and not a.startswith("--") and "f" in a)
                              for a in rest):
        return "git clean deletes untracked files"
    if sub == "rebase" and not flags & {"--continue", "--abort", "--skip", "--quit", "--edit-todo",
                                         "--show-current-patch"}:
        return "git rebase rewrites history"
    if sub == "commit" and "--amend" in flags:
        return "amends an existing commit"
    if sub == "branch" and ("-D" in flags or (flags & {"-d", "--delete"} and flags & {"-f", "--force"})):
        return "force-deletes a branch"
    if sub in ("filter-branch", "filter-repo"):
        return "rewrites the whole history"
    if sub == "checkout" and flags & {"-f", "--force", ".", "--"}:
        return "git checkout discards local changes"
    if sub == "restore" and (not flags & {"--staged", "-S"} or flags & {"--worktree", "-W"}):
        return "git restore discards local changes"
    if sub == "stash" and rest[:1] and rest[0] in ("drop", "clear"):
        return "deletes stashed work"
    if (sub == "reflog" and "expire" in flags) or (sub == "gc" and any(a.startswith("--prune") for a in rest)):
        return "prunes recoverable history"
    return None


def segment_rules(words: list[str], before: str, previous: list[str]) -> tuple[str, str] | None:
    """Rules for one command. Returns (kind, reason) or None."""
    cmd, args = name_of(words[0]), words[1:]
    low = [a.lower() for a in args]
    if before in ("|", "|&") and previous and name_of(previous[0]) in DOWNLOADERS and cmd in SHELLS:
        return "ask", "pipes a download into a shell"
    if cmd in READERS:
        kinds = {file_kind(a) for a in args}
        if "deny" in kinds:
            return "deny", "prints a secret file; secrets must stay out of the conversation"
        if "ask" in kinds:
            return "ask", "prints a file that may hold secrets"
    if cmd in MOVERS and any(file_kind(a) for a in args):
        return "ask", "copies, packs or sends a secret file"
    for i, token in enumerate(words[:-1]):
        if token in (">", ">>", "<") and file_kind(words[i + 1]):
            return "ask", "reads or writes a secret file through a redirection"
    if cmd == "git":
        reason = git_rules(args)
        return ("ask", reason) if reason else None
    if cmd == "rm" and any((a in ("--recursive", "--force")) or (a.startswith("-") and not a.startswith("--")
                                                                  and set(a[1:]) & set("rRf")) for a in args):
        return "ask", "recursive or forced deletion"
    if cmd in ("remove-item", "ri", "del", "erase", "rd", "rmdir") and any(
            a.startswith("-rec") or a in ("-r", "-force", "-fo", "/s") for a in low):
        return "ask", "recursive or forced deletion"
    if cmd == "find" and ("-delete" in low or any(low[i] == "-exec" and i + 1 < len(low) and name_of(low[i + 1])
                                                  in ("rm", "del") for i in range(len(low)))):
        return "ask", "deletes the files it finds"
    if cmd == "docker" and low[:1] == ["push"]:
        return "ask", "pushes an image to a registry"
    if cmd == "docker" and len(low) >= 2 and low[0] in ("system", "volume", "image", "container", "builder") \
            and low[1] in ("prune", "rm"):
        return "ask", "deletes Docker data"
    if cmd in PUBLISHERS and PUBLISHERS[cmd] in low[:2] or (cmd == "dotnet" and low[:2] == ["nuget", "push"]):
        return "ask", "publishes a package"
    if cmd in SQL_CLIENTS and DESTRUCTIVE_SQL.search(" ".join(args)):
        return "ask", "destructive SQL"
    if cmd == "redis-cli" and set(low) & {"flushall", "flushdb"}:
        return "ask", "wipes a Redis database"
    runner_free = list(words)
    while len(runner_free) > 1 and name_of(runner_free[0]) in RUNNERS:
        runner_free = runner_free[1:]
    if DESTRUCTIVE_MIGRATION.match(" ".join([name_of(runner_free[0])] + runner_free[1:])):
        return "ask", "reverts, resets or drops the database schema"
    if cmd == "curl" and curl_sends(args) and not hosts_all_loopback(args):
        return "ask", "sends data over the network"
    if cmd == "wget" and not hosts_all_loopback(args) and any(
            a.startswith(("--post-data", "--post-file", "--body-data", "--body-file"))
            or (a.startswith("--method=") and a.split("=", 1)[1].upper() in MUTATING) for a in args):
        return "ask", "sends data over the network"
    if cmd in ("iwr", "irm", "invoke-webrequest", "invoke-restmethod") and not hosts_all_loopback(args) and (
            set(low) & {"-body", "-infile", "-form"}
            or any(low[i] == "-method" and i + 1 < len(low) and low[i + 1].upper() in MUTATING
                   for i in range(len(low)))):
        return "ask", "sends data over the network"
    if cmd in ("http", "https", "xh", "xhs") and any(a.upper() in MUTATING for a in args) \
            and not hosts_all_loopback(args):
        return "ask", "sends data over the network"
    if cmd in ("scp", "sftp", "ftp", "nc", "ncat", "netcat"):
        return "ask", "transfers data to or from a remote host"
    if cmd == "rsync" and any("rsync://" in a or (re.match(r"^[^/]+:", a) and not re.match(r"^[A-Za-z]:/", a))
                              for a in args):
        return "ask", "copies files to or from a remote host"
    if cmd == "gh" and low[:1] == ["api"] and (set(low) & {"-f", "--field", "--raw-field", "--input"} or any(
            low[i] in ("-x", "--method") and i + 1 < len(low) and low[i + 1].upper() in MUTATING
            for i in range(len(low)))):
        return "ask", "calls the GitHub API with a write"
    if cmd == "gh" and len(low) >= 2 and low[0] in ("pr", "release", "repo", "gist", "issue", "workflow", "secret",
                                                     "variable") and low[1] in (
            "create", "delete", "edit", "upload", "merge", "close", "fork", "comment", "run", "set", "reopen",
            "ready", "review"):
        return "ask", "acts on GitHub on your behalf"
    if cmd == "aws" and ((low[:1] == ["s3"] and len(low) > 1 and low[1] in ("cp", "mv", "rm", "sync", "rb", "mb"))
                         or any(re.match(r"^(delete|put|create|update|terminate|run|start|stop|modify|attach|detach"
                                         r"|invoke|publish|send)-", a) for a in low)):
        return "ask", "changes or transfers cloud resources"
    if cmd == "gsutil" and set(low) & {"cp", "mv", "rm", "rsync"}:
        return "ask", "changes or transfers cloud storage"
    if cmd in DEPLOY_VERBS and set(low) & DEPLOY_VERBS[cmd]:
        return "ask", "deploys or changes infrastructure"
    if cmd == "vercel" and not (low[:1] and low[0] in ("dev", "login", "whoami", "ls", "list", "env", "logs",
                                                       "inspect", "pull", "link", "build")):
        return "ask", "deploys or changes infrastructure"
    if cmd == "ansible-playbook":
        return "ask", "runs a playbook that may change remote machines"
    if cmd == "printenv" or (cmd in ("env", "set") and not [a for a in args if not a.startswith("-")]):
        return "ask", "prints environment variables, which may contain secrets"
    if cmd in ("get-childitem", "gci", "ls", "dir", "get-item", "gi") and any(a.startswith("env:") for a in low):
        return "ask", "prints environment variables, which may contain secrets"
    if (cmd in ("echo", "write-output", "write-host", "printf", "print") and any(SECRET_VAR.search(a) for a in args)) \
            or SECRET_VAR.fullmatch(words[0]):
        return "ask", "prints a secret environment variable"
    return None


def check_command(command: str) -> dict | None:
    if len(command) > MAX_COMMAND:
        return decision("ask", "the command is too long to check. The owner decides.")
    what = secret_in(command)
    if what:
        return decision("deny", f"the command contains {what}; secrets must stay out of commands and the project.")
    asks: list[str] = []
    previous: list[str] = []
    for before, tokens in segments(tokenize(command)):
        words = strip_wrappers(tokens)
        if not words:
            continue
        result = segment_rules(words, before, previous)
        if result and result[0] == "deny":
            return decision("deny", result[1])
        if result:
            asks.append(result[1])
        previous = words
    return decision("ask", asks[0] + ". The owner decides.") if asks else None


# ---------------------------------------------------------------- file writes
MIGRATION_PATH = re.compile(r"(?i)(^|/)(migrations?|migrate|db/schema)(/|$)")


def written_texts(tool_input: dict) -> list[str]:
    texts = [tool_input.get("content"), tool_input.get("new_string"), tool_input.get("new_source")]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict):
            texts.append(edit.get("new_string"))
    return [t for t in texts if isinstance(t, str) and t]


def check_write(tool_input: dict) -> dict | None:
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or "")
    path = path.replace("\\", "/")
    text = "\n".join(written_texts(tool_input))
    what = secret_in(text)
    if what:
        return decision("deny", f"the content contains {what}. Use an environment variable or a secret manager.")
    if path and file_kind(path):
        return decision("ask", f"writes {path}, a file meant for secrets; secrets should not live in the project folder.")
    if not LOW_RISK_PATH.search(path):
        if JWT.search(text):
            return decision("ask", "the content contains what looks like a JWT. The owner decides.")
        if any(looks_random(m.group(2)) for m in CREDENTIAL.finditer(text)):
            return decision("ask", "the content contains what looks like a hard-coded credential. The owner decides.")
    if path and MIGRATION_PATH.search(path) and DESTRUCTIVE_SQL.search(text):
        return decision("ask", f"destructive SQL in the migration {path}. The owner decides.")
    return None


# ---------------------------------------------------------------- entry point
def decision(kind: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": kind,
                                   "permissionDecisionReason": PREFIX + reason}}


def evaluate(event: dict) -> dict | None:
    tool = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    if tool in ("Bash", "PowerShell"):
        command = tool_input.get("command")
        return check_command(command) if isinstance(command, str) else None
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return check_write(tool_input)
    return None


def main() -> int:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        if not raw.strip():
            return 0
        result = evaluate(json.loads(raw))
        if result:
            sys.stdout.write(json.dumps(result))
    except Exception:  # a guardrail must never break the session
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
