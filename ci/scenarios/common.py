# Shared tools of the end-to-end scenarios (stdlib only, Python >= 3.9).
#
# A scenario gets a Ctx: a throw-away directory holding the project (work/), a fake HOME
# (home/), the gh/claude counting shims (bin/) and the simulated gh state. Nothing is read or
# written outside it (SM-05); every call of a real gh or claude is counted (SM-04).

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "skills" / "_core"
K_PATH = CORE / "harness.py"
FAKE_GH = CORE / "tests" / "fake_gh.py"
REPO_FIXTURES = ROOT / "tests" / "fixtures"

TEXT_SUFFIXES = (".py", ".md", ".json", ".txt", ".toml", ".sh", ".ps1", ".patch", ".yml")
SHIMMED = ("gh", "claude")
KEEP_MARKERS = ("git", "python", "python3", "py", "bash", "sh")
EXTENSIONS = ("", ".exe", ".cmd", ".bat")


class Skip(Exception):
    """The scenario cannot run here: a reason is mandatory, a SKIP is never a PASS."""


class Prep(Exception):
    """The preparation of a scenario failed (the cause is the message)."""


def has_exe(directory, names):
    for name in names:
        for ext in EXTENSIONS:
            if os.path.isfile(os.path.join(directory, name + ext)):
                return True
    return False


def scrubbed_path(original):
    """PATH without the folders that hold a real gh or claude (unless they also hold git, python or a shell)."""
    kept = []
    for directory in original.split(os.pathsep):
        if not directory:
            continue
        if has_exe(directory, SHIMMED) and not has_exe(directory, KEEP_MARKERS):
            continue
        kept.append(directory)
    return kept


def find_bash():
    """A working bash: Git Bash first (the WSL launcher of System32 is not a usable shell here)."""
    for candidate in ("C:/Program Files/Git/bin/bash.exe", "C:/Program Files (x86)/Git/bin/bash.exe"):
        if os.path.isfile(candidate):
            return candidate
    found = shutil.which("bash")
    if found and "system32" not in found.lower().replace("\\", "/"):
        return found
    return None


def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def _remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    func(path)


