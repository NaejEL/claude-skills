# Human gates (AskUserQuestion points) of the skills: policy, decision,
# headless fallback, journal events.
#
# - GT-01: the policy is read from .claude/harness.json, key "autonomy" in
#   {gate, auto}. Missing file or key -> gate. Invalid value or unreadable
#   JSON -> usage error (exit 2).
# - GT-02: decision table. gate: ask for kinds a, b and c. auto: default for
#   b and c, ask for a.
# - GT-03: Phase 1 guard. "auto" is applied as "gate", with a logged warning
#   (no partial autonomy without BLOQUEE nor STOP files, Phase 4).
# - GT-04: a dialogue gate (brainstorm.*) always returns ask.
# - GT-05: a gate without a default whose decision would be "default" ->
#   stop (exit 1, message).
# - GT-06: every gate declares a headless fallback (stop | default | skip),
#   returned with the decision; the skill applies it when AskUserQuestion is
#   unavailable and declares it as such (answer source "headless").
# - GT-07: two "gate" events are logged, the decision then the answer: id,
#   kind, policy, decision, default, answer, source in user|default|headless.
# - GT-08: single catalog (core gates, plus the gates the profiles declare: PF-05);
#   an unknown id -> exit 2.
# - AR-02: the gates marked phase2_auto apply `auto` from Phase 2 on: a clear
#   proposal takes the default, an ambiguous one stops (GT-05); every other gate
#   keeps the GT-03 guard.
# - Closed options: a user answer to a gate with closed options must be one of
#   its options. A gate asking several questions in one call ("questions",
#   separated by " ; " in the catalog) takes exactly one valid option per
#   question, in order, joined by " / "; a gate asking the same question for
#   each of up to `repeat` themes takes 1 to `repeat` options of that list.
#   Any other answer (a free "Other" text, typically) is not an error: the
#   CLI returns action "reask" and logs nothing, the skill asks again. The
#   gates declared "free" (free input, options of a draft) keep a free answer.
#
# Options are quoted as written in the French SKILL.md files (shared format,
# kept as is); rationales are one line each.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from . import profiles

POLICY_FILE = Path(".claude") / "harness.json"
POLICY_KEY = "autonomy"
POLICIES = ("gate", "auto")
KINDS = ("a", "b", "c")
ASK, DEFAULT, STOP = "ask", "default", "stop"
DECISIONS = (ASK, DEFAULT, STOP)
SKIP = "skip"
HEADLESS = (STOP, DEFAULT, SKIP)
SOURCES = ("user", "default", "headless")
PHASES = ("decision", "answer")
# GT-03: Phase 4 (BLOQUEE state, STOP-*.md files) is not delivered yet.
AUTO_APPLIED_AS_GATE = True
AUTO_WARNING = ("autonomy 'auto' read from .claude/harness.json is applied as 'gate' "
                "until Phase 4 is delivered")


class GateError(ValueError):
    """Unknown gate, invalid policy or out-of-sequence answer (exit 2)."""


class OffOptions(GateError):
    """User answer outside the closed options of a gate: ask again (never a stop)."""


class GateStop(RuntimeError):
    """Explicit stop decided by a gate (exit 1)."""


class Gate(NamedTuple):
    id: str
    source: str
    kind: str
    options: Tuple[str, ...]
    default: Optional[str]
    rationale: str
    headless: str
    dialogue: bool = False
    free: bool = False
    questions: Tuple[Tuple[str, ...], ...] = ()
    repeat: int = 1
    phase2_auto: bool = False

    @property
    def skill(self) -> str:
        return self.id.split(".", 1)[0]

    @property
    def multi(self) -> bool:
        return len(self.questions) > 1 or self.repeat > 1


def _g(gid: str, source: str, kind: str, options: str, default: Optional[str], rationale: str,
       headless: str, dialogue: bool = False, free: bool = False, repeat: int = 1,
       phase2_auto: bool = False) -> Gate:
    questions = tuple(tuple(o.strip() for o in q.split(" / ")) for q in options.split(" ; "))
    flat = tuple(o for q in questions for o in q)
    return Gate(gid, source, kind, flat, default, rationale, headless, dialogue, free, questions, repeat,
                phase2_auto)


