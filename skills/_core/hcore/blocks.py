# Blocs delimites dans un fichier texte (D9 : module seul, non utilise par
# software-factory dans cet increment).
#
# Styles :
#   md   : <!-- nom:debut --> ... <!-- nom:fin -->
#   hash : # >>> nom >>> ... # <<< nom <<<
# L'insertion est reentrante : un bloc present est remplace en place, sinon il
# est ajoute en fin de fichier ; le texte hors bloc n'est jamais modifie.

from __future__ import annotations

import re
from typing import Optional, Tuple

STYLES = ("md", "hash")


class BlockError(ValueError):
    """Bloc mal forme (marqueur ouvrant sans fermant, ou l'inverse)."""


def markers(name: str, style: str) -> Tuple[str, str]:
    if not re.match(r"^[A-Za-z0-9_.-]+$", name):
        raise BlockError("nom de bloc invalide : %r" % (name,))
    if style == "md":
        return "<!-- %s:debut -->" % name, "<!-- %s:fin -->" % name
    if style == "hash":
        return "# >>> %s >>>" % name, "# <<< %s <<<" % name
    raise BlockError("style inconnu : %r" % (style,))


def _span(text: str, name: str, style: str) -> Optional[Tuple[int, int]]:
    start_m, end_m = markers(name, style)
    start = text.find(start_m)
    end = text.find(end_m)
    if start == -1 and end == -1:
        return None
    if start == -1 or end == -1 or end < start:
        raise BlockError("bloc %r mal forme" % name)
    if text.find(start_m, start + 1) != -1:
        raise BlockError("bloc %r present plusieurs fois" % name)
    return start, end + len(end_m)


def get_block(text: str, name: str, style: str) -> Optional[str]:
    span = _span(text, name, style)
    if span is None:
        return None
    start_m, end_m = markers(name, style)
    inner = text[span[0] + len(start_m): span[1] - len(end_m)]
    return inner.strip("\n")


def upsert_block(text: str, name: str, content: str, style: str) -> str:
    start_m, end_m = markers(name, style)
    block = "%s\n%s\n%s" % (start_m, content.strip("\n"), end_m)
    span = _span(text, name, style)
    if span is not None:
        return text[: span[0]] + block + text[span[1]:]
    if text and not text.endswith("\n"):
        text += "\n"
    sep = "\n" if text else ""
    return text + sep + block + "\n"


def remove_block(text: str, name: str, style: str) -> str:
    span = _span(text, name, style)
    if span is None:
        return text
    before, after = text[: span[0]], text[span[1]:]
    if after.startswith("\n"):
        after = after[1:]
    if before.endswith("\n\n"):
        before = before[:-1]
    return before + after
