# Audit du labo — labo-jouet

Généré par /ai-lab-audit le 2026-10-17. Labo : présent. Factory : présente.
Lentilles : fidelite, validite, fuites, bio. Audit complet. Journal audité jusqu'à l'entrée du 2026-09-01.

## Lentilles non auditées
- bio : non auditée (aucun bloc JSON exploitable après une relance) : couverture incomplète

## Corrections à faire
| ID | Finding | Lentille | Sévérité | Taille | Dépend de | Spec | Statut |
| --- | --- | --- | --- | --- | --- | --- | --- |
| COR-01 | E2 : la baseline n'est pas exécutée avec le même nombre de tokens | fuites | critical | S | — | [specs/SPEC-lab-01-e2-meme-budget.md](specs/SPEC-lab-01-e2-meme-budget.md) | A_FAIRE |
| COR-02 | La valeur par défaut de tau diffère de l'état du projet | fidelite | major | XS | — | — | A_FAIRE |

## Questions de recherche retenues (ordre recommandé)
### Q-01 — Le gain de rappel repose sur un seul seed
- **Question** : Le gain de rappel de E2 subsiste-t-il sur 5 seeds avec un budget de tokens identique ?
- **Motivation** : VAL-01 ; rappel +12 % sur le seul seed 0 (journal du 2026-09-01)
- **Ce qu'elle trancherait** : la conclusion-titre du tableau des résultats
- **Coût estimé** : M — **Dépend de** : COR-01
- **Lancer** : `/lab-run "Le gain de rappel de E2 subsiste-t-il sur 5 seeds avec un budget de tokens identique ?"`
- **Statut** : TRANCHEE (journal 2026-09-12)

## Questions non retenues dans ce cycle
| ID | Question | Raison (exclue par l'utilisateur / au-delà du plafond) |
| --- | --- | --- |

## Findings rejetés à la validation
| ID | Finding | Raison |
| --- | --- | --- |
