# Boucle de revue de ship-pr : rondes, relecteurs, validateurs, registre.
#
# - SP-01 / SP-02 : bornes --rounds et --themes (voir counters).
# - SP-03 : bloc du relecteur ; sortie inexploitable = agent mort.
# - SP-04 : bloc du validateur.
# - SP-05 : theme mort -> une relance -> theme non couvert -> merge refuse ;
#   pas de sortie anticipee sur son silence.
# - SP-06 : validateur mort (deux fois) -> finding UNVALIDATED, ni poste ni corrige.
# - SP-07 : dedoublonnage contre le registre et les candidats en cours,
#   REJECTED compris, avant tout validateur.
# - SP-08 : sortie de boucle par epuisement (zero CONFIRMED, tous les themes
#   couverts) ou par plafond de rondes. Une ronde sans CONFIRMED dont un theme
#   n'est pas couvert ne sort pas : ronde suivante (ou plafond). La reference
#   du diff de la ronde suivante (SP-15) est HEAD avant le commit de correctif
#   de la ronde, pour que ce commit soit relu.
# - SP-09 : finding confirme non corrige consigne NOT_FIXED avec sa raison.
# - SP-10 : compteurs bruts / confirmes / rejetes / dedoublonnes par ronde.

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import counters, registry as registry_mod, relaunch, verdicts

REVIEWER = "reviewer"
VALIDATOR = "validator"


class LoopError(RuntimeError):
    """Transition refusee : appel hors sequence ou etat incoherent."""


def new_state(target: str, rounds: int, themes: List[str]) -> Dict[str, Any]:
    return {
        "target": target,
        "rounds": rounds,
        "themes": list(themes),
        "round": 1,
        "exit": None,
        "uncovered": [],
        "candidates": {},
        "rounds_data": {"1": _new_round()},
        "prev_round_sha": None,
        "commits": [],
        "pr": None,
    }


def _new_round() -> Dict[str, Any]:
    return {"themes": {}, "failures": {}, "raw": 0, "confirmed": 0, "rejected": 0,
            "duplicates": 0, "unvalidated": 0}


def _round(state: Dict[str, Any]) -> Dict[str, Any]:
    if state["exit"] is not None:
        raise LoopError("boucle de revue deja sortie : %s" % state["exit"])
    return state["rounds_data"][str(state["round"])]


