# Roadmap de remise à niveau — projet-jouet

Générée par /legacy-audit le 2026-10-17. Usine logicielle : absente (lancer /software-factory).
L'ordre d'exécution des specs est porté par cette roadmap (jalons puis ordre du tableau).

## Familles non auditées
- qualite : non auditée (aucun bloc JSON exploitable après une relance)

## Jalon 1 — Assainir le dépôt
| ID | Finding | Sévérité | Taille | Dépend de | Spec | Statut |
|---|---|---|---|---|---|---|
| LEG-01 | Secret commité dans config.py | critical | S | — | [specs/SPEC-leg-01-purge-secrets.md](specs/SPEC-leg-01-purge-secrets.md) | A_FAIRE |
| LEG-02 | Aucun .gitignore | major | XS | — | [specs/SPEC-leg-02-gitignore.md](specs/SPEC-leg-02-gitignore.md) | A_FAIRE |

## Jalon 2 — Fiabiliser la configuration
| ID | Finding | Sévérité | Taille | Dépend de | Spec | Statut |
|---|---|---|---|---|---|---|

## Findings non retenus dans ce cycle
| ID | Finding | Raison (exclu par l'utilisateur / au-delà du plafond de specs) |
|---|---|---|
| LEG-03 | Dépendances non épinglées | au-delà du plafond de specs |

## Findings rejetés à la validation
| ID | Finding | Raison |
|---|---|---|
| PORT-01 | Chemin absolu dans le script de build | script d'exemple documenté comme tel |
