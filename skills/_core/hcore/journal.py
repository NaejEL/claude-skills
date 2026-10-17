# JSONL cycle journal: .claude/runs/<skill>-<YYYYMMDD-HHMMSS>.jsonl
#
# One line per sub-agent call: agent, model, duration_ms, iteration
# (iteration or round), verdict, findings {produced, validated, rejected},
# tokens (integer or null). duration_ms is null when it could not be measured
# (neither usage block nor 'begin'): a measurement defect is reported, never
# blocking; any other invalid field is replaced by a reported fallback value
# (sanitize). The journal changes no other behavior.

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILLS = ("factory-run", "ship-pr")
NAME_RE = re.compile(r"^(factory-run|ship-pr)-[0-9]{8}-[0-9]{6}\.jsonl$")
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
