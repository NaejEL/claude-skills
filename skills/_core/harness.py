#!/usr/bin/env python3
# harness - single CLI of the deterministic core of the claude-skills skills.
#
# Usage: <PY> harness.py <subcommand> ...   (see --help of each group)
# Output: one JSON object on stdout; stop message on stderr.
# Codes: 0 success or decision returned, 1 explicit stop, 2 usage error or invalid bound.
#
# Standard library only, Python >= 3.9.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# D1: no bytecode, even when called without -B (versioned copy under .claude/harness/).
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from hcore import CORE_VERSION  # noqa: E402
from hcore import (blocks, counters, factory, fusion, ghflow, interp, journal,  # noqa: E402
                   models, registry, runs, shippr)
from hcore import proc  # noqa: E402
from hcore.proc import Runner  # noqa: E402


class Usage(Exception):
    """Usage or bound error: exit 2."""


def emit(obj: Any) -> None:
    active = proc.overrides(warn=False)
    if active and isinstance(obj, dict):
        obj = dict(obj, hcore_test_mode={"overrides": active})
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def read_output(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if value == "-":
        return sys.stdin.buffer.read().decode("utf-8", "replace")
    return Path(value).read_text(encoding="utf-8", errors="replace")


def _count_arg(name: str, value: Optional[str], warnings: List[str]) -> Optional[int]:
    """Integer >= 0, or None (absent or invalid: reported, never blocking)."""
    if value is None or value.strip().lower() in ("", "null", "none"):
        return None
    try:
        n = int(value.strip())
    except ValueError:
        n = -1
    if n < 0:
        warnings.append("%s invalid (%r): logged as null" % (name, value))
        return None
    return n


def _run_path(value: str) -> Path:
    path = Path(value)
    if not runs.state_path(path).exists():
        raise Usage("unknown run: %s" % value)
    return path


def _measure(state: Dict[str, Any], args: argparse.Namespace, slot: str) -> Dict[str, Any]:
    """Journal measurements, taken BEFORE any write. A measurement defect
    (duration missing without 'begin', invalid value) never blocks the skill:
    the value is logged as null and reported in 'journal_warnings'."""
    warnings: List[str] = []
    tokens = _count_arg("--tokens", args.tokens, warnings)
    given = _count_arg("--duration-ms", args.duration_ms, warnings)
    try:
        duration: Optional[int] = runs.duration_ms(state, slot, given)
    except ValueError as exc:
        warnings.append("%s: logged as null" % exc)
        duration = None
    return {"duration_ms": duration, "tokens": tokens, "warnings": warnings}


def _log(run: Path, args: argparse.Namespace, agent: str, measure: Dict[str, Any],
         fields: Dict[str, Any], decision: Dict[str, Any], **extra: Any) -> None:
    record = journal.make_record(
        agent=agent, model=args.model, duration_ms=measure["duration_ms"],
        iteration=fields["iteration"], verdict=fields["verdict"],
        produced=fields.get("produced", 0), validated=fields.get("validated", 0),
        rejected=fields.get("rejected", 0), tokens=measure["tokens"], **extra)
    record, fallbacks = journal.sanitize(record)
    journal.append(run, record)
    warnings = measure["warnings"] + fallbacks
    if warnings:
        decision["journal_warnings"] = warnings


# ------------------------------------------------------------------- generic

def cmd_version(args: argparse.Namespace) -> int:
    emit({"core_version": CORE_VERSION})
    return 0


def cmd_interp(args: argparse.Namespace) -> int:
    found = interp.detect(timeout=args.timeout)
    emit(found or {"command": None})
    return 0 if found else 1


def cmd_journal_validate(args: argparse.Namespace) -> int:
    errors = journal.validate_file(Path(args.path))
    name_ok = bool(journal.NAME_RE.match(Path(args.path).name))
    emit({"path": args.path, "valid": not errors, "errors": errors, "name_conforms": name_ok})
    return 0 if not errors else 1


def cmd_begin(args: argparse.Namespace) -> int:
    run = _run_path(args.run)
    state = runs.load_state(run)
    runs.mark_begin(state, args.slot)
    runs.save_state(run, state)
    emit({"slot": args.slot})
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    roles = args.roles.split(",") if args.roles else None
    try:
        emit(models.resolve(Path(args.file), args.models, roles))
    except models.ModelsError as exc:
        raise Usage(str(exc))
    return 0


def cmd_block(args: argparse.Namespace) -> int:
    path = Path(args.file)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if args.action == "get":
        emit({"content": blocks.get_block(text, args.name, args.style)})
        return 0
    if args.action == "upsert":
        new = blocks.upsert_block(text, args.name, read_output(args.content) or "", args.style)
    else:
        new = blocks.remove_block(text, args.name, args.style)
    changed = new != text
    if changed:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new)
    emit({"file": args.file, "changed": changed})
    return 0


