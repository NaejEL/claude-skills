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
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# D1: no bytecode, even when called without -B (versioned copy under .claude/harness/).
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from hcore import CORE_VERSION  # noqa: E402
from hcore import (aliases, audit, blocks, bs, counters, cx, factory, findings, fusion, gates,  # noqa: E402
                   ghflow, interp, journal, lab, labrun, loop, models, profiles, registry, runs, scout,
                   shippr, stack, stamp, tshirt, unified, verdicts)
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
    """Path of an input file. A missing file under .harness/runs/ is a transit
    file already consumed (or never written): explicit usage error."""
    path = Path(value)
    if not path.is_file():
        parts = path.resolve().parts
        if any(parts[i:i + 2] == (".harness", "runs") for i in range(len(parts) - 1)):
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



# ------------------------------------------------------------------ profiles

def _profiles_dir(value: Optional[str]) -> Optional[Path]:
    return Path(value) if value else None


def cmd_profile_validate(args: argparse.Namespace) -> int:
    errors = profiles.validate(Path(args.path))
    if errors:
        for e in errors:
            sys.stderr.write("ERROR: %s\n" % e)
        emit({"valid": False, "errors": errors})
        return 2
    emit({"valid": True, "errors": []})
    return 0


def cmd_profile_list(args: argparse.Namespace) -> int:
    emit({"profiles": profiles.summary(_profiles_dir(args.profiles_dir))})
    return 0


def cmd_profile_show(args: argparse.Namespace) -> int:
    """The data a skill needs to generate the files of a profile (EP-04)."""
    prof = profiles.get(args.name, _profiles_dir(args.profiles_dir))
    roles = []
    for role in prof["roles"]:
        roles.append(dict(role, mission_text=profiles.fragment(prof, role["mission"])))
    lenses = [dict(l, fragment_text=profiles.fragment(prof, l["fragment"]),
                   critical_text=profiles.fragment(prof, l["critical_definition"])) for l in prof["lenses"]]
    sets = [dict(s_, **{k.replace("fragment", "text"): profiles.fragment(prof, s_[k])
                        for k in ("fragment", "map_fragment", "intro_fragment", "validator_fragment") if k in s_})
            for s_ in prof["lens_sets"]]
    out = {"name": prof["name"], "orchestrator": prof["orchestrator"], "ci": prof["ci"], "roles": roles,
           "artefacts": prof["artefacts"], "loop": prof["loop"], "model_presets": prof["model_presets"],
           "verifier": prof["verifier"], "lenses": lenses, "lens_sets": sets}
    for key, rel in prof["fragments"].items():
        out[key + "_text"] = profiles.fragment(prof, rel)
    emit(out)
    return 0


# --------------------------------------------------------------------- stamp

def cmd_stamp_add(args: argparse.Namespace) -> int:
    names = [n for n in (args.profiles or "").split(";") if n.strip()]
    if not names:
        raise Usage("stamp add expects --profiles p[;p]")
    emit(stamp.add(Path(args.root), [n.strip() for n in names], args.by, args.date))
    return 0


def cmd_stamp_resolve(args: argparse.Namespace) -> int:
    emit(stamp.resolve(Path(args.root)))
    return 0


def cmd_stamp_compare(args: argparse.Namespace) -> int:
    emit(stamp.compare(Path(args.root), json.loads(read_file(args.verdict))))
    return 0


# --------------------------------------------------------------------- scout

def cmd_scout_signals(args: argparse.Namespace) -> int:
    result = scout.signals(Path(args.root))
    result["judgement"] = scout.judgement_criteria()
    emit(result)
    return 0


def cmd_scout_verdict(args: argparse.Namespace) -> int:
    root = Path(args.root)
    output = None
    try:
        if args.signals:
            try:
                output = json.loads(read_file(args.signals))
            except ValueError as exc:
                raise Usage("--signals is not valid JSON: %s" % exc)
            if not isinstance(output, dict):
                raise Usage("--signals expects a JSON object")
    finally:
        _remove_transit(root, args.signals)
    result = scout.verdict(root, output, args.scout_failed)
    moment = datetime.now()
    out_dir = root / runs.RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ("scout-%s.json" % moment.strftime("%Y%m%d-%H%M%S"))
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        resolved = models.resolve_readonly(root, ("harness.scout",), args.models)
    except models.ModelsError as exc:
        raise Usage(str(exc))
    if args.run:
        run = _run_path(args.run)
    else:
        run = runs.create(root, args.skill, {"scout": True})
    record = journal.make_record(agent="harness-scout", model=resolved["roles"]["harness.scout"]["model"],
                                 duration_ms=_count_arg("--duration-ms", args.duration_ms, []),
                                 iteration=0, verdict="DEAD" if args.scout_failed else "DONE",
                                 produced=len(output.get("signals", [])) if output else 0,
                                 tokens=_count_arg("--tokens", args.tokens, []))
    journal.append(run, journal.sanitize(record)[0])
    emit(dict(result, verdict_file=path.relative_to(root).as_posix(), run=runs.display(run),
              model=resolved["roles"]["harness.scout"]))
    return 0


# --------------------------------------------------------------------- audit (Phase 2)

def _active_for_audit(args: argparse.Namespace) -> List[str]:
    if args.profile:
        names = [n.strip() for n in args.profile.split(";") if n.strip()]
        known = profiles.discover()
        unknown = [n for n in names if n not in known]
        if unknown:
            raise Usage("unknown profile: %s (known: %s)" % (", ".join(unknown), ", ".join(known)))
        return names
    resolved = stamp.resolve(Path(args.root))
    if not resolved["profiles"]:
        raise Usage("no active profile: pass --profile or run the scout (gate audit.profiles)")
    return resolved["profiles"]


def cmd_audit_select(args: argparse.Namespace) -> int:
    """AD-03, AD-04, AD-09: lens selection, waves and caps."""
    names = _active_for_audit(args)
    known = profiles.discover()
    selected = [known[n] for n in names]
    try:
        lenses = profiles.select_lenses(selected, args.lenses, known)
        options = {"--max-specs": args.max_specs, "--max-findings": args.max_findings,
                   "--max-questions": args.max_questions}
        caps = profiles.caps(selected, options)
    except profiles.SelectionError as exc:
        raise Usage(str(exc))
    active_sets = {s["name"]: s for p in selected for s in p["lens_sets"]}
    lenses = [l for l in lenses if l["set"] in active_sets]
    emit({"profiles": names, "lenses": [l["name"] for l in lenses],
          "details": [{"name": l["name"], "profile": l["profile"], "set": l["set"], "prefix": l["prefix"],
                       "model_role": l["model_role"], "debt": l["debt"], "shape": l["shape"]} for l in lenses],
          "waves": profiles.waves(lenses), "caps": caps, "via": args.via})
    return 0


def cmd_audit_alias_args(args: argparse.Namespace) -> int:
    try:
        text = read_file(args.arguments_file) if args.arguments_file else ""
    finally:
        _remove_transit(Path(args.root), args.arguments_file)
    emit(aliases.translate(args.skill, text))
    return 0


def cmd_gate_list(args: argparse.Namespace) -> int:
    emit({"gates": [{"id": g.id, "kind": g.kind, "default": g.default, "rationale": g.rationale,
                     "headless": g.headless, "phase2_auto": g.phase2_auto}
                    for g in gates.all_gates().values()]})
    return 0

# --------------------------------------------------------------------- gates

