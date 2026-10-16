# Decision de relance d'un agent mort (FR-04, SP-05, SP-06).
#
# Un agent mort (erreur d'API, connexion coupee) ou dont la sortie est
# inexploitable est relance une fois. Au second echec : echec explicite. La
# relance ne consomme ni iteration ni ronde : le compteur n'est pas touche ici.

from __future__ import annotations

RELAUNCH = "relaunch"
FAIL = "fail"
MAX_RELAUNCHES = 1


def on_dead(previous_failures: int) -> str:
    """Decision apres un echec, sachant le nombre d'echecs deja subis sur ce poste."""
    if previous_failures < 0:
        raise ValueError("nombre d'echecs negatif")
    return RELAUNCH if previous_failures < MAX_RELAUNCHES else FAIL
