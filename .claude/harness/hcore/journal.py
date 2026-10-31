# JSONL cycle journal: .harness/runs/<skill>-<YYYYMMDD-HHMMSS>.jsonl
#
# One line per sub-agent call: agent, model, duration_ms, iteration
# (iteration or round), verdict, findings {produced, validated, rejected},
# tokens (integer or null). duration_ms is null when it could not be measured
# (neither usage block nor 'begin'): a measurement defect is reported, never
# blocking; any other invalid field is replaced by a reported fallback value
# (sanitize). The journal changes no other behavior.
# Deferred completion (amend): when the duration or the tokens are only known
# after the reviewer/validator/agent call, they complete the last entry of that
# slot (agent name, reviewer:<theme> or validator:<id>); a value already
# logged is never overwritten (reported instead).
# - JR-01: journal names of the ten skills (SKILLS).
# - JR-02: typed events. A line without "event" is an agent line (backward
#   compatible with existing journals); "event": "gate" follows the GT-07
#   schema (hcore/gates.py). Any other event type is invalid.

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import gates

SKILLS = ("software-factory", "factory-run", "ship-pr", "code-index", "ai-lab", "lab-run",
          "ai-lab-audit", "legacy-audit", "vibecode-audit", "brainstorm")
NAME_RE = re.compile(r"^(%s)-[0-9]{8}-[0-9]{6}\.jsonl$" % "|".join(re.escape(s) for s in SKILLS))
EVENTS = ("gate",)
REQUIRED = ("agent", "model", "duration_ms", "iteration", "verdict", "findings", "tokens")
FINDING_KEYS = ("produced", "validated", "rejected")
FALLBACK_TEXT = "unknown"   # fallback value of an invalid text field (sanitize)


def journal_name(skill: str, now: datetime) -> str:
    if skill not in SKILLS:
        raise ValueError("unknown skill for the journal: %r" % (skill,))
    return "%s-%s.jsonl" % (skill, now.strftime("%Y%m%d-%H%M%S"))


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def make_record(agent: str, model: str, duration_ms: Optional[int], iteration: int, verdict: str,
                produced: int = 0, validated: int = 0, rejected: int = 0,
                tokens: Optional[int] = None, **extra: Any) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "agent": agent,
        "model": model,
        "duration_ms": duration_ms,
        "iteration": iteration,
        "verdict": verdict,
        "findings": {"produced": produced, "validated": validated, "rejected": rejected},
        "tokens": tokens,
    }
    record.update(extra)
    return record


def validate_record(obj: Any) -> List[str]:
    if not isinstance(obj, dict):
        return ["the line is not a JSON object"]
    if "event" in obj:
        if obj["event"] not in EVENTS:
            return ["unknown event type: %r" % (obj["event"],)]
        return gates.validate_event(obj)
    errors = ["missing field: %s" % k for k in REQUIRED if k not in obj]
    if errors:
        return errors
    for key in ("agent", "model", "verdict"):
        if not isinstance(obj[key], str) or not obj[key].strip():
            errors.append("%s must be a non-empty string" % key)
    if not _is_count(obj["iteration"]):
        errors.append("iteration must be an integer >= 0")
    if obj["duration_ms"] is not None and not _is_count(obj["duration_ms"]):
        errors.append("duration_ms must be an integer >= 0 or null")
    findings = obj["findings"]
    if not isinstance(findings, dict):
        errors.append("findings must be an object")
    else:
        for key in FINDING_KEYS:
            if not _is_count(findings.get(key)):
                errors.append("findings.%s must be an integer >= 0" % key)
    tokens = obj["tokens"]
    if tokens is not None and not _is_count(tokens):
        errors.append("tokens must be an integer >= 0 or null")
    return errors


def sanitize(record: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Replaces every invalid field with a schema-conforming fallback value
    (FALLBACK_TEXT, null or 0) and returns the list of fallbacks, to report in
    'journal_warnings': a journal defect never stops the skill."""
    fixed, warnings = dict(record), []
    for key in ("agent", "model", "verdict"):
        if not isinstance(fixed.get(key), str) or not fixed[key].strip():
            warnings.append("%s invalid (%r): logged as %r" % (key, fixed.get(key), FALLBACK_TEXT))
            fixed[key] = FALLBACK_TEXT
    for key in ("duration_ms", "tokens"):
        if fixed.get(key) is not None and not _is_count(fixed[key]):
            warnings.append("%s invalid (%r): logged as null" % (key, fixed[key]))
            fixed[key] = None
    if not _is_count(fixed.get("iteration")):
        warnings.append("iteration invalid (%r): logged as 0" % (fixed.get("iteration"),))
        fixed["iteration"] = 0
    findings = fixed.get("findings")
    counts = dict(findings) if isinstance(findings, dict) else {}
    for key in FINDING_KEYS:
        if not _is_count(counts.get(key)):
            warnings.append("findings.%s invalid (%r): logged as 0" % (key, counts.get(key)))
            counts[key] = 0
    fixed["findings"] = counts
    return fixed, warnings


def append(path: Path, record: Dict[str, Any]) -> None:
    errors = validate_record(record)
    if errors:
        raise ValueError("invalid journal record: " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def slot_of(record: Dict[str, Any]) -> str:
    """Slot of a journal entry: reviewer:<theme>, auditor:<lens or family>,
    validator:<id>, or the agent name."""
    agent = record.get("agent")
    if agent == "auditor" and "unit" in record:
        return "auditor:%s" % record["unit"]
    if agent == "reviewer" and "theme" in record:
        return "reviewer:%s" % record["theme"]
    if agent == "validator" and "finding" in record:
        return "validator:%s" % record["finding"]
    return str(agent)


def amend(records: List[Dict[str, Any]], slot: str, duration_ms: Optional[int],
          tokens: Optional[int]) -> Tuple[List[str], List[str]]:
    """Completes, in place, the null measurements of the last entry of `slot`.
    Returns (amended fields, warnings); never raises on a measurement defect."""
    matches = [i for i, r in enumerate(records) if slot_of(r) == slot]
    if not matches:
        return [], ["no journal entry for slot %s: nothing amended" % slot]
    record = records[matches[-1]]
    amended: List[str] = []
    warnings: List[str] = []
    for key, value in (("duration_ms", duration_ms), ("tokens", tokens)):
        if value is None:
            continue
        if record.get(key) is None:
            record[key] = value
            amended.append(key)
        elif record[key] != value:
            warnings.append("%s already logged for %s (%r): kept, %r ignored" % (key, slot, record[key], value))
    return amended, warnings


def dumps(records: List[Dict[str, Any]]) -> str:
    for record in records:
        errors = validate_record(record)
        if errors:
            raise ValueError("invalid journal record: " + "; ".join(errors))
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


def read(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def validate_file(path: Path) -> List[str]:
    """Returns the list of errors, empty if every line follows the schema."""
    errors: List[str] = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return ["cannot read: %s" % exc]
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except ValueError:
            errors.append("line %d: invalid JSON" % number)
            continue
        errors.extend("line %d: %s" % (number, e) for e in validate_record(obj))
    return errors
