"""A security review of the code Luma writes, before anyone runs it.

Reads every Python, JavaScript and HTML file in a folder for the mistakes that most often turn into real breaches:
keys and passwords written into the code, SQL built from strings, shell commands built from input, eval of input,
unsafe deserializing, TLS checks turned off, HTML injected from data, weak password hashing, and debug servers.
Each finding says where it is, why it matters and how to fix it. High findings send the code back to the coding
agent with that list, the way a failing test does, so what reaches the owner has them fixed.

It's a careful first pass, not a guarantee: plain patterns, no network, nothing executed.
"""
from __future__ import annotations

import re
from pathlib import Path

KINDS = {".py": "python", ".js": "js", ".mjs": "js", ".cjs": "js", ".ts": "js", ".jsx": "js", ".tsx": "js", ".html": "html", ".htm": "html"}
SKIP = re.compile(r"(?:^|/)(?:node_modules|\.git|\.venv|venv|__pycache__|dist|build)(?:/|$)")
TEST_FILE = re.compile(r"(?:^|/)(?:tests?/|test_[^/]+\.py$|[^/]+_test\.py$|[^/]+\.test\.[cm]?[jt]sx?$)")

# (id, severity, languages, pattern, what it is, how to fix it)
RULES = [
    ("secret", "high", {"python", "js", "html"},
     r"(?:sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{35}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)",
     "A real-looking API key or private key is written into the code.", "Read it from an environment variable or the system keychain, and revoke this one."),
    ("password", "high", {"python", "js"},
     r"""(?i)(?<![a-z])(?:password|passwd|pwd|secret|api_?key|access_?token|auth_?token)(?![a-z])\s*[:=]\s*["'][^"'\s]{6,}["']""",
     "A password or key is written into the code.", "Load it from an environment variable or a secrets store instead."),
    ("sql", "high", {"python"},
     r"""\.execute(?:many)?\(\s*(?:f["']|["'][^"']*["']\s*(?:%|\+|\.format\())""",
     "SQL is built from strings, so input can rewrite the query (SQL injection).", "Use placeholders: cursor.execute(\"... WHERE id = ?\", (value,))."),
    ("sql", "high", {"js"},
     r"""\.(?:query|execute|raw|run|all|get)\(\s*(?:`[^`]*\$\{|["'][^"']*["']\s*\+)""",
     "SQL is built from strings, so input can rewrite the query (SQL injection).", "Use the driver's placeholders (? or $1) and pass the values separately."),
    ("shell", "high", {"python"},
     r"""(?:os\.system|os\.popen|subprocess\.(?:run|call|check_output|check_call|Popen))\((?=[^)]*shell\s*=\s*True)[^)]*(?:f["']|\+|%|\.format\()""",
     "A shell command is built from data and run with shell=True (command injection).", "Pass a list of arguments without shell=True: subprocess.run([\"ls\", path])."),
    ("shell", "high", {"python"},
     r"""os\.system\(\s*(?:f["']|[^"')]*\+)""",
     "A shell command is built from data (command injection).", "Use subprocess.run with a list of arguments."),
    ("shell", "high", {"js"},
     r"""(?:child_process\.)?\b(?:exec|execSync)\(\s*(?:`[^`]*\$\{|["'][^"']*["']\s*\+)""",
     "A shell command is built from data (command injection).", "Use execFile/spawn with an array of arguments."),
    ("eval", "high", {"python"},
     r"""\b(?:eval|exec)\(\s*(?:input\(|request\.|sys\.argv|data\b|body\b|params\b|user)""",
     "Input is run as code with eval/exec.", "Parse it instead (json.loads, ast.literal_eval for plain values)."),
    ("eval", "high", {"js", "html"},
     r"""\b(?:eval|new Function)\(\s*(?!["'`][^"'`]*["'`]\s*\))""",
     "Text is run as code with eval/new Function.", "Parse it (JSON.parse) or map it to known functions instead."),
    ("deserialize", "high", {"python"},
     r"""\b(?:pickle|cPickle|dill|marshal)\.loads?\(|yaml\.load\((?![^)]*Loader\s*=\s*yaml\.(?:Safe|CSafe)Loader)""",
     "Untrusted data is unpickled or loaded with an unsafe YAML loader, which can run code.", "Use JSON, or yaml.safe_load."),
    ("tls", "high", {"python", "js"},
     r"""verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*["']?0|ssl\._create_unverified_context|CERT_NONE""",
     "Certificate checks are turned off, so anyone on the network can read and change the traffic.", "Leave verification on; fix the certificate instead."),
    ("xss", "medium", {"js", "html"},
     r"""\.(?:innerHTML|outerHTML)\s*\+?=\s*(?!["'`][^"'`$]*["'`]\s*;)|document\.write\(|insertAdjacentHTML\(""",
     "HTML is built from data, so a name or message can run script on the page (XSS).", "Set textContent, or build elements with createElement."),
    ("hash", "medium", {"python", "js"},
     r"""(?i)(?:hashlib\.(?:md5|sha1)\(|createHash\(\s*["'](?:md5|sha1)["'])(?=.{0,80}pass)|(?:pass\w*).{0,80}(?:hashlib\.(?:md5|sha1)\(|createHash\(\s*["'](?:md5|sha1))""",
     "Passwords are hashed with MD5 or SHA-1, which are fast to crack.", "Use a password hash: bcrypt, scrypt or argon2 (hashlib.scrypt in Python)."),
    ("debug", "medium", {"python"},
     r"""\.run\([^)]*debug\s*=\s*True""",
     "The server runs in debug mode, which can let anyone run code from the error page.", "Turn debug off outside your own computer."),
    ("bind", "low", {"python", "js"},
     r"""["']0\.0\.0\.0["']""",
     "The server listens on every network, not just this computer.", "Use 127.0.0.1 unless other devices really need to reach it."),
    ("http", "low", {"python", "js", "html"},
     r"""["']http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|example\.(?:com|org)|www\.w3\.org)[^"']+["']""",
     "A plain http:// address: anything sent there can be read on the way.", "Use https://."),
]
COMPILED = [(rid, sev, langs, re.compile(pattern), what, fix) for rid, sev, langs, pattern, what, fix in RULES]
ORDER = {"high": 0, "medium": 1, "low": 2}


