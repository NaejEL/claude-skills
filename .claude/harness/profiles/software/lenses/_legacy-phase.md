## Phase 2 — Audit parallèle par familles de smells

Lancer **en un seul message** les auditeurs, un par famille retenue (LA-01) :

Chaque prompt contient : la carte, sa famille **et rien d'autre à chercher**, le budget de lecture, la phrase « **zéro finding est une réponse normale et acceptable** », l'interdiction d'écrire, la preuve vérifiable (fichier + ligne + extrait ≤ 3 lignes, ou constat structurel), le barème T-shirt (XS < 30 min, S < 2 h, M demi-journée, L 1-2 jours, XL à découper) et un unique bloc JSON final (LA-05) :

```json
{"findings": [{"id": "HYG-01", "category": "gitignore-absent", "severity": "critical|major|minor",
  "title": "résumé court", "location": {"file": "chemin/relatif ou null", "line": 12},
  "evidence": "extrait ≤ 3 lignes ou constat structurel", "impact": "conséquence concrète",
  "remediation": "correction proposée en une phrase", "size": "XS|S|M|L|XL", "depends_on": []}]}
```

`critical` est réservé aux secrets commités, aux bugs avérés et aux pertes de données potentielles. Chaque retour : `K audit auditor --run <run> --unit <famille> --output <fichier> [--dead] --duration-ms <ms> --tokens <n>` ; `action` : `relaunch` (relancer cette famille **une fois**), `not-audited`, `validate` (`to_validate` ; `duplicates` écartés **sans validateur**, y compris REJECTED du registre projet, `previous=<statut>@<source>`), `none`.