def record_reviewer(state: Dict[str, Any], reg: registry_mod.Registry, theme: str,
                    output: Optional[str], dead: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    rd = _round(state)
    if theme not in state["themes"]:
        raise LoopError("theme inconnu : %r" % (theme,))
    if rd["themes"].get(theme) in ("ok", "uncovered"):
        raise LoopError("le theme %r a deja rendu son resultat pour cette ronde" % theme)
    log = {"iteration": state["round"], "verdict": "DEAD", "produced": 0, "rejected": 0}
    findings: List[Dict[str, Any]] = []
    reason = "agent mort"
    if not dead:
        try:
            findings = verdicts.parse_reviewer(output)
        except verdicts.UnusableOutput as exc:
            dead, reason = True, "sortie inexploitable : %s" % exc
    if dead:
        failures = rd["failures"].get(theme, 0)
        rd["failures"][theme] = failures + 1
        if relaunch.on_dead(failures) == relaunch.RELAUNCH:
            return {"action": "relaunch", "theme": theme, "reason": reason}, log
        rd["themes"][theme] = "uncovered"
        state["uncovered"].append({"round": state["round"], "theme": theme})
        return {"action": "uncovered", "theme": theme,
                "reason": "theme non couvert apres une relance (%s) : merge refuse" % reason}, log
    rd["themes"][theme] = "ok"
    pending = {c["key"] for c in state["candidates"].values()}
    to_validate, duplicates = [], []
    for f in findings:
        key = registry_mod.finding_key(f["file"], f["title"])
        if reg.known(key) or key in pending:
            duplicates.append(dict(f, key=key, previous=reg.current(key) or "PENDING"))
            continue
        pending.add(key)
        fid = "R%d-F%d" % (state["round"], len(state["candidates"]) + 1)
        cand = dict(f, id=fid, key=key, round=state["round"], theme=theme, status="PENDING",
                    vfail=0, comment_id=None, outcome=None, reason=None, commit=None, thread_done=False)
        state["candidates"][fid] = cand
        to_validate.append({k: cand[k] for k in ("id", "file", "line", "side", "severity", "title", "description", "fix")})
    rd["raw"] += len(findings)
    rd["duplicates"] += len(duplicates)
    log.update(verdict="FINDINGS" if findings else "NO_FINDING", produced=len(findings), rejected=len(duplicates))
    return {"action": "validate" if to_validate else "none", "theme": theme,
            "to_validate": to_validate, "duplicates": duplicates}, log


def record_validator(state: Dict[str, Any], reg: registry_mod.Registry, fid: str,
                     output: Optional[str], dead: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    rd = _round(state)
    cand = state["candidates"].get(fid)
    if cand is None or cand["round"] != state["round"]:
        raise LoopError("finding inconnu pour cette ronde : %r" % (fid,))
    if cand["status"] != "PENDING":
        raise LoopError("finding %s deja tranche : %s" % (fid, cand["status"]))
    log = {"iteration": state["round"], "verdict": "DEAD", "validated": 0, "rejected": 0}
    parsed = None
    reason = "agent mort"
    if not dead:
        try:
            parsed = verdicts.parse_validator(output)
        except verdicts.UnusableOutput as exc:
            dead, reason = True, "sortie inexploitable : %s" % exc
    if dead:
        failures = cand["vfail"]
        cand["vfail"] = failures + 1
        if relaunch.on_dead(failures) == relaunch.RELAUNCH:
            return {"action": "relaunch", "finding": fid, "reason": reason}, log
        cand["status"] = "UNVALIDATED"
        rd["unvalidated"] += 1
        reg.add(cand, "UNVALIDATED", round=state["round"], id=fid)
        return {"action": "unvalidated", "finding": fid,
                "reason": "validateur mort deux fois : finding non valide, ni poste ni corrige"}, log
    assert parsed is not None
    cand["status"] = parsed["verdict"]
    cand["reason"] = parsed["reason"]
    reg.add(cand, parsed["verdict"], round=state["round"], id=fid, reason=parsed["reason"])
    if parsed["verdict"] == "CONFIRMED":
        rd["confirmed"] += 1
        log.update(verdict="CONFIRMED", validated=1)
        return {"action": "post", "finding": fid}, log
    rd["rejected"] += 1
    log.update(verdict="REJECTED", rejected=1)
    return {"action": "drop", "finding": fid, "reason": parsed["reason"]}, log


def confirmed_of_round(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c for c in state["candidates"].values()
            if c["round"] == state["round"] and c["status"] == "CONFIRMED"]


def set_outcome(state: Dict[str, Any], reg: registry_mod.Registry, fid: str, fixed: bool,
                reason: Optional[str] = None, commit: Optional[str] = None) -> None:
    """SP-09 : consigne FIXED (avec le commit) ou NOT_FIXED (avec la raison)."""
    cand = state["candidates"].get(fid)
    if cand is None or cand["round"] != state["round"] or cand["status"] != "CONFIRMED":
        raise LoopError("%s n'est pas un finding CONFIRMED de la ronde courante" % fid)
    if cand["outcome"] is not None:
        raise LoopError("%s est deja consigne : %s" % (fid, cand["outcome"]))
    if not fixed and not (reason or "").strip():
        raise LoopError("un finding non corrige exige sa raison : %s" % fid)
    cand["outcome"] = "FIXED" if fixed else "NOT_FIXED"
    cand["commit"] = commit
    cand["reason"] = reason if not fixed else cand["reason"]
    reg.add(cand, cand["outcome"], round=state["round"], id=fid, commit=commit,
            reason=None if fixed else reason)


def mark_pre_fix(state: Dict[str, Any], sha: str) -> None:
    """SP-15 : HEAD juste avant le premier commit de correctif de la ronde."""
    _round(state).setdefault("pre_fix_sha", sha)


def end_round(state: Dict[str, Any], head_sha: Optional[str]) -> Dict[str, Any]:
    """SP-08 : decide de la sortie de boucle a la fin de la ronde courante.

    head_sha (HEAD courant) ne sert de reference que si la ronde n'a commite
    aucun correctif : sinon la reference est le HEAD d'avant ce correctif."""
    rd = _round(state)
    missing = [t for t in state["themes"] if rd["themes"].get(t) not in ("ok", "uncovered")]
    if missing:
        raise LoopError("theme(s) sans bloc exploitable ni relance epuisee : " + ", ".join(missing))
    pending = [c["id"] for c in state["candidates"].values()
               if c["round"] == state["round"] and c["status"] == "PENDING"]
    if pending:
        raise LoopError("finding(s) sans validation : " + ", ".join(pending))
    open_ = [c["id"] for c in confirmed_of_round(state) if c["outcome"] is None]
    if open_:
        raise LoopError("finding(s) CONFIRMED sans correctif ni raison consignee : " + ", ".join(open_))
    uncovered_now = [u["theme"] for u in state["uncovered"] if u["round"] == state["round"]]
    counts = round_counts(rd, state["round"])
    if rd["confirmed"] == 0 and not uncovered_now:
        state["exit"] = "exhaustion"
    elif counters.cap_reached(state["round"], state["rounds"]):
        state["exit"] = "cap"
    if state["exit"] is not None:
        return {"exit": state["exit"], "round": state["round"], "counts": counts,
                "uncovered": state["uncovered"]}
    state["prev_round_sha"] = rd.get("pre_fix_sha") or head_sha
    state["round"] += 1
    state["rounds_data"][str(state["round"])] = _new_round()
    return {"exit": None, "next_round": state["round"], "counts": counts,
            "uncovered": state["uncovered"]}


def round_counts(rd: Dict[str, Any], number: int) -> Dict[str, int]:
    """SP-10 : compteurs d'une ronde."""
    return {"round": number, "raw": rd["raw"], "confirmed": rd["confirmed"],
            "rejected": rd["rejected"], "duplicates": rd["duplicates"],
            "unvalidated": rd["unvalidated"]}


def summary(state: Dict[str, Any]) -> Dict[str, Any]:
    rows = [round_counts(state["rounds_data"][k], int(k))
            for k in sorted(state["rounds_data"], key=int)]
    cands = list(state["candidates"].values())
    return {
        "rounds": rows,
        "exit": state["exit"],
        "uncovered": state["uncovered"],
        "commits": state["commits"],
        "resolved": [c["id"] for c in cands if c["outcome"] == "FIXED" and c["thread_done"]],
        "left_open": [{"id": c["id"], "reason": c["reason"]} for c in cands if c["outcome"] == "NOT_FIXED"],
        "unvalidated": [c["id"] for c in cands if c["status"] == "UNVALIDATED"],
    }


def merge_refusal(state: Dict[str, Any]) -> Optional[str]:
    """SP-05 : raison de refus du merge, ou None si la gate peut etre proposee."""
    if state["exit"] is None:
        return "merge refuse : la boucle de revue n'est pas terminee"
    if state["uncovered"]:
        angles = ", ".join("%s (ronde %d)" % (u["theme"], u["round"]) for u in state["uncovered"])
        return ("merge refuse : theme(s) non couvert(s), angle non relu : %s. "
                "Relancer /ship-pr pour obtenir une revue complete." % angles)
    return None
