# hcore - noyau deterministe des skills claude-skills.
#
# Bibliotheque standard Python uniquement, compatible 3.9. Ce paquet porte les
# regles deterministes sorties des SKILL.md (parsing des blocs JSON, compteurs,
# registre, journal de cycle, relance d'un agent mort, fusions de fichiers,
# sequences gh/git de ship-pr). Les prompts ne gardent que le jugement.
#
# Point d'entree unique : harness.py (CLI), a cote de ce paquet.

CORE_VERSION = "1.0.0"
