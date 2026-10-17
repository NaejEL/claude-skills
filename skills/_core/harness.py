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
from typing import Any, Dict, List, Optional, Tuple

# D1: no bytecode, even when called without -B (versioned copy under .claude/harness/).
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from hcore import CORE_VERSION  # noqa: E402
from hcore import (blocks, counters, factory, fusion, gates, ghflow, interp, journal,  # noqa: E402
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


TRANSIT_MISSING = ("transit file %s was already consumed or never written: "
                   "rewrite it with Write before this call")


def _input_path(value: str) -> Path:
    """Path of an input file. A missing file under .claude/runs/ is a transit
    file already consumed (or never written): explicit usage error."""
    path = Path(value)
    if not path.is_file():
        parts = path.resolve().parts
        if any(parts[i:i + 2] == (".claude", "runs") for i in range(len(parts) - 1)):
            raise Usage(TRANSIT_MISSING % value)
    return path


def read_output(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if value == "-":
        return sys.stdin.buffer.read().decode("utf-8", "replace")
    return _input_path(value).read_text(encoding="utf-8", errors="replace")


def read_file(value: str) -> str:
    """Text written by the Write tool (never stdin, never the shell)."""
    return _input_path(value).read_text(encoding="utf-8-sig", errors="replace")


def _one_line(option: str, text: str) -> str:
    text = text.strip()
    if not text or "\n" in text or "\r" in text:
        raise Usage("%s expects a single non-empty line" % option)
    return text


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


def _model(args: argparse.Namespace, state: Dict[str, Any], role: str) -> str:
    """Model logged for an agent: --model if given, otherwise the model
    resolved for its role at start (MD-07), inherit for an older run."""
    if args.model is not None:
        return args.model
    return state.get("models", {}).get(role, "inherit")


def _log(run: Path, args: argparse.Namespace, agent: str, measure: Dict[str, Any],
         fields: Dict[str, Any], decision: Dict[str, Any], model: str, **extra: Any) -> None:
    record = journal.make_record(
        agent=agent, model=model, duration_ms=measure["duration_ms"],
        iteration=fields["iteration"], verdict=fields["verdict"],
        produced=fields.get("produced", 0), validated=fields.get("validated", 0),
        rejected=fields.get("rejected", 0), tokens=measure["tokens"], **extra)
    record, fallbacks = journal.sanitize(record)
    journal.append(run, record)
    warnings = measure["warnings"] + fallbacks
    if warnings:
        decision["journal_warnings"] = warnings


def _existing_run(args: argparse.Namespace) -> Optional[Path]:
    """Run of the command, if it exists: the command then holds its lock for
    the whole read -> modify -> write cycle (concurrent calls serialized)."""
    value = getattr(args, "run", None)
    if not value:
        return None
    try:
        return Path(value) if runs.state_path(Path(value)).exists() else None
    except ValueError:
        return None


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


def cmd_journal_amend(args: argparse.Namespace) -> int:
    """Deferred completion of the last entry of a slot (measurements known
    after the call). A measurement defect is reported, never blocking."""
    run = _run_path(args.run)
    if args.duration_ms is None and args.tokens is None:
        raise Usage("journal amend expects --duration-ms and/or --tokens")
    warnings: List[str] = []
    duration = _count_arg("--duration-ms", args.duration_ms, warnings)
    tokens = _count_arg("--tokens", args.tokens, warnings)
    records = journal.read(run)
    amended, more = journal.amend(records, args.slot, duration, tokens)
    if amended:
        runs.write_atomic(run, journal.dumps(records))
    result: Dict[str, Any] = {"slot": args.slot, "amended": amended}
    if warnings + more:
        result["journal_warnings"] = warnings + more
    emit(result)
    return 0


def cmd_begin(args: argparse.Namespace) -> int:
    run = _run_path(args.run)
    state = runs.load_state(run)
    runs.mark_begin(state, args.slot)
    runs.save_state(run, state)
    emit({"slot": args.slot})
    return 0


def cmd_models_resolve(args: argparse.Namespace) -> int:
    try:
        emit(models.resolve_root(Path(args.root), models.roles_of(args.roles), args.models, args.aliases))
    except models.ModelsError as exc:
        raise Usage(str(exc))
    return 0


def cmd_models_write(args: argparse.Namespace) -> int:
    if args.preset is None and args.set is None:
        raise Usage("models write expects --preset and/or --set")
    try:
        emit(models.write_preset(Path(args.root), args.preset, args.set))
    except models.ModelsError as exc:
        raise Usage(str(exc))
    return 0


# --------------------------------------------------------------------- gates

def _gate_run(args: argparse.Namespace, gate: gates.Gate) -> Path:
    """Run of a gate: --run, or a new run of the gate's skill (JR-01)."""
    if args.run:
        run = _run_path(args.run)
        skill = runs.load_state(run).get("skill")
        if skill != gate.skill:
            raise Usage("gate %s belongs to %s, the run is a %s run" % (gate.id, gate.skill, skill))
        return run
    if args.gcmd == "answer":
        raise Usage("gate answer expects --run (the run returned by 'gate decide')")
    return runs.create(Path(args.root), gate.skill, {"gate_only": True})


def cmd_gate_decide(args: argparse.Namespace) -> int:
    gate = gates.get(args.id)
    run = _gate_run(args, gate)
    root = Path(runs.load_state(run)["root"])
    event = gates.decide(gate.id, gates.read_policy(root))
    journal.append(run, event)
    if event["decision"] == gates.STOP:
        raise gates.GateStop(gates.stop_message(gate, "decision default without a default to apply"))
    emit(dict(event, options=list(gate.options), dialogue=gate.dialogue, run=runs.display(run)))
    return 0


def cmd_gate_answer(args: argparse.Namespace) -> int:
    gate = gates.get(args.id)
    run = _gate_run(args, gate)
    root = Path(runs.load_state(run)["root"])
    try:
        given = [x for x in (args.answer, args.answer_file) if x is not None]
        if int(args.headless) + int(args.default) + len(given) != 1:
            raise Usage("gate answer expects exactly one of --answer, --answer-file, --headless, --default")
        text = read_file(args.answer_file) if args.answer_file is not None else args.answer
    finally:
        _remove_transit(root, args.answer_file)
    source = "headless" if args.headless else "default" if args.default else "user"
    event = gates.answer(gate.id, gates.last_decision(journal.read(run), gate.id), source, text)
    journal.append(run, event)
    apply = gates.applied(gate.id, event)
    if apply == gates.STOP:
        raise gates.GateStop(gates.stop_message(gate, "no interaction possible (headless fallback: stop)"))
    emit({"id": gate.id, "answer": event["answer"], "source": source, "apply": apply})
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


def _remove_transit(root: Path, source: Optional[str]) -> None:
    """The transit file written by Write under <root>/.claude/runs/ is removed
    once consumed, the command succeeded or not: nothing is left if the skill
    stops, and a stale file is never reused by a later call."""
    if not source or source == "-":
        return
    path = Path(source).resolve()
    if (Path(root) / runs.RUNS_DIR).resolve() in path.parents and path.is_file():
        path.unlink()


def cmd_sf_install(args: argparse.Namespace) -> int:
    try:
        content = read_output(args.source)
        dest = Path(args.root) / args.dest
        if args.model_role is None:
            emit({args.dest: fusion.install_file(dest, content or "")})
            return 0
        try:
            # X1: the frontmatter reflects models.json, never the --models of a cycle.
            resolved = models.resolve_root(Path(args.root), (args.model_role,))
            value = resolved["roles"][args.model_role]["model"]
            result = fusion.install_agent(dest, content or "", value)
        except models.ModelsError as exc:
            raise Usage("%s: %s" % (args.dest, exc))
        emit({args.dest: result["state"], "model": value, "model_block": result["model_block"]})
    finally:
        _remove_transit(Path(args.root), args.source)
    return 0


def cmd_sf_copy_core(args: argparse.Namespace) -> int:
    result = fusion.copy_core(HERE, Path(args.root))
    emit(dict(result, core_version=CORE_VERSION))
    if not result["copied"]:
        raise ghflow.Stop("core not copied: .claude/harness/ holds a different core (customized or another "
                          "version): %s; nothing was copied, the generated factory-run would not work. "
                          "Restore or remove .claude/harness/, then run the installation again."
                          % ", ".join(result["blocked_by"]))
    return 0


# --------------------------------------------------------------- factory-run

def cmd_fr_start(args: argparse.Namespace) -> int:
    root = Path(args.root)
    arguments = ""
    if args.arguments_file:
        arguments = read_file(args.arguments_file)
    try:
        # X6: --models "role=model;..." taken out of $ARGUMENTS, for this cycle only.
        rest, override = models.extract_option(arguments)
        resolved = models.resolve_root(root, models.FACTORY_ROLES, override)
    except models.ModelsError as exc:
        raise Usage(str(exc))
    choice = factory.entry(rest, root)
    state = factory.new_state({r: e["model"] for r, e in resolved["roles"].items()})
    run = runs.create(root, "factory-run", state)
    result = dict(choice, run=runs.display(run), models=resolved["roles"])
    if choice["mode"] == "plan":
        result["need"] = rest
    if resolved["warnings"]:
        result["model_warnings"] = resolved["warnings"]
    emit(result)
    return 0


def cmd_fr_record(args: argparse.Namespace) -> int:
    run = _run_path(args.run)
    state = runs.load_state(run)
    measure = _measure(state, args, args.agent)
    decision, fields = factory.record(state, args.agent, read_output(args.output), args.dead)
    model = _model(args, state, factory.AGENT_ROLES[args.agent])
    _log(run, args, args.agent, measure, fields, decision, model)
    runs.save_state(run, state)
    emit(decision)
    return 0


# ------------------------------------------------------------------- ship-pr

def _reject_duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    seen: Dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise Usage("--not-fixed-file: finding %s given twice" % key)
        seen[key] = value
    return seen


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
    adopted, previous = None, {}
    if args.run:
        # Run opened by the ship-pr.target gate: its journal (gate events) is continued.
        adopted = _run_path(args.run)
        previous = runs.load_state(adopted)
        if previous.get("skill") != "ship-pr" or not previous.get("gate_only"):
            raise Usage("--run %s: start only continues a run opened by 'gate decide'" % args.run)
        root = Path(previous["root"])
    try:
        resolved = models.resolve_root(root, models.SHIPPR_ROLES, args.models)
    except models.ModelsError as exc:
        raise Usage(str(exc))
    run_cmd = Runner(cwd=str(root))
    info = ghflow.preflight_checks(run_cmd, args.target)
    excluded = ghflow.ensure_exclude(run_cmd, root)
    info.update(ghflow.worktree_and_repo(run_cmd))
    assignment = {r: e["model"] for r, e in resolved["roles"].items()}
    state = shippr.new_state(args.target, rounds, themes, assignment)
    state.update(branch=info["branch"], owner_repo=info["owner_repo"])
    if adopted is None:
        run = runs.create(root, "ship-pr", state)
    else:
        run = adopted
        runs.save_state(run, dict(state, skill="ship-pr", root=str(root), begun=previous.get("begun", {})))
    result = dict(info, run=runs.display(run), registry=runs.display(runs.registry_path(run)),
                  rounds=rounds, themes=themes, round=1, exclude_added=excluded, models=resolved["roles"])
    if resolved["warnings"]:
        result["model_warnings"] = resolved["warnings"]
    emit(result)
    return 0


def cmd_sp_sync(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    emit(ghflow.sync_upstream(run_cmd))
    return 0


def cmd_sp_pr(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    try:
        title = args.title
        if args.title_file is not None:
            if title is not None:
                raise Usage("--title and --title-file are exclusive")
            title = _one_line("--title-file", read_file(args.title_file))
        if (title is None) != (args.body_file is None):
            raise Usage("--title (or --title-file) and --body-file go together")
        body = read_output(args.body_file) if args.body_file else None
    finally:
        for source in (args.title_file, args.body_file):
            _remove_transit(Path(state["root"]), source)
    result = ghflow.find_or_create_pr(run_cmd, state, title, body)
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
    model = _model(args, state, shippr.AGENT_ROLES[shippr.REVIEWER])
    _log(run, args, shippr.REVIEWER, measure, fields, decision, model, theme=args.theme)
    runs.save_state(run, state)
    emit(decision)
    return 0


def cmd_sp_validator(args: argparse.Namespace) -> int:
    run, state, _, reg = _ship_ctx(args)
    measure = _measure(state, args, "validator:" + args.finding)
    decision, fields = shippr.record_validator(state, reg, args.finding, read_output(args.output), args.dead)
    model = _model(args, state, shippr.AGENT_ROLES[shippr.VALIDATOR])
    _log(run, args, shippr.VALIDATOR, measure, fields, decision, model, finding=args.finding)
    runs.save_state(run, state)
    emit(decision)
    return 0


def cmd_sp_drop(args: argparse.Namespace) -> int:
    run, state, _, reg = _ship_ctx(args)
    try:
        reason = read_file(args.reason_file).strip() if args.reason_file else ""
    finally:
        _remove_transit(Path(state["root"]), args.reason_file)
    result = shippr.drop_duplicate(state, reg, args.finding, args.of, reason or None)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_sp_comment(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    result = ghflow.post_comment(run_cmd, state, args.finding)
    runs.save_state(run, state)
    emit(result)
    return 0


def _commit_inputs(args: argparse.Namespace) -> Tuple[str, Dict[str, str], List[str]]:
    summary = args.summary or ""
    if args.summary_file is not None:
        if summary.strip():
            raise Usage("--summary and --summary-file are exclusive")
        summary = read_file(args.summary_file)
    if summary.strip():
        summary = _one_line("--summary-file" if args.summary_file is not None else "--summary", summary)
    entries: List[Tuple[str, str]] = []
    for item in args.not_fixed or []:
        fid, sep, reason = item.partition(":")
        if not sep or not reason.strip():
            raise Usage("--not-fixed expects ID:reason, got: %r" % item)
        entries.append((fid.strip(), reason.strip()))
    if args.not_fixed_file is not None:
        try:
            data = json.loads(read_file(args.not_fixed_file), object_pairs_hook=_reject_duplicate_keys)
        except ValueError as exc:
            raise Usage("--not-fixed-file is not valid JSON: %s" % exc)
        if not isinstance(data, dict):
            raise Usage('--not-fixed-file expects a JSON object {"<id>": "<reason>"}')
        for fid, reason in data.items():
            if not isinstance(reason, str) or not reason.strip() or not fid.strip():
                raise Usage("--not-fixed-file: %r needs a non-empty reason" % (fid,))
            entries.append((fid.strip(), reason.strip()))
    not_fixed: Dict[str, str] = {}
    for fid, reason in entries:
        if fid in not_fixed:
            raise Usage("finding %s given twice as not fixed (--not-fixed / --not-fixed-file)" % fid)
        not_fixed[fid] = reason
    trailers = [_one_line("--trailer", t) for t in args.trailer or []]
    if args.fixed and not summary.strip():
        raise Usage("--summary or --summary-file is required when a fix is committed")
    return summary, not_fixed, trailers


def cmd_sp_commit(args: argparse.Namespace) -> int:
    run, state, run_cmd, reg = _ship_ctx(args)
    try:
        pending = state.get("unpushed")
        if pending and pending["round"] == state["round"]:
            # Relaunch after a failed push: the recorded commit is pushed, the
            # inputs (whose transit files are already consumed) are not needed.
            summary, not_fixed, trailers = "", {}, []
        else:
            summary, not_fixed, trailers = _commit_inputs(args)
    finally:
        for source in (args.summary_file, args.not_fixed_file):
            _remove_transit(Path(state["root"]), source)
    result = ghflow.commit_round(run_cmd, state, reg, summary, args.fixed or [], not_fixed, trailers,
                                 checkpoint=lambda: runs.save_state(run, state))
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_sp_threads(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    result = ghflow.handle_threads(run_cmd, state, checkpoint=lambda: runs.save_state(run, state))
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
    p.add_argument("--model", default=None,
                   help="model used; default: the model resolved for the agent's role at start")
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
    q = jsub.add_parser("amend", help="completes the last entry of a slot (measurements known after the call)")
    q.add_argument("--run", required=True)
    q.add_argument("--slot", required=True, help="agent, reviewer:<theme> or validator:<id>")
    q.add_argument("--duration-ms", default=None, help="fills a null duration_ms")
    q.add_argument("--tokens", default=None, help="fills null tokens")
    q.set_defaults(func=cmd_journal_amend)
    p = sub.add_parser("begin", help="timestamp before an agent call")
    p.add_argument("--run", required=True)
    p.add_argument("--slot", required=True, help="agent, reviewer:<theme> or validator:<id>")
    p.set_defaults(func=cmd_begin)
    p = sub.add_parser("models", help="model per role: .claude/models.json and --models (MD-01 to MD-08)")
    msub = p.add_subparsers(dest="mcmd", required=True)
    q = msub.add_parser("resolve", help="effective assignment {role: {model, pass_param}}")
    q.add_argument("--root", default=".")
    q.add_argument("--roles", default=None, help="factory, shippr, audit, lab or roles, comma-separated")
    q.add_argument("--models", default=None, help='"role=model;..." for this cycle only')
    q.add_argument("--aliases", default=None, choices=sorted(models.ALIAS_TABLES), help="short role names")
    q.set_defaults(func=cmd_models_resolve)
    q = msub.add_parser("write", help="merges a preset and explicit choices into .claude/models.json")
    q.add_argument("--root", default=".")
    q.add_argument("--preset", default=None, choices=sorted(models.PRESETS))
    q.add_argument("--set", default=None, help='explicit choices "role=model;...", they win')
    q.set_defaults(func=cmd_models_write)
    p = sub.add_parser("gate", help="human gates (GT-01 to GT-08)")
    gsub = p.add_subparsers(dest="gcmd", required=True)
    for name, func in (("decide", cmd_gate_decide), ("answer", cmd_gate_answer)):
        q = gsub.add_parser(name)
        q.add_argument("--id", required=True, help="gate id of the GT-08 catalog")
        q.add_argument("--run", default=None, help="run journal; absent (decide only): a new run of the gate's skill")
        q.add_argument("--root", default=".")
        q.set_defaults(func=func)
    q.add_argument("--answer", default=None, help="option chosen by the user")
    q.add_argument("--answer-file", default=None, help="free answer, file written by Write (consumed)")
    q.add_argument("--headless", action="store_true", help="AskUserQuestion unavailable: headless fallback (GT-06)")
    q.add_argument("--default", action="store_true", help="applies the default (decision default)")
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
    q.add_argument("--source", required=True,
                   help="content file, '-' = stdin; removed once read when it lies under .claude/runs/")
    q.add_argument("--model-role", default=None, choices=models.ROLES,
                   help="generated agent: its role's model written in a frontmatter block (X1)")
    q.set_defaults(func=cmd_sf_install)
    q = ssub.add_parser("copy-core", help="copies the core under .claude/harness/ (D1); exit 1 if blocked")
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
    q.add_argument("--run", default=None, help="run opened by the ship-pr.target gate")
    q.add_argument("--models", default=None, help='"role=model;..." for this cycle only (X6)')
    q.add_argument("--rounds", default=None)
    q.add_argument("--themes", default=None,
                   help="1 to 4 themes separated by ';' (default: 3 themes); empty list, more than 4 "
                        "or a theme given twice = explicit error (D8)")
    q.set_defaults(func=cmd_sp_start)
    for name, func in (("sync", cmd_sp_sync), ("pr-state", cmd_sp_pr_state), ("diff", cmd_sp_diff),
                       ("threads", cmd_sp_threads), ("end-round", cmd_sp_end_round)):
        q = psub.add_parser(name)
        q.add_argument("--run", required=True)
        q.set_defaults(func=func)
    q = psub.add_parser("pr")
    q.add_argument("--run", required=True)
    q.add_argument("--title", default=None)
    q.add_argument("--title-file", default=None, help="file holding the title (one line), written by Write")
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
    q = psub.add_parser("drop", help="sets aside a PENDING finding as a duplicate of another (SP-07)")
    q.add_argument("--run", required=True)
    q.add_argument("--finding", required=True, help="PENDING finding of the current round")
    q.add_argument("--of", required=True, help="existing finding it duplicates")
    q.add_argument("--reason-file", default=None, help="file holding the reason, written by Write")
    q.set_defaults(func=cmd_sp_drop)
    q = psub.add_parser("comment")
    q.add_argument("--run", required=True)
    q.add_argument("--finding", required=True)
    q.set_defaults(func=cmd_sp_comment)
    q = psub.add_parser("commit")
    q.add_argument("--run", required=True)
    q.add_argument("--summary", default="")
    q.add_argument("--summary-file", default=None, help="file holding the summary, written by Write")
    q.add_argument("--fixed", nargs="*", default=[])
    q.add_argument("--not-fixed", action="append", default=[], help="ID:reason, repeatable")
    q.add_argument("--not-fixed-file", default=None,
                   help='JSON file {"<id>": "<reason>"}, written by Write; an id given twice is refused')
    q.add_argument("--trailer", action="append", default=[],
                   help="trailer line added after a blank line (attribution), repeatable")
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
        run = _existing_run(args)
        if run is None:
            return args.func(args)
        with runs.locked(run):
            return args.func(args)
    except (ghflow.Stop, runs.LockTimeout, gates.GateStop) as exc:
        sys.stderr.write("STOP: %s\n" % exc)
        return 1
    except (Usage, ValueError, factory.RunOver, shippr.LoopError, fusion.FusionError,
            blocks.BlockError, FileNotFoundError) as exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