def _gate_run(args: argparse.Namespace, gate: gates.Gate) -> Optional[Path]:
    """Existing run of a gate (--run), or None: 'decide' then opens a new run
    of the gate's skill (JR-01), once the policy is known to be valid."""
    if args.run:
        run = _run_path(args.run)
        skill = runs.load_state(run).get("skill")
        if skill != gate.skill:
            raise Usage("gate %s belongs to %s, the run is a %s run" % (gate.id, gate.skill, skill))
        return run
    if args.gcmd == "answer":
        raise Usage("gate answer expects --run (the run returned by 'gate decide')")
    return None


def cmd_gate_decide(args: argparse.Namespace) -> int:
    gate = gates.get(args.id)
    run = _gate_run(args, gate)
    root = Path(runs.load_state(run)["root"]) if run is not None else Path(args.root)
    # GT-01: an invalid .claude/harness.json is refused BEFORE any run is opened
    # (no orphan run left behind by an exit 2).
    event = gates.decide(gate.id, gates.read_policy(root), ambiguous=args.ambiguous)
    if run is None:
        run = runs.create(root, gate.skill, {"gate_only": True})
    journal.append(run, event)
    if event["decision"] == gates.STOP:
        if event.get("ambiguous"):
            raise gates.GateStop("gate %s: ambiguous proposal under autonomy auto: see %s; resume with /%s "
                                 "--profile <p>[;<p>]" % (gate.id, args.verdict or "the scout-*.json verdict",
                                                           gate.skill))
        raise gates.GateStop(gates.stop_message(gate, "decision default without a default to apply"))
    emit(dict(event, options=list(gate.options), dialogue=gate.dialogue, run=runs.display(run)))
    return 0


def cmd_gate_answer(args: argparse.Namespace) -> int:
    gate = gates.get(args.id)
    run = _gate_run(args, gate)
    assert run is not None
    root = Path(runs.load_state(run)["root"])
    try:
        given = [x for x in (args.answer, args.answer_file) if x is not None]
        if int(args.headless) + int(args.default) + len(given) != 1:
            raise Usage("gate answer expects exactly one of --answer, --answer-file, --headless, --default")
        text = read_file(args.answer_file) if args.answer_file is not None else args.answer
    finally:
        _remove_transit(root, args.answer_file)
    source = "headless" if args.headless else "default" if args.default else "user"
    try:
        event = gates.answer(gate.id, gates.last_decision(journal.read(run), gate.id), source, text)
    except gates.OffOptions as exc:
        # A free "Other" answer to a closed gate never kills the run: nothing is
        # logged, the decision stays pending, the skill asks the question again.
        emit({"id": gate.id, "action": "reask", "reason": str(exc), "options": list(gate.options)})
        return 0
    journal.append(run, event)
    apply = gates.applied(gate.id, event)
    if apply == gates.STOP:
        raise gates.GateStop(gates.stop_message(gate, "no interaction possible (headless fallback: stop)"))
    emit({"id": gate.id, "action": "apply", "answer": event["answer"], "source": source, "apply": apply})
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
    stacks = [s.strip() for s in (args.stacks or "").split(",") if s.strip()]
    if args.profiles:
        known = profiles.discover()
        names = [n.strip() for n in args.profiles.replace(",", ";").split(";") if n.strip()]
        unknown = [n for n in names if n not in known]
        if unknown:
            raise Usage("unknown profile: %s (known: %s)" % (", ".join(unknown), ", ".join(known)))
        merged = profiles.merged([known[n] for n in names], stacks, Path(args.root), args.test_command,
                                 args.test_windows)
        emit(fusion.apply_merged(Path(args.root), merged))
        return 0
    emit(fusion.apply(Path(args.root), stacks))
    return 0


