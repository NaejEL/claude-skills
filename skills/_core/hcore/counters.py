# Compteurs d'iterations et de rondes, et leurs bornes.
#
# - FR-03 : factory-run, 3 iterations Build/Verify au plus.
# - SP-01 : ship-pr --rounds N, borne dure min(N, 3), defaut 3 ; N <= 0 ou non
#   entier -> erreur explicite (D8).
# - SP-02 : ship-pr --themes "a;b;c", separateur ';', 4 au plus, 3 par defaut ;
#   liste vide ou plus de 4 entrees -> erreur explicite (D8).

from __future__ import annotations

from typing import List, Optional

MAX_ITERATIONS = 3
MAX_ROUNDS = 3
DEFAULT_ROUNDS = 3
MAX_THEMES = 4
DEFAULT_THEMES = [
    "logique et cas limites",
    "régressions et contrats des sites d'appel",
    "cohérence interne du diff",
]


class BoundsError(ValueError):
    """Borne invalide passee en argument (D8)."""


def parse_rounds(value: Optional[str]) -> int:
    if value is None:
        return DEFAULT_ROUNDS
    text = str(value).strip()
    try:
        n = int(text)
    except ValueError:
        raise BoundsError("--rounds attend un entier strictement positif, recu : %r" % (value,))
    if n <= 0:
        raise BoundsError("--rounds attend un entier strictement positif, recu : %d" % n)
    return min(n, MAX_ROUNDS)


def parse_themes(value: Optional[str]) -> List[str]:
    if value is None:
        return list(DEFAULT_THEMES)
    themes = [t.strip() for t in str(value).split(";") if t.strip()]
    if not themes:
        raise BoundsError("--themes est vide : au moins un theme est requis")
    if len(themes) > MAX_THEMES:
        raise BoundsError("--themes accepte %d themes au plus, recu : %d" % (MAX_THEMES, len(themes)))
    if len(set(themes)) != len(themes):
        raise BoundsError("--themes contient un theme en double")
    return themes


def cap_reached(current: int, cap: int) -> bool:
    """Vrai quand le compteur courant a atteint le plafond."""
    return current >= cap
