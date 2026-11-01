# Runner of the end-to-end harness scenarios (stdlib only, Python >= 3.9).
#
#   <PY> -B -I -S ci/scenarios/run.py [--list [--verbose]] [--scenario ID]... [--live] [--keep]
#                                     [--fixtures DIR] [--report FILE]
#
# Exit codes: 0 = every scenario PASS or SKIP (with a reason), 1 = a FAIL or --live without claude,
# 2 = unknown option or scenario. One line per scenario: PASS|FAIL|SKIP <id> <duration> ms [reason].

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:                      # -I does not put the script folder on sys.path
    sys.path.insert(0, HERE)

import common  # noqa: E402

MODULES = ("sc_install_fresh", "sc_install_skills", "sc_install_unlink", "sc_plugin",
           "sc_plugin_validate", "sc_upgrade_legacy", "sc_factory_auto", "sc_stop_iteration3",
           "sc_shippr_automerge", "sc_hook_diff", "sc_models_absent", "sc_models_legacy", "live")


def load_registry():
    """Ordered list of (id, module, live)."""
    registry = []
    for name in MODULES:
        module = importlib.import_module(name)
        if name == "live":
            for sid in module.IDS:
                registry.append((sid, module, True))
        else:
            registry.append((module.ID, module, False))
    return registry


def ascii_line(text):
    return text.encode("ascii", "replace").decode("ascii")


def detect_interpreter():
    """Rule D5 through the core itself: the command that answers with Python >= 3.9."""
    res = subprocess.run([sys.executable, "-B", str(common.K_PATH), "interp"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=120)
    if res.returncode != 0:
        return None, None
    data = json.loads(res.stdout)
    return " ".join(data["command"]), data.get("version")


def core_version():
    res = subprocess.run([sys.executable, "-B", str(common.K_PATH), "version"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=120)
    try:
        return json.loads(res.stdout)["core_version"]
    except (ValueError, KeyError):
        return None


def run_one(sid, module, args, interp, original_path):
    """Runs a scenario; returns the report entry."""
    ctx = common.Ctx(sid, args.fixtures, interp, original_path, keep=args.keep)
    started = time.time()
    status, reason = "PASS", ""
    try:
        module.run(ctx)
    except common.Skip as exc:
        status, reason = "SKIP", str(exc)
        for number in getattr(module, "NUMBERS", ()):     # the assertions that were not made are listed, not passed
            ctx.assertions.append({"id": "%s.%d" % (sid, number), "ok": None, "detail": "skipped: %s" % reason})
    except Exception as exc:  # a scenario failure is a result, not a crash of the runner
        status = "FAIL"
        ctx.assertions.append({"id": "%s.error" % sid, "ok": False,
                               "detail": "%s: %s" % (type(exc).__name__, str(exc)[:300])})
        if os.environ.get("HTS_TRACE"):
            traceback.print_exc()
    gh_calls, claude_calls = ctx.real_calls("gh"), ctx.real_calls("claude")
    if getattr(module, "LIVE", False):
        claude_calls += ctx.live_calls            # intended: a live scenario runs the real claude
    elif gh_calls or claude_calls:
        ctx.assertions.append({"id": "%s.real-calls" % sid, "ok": False,
                               "detail": "real gh calls=%d, real claude calls=%d" % (gh_calls, claude_calls)})
    if status == "PASS" and (not ctx.assertions or not all(a["ok"] for a in ctx.assertions)):
        status = "FAIL"
        if not ctx.assertions:
            ctx.assertions.append({"id": "%s.none" % sid, "ok": False, "detail": "no assertion was made"})
    entry = {"id": sid, "status": status, "duration_ms": int((time.time() - started) * 1000),
             "assertions": ctx.assertions, "real_gh_calls": gh_calls, "real_claude_calls": claude_calls}
    if reason:
        entry["reason"] = reason
    where = str(ctx.tmp)
    ctx.close()
    return entry, where


def main(argv=None):
    parser = argparse.ArgumentParser(prog="test-harness", description="end-to-end scenarios of the harness")
    parser.add_argument("--list", action="store_true", help="list the scenarios")
    parser.add_argument("--verbose", action="store_true", help="with --list: core subcommands and prescribing files")
    parser.add_argument("--scenario", action="append", default=[], help="run only this scenario (repeatable)")
    parser.add_argument("--live", action="store_true", help="also run the live-* scenarios (real claude, costs tokens)")
    parser.add_argument("--keep", action="store_true", help="keep the temporary folders and print their path")
    parser.add_argument("--fixtures", default=str(common.ROOT / "ci" / "fixtures"), help="fixtures folder")
    parser.add_argument("--report", default=None, help="JSON report file")
    args = parser.parse_args(argv)
    args.fixtures = Path(args.fixtures).resolve()

    registry = load_registry()
    known = [sid for sid, _, _ in registry]
    unknown = [s for s in args.scenario if s not in known]
    if unknown:
        sys.stderr.write("unknown scenario: %s (known: %s)\n" % (", ".join(unknown), ", ".join(known)))
        return 2

    if args.list:
        for sid, module, _ in registry:
            if args.verbose:
                rows = module.PRESCRIBES[sid] if isinstance(module.PRESCRIBES, dict) else module.PRESCRIBES
                for sub, rel in rows:
                    print("%s\t%s\t%s" % (sid, sub, rel))
            else:
                print(sid)
        return 0

    original_path = os.environ.get("PATH", "")
    if args.live and not shutil.which("claude"):
        sys.stderr.write("claude not found in PATH: --live needs the claude CLI\n")
        return 1

    interp, version = detect_interpreter()
    if not interp:
        sys.stderr.write("no Python >= 3.9 interpreter found (rule D5)\n")
        return 1

    selected = [(sid, module, live) for sid, module, live in registry if not args.scenario or sid in args.scenario]
    report_dir = Path(tempfile.mkdtemp(prefix="hts-report-"))
    entries, kept = [], []
    for sid, module, live in selected:
        if live and not args.live:
            entry = {"id": sid, "status": "SKIP", "duration_ms": 0, "assertions": [], "real_gh_calls": 0,
                     "real_claude_calls": 0, "reason": "live not requested"}
        else:
            entry, where = run_one(sid, module, args, interp, original_path)
            kept.append(where)
        entries.append(entry)
        line = "%s %s %d ms" % (entry["status"], sid, entry["duration_ms"])
        if entry.get("reason"):
            line += " " + entry["reason"]
        print(ascii_line(line))
        sys.stdout.flush()
        if entry["status"] == "FAIL":
            for a in entry["assertions"]:
                if not a["ok"]:
                    print(ascii_line("  failed %s: %s" % (a["id"], a["detail"])))

    report = {"scenarios": entries, "core_version": core_version(), "interpreter": interp,
              "interpreter_version": version, "launcher": os.environ.get("HTS_LAUNCHER", "")}
    report_path = Path(args.report) if args.report else report_dir / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    if args.report:
        shutil.rmtree(str(report_dir), ignore_errors=True)
    print(ascii_line("report: %s" % report_path))
    if args.keep:
        for where in kept:
            print(ascii_line("kept: %s" % where))
    return 1 if any(e["status"] == "FAIL" for e in entries) else 0


if __name__ == "__main__":
    sys.exit(main())
