# install-unlink: --unlink / -Unlink removes only the links the installer made to this repository (5 assertions).
#
# Like install-skills, the installer runs unchanged with a fake HOME; the real ~/.claude is never touched.
# The installer is run once to create its links, then foreign things are put next to them: a link to
# another folder under a skill name, a link with another name, and a real folder.

import os
import shutil
import subprocess

from common import ROOT, Skip, find_bash

ID = "install-unlink"
NUMBERS = (1, 2, 3, 4, 5)
PRESCRIBES = [
    ("install_skills.sh --unlink", "README.md"),
    ("install_skills.ps1 -Unlink", "README.md"),
]
IS_WINDOWS = os.name == "nt"


def names():
    return sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())


def make_link(link, target):
    """A directory link: a junction on Windows (no privilege needed), a symlink elsewhere."""
    if IS_WINDOWS:
        res = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError("mklink failed: %s" % (res.stdout + res.stderr).strip())
    else:
        os.symlink(str(target), str(link))


def is_link(path):
    return os.path.islink(str(path)) or (IS_WINDOWS and os.path.isdir(str(path)) and bool(
        os.stat(str(path), follow_symlinks=False).st_file_attributes & 0x400))


def installer(flag):
    if not IS_WINDOWS:
        return [find_bash(), str(ROOT / "install_skills.sh"), "--skip-tools"] + (["--unlink"] if flag else [])
    pwsh = shutil.which("pwsh")
    return [pwsh, "-NoProfile", "-File", str(ROOT / "install_skills.ps1"), "-SkipTools"] + (["-Unlink"] if flag else [])


def run(ctx):
    launcher = os.environ.get("HTS_LAUNCHER", "")
    if IS_WINDOWS and launcher != "pwsh":
        raise Skip("Git Bash has no native symlinks (Q7); the Windows installer is covered by the PowerShell launcher")
    if not IS_WINDOWS and not find_bash():
        raise Skip("no bash found")
    if IS_WINDOWS and not shutil.which("pwsh"):
        raise Skip("no pwsh found")
    env = {"MSYS": "winsymlinks:nativestrict"} if not IS_WINDOWS else None
    target = ctx.home / ".claude" / "skills"
    wanted = names()

    first = ctx.run(installer(False), cwd=ROOT, extra_env=env, fake_gh=False)
    if first.returncode != 0:
        ctx.check(1, False, "install failed: exit=%d %s" % (first.returncode, (first.stdout + first.stderr)[-200:]))
        return

    # Foreign items: a link under a skill name that points elsewhere, an unrelated link, a real folder.
    elsewhere = ctx.tmp / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_bytes(b"other")
    divergent = target / wanted[0]
    if os.path.isdir(str(divergent)):
        os.rmdir(str(divergent)) if IS_WINDOWS else divergent.unlink()
    make_link(divergent, elsewhere)
    foreign = target / "zz-foreign"
    make_link(foreign, elsewhere)
    mine = target / "zz-mine"
    mine.mkdir()
    (mine / "keep.txt").write_bytes(b"mine")

    res = ctx.run(installer(True), cwd=ROOT, extra_env=env, fake_gh=False)
    remaining = sorted(p.name for p in target.iterdir())
    expected = sorted([wanted[0], "zz-foreign", "zz-mine"])
    ctx.check(1, res.returncode == 0 and remaining == expected,
              "exit=%d remaining=%s expected=%s" % (res.returncode, remaining, expected))
    ctx.check(2, os.path.isfile(str(divergent / "keep.txt")) and os.path.isfile(str(foreign / "keep.txt")),
              "targets of the foreign links are intact")
    ctx.check(3, (mine / "keep.txt").read_bytes() == b"mine" and not is_link(mine), "real folder untouched")
    ctx.check(4, all((ROOT / "skills" / n).is_dir() for n in wanted) and (ROOT / "skills" / "_core" / "harness.py").is_file(),
              "the repository itself is intact")
    # A second pass removes nothing and still succeeds.
    again = ctx.run(installer(True), cwd=ROOT, extra_env=env, fake_gh=False)
    ctx.check(5, again.returncode == 0 and "0 link(s) removed" in again.stdout and
              sorted(p.name for p in target.iterdir()) == expected,
              "second pass exit=%d out=%s" % (again.returncode, again.stdout.strip()[-120:]))
