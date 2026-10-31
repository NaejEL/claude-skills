## Phase 2 — Audit parallèle par lentilles

Lancer **en un seul message** les auditeurs (lecture seule, AA-05), un par lentille retenue :

Chaque prompt contient : la carte, sa lentille **et rien d'autre**, le budget de lecture, la phrase « **zéro finding est une réponse normale et acceptable** », l'interdiction d'écrire et d'exécuter, la preuve vérifiable, la distinction des deux natures, et un unique bloc JSON final (AA-07) :

```json
{"findings": [{"id": "VAL-01", "lens": "validite", "nature": "correction|question",
  "severity": "critical|major|minor", "title": "résumé court",
  "location": {"file": "chemin/relatif ou null", "line": 12, "journal_date": "AAAA-MM-JJ ou null"},
  "evidence": "extrait ≤ 3 lignes ou citation", "impact": "ce que ça change pour les conclusions du projet",
  "proposal": "correction en une phrase, OU question de recherche falsifiable en une phrase",
  "size": "XS|S|M|L|XL", "depends_on": []}]}
```

`correction` = quelque chose de faux ou d'incohérent à réparer ; `question` = quelque chose d'inconnu que seule une expérience tranche. `critical` est réservé aux fuites qui invalident un résultat publié dans le tableau, aux violations d'une contrainte non négociable et aux conclusions-titre reposant sur une preuve insuffisante. `size` : barème XS < 30 min, S < 2 h, M demi-journée, L 1-2 jours, XL à découper ; pour une question, coût de l'expérience sur le matériel déclaré (XS quelques minutes GPU, S < 1 h, M demi-journée de runs, L plusieurs jours, XL hors de portée). Chaque retour : `K audit auditor --run <run> --unit <lentille> --output <fichier> [--dead] --duration-ms <ms> --tokens <n>` (`relaunch` : une fois ; `not-audited` ; `validate` avec `to_validate` ; doublons — AA-08 : même fichier et ligne, ou même document et date, et même lentille, y compris REJECTED, `TRANCHEE` et audit préexistant — écartés **sans validateur**).