def _remove_transit(root: Path, source: Optional[str]) -> None:
    """The transit file written by Write under <root>/.harness/runs/ is removed
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


def cmd_sf_args(args: argparse.Namespace) -> int:
    """EP-01: [--profile p[;p] | --rescan] [first need]; both options -> exit 2, unknown profile -> exit 2."""
    root = Path(args.root)
    try:
        text = read_file(args.arguments_file) if args.arguments_file else ""
    finally:
        _remove_transit(root, args.arguments_file)
    rest, forced = loop.extract_profile_option(text)
    rescan = re.search(r"(?:(?<=\s)|^)--rescan(?=\s|$)", rest) is not None
    if rescan:
        rest = re.sub(r"(?:(?<=\s)|^)--rescan(?=\s|$)", "", rest, count=1).strip()
    if forced is not None and rescan:
        raise Usage("--profile and --rescan cannot be used together")
    names = [n.strip() for n in (forced or "").split(";") if n.strip()]
    unknown = [n for n in names if n not in profiles.discover()]
    if unknown:
        raise Usage("unknown profile: %s (known: %s)" % (", ".join(unknown), ", ".join(profiles.discover())))
    emit({"profiles": names, "rescan": rescan, "need": rest})
    return 0


def cmd_sf_copy_core(args: argparse.Namespace) -> int:
    if args.force and not args.refresh:
        raise Usage("--force goes with --refresh only")
    if args.check:
        # Strict identity of the copy with this core, on demand only.
        result = fusion.check_core_copy(HERE, Path(args.root))
        emit(dict(result, core_version=CORE_VERSION))
        if not result["identical"]:
            raise ghflow.Stop(".claude/harness/ differs from the core: %d different, %d missing, %d extra; "
                              "refresh it with 'sf copy-core --refresh'"
                              % (len(result["differs"]), len(result["missing"]), len(result["extra"])))
        return 0
    if args.refresh:
        result = fusion.refresh_core(HERE, Path(args.root), force=args.force)
        emit(dict(result, core_version=CORE_VERSION))
        if not result["refreshed"]:
            raise ghflow.Stop("%s: nothing refreshed, nothing touched" % result["reason"])
        return 0
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
    try:
        if args.arguments_file:
            arguments = read_file(args.arguments_file)
    finally:
        # The transit file is removed once read, the command succeeded or not.
        _remove_transit(root, args.arguments_file)
    try:
        # X6: --models "role=model;..." taken out of $ARGUMENTS, for this cycle only.
        rest, override = models.extract_option(arguments)
    except models.ModelsError as exc:
        raise Usage(str(exc))
    # LP-05, LP-06: the input is routed to a profile of the stamp.
    stamped = stamp.resolve(root)
    instance = args.orchestrator if args.orchestrator != "factory-run" else None
    try:
        routed = loop.route(rest, root, stamped["profiles"], instance, forced_profile=args.profile)
    except loop.LoopUsage as exc:
        raise Usage(str(exc))
    except loop.LoopStop as exc:
        raise ghflow.Stop(str(exc))
    if routed["gate"]:
        emit({"profile": None, "gate": routed["gate"], "candidates": routed["candidates"],
              "default": routed["default"], "need": routed["need"], "source": stamped["source"]})
        return 0
    prof = profiles.get(routed["profile"])
    rest = loop.extract_profile_option(rest)[0]
    lab_machine = loop.machine_of(prof) == "lab"
    try:
        resolved = models.resolve_root(root, tuple(prof["model_roles"]), override, "lab" if lab_machine else None)
    except models.ModelsError as exc:
        raise Usage(str(exc))
    assignment = {r: e["model"] for r, e in resolved["roles"].items()}
    if lab_machine:
        entered = labrun.entry(rest, root)
        state = labrun.new_state(assignment, entered["mode"])
        choice = {"mode": "build" if entered["mode"] == "build" else "plan", "protocol": entered["protocol"]}
    else:
        choice = factory.entry(rest, root)
        state = factory.new_state(assignment)
    state["profile"] = prof["name"]
    run = runs.create(root, args.orchestrator, state)
    result = dict(choice, profile=prof["name"], orchestrator=args.orchestrator, run=runs.display(run),
                  models=resolved["roles"])
    if choice["mode"] == "plan":
        result["need"] = rest
    if resolved["warnings"]:
        result["model_warnings"] = resolved["warnings"]
    emit(result)
    return 0


def _profile_extra(state: Dict[str, Any]) -> Dict[str, Any]:
    """LP-07: every journal line of a routed run carries its profile."""
    return {"profile": state["profile"]} if state.get("profile") else {}


def cmd_fr_record(args: argparse.Namespace) -> int:
    run = _run_path(args.run)
    state = runs.load_state(run)
    if state.get("profile") and loop.machine_of(profiles.get(state["profile"])) == "lab":
        return cmd_lr_record(args)
    measure = _measure(state, args, args.agent)
    decision, fields = factory.record(state, args.agent, read_output(args.output), args.dead)
    model = _model(args, state, factory.AGENT_ROLES[args.agent])
    _log(run, args, args.agent, measure, fields, decision, model, **_profile_extra(state))
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
    # RG-04: the project registry is read once, when the run starts.
    state["project"] = {k: {"status": e["status"], "source": e["source"]}
                        for k, e in registry.ProjectRegistry(root).read().items()}
    if adopted is None:
        run = runs.create(root, "ship-pr", state)
    else:
        run = adopted
        runs.save_state(run, dict(state, skill="ship-pr", root=str(root), begun=previous.get("begun", {})))
    result = dict(info, run=runs.display(run), registry=runs.display(runs.registry_path(run)),
                  rounds=rounds, themes=themes, round=1, exclude_added=excluded, models=resolved["roles"],
                  project_findings=len(state["project"]))
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
    run, state, run_cmd, reg = _ship_ctx(args)
    head = run_cmd(["git", "rev-parse", "HEAD"])
    result = shippr.end_round(state, head.out.strip() if head.ok else None)
    if result["exit"] is not None:
        # RG-03: end of the review loop, the run registry is published to the
        # project BEFORE the final state is saved: a failed publication (lock
        # timeout, exit 1) leaves the round open, and 'end-round' run again
        # publishes (idempotent) then exits.
        result["project_registry"] = registry.ProjectRegistry(Path(state["root"])).publish(
            reg.last.values(), "ship-pr", Path(run).name)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_sp_merge(args: argparse.Namespace) -> int:
    run, state, run_cmd, _ = _ship_ctx(args)
    result = ghflow.merge(run_cmd, state, args.check)
    runs.save_state(run, state)
    emit(result)
    return 0


# ------------------------------------------------------------------ findings

def _findings_file(value: str) -> List[Any]:
    try:
        return findings.load_findings(read_file(value))
    except ValueError as exc:
        raise Usage("%s is not valid JSON: %s" % (value, exc))


def _valid_findings(value: str) -> List[Dict[str, Any]]:
    """FD-01 findings of a file; a non-conforming finding is a usage error."""
    items = _findings_file(value)
    for f in items:
        errors, _ = findings.validate(f)
        if errors:
            raise Usage("%s: %s" % (value, "; ".join(errors)))
    return items


def _one_finding(value: str) -> Dict[str, Any]:
    items = _valid_findings(value)
    if len(items) != 1:
        raise Usage("%s must hold exactly one finding" % value)
    return items[0]


def cmd_finding_validate(args: argparse.Namespace) -> int:
    report = findings.validate_text(read_file(args.path))
    emit(dict(report, path=args.path))
    return 0 if report["valid"] else 1


def cmd_finding_adapt(args: argparse.Namespace) -> int:
    try:
        data = json.loads(read_file(args.input))
    except ValueError as exc:
        raise Usage("%s is not valid JSON: %s" % (args.input, exc))
    if isinstance(data, dict) and "id" not in data:
        data = data.get("findings", data.get("issues", data))
    items = data if isinstance(data, list) else [data]
    ids = [x.strip() for x in (args.ids or "").split(",") if x.strip()]
    if ids and len(ids) != len(items):
        raise Usage("--ids gives %d ids for %d findings" % (len(ids), len(items)))
    out = [findings.adapt(args.format, obj, ids[i] if ids else None, args.axis, args.source)
           for i, obj in enumerate(items)]
    emit({"format": args.format, "findings": out})
    return 0


def cmd_finding_verdict(args: argparse.Namespace) -> int:
    try:
        emit(dict(findings.parse_verdict(read_output(args.output), args.source), usable=True))
    except verdicts.UnusableOutput as exc:
        # FD-06: an unusable output is a dead agent, for the skill to relaunch.
        emit({"usable": False, "reason": "unusable output: %s" % exc})
    return 0


def cmd_finding_apply(args: argparse.Namespace) -> int:
    f = _one_finding(args.finding)
    try:
        parsed = findings.parse_verdict(read_output(args.verdict), args.source)
    except verdicts.UnusableOutput as exc:
        raise Usage("unusable verdict: %s" % exc)
    emit({"findings": findings.apply_verdict(f, parsed)})
    return 0


def cmd_finding_spec(args: argparse.Namespace) -> int:
    f = _one_finding(args.finding)
    try:
        sections = json.loads(read_file(args.sections))
    except ValueError as exc:
        raise Usage("--sections is not valid JSON: %s" % exc)
    if not isinstance(sections, dict):
        raise Usage("--sections expects a JSON object")
    text = findings.to_spec(f, sections, args.prefix, args.number)
    emit({args.dest: fusion.install_file(Path(args.root) / args.dest, text)})
    return 0


def cmd_finding_note(args: argparse.Namespace) -> int:
    emit(findings.to_note(_one_finding(args.finding)))
    return 0


def cmd_finding_forbidden(args: argparse.Namespace) -> int:
    found = {}
    for path in args.paths:
        hits = findings.check_forbidden(read_file(path))
        if hits:
            found[path] = hits
    emit({"clean": not found, "hits": found})
    if found:
        raise ghflow.Stop("forbidden string ('Statut :' followed by the ready status of an artefact) in: %s"
                          % ", ".join(sorted(found)))
    return 0


# ------------------------------------------------------------------ registry

def cmd_registry_publish(args: argparse.Namespace) -> int:
    run = _run_path(args.run)
    state = runs.load_state(run)
    reg = registry.Registry(runs.registry_path(run))
    emit(registry.ProjectRegistry(Path(state["root"])).publish(
        reg.last.values(), args.source or state["skill"], Path(run).name, args.deliverable))
    return 0


def cmd_registry_check(args: argparse.Namespace) -> int:
    project = registry.ProjectRegistry(Path(args.root))
    entries = project.read()
    dismissed, history, new = [], [], []
    for f in _valid_findings(args.file):
        look = project.lookup(registry.project_key(f), entries)
        item = {"id": f["id"], "key": look["key"], "previous": look["previous"]}
        if look["dismiss"]:
            dismissed.append(item)
        elif look["previous"]:
            history.append(item)
        else:
            new.append(f["id"])
    emit({"dismissed": dismissed, "history": history, "new": new})
    return 0


# -------------------------------------------------------------- stack, tshirt

def cmd_stack_detect(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.is_dir():
        raise ghflow.Stop("the path %s does not exist" % args.root)
    emit(stack.survey(root))
    return 0


def cmd_stack_journal(args: argparse.Namespace) -> int:
    emit(stack.journal_bounds(Path(args.file)))
    return 0


def cmd_tshirt(args: argparse.Namespace) -> int:
    items = tshirt.ordered(_valid_findings(args.file), args.order)
    result: Dict[str, Any] = {"order": [f["id"] for f in items], "quick_wins": tshirt.quick_wins(items)}
    if args.order == "VIB":
        result["raised_criticals"] = tshirt.raised_criticals(items)
    if args.grouping:
        result["specs"] = tshirt.plan_specs(items, args.grouping)
    if args.cap is not None:
        result["cap"] = tshirt.apply_cap(result.get("specs") or result["order"], args.cap)
    if args.load_by:
        result["load"] = tshirt.load(items, args.load_by)
    emit(result)
    return 0


# -------------------------------------------------------------------- audits

def _audit_ctx(args: argparse.Namespace):
    run = _run_path(args.run)
    state = runs.load_state(run)
    if "audit_skill" not in state:
        raise Usage("not an audit run: %s" % args.run)
    return run, state, audit.profile(state["audit_skill"]), registry.Registry(runs.registry_path(run))


def _json_file(option: str, value: str) -> Any:
    try:
        return json.loads(read_file(value))
    except ValueError as exc:
        raise Usage("%s is not valid JSON: %s" % (option, exc))


def cmd_audit_start(args: argparse.Namespace) -> int:
    """AU-01 to AU-03, AU-09, AU-12: arguments, git probe, resume, run opened
    in the audited repository (X5: journal under its .harness/runs/)."""
    p = audit.profile(args.skill)
    try:
        arguments = read_file(args.arguments_file) if args.arguments_file else ""
    finally:
        _remove_transit(Path(args.root), args.arguments_file)
    parsed = audit.parse_arguments(args.skill, arguments, Path(args.root))
    if args.only:
        # AD-03: /audit selects single lenses; the engine selects units (an axis may be partial).
        try:
            wanted = profiles.split_list(args.only)
        except profiles.SelectionError as exc:
            raise Usage("--only: %s" % exc)
        outside = [w for w in wanted if w not in parsed["auditors"]]
        if outside:
            raise Usage("--only: lens not in this audit: %s" % ", ".join(outside))
        parsed["auditors"] = [a for a in parsed["auditors"] if a in wanted]
        parsed["units"] = [u for u in parsed["units"]
                           if any(x.unit == u and x.name in wanted for x in p.auditors)]
    repo = Path(parsed["repo"])
    try:
        # X5: an audit writes nothing but its allowed paths: no models.json migration.
        resolved = models.resolve_readonly(repo, p.roles, parsed["models"], p.aliases)
    except models.ModelsError as exc:
        raise Usage(str(exc))
    deliverable = repo / p.deliverable
    resumed = None
    imports: List[Dict[str, str]] = []
    import_warnings: List[str] = []
    if args.unified:
        # MG-01 to MG-03: AUDIT.md first, then the previous deliverable if it was never imported.
        found = unified.resume(repo, args.skill)
        resumed, imports, import_warnings = found["parsed"], found["imports"], found["warnings"]
    elif deliverable.is_file():
        resumed = audit.parse_deliverable(args.skill, deliverable.read_text(encoding="utf-8"))
    run_cmd = Runner(cwd=str(repo))
    git_absent = audit.probe_git(run_cmd, repo)
    # AU-12: with GIT_ABSENT, no git command afterwards (no exclusion either).
    excluded = None if git_absent else registry.git_exclude(
        repo, audit.RUN_EXCLUDE + registry.PROJECT_EXCLUDE, run_cmd)
    project = {k: {"status": e["status"], "source": e["source"]}
               for k, e in registry.ProjectRegistry(repo).read().items()}
    factory_here = (repo / ".claude" / "skills" / "factory-run" / "SKILL.md").is_file()
    assignment = {r: e["model"] for r, e in resolved["roles"].items()}
    state = audit.new_state(args.skill, parsed, git_absent, factory_here, project, resumed, assignment)
    state["unified"] = bool(args.unified)
    state["imports"] = imports
    run = runs.create(repo, args.skill, state)
    reg = registry.Registry(runs.registry_path(run))
    count = audit.register_resumed(resumed, reg) if resumed else 0
    auditors = []
    lab_here = audit.lab_present(repo) if args.skill == "ai-lab-audit" else False
    for a in p.auditors:
        if a.name in parsed["auditors"]:
            role = audit.auditor_role(p, a.name)
            auditors.append(dict(resolved["roles"][role], auditor=a.name, unit=a.unit, prefix=a.prefix, role=role,
                                 subagent_type=audit.subagent_type(p, a.name, lab_here)))
    result = {"run": runs.display(run), "repo": str(repo), "skill": args.skill, "units": parsed["units"],
              "auditors": auditors, "validator": dict(resolved["roles"][p.validator_role], role=p.validator_role),
              "cap": parsed["cap"], "git_absent": git_absent, "exclude_added": excluded, "factory": factory_here,
              "lab": lab_here,
              "resumed": None if resumed is None else {"entries": count, "numbering": resumed["numbering"],
                                                       "ids": audit.resumed_ids(resumed)},
              "project_findings": len(project), "allowed_writes": audit.allowed_writes(args.skill)}
    if args.unified:
        result["imports"] = imports
        result["allowed_writes"] = [unified.DELIVERABLE] + result["allowed_writes"][1:]
    if import_warnings:
        result["import_warnings"] = import_warnings
    if resolved["warnings"]:
        result["model_warnings"] = resolved["warnings"]
    emit(result)
    return 0


def cmd_audit_auditor(args: argparse.Namespace) -> int:
    run, state, p, reg = _audit_ctx(args)
    measure = _measure(state, args, "auditor:" + args.unit)
    peers = unified.cycle_peers(Path(state["repo"]), run) if state.get("unified") else None
    decision, fields = audit.record_auditor(state, reg, args.unit, read_output(args.output), args.dead, peers)
    model = _model(args, state, audit.auditor_role(p, args.unit))
    _log(run, args, "auditor", measure, fields, decision, model, unit=args.unit)
    runs.save_state(run, state)
    emit(decision)
    return 0


def cmd_audit_validator(args: argparse.Namespace) -> int:
    run, state, p, reg = _audit_ctx(args)
    measure = _measure(state, args, "validator:" + args.finding)
    decision, fields = audit.record_validator(state, reg, args.finding, read_output(args.output), args.dead)
    model = _model(args, state, p.validator_role)
    _log(run, args, "validator", measure, fields, decision, model, finding=args.finding)
    runs.save_state(run, state)
    emit(decision)
    return 0


def cmd_audit_next(args: argparse.Namespace) -> int:
    run, state, p, reg = _audit_ctx(args)
    emit(audit.next_step(state))
    return 0


def cmd_audit_consolidate(args: argparse.Namespace) -> int:
    run, state, p, reg = _audit_ctx(args)
    result = audit.consolidate(state)
    runs.save_state(run, state)
    ordered = [state["findings"][fid] for prefix, _ in p.numbering for fid in result["order"][prefix]]
    keys = ("id", "title", "severity", "size", "axis", "nature", "category", "depends_on", "status")
    # The resumed ids per section (vibecode-audit: an explicit order lists the
    # resumed attack lines too) are returned so that the skill need not reread
    # the deliverable.
    out = dict(result, findings=[{k: f.get(k) for k in keys} for f in ordered],
               quick_wins=tshirt.quick_wins(ordered), resumed_ids=audit.resumed_ids(state["resumed"]))
    if "VIB" in result["order"]:
        out["raised_criticals"] = tshirt.raised_criticals(ordered)
    emit(out)
    return 0


def cmd_audit_plan(args: argparse.Namespace) -> int:
    if args.run is None:
        return cmd_audit_select(args)
    if args.data_file is None:
        raise Usage("audit plan expects --data-file with --run")
    run, state, p, reg = _audit_ctx(args)
    data = _json_file("--data-file", args.data_file)     # read, not consumed: 'render' takes it later
    if not isinstance(data, dict):
        raise Usage("--data-file expects a JSON object")
    emit(audit.plan(state, data))
    runs.save_state(run, state)
    return 0


def cmd_audit_settle(args: argparse.Namespace) -> int:
    emit({"status": audit.settle_status(args.audit_date, args.entry_date)})
    return 0


def cmd_audit_themes(args: argparse.Namespace) -> int:
    emit(audit.gate_calls(args.skill, args.count))
    return 0


def cmd_audit_readjust(args: argparse.Namespace) -> int:
    run, state, p, reg = _audit_ctx(args)
    result = audit.readjust(state)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_audit_render(args: argparse.Namespace) -> int:
    run, state, p, reg = _audit_ctx(args)
    try:
        data = _json_file("--data-file", args.data_file)
    finally:
        _remove_transit(Path(state["repo"]), args.data_file)
    if not isinstance(data, dict):
        raise Usage("--data-file expects a JSON object")
    text = audit.render(p.skill, audit.document(state, data))
    if state.get("unified"):
        # SO-05: the old deliverable is never written; the set block waits for 'audit assemble'.
        section = Path(state["repo"]) / runs.RUNS_DIR / ("section-%s.md" % p.skill)
        section.parent.mkdir(parents=True, exist_ok=True)
        with open(str(section), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(unified.strip_set_block(p.skill, text))
        state["section_file"] = section.name
        runs.save_state(run, state)
        emit({"section": section.name, "deliverable": unified.DELIVERABLE})
        return 0
    result = audit.write_text(p.skill, Path(state["repo"]), Path(state["repo"]) / p.deliverable, text)
    runs.save_state(run, state)
    emit(result)
    return 0


def cmd_audit_open(args: argparse.Namespace) -> int:
    """AD-12: the journal audit-<timestamp>.jsonl of /audit; `--via` is journaled (AX-04, E-A8)."""
    root = Path(args.root)
    run = runs.create(root, "audit", {"unified": True})
    if args.via:
        journal.append(run, {"event": "alias", "alias": args.via, "target": "audit"})
    emit({"run": runs.display(run), "via": args.via})
    return 0


def cmd_audit_assemble(args: argparse.Namespace) -> int:
    """SO-01, MG-02: AUDIT.md from the section blocks of the runs, in the order given."""
    repo = Path(args.root).resolve()
    blocks_: List[Tuple[str, str]] = []
    imports: List[Dict[str, str]] = []
    consumed: List[Path] = []
    for value in args.set_run:
        run = _run_path(value)
        state = runs.load_state(run)
        if not state.get("section_file"):
            raise Usage("run %s has no rendered section: call 'audit render' first" % value)
        path = repo / runs.RUNS_DIR / state["section_file"]
        blocks_.append((state["audit_skill"], read_file(str(path))))
        imports += state.get("imports", [])
        consumed.append(path)
    result = unified.assemble(repo, blocks_, args.date or datetime.now().strftime("%Y-%m-%d"),
                              [n for n in args.profiles.split(";") if n], [n for n in args.lenses.split(";") if n],
                              args.sampled, imports)
    for path in consumed:
        path.unlink()
    emit(result)
    return 0


def cmd_audit_spec(args: argparse.Namespace) -> int:
    run, state, p, reg = _audit_ctx(args)
    try:
        sections = _json_file("--sections", args.sections)
    finally:
        _remove_transit(Path(state["repo"]), args.sections)
    f = state["findings"].get(args.finding)
    if f is None or f["status"] != findings.CONFIRMED:
        raise Usage("finding %s is not a CONFIRMED finding of this run" % args.finding)
    if not isinstance(sections, dict):
        raise Usage("--sections expects a JSON object")
    emit(audit.write_spec(p.skill, Path(state["repo"]), f, sections, args.number, args.slug))
    return 0


def cmd_audit_publish(args: argparse.Namespace) -> int:
    run, state, p, reg = _audit_ctx(args)
    emit(audit.publish(state, reg, Path(run).name, args.deliverable))
    return 0


# ---------------------------------------------------------------- code-index

def _json_text(option: str, text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError as exc:
        raise Usage("%s is not valid JSON: %s" % (option, exc))


def cmd_cx_args(args: argparse.Namespace) -> int:
    try:
        text = read_file(args.arguments_file) if args.arguments_file else ""
    finally:
        _remove_transit(Path(args.root), args.arguments_file)
    emit(cx.parse_arguments(text))
    return 0


def cmd_cx_rg(args: argparse.Namespace) -> int:
    emit(cx.probe_rg())
    return 0


def cmd_cx_survey(args: argparse.Namespace) -> int:
    emit(cx.survey(Path(args.root)))
    return 0


def cmd_cx_install(args: argparse.Namespace) -> int:
    emit(cx.install_server(Path(args.asset), Path(args.root)))
    return 0


def cmd_cx_register(args: argparse.Namespace) -> int:
    emit(cx.register(Path(args.root), args.interp.split()))
    return 0


def cmd_cx_scope(args: argparse.Namespace) -> int:
    emit(cx.scope(Path(args.root)))
    return 0


def cmd_cx_wire(args: argparse.Namespace) -> int:
    try:
        contents = _json_text("--blocks-file", read_file(args.blocks_file))
    finally:
        _remove_transit(Path(args.root), args.blocks_file)
    if not isinstance(contents, dict):
        raise Usage("--blocks-file expects a JSON object {name: block text}")
    emit(cx.wire(Path(args.root), contents, args.interp.split()))
    return 0


# ------------------------------------------------------------------- ai-lab

def cmd_lab_apply(args: argparse.Namespace) -> int:
    emit(lab.apply(Path(args.root), args.test_command, args.test_windows))
    return 0


def cmd_lab_ci(args: argparse.Namespace) -> int:
    emit(lab.install_ci(Path(args.root), args.allow or []))
    return 0


def cmd_lr_start(args: argparse.Namespace) -> int:
    root = Path(args.root)
    arguments = ""
    try:
        if args.arguments_file:
            arguments = read_file(args.arguments_file)
    finally:
        _remove_transit(root, args.arguments_file)
    try:
        rest, override = models.extract_option(arguments)
        resolved = models.resolve_root(root, models.LAB_ROLES, override, "lab")
    except models.ModelsError as exc:
        raise Usage(str(exc))
    choice = labrun.entry(rest, root)
    state = labrun.new_state({r: e["model"] for r, e in resolved["roles"].items()}, choice["mode"])
    run = runs.create(root, "lab-run", state)
    result = dict(choice, run=runs.display(run), models=resolved["roles"])
    if choice["mode"] == "cadrage":
        result["question"] = rest
    if resolved["warnings"]:
        result["model_warnings"] = resolved["warnings"]
    emit(result)
    return 0


def cmd_lr_record(args: argparse.Namespace) -> int:
    run = _run_path(args.run)
    state = runs.load_state(run)
    slot = args.agent + (":" + args.mode if args.mode else "")
    measure = _measure(state, args, slot)
    decision, fields = labrun.record(state, args.agent, args.mode, read_output(args.output), args.dead)
    model = _model(args, state, labrun.role_of(args.agent, args.mode))
    _log(run, args, args.agent, measure, fields, decision, model, **_profile_extra(state))
    runs.save_state(run, state)
    emit(decision)
    return 0


# --------------------------------------------------------------- brainstorm
# Nothing is written before the final gate (X5): the session state travels
# on stdin ('-'), and 'finish' writes the journal with the synthesis.

def _stdin_json(option: str, value: str) -> Any:
    return _json_text(option, read_output(value) or "")


def cmd_bs_args(args: argparse.Namespace) -> int:
    emit(bs.parse_arguments(read_output(args.arguments) or ""))
    return 0


def cmd_bs_resume(args: argparse.Namespace) -> int:
    emit(bs.resume(Path(args.root), args.path))
    return 0


def cmd_bs_round(args: argparse.Namespace) -> int:
    data = _stdin_json("--data", args.data)
    emit(bs.round_step(int(data["round"]), int(data["rounds"]), data["lenses"], data.get("discarded") or [],
                       data.get("relaunched") or []))
    return 0


def cmd_bs_render(args: argparse.Namespace) -> int:
    data = _stdin_json("--data", args.data)
    previous = bs.resume(Path(args.root), bs.synthesis_path(data["subject"]))["rows"]
    sys.stdout.write(bs.render(data, previous))
    return 0


def cmd_bs_finish(args: argparse.Namespace) -> int:
    emit(bs.finish(Path(args.root), _stdin_json("--data", args.data)))
    return 0


# -------------------------------------------------------------------- parser

def _agent_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--run", required=True, help="run journal (.harness/runs/<skill>-<timestamp>.jsonl)")
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
        if name == "decide":
            q.add_argument("--ambiguous", action="store_true",
                           help="AR-02: the scout proposal is ambiguous (phase2_auto gates)")
            q.add_argument("--verdict", default=None, help="scout verdict file, named in the stop message")
    gsub.add_parser("list", help="the gate catalog (core and profiles)").set_defaults(func=cmd_gate_list)
    q.add_argument("--answer", default=None, help="option chosen by the user")
    q.add_argument("--answer-file", default=None, help="free answer, file written by Write (consumed)")
    q.add_argument("--headless", action="store_true", help="AskUserQuestion unavailable: headless fallback (GT-06)")
    q.add_argument("--default", action="store_true", help="applies the default (decision default)")
    p = sub.add_parser("finding", help="finding schema (FD-01 to FD-11)")
    fdsub = p.add_subparsers(dest="fdcmd", required=True)
    q = fdsub.add_parser("validate", help="validates a finding file (FD-03, FD-04); exit 1 if not conforming")
    q.add_argument("path")
    q.set_defaults(func=cmd_finding_validate)
    q = fdsub.add_parser("adapt", help="agent output block -> FD-01 findings (FD-05)")
    q.add_argument("--format", required=True, choices=findings.FORMATS)
    q.add_argument("--input", required=True, help="JSON file: one finding, a list, or {findings|issues: [...]}")
    q.add_argument("--ids", default=None, help="ids, comma-separated, when the format has none")
    q.add_argument("--axis", default=None, help="axis (theme of a ship-pr reviewer)")
    q.add_argument("--source", default=None, choices=journal.SKILLS)
    q.set_defaults(func=cmd_finding_adapt)
    q = fdsub.add_parser("verdict", help="parses a validator output (FD-06); usable false = dead agent")
    q.add_argument("--source", required=True, choices=sorted(findings.VERDICT_FIELDS))
    q.add_argument("--output", required=True, help="file holding the validator output, '-' = stdin")
    q.set_defaults(func=cmd_finding_verdict)
    q = fdsub.add_parser("apply", help="applies a validator verdict to a finding (FD-07)")
    q.add_argument("--finding", required=True)
    q.add_argument("--verdict", required=True, help="file holding the validator output")
    q.add_argument("--source", required=True, choices=sorted(findings.VERDICT_FIELDS))
    q.set_defaults(func=cmd_finding_apply)
    q = fdsub.add_parser("spec", help="finding -> factory spec, never overwritten (FD-08, FD-11)")
    q.add_argument("--root", default=".")
    q.add_argument("--finding", required=True)
    q.add_argument("--sections", required=True, help="JSON file of the judgment sections, written by Write")
    q.add_argument("--prefix", required=True, help="leg, lab, ...")
    q.add_argument("--number", required=True, type=int)
    q.add_argument("--dest", required=True, help="specs/SPEC-<prefix>-<nn>-<slug>.md")
    q.set_defaults(func=cmd_finding_spec)
    q = fdsub.add_parser("note", help="finding -> rgkb note (FD-09)")
    q.add_argument("--finding", required=True)
    q.set_defaults(func=cmd_finding_note)
    q = fdsub.add_parser("forbidden", help="forbidden strings of rendered deliverables (FD-11); exit 1 if found")
    q.add_argument("paths", nargs="+")
    q.set_defaults(func=cmd_finding_forbidden)
    p = sub.add_parser("registry", help="project registry .claude/findings.jsonl (RG-01 to RG-07)")
    rsub = p.add_subparsers(dest="rgcmd", required=True)
    q = rsub.add_parser("publish", help="publishes the run registry to the project (RG-03)")
    q.add_argument("--run", required=True)
    q.add_argument("--source", default=None, choices=journal.SKILLS, help="default: the skill of the run")
    q.add_argument("--deliverable", action="store_true", help="the deliverable holding the CONFIRMED is written")
    q.set_defaults(func=cmd_registry_publish)
    q = rsub.add_parser("check", help="what a run does with new findings (RG-04)")
    q.add_argument("--root", default=".")
    q.add_argument("--file", required=True, help="FD-01 findings file")
    q.set_defaults(func=cmd_registry_check)
    p = sub.add_parser("stack", help="stack detection and bounds (ST-01 to ST-05)")
    stsub = p.add_subparsers(dest="stcmd", required=True)
    q = stsub.add_parser("detect", help="markers, manifests, core stacks, artifact folders, file count")
    q.add_argument("--root", default=".")
    q.set_defaults(func=cmd_stack_detect)
    q = stsub.add_parser("journal", help="sampling of a long journal (ST-05)")
    q.add_argument("--file", required=True)
    q.set_defaults(func=cmd_stack_journal)
    p = sub.add_parser("tshirt", help="orderings, quick wins, spec mapping, load (TS-01 to TS-05)")
    p.add_argument("--file", required=True, help="FD-01 findings file")
    p.add_argument("--order", required=True, choices=tshirt.ORDERS)
    p.add_argument("--grouping", default=None, choices=tshirt.GROUPINGS, help="finding -> spec mapping (TS-02)")
    p.add_argument("--load-by", default=None, help="key of the load groups (milestone, ...)")
    p.add_argument("--cap", type=int, default=None, help="ceiling: first N specs (or findings) kept, excess listed")
    p.set_defaults(func=cmd_tshirt)
    p = sub.add_parser("audit", help="shared audit engine (AU-01 to AU-16)")
    asub = p.add_subparsers(dest="aucmd", required=True)
    q = asub.add_parser("start", help="arguments, git probe, resume; opens the run in the audited repository")
    q.add_argument("--skill", required=True, choices=sorted(audit.PROFILES))
    q.add_argument("--root", default=".", help="current directory of the session (REPO is relative to it)")
    q.add_argument("--only", default=None, help="l;l: keeps these lenses only (AD-03)")
    q.add_argument("--unified", action="store_true", help="/audit: resume from AUDIT.md and the previous deliverables (MG-01)")
    q.add_argument("--arguments-file", default=None, help="file holding $ARGUMENTS, written by Write (consumed)")
    q.set_defaults(func=cmd_audit_start)
    q = asub.add_parser("auditor", help="return of a lens or family auditor (AU-04, AU-06)")
    _agent_args(q)
    q.add_argument("--unit", required=True, help="lens or family of the auditor")
    q.set_defaults(func=cmd_audit_auditor)
    q = asub.add_parser("validator", help="return of a validator (AU-05)")
    _agent_args(q)
    q.add_argument("--finding", required=True)
    q.set_defaults(func=cmd_audit_validator)
    for name, func in (("next", cmd_audit_next), ("consolidate", cmd_audit_consolidate),
                       ("readjust", cmd_audit_readjust)):
        q = asub.add_parser(name)
        q.add_argument("--run", required=True)
        q.set_defaults(func=func)
    q = asub.add_parser("plan", help="with --run: ceiling, spec mapping, load and quick wins (LA-10); without: "
                                     "lens selection, waves and caps of /audit (AD-03, AD-04, AD-09)")
    q.add_argument("--run", default=None)
    q.add_argument("--data-file", default=None, help="the render data of the skill (not consumed)")
    q.add_argument("--root", default=".")
    q.add_argument("--profile", default=None, help="p[;p]: forces the active profiles")
    q.add_argument("--lenses", default=None)
    q.add_argument("--max-specs", default=None)
    q.add_argument("--max-findings", default=None)
    q.add_argument("--max-questions", default=None)
    q.add_argument("--via", default=None, help="alias that invoked the audit (journaled)")
    q.set_defaults(func=cmd_audit_plan)
    q = asub.add_parser("open", help="opens the audit-<timestamp> journal of /audit, journals --via (AD-12)")
    q.add_argument("--root", default=".")
    q.add_argument("--via", default=None)
    q.set_defaults(func=cmd_audit_open)
    q = asub.add_parser("assemble", help="writes AUDIT.md from the rendered set blocks (SO-01, MG-02)")
    q.add_argument("--root", default=".", help="the audited repository")
    q.add_argument("--set-run", action="append", required=True, help="run of a lens set, in the order of the stamp")
    q.add_argument("--profiles", required=True, help="p;p")
    q.add_argument("--lenses", required=True, help="l;l")
    q.add_argument("--date", default=None)
    q.add_argument("--sampled", action="store_true")
    q.set_defaults(func=cmd_audit_assemble)
    q = asub.add_parser("alias-args", help="arguments of an old audit skill -> arguments of /audit (AX-05)")
    q.add_argument("--skill", required=True, choices=sorted(aliases.ALIASES))
    q.add_argument("--root", default=".")
    q.add_argument("--arguments-file", default=None, help="file holding $ARGUMENTS, written by Write (consumed)")
    q.set_defaults(func=cmd_audit_alias_args)
    q = asub.add_parser("settle", help="TRANCHEE (journal <date>) when the entry is later than the audit (AA-10)")
    q.add_argument("--audit-date", required=True)
    q.add_argument("--entry-date", required=True)
    q.set_defaults(func=cmd_audit_settle)
    q = asub.add_parser("themes", help="gate calls for N themes (AU-16)")
    q.add_argument("--skill", required=True, choices=sorted(audit.PROFILES))
    q.add_argument("--count", required=True, type=int)
    q.set_defaults(func=cmd_audit_themes)
    q = asub.add_parser("render", help="writes the deliverable from the run and the skill's data (AU-11)")
    q.add_argument("--run", required=True)
    q.add_argument("--data-file", required=True, help="JSON file of the skill's choices, written by Write (consumed)")
    q.set_defaults(func=cmd_audit_render)
    q = asub.add_parser("spec", help="spec of a CONFIRMED finding, never overwritten (AU-14)")
    q.add_argument("--run", required=True)
    q.add_argument("--finding", required=True)
    q.add_argument("--sections", required=True, help="JSON file of the judgment sections, written by Write")
    q.add_argument("--number", required=True, type=int)
    q.add_argument("--slug", required=True)
    q.set_defaults(func=cmd_audit_spec)
    q = asub.add_parser("publish", help="publishes the run registry to the project (RG-03, AU-12)")
    q.add_argument("--run", required=True)
    q.add_argument("--deliverable", action="store_true", help="the deliverable holding the CONFIRMED is written")
    q.set_defaults(func=cmd_audit_publish)
    p = sub.add_parser("profile", help="profiles: data folders (PF-01 to PF-05)")
    prsub = p.add_subparsers(dest="prcmd", required=True)
    q = prsub.add_parser("validate", help="exit 0 if conforming, 2 with the list of errors (PF-03)")
    q.add_argument("path")
    q.set_defaults(func=cmd_profile_validate)
    q = prsub.add_parser("list", help="profiles, lenses and roles (PF-04)")
    q.add_argument("--profiles-dir", default=None)
    q.set_defaults(func=cmd_profile_list)
    q = prsub.add_parser("show", help="roles and fragments of a profile, for the generation (EP-04)")
    q.add_argument("name")
    q.add_argument("--profiles-dir", default=None)
    q.set_defaults(func=cmd_profile_show)
    p = sub.add_parser("stamp", help="profile stamp of .claude/harness.json (HJ-01 to HJ-05); no removal")
    stsub2 = p.add_subparsers(dest="stampcmd", required=True)
    q = stsub2.add_parser("add")
    q.add_argument("--root", default=".")
    q.add_argument("--profiles", required=True, help="p[;p]")
    q.add_argument("--by", required=True, choices=stamp.BY_VALUES)
    q.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    q.set_defaults(func=cmd_stamp_add)
    q = stsub2.add_parser("resolve", help="{source, profiles}: stamp, inferred or none (HJ-04)")
    q.add_argument("--root", default=".")
    q.set_defaults(func=cmd_stamp_resolve)
    q = stsub2.add_parser("compare", help="added / kept / vanished against a scout verdict (EP-03)")
    q.add_argument("--root", default=".")
    q.add_argument("--verdict", required=True)
    q.set_defaults(func=cmd_stamp_compare)
    p = sub.add_parser("scout", help="profile scout (SC-01 to SC-08)")
    scsub = p.add_subparsers(dest="sccmd", required=True)
    q = scsub.add_parser("signals", help="deterministic signals of every profile and the judgement criteria")
    q.add_argument("--root", default=".")
    q.set_defaults(func=cmd_scout_signals)
    q = scsub.add_parser("verdict", help="verifies the proofs, scores and ranks the profiles (SC-05)")
    q.add_argument("--root", default=".")
    q.add_argument("--signals", default=None, help="the agent's JSON block, written by Write (consumed)")
    q.add_argument("--scout-failed", action="store_true", help="the agent died twice (SC-06)")
    q.add_argument("--run", default=None)
    q.add_argument("--skill", default="software-factory", choices=("software-factory", "audit"))
    q.add_argument("--models", default=None)
    q.add_argument("--duration-ms", default=None)
    q.add_argument("--tokens", default=None)
    q.set_defaults(func=cmd_scout_verdict)
    p = sub.add_parser("block", help="delimited blocks (D9, BK-01)")
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
    q.add_argument("--profiles", default=None, help="p[;p]: union of the profiles' deny rules, tasks, .gitignore (HJ-06)")
    q.add_argument("--test-command", default=None, help="with --profiles: test task of the profiles that have one")
    q.add_argument("--test-windows", default=None)
    q.set_defaults(func=cmd_sf_apply)
    q = ssub.add_parser("install", help="writes a generated file without overwriting (SF-04)")
    q.add_argument("--root", default=".")
    q.add_argument("--dest", required=True)
    q.add_argument("--source", required=True,
                   help="content file, '-' = stdin; removed once read when it lies under .harness/runs/")
    q.add_argument("--model-role", default=None, choices=models.ROLES,
                   help="generated agent: its role's model written in a frontmatter block (X1)")
    q.set_defaults(func=cmd_sf_install)
    q = ssub.add_parser("args", help="entry point arguments: --profile, --rescan, first need (EP-01)")
    q.add_argument("--root", default=".")
    q.add_argument("--arguments-file", default=None, help="file holding $ARGUMENTS, written by Write (consumed)")
    q.set_defaults(func=cmd_sf_args)
    q = ssub.add_parser("copy-core", help="copies the core under .claude/harness/ (D1); exit 1 if blocked")
    q.add_argument("--root", default=".")
    mode = q.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="strict comparison with this core; exit 1 if it differs")
    mode.add_argument("--refresh", action="store_true",
                      help="replaces a recognized core copy, never touching a file that is not a core file")
    q.add_argument("--force", action="store_true", help="with --refresh: replaces a copy declaring a newer CORE_VERSION")
    q.set_defaults(func=cmd_sf_copy_core)

    p = sub.add_parser("factory-run", help="factory-run orchestration (FR-01 to FR-04)")
    fsub = p.add_subparsers(dest="frcmd", required=True)
    q = fsub.add_parser("start")
    q.add_argument("--root", default=".")
    q.add_argument("--profile", default=None, help="forces the profile of this cycle (LP-05)")
    q.add_argument("--orchestrator", default="factory-run",
                   choices=sorted({p["orchestrator"]["name"] for p in profiles.discover().values()}),
                   help="instance of the orchestrator template (LP-06)")
    q.add_argument("--arguments-file", default=None,
                   help="file holding $ARGUMENTS, written by the Write tool (never through the shell)")
    q.set_defaults(func=cmd_fr_start)
    q = fsub.add_parser("record")
    _agent_args(q)
    q.add_argument("--agent", required=True, help="an agent of the run's profile")
    q.add_argument("--mode", default=None, help="director mode of a loop with consultation (cadrage|interpretation)")
    q.set_defaults(func=cmd_fr_record)

    p = sub.add_parser("cx", help="code-index rules (CX-01 to CX-16)")
    csub = p.add_subparsers(dest="cxcmd", required=True)
    q = csub.add_parser("args", help="--reindex, --no-wire; the rest handed back (CX-01)")
    q.add_argument("--root", default=".")
    q.add_argument("--arguments-file", default=None, help="file holding $ARGUMENTS, written by Write (consumed)")
    q.set_defaults(func=cmd_cx_args)
    csub.add_parser("rg", help="ripgrep probe and install command (CX-02)").set_defaults(func=cmd_cx_rg)
    q = csub.add_parser("survey", help="repository state (CX-04)")
    q.add_argument("--root", default=".")
    q.set_defaults(func=cmd_cx_survey)
    q = csub.add_parser("install", help="copies rgkb.py (CX-05)")
    q.add_argument("--root", default=".")
    q.add_argument("--asset", required=True, help="assets/rgkb.py of the skill")
    q.set_defaults(func=cmd_cx_install)
    q = csub.add_parser("register", help=".mcp.json, settings.json, tasks.json (CX-06, CX-07, CX-15)")
    q.add_argument("--root", default=".")
    q.add_argument("--interp", required=True, help="interpreter command, e.g. 'py -3'")
    q.set_defaults(func=cmd_cx_register)
    q = csub.add_parser("scope", help="config.json exclusions and .gitignore counter-rule (CX-08, CX-10)")
    q.add_argument("--root", default=".")
    q.set_defaults(func=cmd_cx_scope)
    q = csub.add_parser("wire", help="blocks, tools and CI allow lists (CX-12 to CX-14)")
    q.add_argument("--root", default=".")
    q.add_argument("--interp", required=True)
    q.add_argument("--blocks-file", required=True, help="JSON {target: block text}, written by Write (consumed)")
    q.set_defaults(func=cmd_cx_wire)

    p = sub.add_parser("lab", help="ai-lab installation rules (AL-01 to AL-09)")
    lsub = p.add_subparsers(dest="labcmd", required=True)
    q = lsub.add_parser("apply", help="settings.json deny rules, tasks.json, .gitignore (AL-01 to AL-03)")
    q.add_argument("--root", default=".")
    q.add_argument("--test-command", default=None, help="detected test command (task 'Lab: tests unitaires')")
    q.add_argument("--test-windows", default=None, help="its windows variant when different")
    q.set_defaults(func=cmd_lab_apply)
    q = lsub.add_parser("ci", help="ci/lab.sh and ci/lab.ps1 (AL-07)")
    q.add_argument("--root", default=".")
    q.add_argument("--allow", action="append", help="allow-list entry added to the base list (repeatable)")
    q.set_defaults(func=cmd_lab_ci)

    p = sub.add_parser("lab-run", help="lab-run orchestration (LR-01 to LR-09)")
    lrsub = p.add_subparsers(dest="lrcmd", required=True)
    q = lrsub.add_parser("start")
    q.add_argument("--root", default=".")
    q.add_argument("--arguments-file", default=None, help="file holding $ARGUMENTS, written by Write (consumed)")
    q.set_defaults(func=cmd_lr_start)
    q = lrsub.add_parser("record")
    _agent_args(q)
    q.add_argument("--agent", required=True, choices=labrun.AGENTS)
    q.add_argument("--mode", default=None, choices=labrun.MODES, help="Director only")
    q.set_defaults(func=cmd_lr_record)

    p = sub.add_parser("bs", help="brainstorm rules (BS-01 to BS-12); state on stdin, nothing written before 'finish'")
    bsub = p.add_subparsers(dest="bscmd", required=True)
    q = bsub.add_parser("args")
    q.add_argument("--arguments", default="-", help="'-' = $ARGUMENTS on stdin")
    q.set_defaults(func=cmd_bs_args)
    q = bsub.add_parser("resume")
    q.add_argument("--root", default=".")
    q.add_argument("--path", required=True)
    q.set_defaults(func=cmd_bs_resume)
    q = bsub.add_parser("round")
    q.add_argument("--data", default="-")
    q.set_defaults(func=cmd_bs_round)
    for name, func in (("render", cmd_bs_render), ("finish", cmd_bs_finish)):
        q = bsub.add_parser(name)
        q.add_argument("--root", default=".")
        q.add_argument("--data", default="-")
        q.set_defaults(func=func)

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
    except (ghflow.Stop, runs.LockTimeout, gates.GateStop, audit.AuditStop) as exc:
        sys.stderr.write("STOP: %s\n" % exc)
        return 1
    except (Usage, ValueError, factory.RunOver, labrun.RunOver, shippr.LoopError, fusion.FusionError,
            blocks.BlockError, FileNotFoundError, KeyError) as exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
