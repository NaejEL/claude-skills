Statut : PROPOSEE

# SPEC-leg-03 — Ajouter un .gitignore adapté à la stack Python

## Contexte
Finding LEG-03 (major, XS) : aucun .gitignore ; __pycache__/ et .venv/ apparaissent dans git status.

## Périmètre
Créer un fichier .gitignore à la racine couvrant les artefacts Python et l'IDE.

## Critères d'acceptation
1. Un fichier `.gitignore` existe à la racine et contient au minimum `__pycache__/`, `*.pyc`, `.venv/`.

## Hors-périmètre
Réécriture d'historique ; .gitignore par sous-dossier.

## Risques
Un motif trop large pourrait ignorer des fichiers légitimes.

## Questions ouvertes
Aucune