# ---------------------------------------------------------- software-factory

def cmd_sf_apply(args: argparse.Namespace) -> int:
    stacks = [s for s in (args.stacks or "").split(",") if s.strip()]
    emit(fusion.apply(Path(args.root), [s.strip() for s in stacks]))
    return 0


def cmd_sf_install(args: argparse.Namespace) -> int:
    content = read_output(args.source)
    dest = Path(args.root) / args.dest
    emit({args.dest: fusion.install_file(dest, content or "")})
    return 0


def cmd_sf_copy_core(args: argparse.Namespace) -> int:
    emit(dict(fusion.copy_core(HERE, Path(args.root)), core_version=CORE_VERSION))
    return 0


# --------------------------------------------------------------- factory-run

def cmd_fr_start(args: argparse.Namespace) -> int:
    root = Path(args.root)
    arguments = ""
    if args.arguments_file:
        arguments = Path(args.arguments_file).read_text(encoding="utf-8-sig", errors="replace")
    choice = factory.entry(arguments, root)
    run = runs.create(root, "factory-run", factory.new_state())
    emit(dict(choice, run=runs.display(run)))
    return 0


def cmd_fr_record(args: argparse.Namespace) -> int:
    run = _run_path(args.run)
    state = runs.load_state(run)
    measure = _measure(state, args, args.agent)
    decision, fields = factory.record(state, args.agent, read_output(args.output), args.dead)
    _log(run, args, args.agent, measure, fields, decision)
    runs.save_state(run, state)
    emit(decision)
    return 0


# ------------------------------------------------------------------- ship-pr

def _ship_ctx(args: argparse.Namespace):
    run = _run_path(args.run)
    state = runs.load_state(run)
    return run, state, Runner(cwd=state["root"]), registry.Registry(runs.registry_path(run))


def cmd_sp_start(args: argparse.Namespace) -> int:
    try:
        rounds = counters.parse_rounds(args.rounds)
        themes = counters.parse_themes(args.themes)
    except counters.BoundsError as exc:
        raise Usage(str(exc))
    root = Path(args.root).resolve()
    run_cmd = Runner(cwd=str(root))
    info = ghflow.preflight_checks(run_cmd, args.target)
    excluded = ghflow.ensure_exclude(run_cmd, root)
    info.update(ghflow.worktree_and_repo(run_cmd))
    state = shippr.new_state(args.target, rounds, themes)
    state.update(branch=info["branch"], owner_repo=info["owner_repo"])
    run = runs.create(root, "ship-pr", state)
    emit(dict(info, run=runs.display(run), registry=runs.display(runs.registry_path(run)),
              rounds=rounds, themes=themes, round=1, exclude_added=excluded))
    return 0


