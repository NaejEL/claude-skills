# Parsing and validation of the terminal JSON blocks returned by sub-agents.
#
# - factory-run Verifier: {"verdict", "tests_passed", "issues"} (FR-02).
# - ship-pr reviewer: {"findings": [...]} (SP-03).
# - ship-pr validator: {"verdict", "reason"} (SP-04).
#
# An output without a usable JSON block raises UnusableOutput: for the
# orchestrator, it is a dead agent (FR-04, SP-03).

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

SEVERITIES = ("critical", "major", "minor")
VERIFIER_VERDICTS = ("APPROVED", "CHANGES_REQUESTED")
VALIDATOR_VERDICTS = ("CONFIRMED", "REJECTED")


class UnusableOutput(ValueError):
    """Agent output without a usable terminal JSON block."""


def extract_terminal_json(text: Optional[str]) -> Dict[str, Any]:
    """Returns the last JSON object that ends the text.

    Accepts a bare block or a closed ```json block at the end of the text; any
    text after the block makes the output unusable.
    """
    if text is None:
        raise UnusableOutput("missing output")
    body = text.strip()
    if body.endswith("```"):
        body = body[:-3].rstrip()
    if not body.endswith("}"):
        raise UnusableOutput("the output does not end with a JSON block")
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
    raise UnusableOutput("no decodable terminal JSON block")


def _require_str(obj: Dict[str, Any], key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise UnusableOutput("%s: field '%s' missing or empty" % (where, key))
    return value


def parse_verifier(text: Optional[str]) -> Dict[str, Any]:
    obj = extract_terminal_json(text)
    verdict = obj.get("verdict")
    if verdict not in VERIFIER_VERDICTS:
        raise UnusableOutput("invalid Verifier verdict: %r" % (verdict,))
    tests = obj.get("tests_passed")
    if not isinstance(tests, bool):
        raise UnusableOutput("tests_passed must be a boolean")
    issues = obj.get("issues", [])
    if not isinstance(issues, list):
        raise UnusableOutput("issues must be a list")
    clean: List[Dict[str, Any]] = []
    for i, issue in enumerate(issues):
        where = "issue %d" % i
        if not isinstance(issue, dict):
            raise UnusableOutput(where + " is not an object")
        if issue.get("severity") not in SEVERITIES:
            raise UnusableOutput(where + ": invalid severity")
        if not isinstance(issue.get("file", ""), str):
            raise UnusableOutput(where + ": 'file' must be a string")
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
        raise UnusableOutput("the reviewer block must carry a 'findings' list")
    clean: List[Dict[str, Any]] = []
    for i, f in enumerate(findings):
        where = "finding %d" % i
        if not isinstance(f, dict):
            raise UnusableOutput(where + " is not an object")
        line = f.get("line")
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            raise UnusableOutput(where + ": 'line' must be an integer >= 1")
        if f.get("severity") not in SEVERITIES:
            raise UnusableOutput(where + ": invalid severity")
        side = f.get("side", "RIGHT")
        if side not in ("RIGHT", "LEFT"):
            raise UnusableOutput(where + ": invalid 'side'")
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
        raise UnusableOutput("invalid validator verdict: %r" % (verdict,))
    return {"verdict": verdict, "reason": _require_str(obj, "reason", "validator")}
