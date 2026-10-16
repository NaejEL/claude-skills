# Lecture et complement de fichiers JSON tels que les ecrivent VS Code et les
# outils Windows (SF-01, SF-02) :
#
# - BOM UTF-8 accepte (et conserve a la reecriture) ;
# - JSONC : commentaires // et /* */ hors des chaines, virgules finales.
#
# Un fichier JSONC (commentaires ou virgules finales) n'est jamais re-serialise :
# la fusion y insere seulement le texte des cles et elements ajoutes, a la fin
# de l'objet ou du tableau concerne, avec l'indentation et la fin de ligne du
# fichier. Commentaires, mise en forme et ordre existants sont conserves.

from __future__ import annotations

import json
import re
from json.decoder import scanstring
from typing import Any, Dict, List, Optional, Tuple

BOM = "﻿"
_LITERAL = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null")


class JsoncError(ValueError):
    """Texte JSON/JSONC invalide."""


class Node:
    """Valeur analysee avec sa position : start/end (end exclusif) dans le texte."""

    def __init__(self, kind: str, start: int):
        self.kind = kind          # "object", "array" ou "value"
        self.start = start
        self.end = start
        self.lead = start         # debut de l'entree (la cle pour un membre d'objet)
        self.value: Any = None
        self.members: List[Tuple[str, "Node"]] = []   # objet
        self.items: List["Node"] = []                  # tableau


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.loose = False   # commentaire ou virgule finale rencontre

    def fail(self, pos: int, what: str) -> JsoncError:
        line = self.text.count("\n", 0, pos) + 1
        return JsoncError("%s (ligne %d)" % (what, line))

    def skip(self, i: int) -> int:
        t = self.text
        while i < len(t):
            c = t[i]
            if c in " \t\r\n":
                i += 1
            elif t.startswith("//", i):
                self.loose = True
                j = t.find("\n", i)
                i = len(t) if j < 0 else j + 1
            elif t.startswith("/*", i):
                self.loose = True
                j = t.find("*/", i + 2)
                if j < 0:
                    raise self.fail(i, "commentaire /* non termine")
                i = j + 2
            else:
                break
        return i

    def value(self, i: int) -> Node:
        i = self.skip(i)
        t = self.text
        if i >= len(t):
            raise self.fail(i, "valeur attendue, fin de texte")
        c = t[i]
        if c == "{":
            return self.container(i, "object", "}")
        if c == "[":
            return self.container(i, "array", "]")
        node = Node("value", i)
        if c == '"':
            try:
                node.value, node.end = scanstring(t, i + 1)
            except ValueError as exc:
                raise self.fail(i, "chaine invalide : %s" % exc)
            return node
        m = _LITERAL.match(t, i)
        if not m:
            raise self.fail(i, "valeur inattendue %r" % t[i:i + 10])
        node.value, node.end = json.loads(m.group(0)), m.end()
        return node

    def container(self, i: int, kind: str, close: str) -> Node:
        node = Node(kind, i)
        result: Any = {} if kind == "object" else []
        i = self.skip(i + 1)
        t = self.text
        while True:
            if i < len(t) and t[i] == close:
                node.end, node.value = i + 1, result
                return node
            if kind == "object":
                if i >= len(t) or t[i] != '"':
                    raise self.fail(i, "cle attendue")
                key_start = i
                key, i = scanstring(t, i + 1)
                i = self.skip(i)
                if i >= len(t) or t[i] != ":":
                    raise self.fail(i, "':' attendu")
                child = self.value(i + 1)
                child.lead = key_start
                node.members.append((key, child))
                result[key] = child.value
            else:
                child = self.value(i)
                node.items.append(child)
                result.append(child.value)
            i = self.skip(child.end)
            if i < len(t) and t[i] == ",":
                i = self.skip(i + 1)
                if i < len(t) and t[i] == close:
                    self.loose = True
            elif i >= len(t) or t[i] != close:
                raise self.fail(i, "',' ou '%s' attendu" % close)


