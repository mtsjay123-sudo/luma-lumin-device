"""Running code Luma wrote, without letting it touch anything else.

Only Python (Luma's own) and Node can run, only inside one project folder, with a clean environment
(no keys, no tokens, no proxies), a time limit, and caps on CPU, file size and open files. On a Mac
it also runs inside Apple's sandbox: no network at all, writes only inside the project folder and the
temp folders, and nothing in the owner's home folder can be read except the project and the tools
themselves. Elsewhere those last guarantees aren't available, so the engine asks the owner once per
project before any code runs (contained() says which is which).
"""
from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
OUTPUT_LIMIT = 20_000
BLOCKED = ("pip", "ensurepip", "venv", "http.server", "smtpd")  # installing and serving need the owner, not a script


def contained():
    """True when code runs inside the operating system's sandbox (no network, no reading the owner's files)."""
    return sys.platform == "darwin" and os.path.exists(SANDBOX_EXEC)


def node_path():
    """Node to run JavaScript: the one the app hands over (Electron running as Node), else one on PATH."""
    given = os.environ.get("LUMA_NODE")
    if given and os.path.exists(given):
        return given
    return shutil.which("node")


def _quote(path):
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


def profile(cwd, reads):
    """Apple sandbox rules. Later rules win, so each deny is followed by the narrow allows it needs."""
    home = Path.home().resolve()
    readable = " ".join(f"(subpath {_quote(p)})" for p in sorted({str(Path(r).resolve()) for r in reads if r}))
    return "\n".join([
        "(version 1)",
        "(allow default)",
        "(deny network*)",
        "(deny file-write*)",
        f'(allow file-write* (subpath {_quote(cwd)}) (subpath "/private/tmp") (subpath "/private/var/folders") (literal "/dev/null") (literal "/dev/tty") (regex #"^/dev/fd/"))',
        f"(deny file-read* (subpath {_quote(home)}))",
        f"(allow file-read* (subpath {_quote(cwd)}) {readable})",
    ])


def _command(command, cwd):
    """The command as a list, with 'python'/'node' pointed at the real interpreters. Anything else is refused."""
    parts = shlex.split(command) if isinstance(command, str) else [str(p) for p in command]
    if not parts:
        raise ValueError("There's no command to run.")
    head = Path(parts[0]).name
    if head in {"python", "python3", "py"}:
        interpreter = sys.executable
        if len(parts) > 2 and parts[1] == "-m" and parts[2].split(".")[0] in BLOCKED:
            raise ValueError("Installing packages or starting servers needs your OK; a script can't do it on its own.")
    elif head in {"node", "nodejs"}:
        interpreter = node_path()
        if not interpreter:
            raise ValueError("Node isn't available here, so JavaScript can't run yet.")
    else:
        raise ValueError("Only Python and Node can run in a project.")
    for arg in parts[1:]:
        if arg.startswith("/") and not str(Path(arg).resolve()).startswith(str(Path(cwd).resolve())):
            raise ValueError("Scripts can only use files inside the project.")
    return [interpreter] + parts[1:]


def _limits(cpu_seconds, memory_mb):
    def apply():
        import resource
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 5))
        resource.setrlimit(resource.RLIMIT_FSIZE, (100 * 2 ** 20, 100 * 2 ** 20))
        resource.setrlimit(resource.RLIMIT_NOFILE, (512, 512))
        if sys.platform.startswith("linux"):  # macOS doesn't enforce address-space limits
            resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 2 ** 20, memory_mb * 2 ** 20))
    return apply


def _tail(text):
    text = text.decode("utf-8", "replace") if isinstance(text, bytes) else (text or "")
    return text if len(text) <= OUTPUT_LIMIT else "…" + text[-OUTPUT_LIMIT:]


def run(command, cwd, timeout=60, memory_mb=2048, stdin=None):
    """Run one Python or Node command inside `cwd`. Returns what happened; never raises for the program's own failure."""
    cwd = Path(cwd).resolve()
    cwd.mkdir(parents=True, exist_ok=True)
    argv = _command(command, cwd)
    scratch = cwd / ".luma"
    (scratch / "home").mkdir(parents=True, exist_ok=True)
    (scratch / "tmp").mkdir(parents=True, exist_ok=True)
    env = {"PATH": os.pathsep.join([str(Path(argv[0]).parent), "/usr/bin", "/bin"]), "HOME": str(scratch / "home"),
           "TMPDIR": str(scratch / "tmp"), "LANG": "en_US.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
           "PYTHONIOENCODING": "utf-8", "NODE_OPTIONS": "", "NO_COLOR": "1"}
    if os.environ.get("LUMA_NODE") and argv[0] == os.environ.get("LUMA_NODE"):
        env["ELECTRON_RUN_AS_NODE"] = "1"
    sandboxed = contained()
    if sandboxed:
        reads = [Path(argv[0]).resolve().parent.parent, sys.prefix, sys.base_prefix, sys.exec_prefix]
        argv = [SANDBOX_EXEC, "-p", profile(cwd, reads)] + argv
    posix = os.name == "posix"
    started = time.time()
    proc = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            preexec_fn=_limits(int(timeout) + 2, memory_mb) if posix else None,
                            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if not posix else 0)
    timed_out = False
    try:
        out, err = proc.communicate(input=stdin.encode() if isinstance(stdin, str) else stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL) if posix else proc.kill()
        except (ProcessLookupError, PermissionError):
            pass
        out, err = proc.communicate()
    code = proc.returncode
    return {"ok": code == 0 and not timed_out, "code": code, "timed_out": timed_out, "seconds": round(time.time() - started, 2),
            "stdout": _tail(out), "stderr": _tail(err) + ("\n[stopped: it ran past the time limit]" if timed_out else ""),
            "contained": "sandbox" if sandboxed else "limits"}