CATALOG: Dict[str, Gate] = {g.id: g for g in (
    _g("software-factory.code-index", "software-factory:92", "b", "installer / refus", "refus",
       "the knowledge base adds a versioned folder: that is decided, never assumed", SKIP),
    _g("factory-run.questions", "software-factory:54", "b", "options du brouillon", None,
       "headless keeps the planner's defaults; only a blocking question stops", SKIP, free=True),
    _g("factory-run.approval", "software-factory:54", "c", "approbation / itérer", "approbation",
       "roadmap 4.2: approved unless a blocking question remains", DEFAULT),
    _g("factory-run.need", ".claude/skills/factory-run/SKILL.md:16", "c", "saisie libre", None,
       "a need cannot be guessed", STOP, free=True),
    _g("ship-pr.target", "ship-pr:29", "c", "saisie", None,
       "the target branch cannot be guessed", STOP, free=True),
    _g("ship-pr.dirty", "ship-pr:46", "a", "commiter maintenant / stash / abandonner", "abandonner",
       "the only option that writes nothing", DEFAULT),
    _g("ship-pr.conflict", "ship-pr:53", "b",
       "résoudre maintenant / continuer la revue quand même / abandonner", "continuer la revue quand même",
       "non destructive, the merge keeps its own gate", DEFAULT),
    _g("ship-pr.merge", "ship-pr:98", "a", "Merger / Laisser la PR ouverte", "Laisser la PR ouverte",
       "a merge is irreversible", DEFAULT),
    _g("code-index.rg-install", "code-index:38", "c", "commande retenue / repli local", "repli local",
       "a system dependency is not installed unasked; local fallback reported", SKIP),
    _g("code-index.hooks", "code-index:113", "b", "hooks install / --with-commit / refus", "hooks install",
       "the default stated by code-index:113", SKIP),
    _g("ai-lab.models", "ai-lab:137-142", "b", "Tout hérité / experts / interprétation / Sur-mesure",
       "Tout hérité", "no extra cost", DEFAULT),
    _g("ai-lab.code-index", "ai-lab:225", "b", "installer / refus", "refus",
       "the knowledge base adds a versioned folder", SKIP),
    _g("lab-run.pi-questions", "ai-lab:180", "b", "Questions pour le PI", None,
       "nothing to invent in the PI's place", STOP, free=True),
    _g("lab-run.preregistration", "ai-lab:180", "a", "approbation / itérer", None,
       "no measurement without an approved protocol", STOP),
    _g("lab-run.consignation", "ai-lab:188", "c", "approbation", "approbation",
       "logged, marked 'to be reviewed' (ai-lab:188)", DEFAULT),
    _g("legacy-audit.framing", "legacy-audit:84", "b",
       "2 / 3 / 4 ; risque d'abord / quick wins / fondations / ordre proposé", "3 / risque d'abord",
       "close to 'make it reliable first' (roadmap 4.2)", STOP),
    _g("legacy-audit.assignment", "legacy-audit:85", "b",
       "Jalon 1 / Jalon 2 / Jalon dernier / Exclure de la roadmap", None,
       "the computation belongs to Phase 4", STOP, repeat=4),
    _g("legacy-audit.final", "legacy-audit:87", "c", "Générer roadmap + specs / Réajuster / Abandonner",
       "Générer roadmap + specs", "the deliverable the audit was run for", STOP),
    _g("ai-lab-audit.framing", "ai-lab-audit:92", "b",
       "specs / lister / ignorer les mineures ; fiabiliser / moins cher / feuille de route / ordre proposé",
       "specs / fiabiliser", "specs when a factory is present, otherwise lister; make it reliable first",
       STOP),
    _g("ai-lab-audit.selection", "ai-lab-audit:93", "b", "Toutes / Seulement la mieux classée / Aucune",
       "Toutes", "the cap applies afterwards", STOP, repeat=4),
    _g("ai-lab-audit.final", "ai-lab-audit:95", "c", "Écrire AUDIT-lab.md / Réajuster / Abandonner",
       "Écrire AUDIT-lab.md", "the deliverable the audit was run for", STOP),
    _g("vibecode-audit.drop-security", "vibecode-audit:20", "b", "confirmer le retrait / garder", "garder",
       "security is the priority axis", DEFAULT),
    _g("vibecode-audit.order", "vibecode-audit:115-116", "b",
       "Gravité d'abord / Gains rapides / Tout ce qui bloque / Garder l'ordre ; Les détailler / "
       "Les lister en une ligne / Les omettre", "Gravité d'abord / Les détailler",
       "marked default at :115; detailing loses nothing", DEFAULT),
    _g("vibecode-audit.final", "vibecode-audit:120", "c", "Écrire AUDIT-vibecode.md / Réajuster / Abandonner",
       "Écrire AUDIT-vibecode.md", "the deliverable the audit was run for", DEFAULT),
    # Phase 2: profiles, entry point and unified audit (AR-01, LP-05, AD-08).
    _g("software-factory.profiles", "SPEC-phase2 AR-01", "b", "profils proposés / Abandonner", "proposition",
       "a clear scout proposal is taken; an ambiguous one is never guessed", DEFAULT, free=True,
       phase2_auto=True),
    _g("factory-run.profile", "SPEC-phase2 LP-05", "b", "profil du besoin", "premier profil du tampon",
       "the first profile of the stamp is the first one retained at installation", STOP, free=True),
    _g("audit.profiles", "SPEC-phase2 AD-02", "b", "profils proposés / Abandonner", "proposition",
       "read-only scout verdict, used for this audit and never written to the stamp", DEFAULT, free=True,
       phase2_auto=True),
    _g("audit.drop-security", "SPEC-phase2 AD-08", "b", "confirmer le retrait / garder", "garder",
       "security is the priority axis", DEFAULT),
    _g("audit.final", "SPEC-phase2 AD-08", "c", "Écrire AUDIT.md (+ specs) / Réajuster / Abandonner",
       "Écrire AUDIT.md (+ specs)", "the deliverable the audit was run for", STOP),
    _g("brainstorm.subject", "brainstorm:16", "c", "saisie libre", None,
       "a subject cannot be guessed", STOP, dialogue=True, free=True),
    _g("brainstorm.round", "brainstorm:67", "b", "Creuser / Écarter / Amender / continuer / converger", None,
       "the user steers every round", STOP, dialogue=True, free=True),
    _g("brainstorm.write", "brainstorm:103", "c", "Écrire la synthèse / Ne rien écrire", "Ne rien écrire",
       "nothing is written unasked", STOP, dialogue=True),
)}