def cmd_sp_sync(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    emit(ghflow.sync_upstream(run_cmd))
    return 0


def cmd_sp_pr(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    if (args.title is None) != (args.body_file is None):
        raise Usage("--title and --body-file go together")
    body = read_output(args.body_file) if args.body_file else None
    result = ghflow.find_or_create_pr(run_cmd, state, args.title, body)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_sp_pr_state(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    emit(ghflow.pr_state(run_cmd, state["pr"]))
    return 0


def cmd_sp_diff(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    sys.stdout.write(ghflow.collect_diff(run_cmd, state))
    return 0


def cmd_sp_reviewer(args: argparse.Namespace) -> int:
    run, state, _, reg = _ship_ctx(args)
    measure = _measure(state, args, "reviewer:" + args.theme)
    decision, fields = shippr.record_reviewer(state, reg, args.theme, read_output(args.output), args.dead)
    _log(run, args, shippr.REVIEWER, measure, fields, decision, theme=args.theme)
    runs.save_state(run, state)
    emit(decision)
    return 0


def cmd_sp_validator(args: argparse.Namespace) -> int:
    run, state, _, reg = _ship_ctx(args)
    measure = _measure(state, args, "validator:" + args.finding)
    decision, fields = shippr.record_validator(state, reg, args.finding, read_output(args.output), args.dead)
    _log(run, args, shippr.VALIDATOR, measure, fields, decision, finding=args.finding)
    runs.save_state(run, state)
    emit(decision)
    return 0


def cmd_sp_comment(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    result = ghflow.post_comment(run_cmd, state, args.finding)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_sp_commit(args: argparse.Namespace) -> int:
    run, state, run_cmd, reg = _ship_ctx(args)
    not_fixed: Dict[str, str] = {}
    for item in args.not_fixed or []:
        fid, sep, reason = item.partition(":")
        if not sep or not reason.strip():
            raise Usage("--not-fixed expects ID:reason, got: %r" % item)
        not_fixed[fid.strip()] = reason.strip()
    if args.fixed and not (args.summary or "").strip():
        raise Usage("--summary is required when a fix is committed")
    result = ghflow.commit_round(run_cmd, state, reg, args.summary or "", args.fixed or [], not_fixed)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_sp_threads(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    result = ghflow.handle_threads(run_cmd, state)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_sp_end_round(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    head = run_cmd(["git", "rev-parse", "HEAD"])
    result = shippr.end_round(state, head.out.strip() if head.ok else None)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_sp_merge(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    result = ghflow.merge(run_cmd, state, args.check)
    runs.save_state(run, state)
    emit(result)
    return 0


# -------------------------------------------------------------------- parser

def _agent_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--run", required=True, help="run journal (.claude/runs/<skill>-<timestamp>.jsonl)")
    p.add_argument("--model", required=True, help="agent model (inherit if not passed)")
    p.add_argument("--duration-ms", default=None, help="duration from the usage block; otherwise 'begin' (absent = null)")
    p.add_argument("--tokens", default=None, help="tokens from the usage block, absent = null")
    p.add_argument("--dead", action="store_true", help="the agent died (API error, disconnection)")
    p.add_argument("--output", default=None, help="file holding the agent output, '-' = stdin")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness.py", description="claude-skills deterministic core")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version").set_defaults(func=cmd_version)
    p = sub.add_parser("interp", help="interpreter detection (D5)")
    p.add_argument("--timeout", type=float, default=interp.TIMEOUT)
    p.set_defaults(func=cmd_interp)
    p = sub.add_parser("journal", help="cycle journal")
    jsub = p.add_subparsers(dest="jcmd", required=True)
    q = jsub.add_parser("validate", help="validates the schema of a journal")
    q.add_argument("path")
    q.set_defaults(func=cmd_journal_validate)
    p = sub.add_parser("begin", help="timestamp before an agent call")
    p.add_argument("--run", required=True)
    p.add_argument("--slot", required=True, help="agent, reviewer:<theme> or validator:<id>")
    p.set_defaults(func=cmd_begin)
    p = sub.add_parser("models", help="reads models.json and --models (D6, not wired)")
    p.add_argument("--file", default=".claude/models.json")
    p.add_argument("--models", default=None)
    p.add_argument("--roles", default=None)
    p.set_defaults(func=cmd_models)
    p = sub.add_parser("block", help="delimited blocks (D9, unused)")
    p.add_argument("action", choices=("get", "upsert", "remove"))
    p.add_argument("--file", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--style", choices=blocks.STYLES, default="md")
    p.add_argument("--content", default=None, help="content file, '-' = stdin")
    p.set_defaults(func=cmd_block)

    p = sub.add_parser("sf", help="software-factory")
    ssub = p.add_subparsers(dest="sfcmd", required=True)
    q = ssub.add_parser("apply", help="merges settings.json, tasks.json, .gitignore (SF-01 to SF-04)")
    q.add_argument("--root", default=".")
    q.add_argument("--stacks", default="", help="node,dotnet,python,cpp,rust (comma-separated)")
    q.set_defaults(func=cmd_sf_apply)
    q = ssub.add_parser("install", help="writes a generated file without overwriting (SF-04)")
    q.add_argument("--root", default=".")
    q.add_argument("--dest", required=True)
    q.add_argument("--source", required=True, help="content file, '-' = stdin")
    q.set_defaults(func=cmd_sf_install)
    q = ssub.add_parser("copy-core", help="copies the core under .claude/harness/ (D1)")
    q.add_argument("--root", default=".")
    q.set_defaults(func=cmd_sf_copy_core)

    p = sub.add_parser("factory-run", help="factory-run orchestration (FR-01 to FR-04)")
    fsub = p.add_subparsers(dest="frcmd", required=True)
    q = fsub.add_parser("start")
    q.add_argument("--root", default=".")
    q.add_argument("--arguments-file", default=None,
                   help="file holding $ARGUMENTS, written by the Write tool (never through the shell)")
    q.set_defaults(func=cmd_fr_start)
    q = fsub.add_parser("record")
    _agent_args(q)
    q.add_argument("--agent", required=True, choices=factory.AGENTS)
    q.set_defaults(func=cmd_fr_record)

    p = sub.add_parser("ship-pr", help="ship-pr orchestration (SP-01 to SP-19)")
    psub = p.add_subparsers(dest="spcmd", required=True)
    q = psub.add_parser("start")
    q.add_argument("--root", default=".")
    q.add_argument("--target", required=True)
    q.add_argument("--rounds", default=None)
    q.add_argument("--themes", default=None)
    q.set_defaults(func=cmd_sp_start)
    for name, func in (("sync", cmd_sp_sync), ("pr-state", cmd_sp_pr_state), ("diff", cmd_sp_diff),
                       ("threads", cmd_sp_threads), ("end-round", cmd_sp_end_round)):
        q = psub.add_parser(name)
        q.add_argument("--run", required=True)
        q.set_defaults(func=func)
    q = psub.add_parser("pr")
    q.add_argument("--run", required=True)
    q.add_argument("--title", default=None)
    q.add_argument("--body-file", default=None, help="body file, '-' = stdin")
    q.set_defaults(func=cmd_sp_pr)
    q = psub.add_parser("reviewer")
    _agent_args(q)
    q.add_argument("--theme", required=True)
    q.set_defaults(func=cmd_sp_reviewer)
    q = psub.add_parser("validator")
    _agent_args(q)
    q.add_argument("--finding", required=True)
    q.set_defaults(func=cmd_sp_validator)
    q = psub.add_parser("comment")
    q.add_argument("--run", required=True)
    q.add_argument("--finding", required=True)
    q.set_defaults(func=cmd_sp_comment)
    q = psub.add_parser("commit")
    q.add_argument("--run", required=True)
    q.add_argument("--summary", default="")
    q.add_argument("--fixed", nargs="*", default=[])
    q.add_argument("--not-fixed", action="append", default=[], help="ID:reason, repeatable")
    q.set_defaults(func=cmd_sp_commit)
    q = psub.add_parser("merge")
    q.add_argument("--run", required=True)
    q.add_argument("--check", action="store_true", help="checks and summarizes without merging")
    q.set_defaults(func=cmd_sp_merge)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ghflow.Stop as exc:
        sys.stderr.write("STOP: %s\n" % exc)
        return 1
    except (Usage, ValueError, factory.RunOver, shippr.LoopError, fusion.FusionError,
            blocks.BlockError, FileNotFoundError) as exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
