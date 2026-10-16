# Machine d'etat de factory-run (gabarit genere par software-factory).
#
# - FR-01 : entree sur une spec existante sous specs/ dont la ligne de statut
#   vaut exactement "Statut : APPROUVEE" -> phase Build ; sinon phase Plan.
# - FR-02 : succes si et seulement si verdict == APPROVED et tests_passed vrai.
# - FR-03 : 3 iterations au plus ; apres la 3e iteration non approuvee, echec
#   explicite avec les issues restantes. Jamais d'approbation par epuisement.
# - FR-04 : agent mort ou sortie inexploitable -> une relance sans consommer
#   d'iteration, puis echec explicite.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import counters, relaunch, verdicts

PLANNER = "factory-planner"
BUILDER = "factory-builder"
VERIFIER = "factory-verifier"
AGENTS = (PLANNER, BUILDER, VERIFIER)
APPROVED_LINE = "Statut : APPROUVEE"


class RunOver(RuntimeError):
    """Appel apres la fin du cycle (succes ou echec deja rendu)."""


def entry(arguments: str, root: Path) -> Dict[str, Any]:
    """FR-01 : choisit la phase d'entree a partir de $ARGUMENTS."""
    candidate = (arguments or "").strip().strip("'\"")
    if candidate:
        try:
            path = Path(candidate)
            full = path if path.is_absolute() else Path(root) / path
            rel = full.resolve().relative_to(Path(root).resolve())
            is_spec = full.is_file() and rel.parts[:1] == ("specs",)
        except (OSError, ValueError):
            # Texte libre (besoin) qui n'est pas un chemin valide : phase Plan.
            is_spec = False
        if is_spec:
            status = None
            for line in full.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("Statut"):
                    status = line.strip()
                    break
            if status == APPROVED_LINE:
                return {"mode": "build", "spec": rel.as_posix()}
    return {"mode": "plan", "spec": None}


def new_state() -> Dict[str, Any]:
    return {
        "iteration": 1,
        "max_iterations": counters.MAX_ITERATIONS,
        "failures": {},
        "status": "running",
        "issues": [],
        "expect": BUILDER,
    }


def record(state: Dict[str, Any], agent: str, output: Optional[str], dead: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Applique le retour d'un agent. Rend (decision, champs du journal)."""
    if state["status"] != "running":
        raise RunOver("cycle deja termine : %s" % state["status"])
    if agent not in AGENTS:
        raise ValueError("agent inconnu : %r" % (agent,))
    if agent == PLANNER and (state["iteration"] != 1 or state["expect"] != BUILDER):
        raise ValueError("le Planner n'intervient qu'avant la phase Build")
    if agent != PLANNER and agent != state["expect"]:
        raise ValueError("appel hors sequence : attendu %s, recu %s" % (state["expect"], agent))
    iteration = 0 if agent == PLANNER else state["iteration"]
    parsed = None
    reason = "agent mort" if dead else None
    if not dead and agent == VERIFIER:
        try:
            parsed = verdicts.parse_verifier(output)
        except verdicts.UnusableOutput as exc:
            dead, reason = True, "sortie inexploitable : %s" % exc
    log = {"iteration": iteration, "verdict": "DEAD", "produced": 0}
    if dead:
        failures = state["failures"].get(agent, 0)
        decision = relaunch.on_dead(failures)
        state["failures"][agent] = failures + 1
        if decision == relaunch.RELAUNCH:
            return {"action": "relaunch", "agent": agent, "iteration": iteration, "reason": reason}, log
        state["status"] = "failed"
        return {
            "action": "fail",
            "agent": agent,
            "iteration": iteration,
            "reason": "%s mort deux fois (%s) : echec explicite, aucun verdict" % (agent, reason),
            "issues": state["issues"],
        }, log
    state["failures"][agent] = 0
    if agent == PLANNER:
        log["verdict"] = "DONE"
        return {"action": "plan-done", "iteration": 0}, log
    if agent == BUILDER:
        log["verdict"] = "DONE"
        state["expect"] = VERIFIER
        return {"action": "verify", "iteration": iteration}, log
    assert parsed is not None
    log["verdict"] = parsed["verdict"]
    log["produced"] = len(parsed["issues"])
    state["issues"] = parsed["issues"]
    if parsed["verdict"] == "APPROVED" and parsed["tests_passed"] is True:
        state["status"] = "success"
        return {"action": "success", "iteration": iteration, "tests_passed": True}, log
    if counters.cap_reached(iteration, state["max_iterations"]):
        state["status"] = "failed"
        return {
            "action": "fail",
            "iteration": iteration,
            "reason": "%d iterations sans approbation : echec explicite" % iteration,
            "issues": parsed["issues"],
        }, log
    state["iteration"] = iteration + 1
    state["expect"] = BUILDER
    return {
        "action": "fix",
        "iteration": iteration + 1,
        "tests_passed": parsed["tests_passed"],
        "issues": parsed["issues"],
    }, log
