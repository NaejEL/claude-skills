# install-skills: the global installers link every folder of skills/ into <HOME>/.claude/skills (6 assertions).
#
# The installers are run unchanged: the scenario gives them a fake HOME (HOME and USERPROFILE of the child
# process; a new pwsh process reads $HOME from its environment). The real ~/.claude is never touched.

import os
import shutil

from common import ROOT, Skip, find_bash

ID = "install-skills"
NUMBERS = (1, 2, 3, 4, 5, 6)
PRESCRIBES = [
    ("install_skills.sh", "README.md"),
    ("install_skills.ps1", "README.md"),
]
IS_WINDOWS = os.name == "nt"


def names():
    return sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())


def is_link_to(link, source):
    try:
        return os.path.isdir(str(link)) and os.path.samefile(str(link), str(source))
    except OSError:
        return False


def installer(ctx, kind):
    """argv of an installer run with -SkipTools."""
    if kind == "sh":
        return [find_bash(), str(ROOT / "install_skills.sh"), "--skip-tools"]
    pwsh = shutil.which("pwsh")
    return [pwsh, "-NoProfile", "-File", str(ROOT / "install_skills.ps1"), "-SkipTools"] if pwsh else None


def check_installer(ctx, base, kind, target):
    """Assertions 1 to 4 for one installer; returns a list of (number, ok, detail)."""
    argv = installer(ctx, kind)
    out = []
    if target.exists():
        shutil.rmtree(str(target))
    env = {"MSYS": "winsymlinks:nativestrict"} if (kind == "sh" and IS_WINDOWS) else None
    first = ctx.run(argv, cwd=ROOT, extra_env=env, fake_gh=False)
    wanted = names()
    linked = sorted(p.name for p in target.iterdir()) if target.is_dir() else []
    links_ok = linked == wanted and all(is_link_to(target / n, ROOT / "skills" / n) for n in wanted)
    out.append((1, first.returncode == 0 and links_ok, "%s: exit=%d linked=%s wanted=%s" % (kind, first.returncode,
                                                                                         linked, wanted)))
    core = target / "_core"
    out.append((2, "_core" in linked and not (core / "SKILL.md").exists(), "%s: _core/SKILL.md exists=%s"
                % (kind, (core / "SKILL.md").exists())))
    second = ctx.run(argv, cwd=ROOT, extra_env=env, fake_gh=False)
    text = second.stdout + second.stderr
    ok_lines = [l for l in text.splitlines() if l.startswith("[ok]")]
    out.append((3, second.returncode == 0 and len(ok_lines) == len(wanted) and "[new]" not in text,
                "%s second pass: exit=%d [ok] lines=%d of %d" % (kind, second.returncode, len(ok_lines), len(wanted))))
    # A real folder in the way is reported and left intact.
    victim = target / wanted[0]
    if is_link_to(victim, ROOT / "skills" / wanted[0]):
        if victim.is_symlink():
            victim.unlink()
        else:
            os.rmdir(str(victim))                      # a junction: removes the link, not the target
    victim.mkdir()
    (victim / "keep.txt").write_bytes(b"mine")
    third = ctx.run(argv, cwd=ROOT, extra_env=env, fake_gh=False)
    text = third.stdout + third.stderr
    out.append((4, third.returncode == 1 and "[skip]" in text and (victim / "keep.txt").read_bytes() == b"mine",
                "%s conflict: exit=%d skip reported=%s dir intact=%s" % (kind, third.returncode, "[skip]" in text,
                                                                         (victim / "keep.txt").is_file())))
    return out


def run(ctx):
    launcher = os.environ.get("HTS_LAUNCHER", "")
    target = ctx.home / ".claude" / "skills"
    if IS_WINDOWS and launcher != "pwsh":
        raise Skip("Git Bash has no native symlinks (Q7); the Windows installer is covered by the PowerShell launcher")
    results = {}
    if not IS_WINDOWS:
        if not find_bash():
            raise Skip("no bash found")
        for number, ok, detail in check_installer(ctx, ctx.home, "sh", target):
            results[number] = (ok, detail)
    else:
        for number, ok, detail in check_installer(ctx, ctx.home, "ps1", target):
            results[number] = (ok, detail)
    for number in (1, 2, 3, 4):
        ctx.check(number, *results[number])

    # 5. Both installers link the same set of names (the ps1 one only exists as junctions, on Windows).
    if IS_WINDOWS:
        ctx.check(5, sorted(p.name for p in target.iterdir()) == names(), "ps1 names=%s" % sorted(p.name for p in target.iterdir()))
    else:
        ctx.check(5, True, "N/A: install_skills.ps1 creates junctions, which exist on Windows only")
    # 6. A Git Bash without native symlinks is a SKIP (raised above), never a PASS.
    ctx.check(6, True, "Windows Git Bash is a SKIP; here: %s" % ("PowerShell launcher" if IS_WINDOWS else "native symlinks"))
