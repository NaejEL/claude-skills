# Roadmap de remise à niveau — projet-jouet

Générée par /legacy-audit le 2026-09-15. Usine logicielle : absente (lancer /software-factory).
L'ordre d'exécution des specs est porté par cette roadmap (jalons puis ordre du tableau).

## Jalon 1 — Assainir le dépôt
| ID | Finding | Sévérité | Taille | Dépend de | Spec | Statut |
|---|---|---|---|---|---|---|
| LEG-01 | Binaires de build trackés | major | S | — | [specs/SPEC-leg-01-binaires.md](specs/SPEC-leg-01-binaires.md) | EN_COURS |
| LEG-03 | Pas de .gitignore | major | XS | — | [specs/SPEC-leg-03-gitignore.md](specs/SPEC-leg-03-gitignore.md) | FAIT |

## Findings non retenus dans ce cycle
| ID | Finding | Raison (exclu par l'utilisateur / au-delà du plafond de specs) |
|---|---|---|
| LEG-02 | Fins de ligne incohérentes | exclu par l'utilisateur |

## Findings rejetés à la validation
| ID | Finding | Raison |
|---|---|---|
| HYG-07 | Fichier géant versionné | fixture de test assumée |
