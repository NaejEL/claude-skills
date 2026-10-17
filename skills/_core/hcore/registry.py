# Cumulative registry of ship-pr findings (SP-07, SP-09, D2).
#
# File .claude/runs/ship-pr-<timestamp>.registry.jsonl, one JSON line per
# finding event, keys file/line/title/verdict. The last event of a key gives
# its current status. Deterministic deduplication on file + normalized title,
# all statuses included (a REJECTED finding does not come back to life).
# Semantic dedup (same subject, other title) is left to the prompt's judgment.
# Adding is idempotent: an event identical to the last event of its key is
# not rewritten (a relaunch after an interruption does not duplicate).

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Optional

STATUSES = ("CONFIRMED", "REJECTED", "UNVALIDATED", "FIXED", "NOT_FIXED")


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKD", title)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w]+", " ", text.lower())
    return " ".join(text.split())


def finding_key(file: str, title: str) -> str:
    path = file.replace("\\", "/").strip()
    while path.startswith("./"):
        path = path[2:]
    return path + "::" + normalize_title(title)


class Registry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.status: Dict[str, str] = {}
        self.last: Dict[str, Dict[str, Any]] = {}
        if self.path.exists():
            with open(self.path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        entry = json.loads(line)
                        self.status[entry["key"]] = entry["verdict"]
                        self.last[entry["key"]] = entry

    def known(self, key: str) -> bool:
        return key in self.status

    def current(self, key: str) -> Optional[str]:
        return self.status.get(key)

    def add(self, finding: Dict[str, Any], verdict: str, **extra: Any) -> Dict[str, Any]:
        if verdict not in STATUSES:
            raise ValueError("unknown registry status: %r" % (verdict,))
        key = finding_key(finding["file"], finding["title"])
        entry: Dict[str, Any] = {
            "key": key,
            "file": finding["file"],
            "line": finding["line"],
            "title": finding["title"],
            "verdict": verdict,
        }
        entry.update({k: v for k, v in extra.items() if v is not None})
        if self.last.get(key) == entry:
            return entry
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.status[key] = verdict
        self.last[key] = entry
        return entry
