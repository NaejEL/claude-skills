# Parsing et validation des blocs JSON terminaux rendus par les sous-agents.
#
# - Verifier de factory-run : {"verdict", "tests_passed", "issues"} (FR-02).
# - Relecteur de ship-pr : {"findings": [...]} (SP-03).
# - Validateur de ship-pr : {"verdict", "reason"} (SP-04).
#
# Une sortie sans bloc JSON exploitable leve UnusableOutput : pour
# l'orchestrateur, c'est un agent mort (FR-04, SP-03).

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

SEVERITIES = ("critical", "major", "minor")
VERIFIER_VERDICTS = ("APPROVED", "CHANGES_REQUESTED")
VALIDATOR_VERDICTS = ("CONFIRMED", "REJECTED")


class UnusableOutput(ValueError):
    """Sortie d'agent sans bloc JSON terminal exploitable."""


def extract_terminal_json(text: Optional[str]) -> Dict[str, Any]:
    """Rend le dernier objet JSON qui termine le texte.

    Accepte un bloc nu ou un bloc ```json clos en fin de texte ; tout texte
    apres le bloc rend la sortie inexploitable.
    """
    if text is None:
        raise UnusableOutput("sortie absente")
    body = text.strip()
    if body.endswith("```"):
        body = body[:-3].rstrip()
    if not body.endswith("}"):
        raise UnusableOutput("la sortie ne se termine pas par un bloc JSON")
    decoder = json.JSONDecoder()
    start = body.find("{")
    while start != -1:
        try:
            obj, end = decoder.raw_decode(body, start)
        except ValueError:
            obj, end = None, -1
        if end == len(body) and isinstance(obj, dict):
            return obj
        start = body.find("{", start + 1)
    raise UnusableOutput("aucun bloc JSON terminal decodable")


def _require_str(obj: Dict[str, Any], key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise UnusableOutput("%s : champ '%s' absent ou vide" % (where, key))
    return value


def parse_verifier(text: Optional[str]) -> Dict[str, Any]:
    obj = extract_terminal_json(text)
    verdict = obj.get("verdict")
    if verdict not in VERIFIER_VERDICTS:
        raise UnusableOutput("verdict du Verifier invalide : %r" % (verdict,))
    tests = obj.get("tests_passed")
    if not isinstance(tests, bool):
        raise UnusableOutput("tests_passed doit etre un booleen")
    issues = obj.get("issues", [])
    if not isinstance(issues, list):
        raise UnusableOutput("issues doit etre une liste")
    clean: List[Dict[str, Any]] = []
    for i, issue in enumerate(issues):
        where = "issue %d" % i
        if not isinstance(issue, dict):
            raise UnusableOutput(where + " n'est pas un objet")
        if issue.get("severity") not in SEVERITIES:
            raise UnusableOutput(where + " : severite invalide")
        if not isinstance(issue.get("file", ""), str):
            raise UnusableOutput(where + " : 'file' doit etre une chaine")
        clean.append({
            "file": issue.get("file", ""),
            "severity": issue["severity"],
            "description": _require_str(issue, "description", where),
        })
    return {"verdict": verdict, "tests_passed": tests, "issues": clean}


def parse_reviewer(text: Optional[str]) -> List[Dict[str, Any]]:
    obj = extract_terminal_json(text)
    findings = obj.get("findings")
    if not isinstance(findings, list):
        raise UnusableOutput("le bloc du relecteur doit porter une liste 'findings'")
    clean: List[Dict[str, Any]] = []
    for i, f in enumerate(findings):
        where = "finding %d" % i
        if not isinstance(f, dict):
            raise UnusableOutput(where + " n'est pas un objet")
        line = f.get("line")
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            raise UnusableOutput(where + " : 'line' doit etre un entier >= 1")
        if f.get("severity") not in SEVERITIES:
            raise UnusableOutput(where + " : severite invalide")
        side = f.get("side", "RIGHT")
        if side not in ("RIGHT", "LEFT"):
            raise UnusableOutput(where + " : 'side' invalide")
        clean.append({
            "file": _require_str(f, "file", where),
            "line": line,
            "side": side,
            "severity": f["severity"],
            "title": _require_str(f, "title", where),
            "description": str(f.get("description", "")),
            "fix": str(f.get("fix", "")),
        })
    return clean


def parse_validator(text: Optional[str]) -> Dict[str, str]:
    obj = extract_terminal_json(text)
    verdict = obj.get("verdict")
    if verdict not in VALIDATOR_VERDICTS:
        raise UnusableOutput("verdict du validateur invalide : %r" % (verdict,))
    return {"verdict": verdict, "reason": _require_str(obj, "reason", "validateur")}