class Document:
    """Fichier JSON/JSONC lu : valeur, arbre positionne, BOM, fin de ligne."""

    def __init__(self, raw: str):
        self.bom = raw.startswith(BOM)
        self.text = raw[1:] if self.bom else raw
        parser = _Parser(self.text)
        self.root = parser.value(0)
        end = parser.skip(self.root.end)
        if end != len(self.text):
            raise parser.fail(end, "contenu inattendu apres la valeur")
        self.loose = parser.loose
        self.value = self.root.value
        self.newline = "\r\n" if "\r\n" in self.text else "\n"

    def patched(self, merged: Any) -> str:
        """Texte complet (BOM compris) ou `merged` est obtenu par seuls ajouts."""
        inserts: List[Tuple[int, str]] = []
        self._collect(self.root, merged, inserts)
        text = self.text
        for pos, chunk in sorted(inserts, key=lambda x: x[0], reverse=True):
            text = text[:pos] + chunk + text[pos:]
        return (BOM if self.bom else "") + text

    # -- interne

    def _unit(self) -> str:
        m = re.search(r"\n([ \t]+)\S", self.text)
        if not m:
            return "  "
        return "\t" if m.group(1).startswith("\t") else m.group(1)

    def _line_indent(self, pos: int) -> str:
        start = self.text.rfind("\n", 0, pos) + 1
        m = re.match(r"[ \t]*", self.text[start:])
        return m.group(0) if m else ""

    def _collect(self, node: Node, merged: Any, out: List[Tuple[int, str]]) -> None:
        if node.kind == "object" and isinstance(merged, dict):
            present = dict(node.members)
            for key, child in node.members:
                if key in merged:
                    self._collect(child, merged[key], out)
            extra = [(k, v) for k, v in merged.items() if k not in present]
            if extra:
                self._append(node, [json.dumps(k, ensure_ascii=False) + ": " for k, _ in extra],
                             [v for _, v in extra], node.members[-1][1] if node.members else None, out)
        elif node.kind == "array" and isinstance(merged, list):
            if merged[: len(node.items)] != node.value:
                raise JsoncError("fusion JSONC : le tableau existant n'est pas un prefixe du resultat")
            for child, value in zip(node.items, merged):
                self._collect(child, value, out)
            extra = merged[len(node.items):]
            if extra:
                self._append(node, [""] * len(extra), extra,
                             node.items[-1] if node.items else None, out)
        elif node.value != merged:
            raise JsoncError("fusion JSONC : seule l'addition de cles ou d'elements est prise en charge")

    def _append(self, node: Node, prefixes: List[str], values: List[Any], last: Optional[Node],
                out: List[Tuple[int, str]]) -> None:
        nl, unit = self.newline, self._unit()
        outer = self._line_indent(node.start)
        indent = outer + unit
        if last is not None:
            before = self.text[self.text.rfind("\n", 0, last.lead) + 1:last.lead]
            if not before.strip():
                indent = before   # le dernier element ouvre sa ligne : meme retrait
        rendered = []
        for prefix, value in zip(prefixes, values):
            body = json.dumps(value, ensure_ascii=False, indent=unit)
            body = body.replace("\n", nl + indent)
            rendered.append(indent + prefix + body)
        joined = ("," + nl).join(rendered)
        tail = self._comment_tail(last.end) if last is not None else None
        if tail is not None:
            # commentaire de fin de ligne : il reste avec l'element qu'il suivait
            eol, has_comma = tail
            if not has_comma:
                out.append((last.end, ","))
            out.append((eol, nl + joined))
        elif last is not None:
            out.append((last.end, "," + nl + joined))
        else:
            out.append((node.start + 1, nl + joined + nl + outer))

    def _comment_tail(self, pos: int) -> Optional[Tuple[int, bool]]:
        """Si la fin de la ligne apres `pos` ne contient que des blancs, au plus une
        virgule et au moins un commentaire, rend (fin de ligne, virgule presente)."""
        t = self.text
        eol = t.find("\n", pos)
        if eol < 0:
            return None
        if eol > pos and t[eol - 1] == "\r":
            eol -= 1
        i, comma, comment = pos, False, False
        while i < eol:
            if t[i] in " \t":
                i += 1
            elif t[i] == "," and not comma:
                comma, i = True, i + 1
            elif t.startswith("//", i):
                comment, i = True, eol
            elif t.startswith("/*", i):
                j = t.find("*/", i + 2)
                if j < 0 or j + 2 > eol:
                    return None
                comment, i = True, j + 2
            else:
                return None
        return (eol, comma) if comment else None


def loads(raw: str) -> Document:
    """Analyse un texte JSON ou JSONC (BOM accepte)."""
    return Document(raw)