def profile_gates(profiles_dir=None) -> Dict[str, Gate]:
    """PF-05: the gates declared by the profiles (same fields as the core ones)."""
    found: Dict[str, Gate] = {}
    for prof in profiles.discover(profiles_dir).values():
        for g in prof.get("gates", []):
            found[g["id"]] = _g(g["id"], g.get("source", prof["name"]), g["kind"], g["options"],
                                 g.get("default"), g.get("rationale", ""), g["headless"],
                                 bool(g.get("dialogue")), bool(g.get("free")), int(g.get("repeat", 1)),
                                 bool(g.get("phase2_auto")))
    return found


def all_gates(profiles_dir=None) -> Dict[str, Gate]:
    merged = dict(profile_gates(profiles_dir))
    merged.update(CATALOG)
    return merged


def get(gate_id: str) -> Gate:
    """GT-08: catalog lookup; an unknown id is a usage error."""
    gate = CATALOG.get(gate_id) or profile_gates().get(gate_id)
    if gate is None:
        raise GateError("unknown gate: %r (see the GT-08 catalog in hcore/gates.py)" % (gate_id,))
    return gate


def read_policy(root: Path) -> str:
    """GT-01: autonomy policy of the project (missing file or key -> gate)."""
    path = Path(root) / POLICY_FILE
    if not path.exists():
        return "gate"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise GateError("%s is not readable JSON: %s" % (POLICY_FILE.as_posix(), exc))
    if not isinstance(data, dict):
        raise GateError("%s must contain a JSON object" % POLICY_FILE.as_posix())
    value = data.get(POLICY_KEY, "gate")
    if value not in POLICIES:
        raise GateError("%s: %s must be one of %s, got %r"
                        % (POLICY_FILE.as_posix(), POLICY_KEY, ", ".join(POLICIES), value))
    return value


def decision(kind: str, policy: str) -> str:
    """GT-02: decision table, before the Phase 1 guard."""
    if kind not in KINDS:
        raise GateError("unknown gate kind: %r" % (kind,))
    if policy not in POLICIES:
        raise GateError("unknown policy: %r" % (policy,))
    if policy == "auto" and kind in ("b", "c"):
        return DEFAULT
    return ASK


def decide(gate_id: str, policy: str, auto_as_gate: bool = AUTO_APPLIED_AS_GATE,
           ambiguous: bool = False) -> Dict[str, Any]:
    """Decision for a gate under a policy: GT-02 to GT-06. Returns the
    'decision' journal event, plus the options and the headless fallback."""
    gate = get(gate_id)
    warnings: List[str] = []
    applied = policy
    if policy == "auto" and auto_as_gate and not gate.phase2_auto:
        applied = "gate"
        warnings.append(AUTO_WARNING)
    choice = ASK if gate.dialogue else decision(gate.kind, applied)
    if choice == DEFAULT and (gate.default is None or (ambiguous and gate.phase2_auto)):
        choice = STOP
    event: Dict[str, Any] = {
        "event": "gate", "phase": "decision", "id": gate.id, "kind": gate.kind, "policy": applied,
        "decision": choice, "default": gate.default, "answer": None, "source": None,
        "headless": gate.headless,
    }
    if ambiguous and gate.phase2_auto:
        event["ambiguous"] = True
    if warnings:
        event["warning"] = "; ".join(warnings)
    return event