def audit_text(text, path="file.py"):
    """Findings in one file: [{"rule", "severity", "path", "line", "code", "what", "fix"}]."""
    lang = KINDS.get(Path(path).suffix.lower())
    if not lang:
        return []
    found = []
    is_test = bool(TEST_FILE.search(str(path).replace("\\", "/")))
    for number, line in enumerate(str(text).splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "*", "<!--")) or "luma: allow" in line:
            continue
        for rid, sev, langs, pattern, what, fix in COMPILED:
            if lang not in langs or not pattern.search(line):
                continue
            if is_test and rid in {"password", "bind", "http"}:
                continue  # made-up passwords and local servers in tests aren't a risk
            if rid == "password" and re.search(r"(?i)[\"'](?:\*+|x+|changeme|your[_-]?\w*|<[^>]+>|example\w*|test\w*|placeholder|\.\.\.)[\"']", line):
                continue
            found.append({"rule": rid, "severity": sev, "path": str(path), "line": number, "code": stripped[:160], "what": what, "fix": fix})
            break
    return found


def audit_folder(folder, limit_files=400):
    """Every finding in the code under folder, worst first."""
    folder = Path(folder)
    findings = []
    for path in sorted(folder.rglob("*"))[: limit_files * 4]:
        rel = path.relative_to(folder).as_posix()
        if not path.is_file() or SKIP.search(rel) or path.suffix.lower() not in KINDS or path.stat().st_size > 1_000_000:
            continue
        findings += audit_text(path.read_text(encoding="utf-8", errors="replace"), rel)
    return sorted(findings, key=lambda f: (ORDER[f["severity"]], f["path"], f["line"]))


def report(findings, title="Security review"):
    """The findings as a short markdown report a person can act on."""
    if not findings:
        return f"# {title}\n\nNo common security mistakes found. (A careful first pass, not a guarantee.)\n"
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in ("high", "medium", "low")}
    lines = [f"# {title}", "", ", ".join(f"{n} {s}" for s, n in counts.items() if n) + ".", ""]
    for f in findings:
        lines += [f"## {f['severity'].title()}: {f['path']}:{f['line']}", "", f"`{f['code']}`", "", f"{f['what']} **Fix:** {f['fix']}", ""]
    return "\n".join(lines)


def blocking(findings):
    return [f for f in findings if f["severity"] == "high"]


def for_the_coder(findings, limit=8):
    """What goes back to the coding agent: each high finding, where it is and how to fix it."""
    return "; ".join(f"{f['path']}:{f['line']} {f['what']} Fix: {f['fix']}" for f in blocking(findings)[:limit])