class Ctx:
    def __init__(self, sid, fixtures, interp, original_path, keep=False):
        self.sid = sid
        self.fixtures = Path(fixtures)
        self.interp = interp                      # D5 command, e.g. "py -3"
        self.keep = keep
        self.tmp = Path(tempfile.mkdtemp(prefix="hts-%s-" % sid))
        self.home = self.tmp / "home"
        self.work = self.tmp / "work"
        self.bin = self.tmp / "bin"
        self.gh_state = self.tmp / "gh-state.json"
        self.assertions = []
        self.live_calls = 0                       # claude invocations made on purpose by a live-* scenario
        self.home.mkdir()
        self.bin.mkdir()
        self._make_shims()
        self.path = os.pathsep.join([str(self.bin)] + scrubbed_path(original_path))

    # ------------------------------------------------------------------ shims and counters

    def _make_shims(self):
        for name in SHIMMED:
            calls = self.bin / ("calls-%s.txt" % name)
            calls.write_bytes(b"")
            sh = self.bin / name
            sh.write_bytes(('#!/bin/sh\necho "$0 $*" >> "%s"\nexit 127\n' % calls.as_posix()).encode("utf-8"))
            sh.chmod(0o755)
            cmd = ("@echo off\r\necho %%0 %%* >> \"%s\"\r\nexit /b 127\r\n" % str(calls)).encode("utf-8")
            (self.bin / (name + ".cmd")).write_bytes(cmd)
            (self.bin / (name + ".bat")).write_bytes(cmd)

    def real_calls(self, name):
        text = (self.bin / ("calls-%s.txt" % name)).read_text(encoding="utf-8", errors="replace")
        return len([line for line in text.splitlines() if line.strip()])

    # ------------------------------------------------------------------ environment and processes

    def env(self, extra=None, fake_gh=True):
        env = dict(os.environ)
        for name in ("CLAUDE_PROJECT_DIR", "CLAUDECODE", "HCORE_GIT", "HCORE_CLAUDE"):
            env.pop(name, None)
        env.update({"HOME": str(self.home), "USERPROFILE": str(self.home), "PATH": self.path,
                    "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "GIT_TERMINAL_PROMPT": "0",
                    "GIT_CONFIG_NOSYSTEM": "1"})
        if fake_gh:
            env.update({"HCORE_TEST_MODE": "1", "HCORE_FAKE_GH_STATE": str(self.gh_state),
                        "HCORE_GH": json.dumps([sys.executable, "-B", str(FAKE_GH)])})
        env.update(extra or {})
        return env

    def run(self, argv, cwd=None, extra_env=None, stdin=None, timeout=300, fake_gh=True):
        return subprocess.run([str(a) for a in argv], cwd=str(cwd or self.work), input=stdin, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout,
                              env=self.env(extra_env, fake_gh))

    def k(self, *args, **kw):
        """The core of this repository (what the SKILL.md files reach through ${CLAUDE_SKILL_DIR}/../_core)."""
        return self.run([sys.executable, "-B", K_PATH] + list(args), **kw)

    def h(self, *args, **kw):
        """The core copy installed in the project (.claude/harness/)."""
        return self.run([sys.executable, "-B", self.work / ".claude" / "harness" / "harness.py"] + list(args), **kw)

    def git(self, *args, cwd=None):
        res = self.run(["git"] + list(args), cwd=cwd, fake_gh=False)
        if res.returncode != 0:
            raise Prep("git %s: %s" % (" ".join(args), res.stderr.strip()))
        return res.stdout

    # ------------------------------------------------------------------ assertions

    def check(self, number, ok, detail=""):
        self.assertions.append({"id": "%s.%d" % (self.sid, number), "ok": bool(ok), "detail": str(detail)[:400]})
        return bool(ok)

    @staticmethod
    def json(res, what="command"):
        """The JSON of a successful command; a failure is an error of the scenario with the real message."""
        if res.returncode != 0:
            raise Prep("%s: exit %d: %s" % (what, res.returncode, (res.stderr or res.stdout).strip()[:300]))
        try:
            return json.loads(res.stdout)
        except ValueError as exc:
            raise Prep("%s: output is not JSON (%s)" % (what, exc))

    def close(self):
        if not self.keep:
            shutil.rmtree(str(self.tmp), onerror=_remove_readonly)

    # ------------------------------------------------------------------ files

    def write(self, rel, text, root=None):
        _write((root or self.work) / rel, text)
        return rel

    def read(self, rel, root=None):
        return (Path(root or self.work) / rel).read_bytes().decode("utf-8")

    def write_transit(self, name, text):
        """What the Write tool does for the files the SKILL.md prescribe: the text, as is, under .harness/runs/."""
        return self.write(".harness/runs/" + name, text)

    def copy_fixture(self, src, dest, renames=None, skip=()):
        """Copies a fixture project under its real names; text files are normalized to LF."""
        src, dest = Path(src), Path(dest)
        renames = renames or {}
        for path in sorted(src.rglob("*")):
            if not path.is_file() or path.name in skip:
                continue
            parts = [renames.get(p, p) for p in path.relative_to(src).parts]
            target = dest.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = path.read_bytes()
            if path.suffix in TEXT_SUFFIXES or path.name == "claude-md.txt":
                data = data.replace(b"\r\n", b"\n")
            target.write_bytes(data)

    def init_git(self, root=None, message="init"):
        root = Path(root or self.work)
        root.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q", "-b", "main", cwd=root)
        for key, value in (("user.name", "Scenario"), ("user.email", "scenario@example.invalid"),
                           ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
            self.git("config", key, value, cwd=root)
        self.git("add", "-A", cwd=root)
        self.git("commit", "-q", "-m", message, cwd=root)

    def tree(self, root=None, skip=(".git", ".harness")):
        root = Path(root or self.work)
        out = {}
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if path.is_file() and not any(rel == s or rel.startswith(s + "/") for s in skip):
                out[rel] = path.read_bytes()
        return out

    def journal(self, run, root=None):
        text = (Path(root or self.work) / run).read_bytes().decode("utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def lines_of(text):
    return [line.rstrip("\r") for line in text.splitlines()]