def stop_message(gate: Gate, why: str) -> str:
    return "gate %s: %s: explicit stop" % (gate.id, why)


def check_option(gate: Gate, value: str) -> str:
    """A user answer to a gate with closed options: one option per question,
    in order, joined by " / " (OffOptions otherwise)."""
    if gate.free:
        return value
    parts = [p.strip() for p in value.split(" / ")] if gate.multi else [value]
    if gate.repeat > 1:
        expected = [gate.questions[0]] * len(parts) if 1 <= len(parts) <= gate.repeat else []
    else:
        expected = list(gate.questions) if len(parts) == len(gate.questions) else []
    if not expected or any(p not in options for p, options in zip(parts, expected)):
        shape = " ; ".join(" / ".join(q) for q in gate.questions)
        if gate.repeat > 1:
            shape = "1 to %d of: %s" % (gate.repeat, shape)
        elif len(gate.questions) > 1:
            shape = "one per question, in order, joined by ' / ': " + shape
        raise OffOptions("gate %s: answer %r is not one of the options (%s)" % (gate.id, value, shape))
    return value


def answer(gate_id: str, last_decision: Optional[Dict[str, Any]], source: str,
           text: Optional[str]) -> Dict[str, Any]:
    """'answer' journal event for the last decision of a gate (GT-06, GT-07).
    Raises GateError on an out-of-sequence or inconsistent answer."""
    gate = get(gate_id)
    if last_decision is None:
        raise GateError("gate %s: no pending decision in this run: call 'gate decide' first" % gate.id)
    choice = last_decision["decision"]
    if choice == STOP:
        raise GateError("gate %s: the decision was stop, no answer is expected" % gate.id)
    if source not in SOURCES:
        raise GateError("unknown answer source: %r" % (source,))
    if source == "default":
        if choice != DEFAULT:
            raise GateError("gate %s: decision is %s, a default answer is not allowed" % (gate.id, choice))
        value: Optional[str] = gate.default
    elif choice != ASK:
        raise GateError("gate %s: decision is %s, apply the default (--default)" % (gate.id, choice))
    elif source == "headless":
        # AR-01: an ambiguous proposal is never taken by default, headless or not.
        fallback = STOP if last_decision.get("ambiguous") else gate.headless
        value = {STOP: STOP, SKIP: SKIP, DEFAULT: gate.default}[fallback]
    else:
        value = (text or "").strip()
        if not value:
            raise GateError("gate %s: empty answer" % gate.id)
        check_option(gate, value)
    event = dict(last_decision, phase="answer", answer=value, source=source)
    event.pop("warning", None)
    return event


def applied(gate_id: str, event: Dict[str, Any]) -> str:
    """What the skill applies after an answer: 'answer', 'default', 'skip' or 'stop'."""
    if event["source"] != "headless":
        return "default" if event["source"] == "default" else "answer"
    return STOP if event.get("answer") == STOP else get(gate_id).headless


def validate_event(obj: Dict[str, Any]) -> List[str]:
    """JR-02: schema of a 'gate' journal event (GT-07)."""
    errors: List[str] = []
    for key in ("phase", "id", "kind", "policy", "decision", "default", "answer", "source"):
        if key not in obj:
            errors.append("gate event: missing field: %s" % key)
    if errors:
        return errors
    if not isinstance(obj["id"], str) or not obj["id"].strip():
        errors.append("gate event: id must be a non-empty string")
    checks = (("phase", PHASES), ("kind", KINDS), ("policy", POLICIES), ("decision", DECISIONS))
    for key, allowed in checks:
        if obj[key] not in allowed:
            errors.append("gate event: %s must be one of %s" % (key, "|".join(allowed)))
    if obj["default"] is not None and not isinstance(obj["default"], str):
        errors.append("gate event: default must be a string or null")
    if obj["phase"] == "decision":
        if obj["answer"] is not None or obj["source"] is not None:
            errors.append("gate event: a decision carries neither answer nor source")
    elif obj["phase"] == "answer":
        if obj["source"] not in SOURCES:
            errors.append("gate event: source must be one of %s" % "|".join(SOURCES))
        if not isinstance(obj["answer"], str) or not obj["answer"].strip():
            errors.append("gate event: answer must be a non-empty string")
        if obj["decision"] == STOP:
            errors.append("gate event: a stop decision has no answer")
    return errors


def last_decision(records: List[Dict[str, Any]], gate_id: str) -> Optional[Dict[str, Any]]:
    """Last decision of `gate_id` not followed by its answer, or None."""
    for record in reversed(records):
        if record.get("event") == "gate" and record.get("id") == gate_id:
            return record if record.get("phase") == "decision" else None
    return None
