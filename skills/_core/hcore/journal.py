# Journal de cycle JSONL : .claude/runs/<skill>-<AAAAMMJJ-HHMMSS>.jsonl
#
# Une ligne par appel de sous-agent : agent, model, duration_ms, iteration
# (iteration ou ronde), verdict, findings {produced, validated, rejected},
# tokens (entier ou null). duration_ms vaut null si elle n'a pu etre mesuree
# (ni bloc d'usage ni 'begin') : un defaut de mesure est signale, jamais
# bloquant ; tout autre champ invalide est remplace par une valeur de repli
# signalee (sanitize). Le journal ne change aucun autre comportement.

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
FALLBACK_TEXT = "inconnu"   # valeur de repli d'un champ texte invalide (sanitize)


def journal_name(skill: str, now: datetime) -> str:
    if skill not in SKILLS:
        raise ValueError("skill inconnu pour le journal : %r" % (skill,))
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
        return ["la ligne n'est pas un objet JSON"]
    errors = ["champ manquant : %s" % k for k in REQUIRED if k not in obj]
    if errors:
        return errors
    for key in ("agent", "model", "verdict"):
        if not isinstance(obj[key], str) or not obj[key].strip():
            errors.append("%s doit etre une chaine non vide" % key)
    if not _is_count(obj["iteration"]):
        errors.append("iteration doit etre un entier >= 0")
    if obj["duration_ms"] is not None and not _is_count(obj["duration_ms"]):
        errors.append("duration_ms doit etre un entier >= 0 ou null")
    findings = obj["findings"]
    if not isinstance(findings, dict):
        errors.append("findings doit etre un objet")
    else:
        for key in FINDING_KEYS:
            if not _is_count(findings.get(key)):
                errors.append("findings.%s doit etre un entier >= 0" % key)
    tokens = obj["tokens"]
    if tokens is not None and not _is_count(tokens):
        errors.append("tokens doit etre un entier >= 0 ou null")
    return errors


def sanitize(record: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Remplace chaque champ invalide par une valeur de repli conforme au schema
    (FALLBACK_TEXT, null ou 0) et rend la liste des replis, a signaler dans
    'journal_warnings' : un defaut de journal n'arrete jamais le skill."""
    fixed, warnings = dict(record), []
    for key in ("agent", "model", "verdict"):
        if not isinstance(fixed.get(key), str) or not fixed[key].strip():
            warnings.append("%s invalide (%r) : journalise %r" % (key, fixed.get(key), FALLBACK_TEXT))
            fixed[key] = FALLBACK_TEXT
    for key in ("duration_ms", "tokens"):
        if fixed.get(key) is not None and not _is_count(fixed[key]):
            warnings.append("%s invalide (%r) : journalise null" % (key, fixed[key]))
            fixed[key] = None
    if not _is_count(fixed.get("iteration")):
        warnings.append("iteration invalide (%r) : journalise 0" % (fixed.get("iteration"),))
        fixed["iteration"] = 0
    findings = fixed.get("findings")
    counts = dict(findings) if isinstance(findings, dict) else {}
    for key in FINDING_KEYS:
        if not _is_count(counts.get(key)):
            warnings.append("findings.%s invalide (%r) : journalise 0" % (key, counts.get(key)))
            counts[key] = 0
    fixed["findings"] = counts
    return fixed, warnings


def append(path: Path, record: Dict[str, Any]) -> None:
    errors = validate_record(record)
    if errors:
        raise ValueError("enregistrement de journal invalide : " + "; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def read(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def validate_file(path: Path) -> List[str]:
    """Rend la liste des erreurs, vide si chaque ligne respecte le schema."""
    errors: List[str] = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return ["lecture impossible : %s" % exc]
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
        except ValueError:
            errors.append("ligne %d : JSON invalide" % number)
            continue
        errors.extend("ligne %d : %s" % (number, e) for e in validate_record(obj))
    return errors
