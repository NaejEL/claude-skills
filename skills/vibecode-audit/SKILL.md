---
name: vibecode-audit
description: Alias de /audit pour un projet généré par IA (accès, injection, métier, maintenabilité, évolutivité) — produit désormais AUDIT.md. À utiliser quand l'utilisateur veut savoir par où attaquer un projet généré par IA.
user-invocable: true
argument-hint: "[REPO] [--axes \"securite;maintenabilite;evolutivite\"] [--max-findings N] [--models \"role=modele;...\"] [--autonomy gate|auto]"
---

# Vibecode audit — alias de `/audit`

`/vibecode-audit` est un alias de `/audit`, conservé pendant la version 2.0.0 et retiré à la version suivante.

Afficher d'abord cette phrase mot pour mot, puis :

1. Écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.harness/runs/vibecode-audit-arguments.txt` (jamais par le shell), puis appeler `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" audit alias-args --skill vibecode-audit --arguments-file .harness/runs/vibecode-audit-arguments.txt` (`<PY>` : voir `/software-factory`). Le champ `arguments` rendu développe les axes de `--axes` en lentilles, force `--profile software` et ajoute `--via vibecode-audit`.
2. Invoquer **en ligne** (sans sous-agent) l'outil Skill sur `audit` avec ces arguments. Repli si l'outil Skill est indisponible : lire `${CLAUDE_SKILL_DIR}/../audit/SKILL.md` et suivre ses instructions avec ces arguments.

## Défauts en politique `auto` (AP-09)

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement et n'écrit jamais `.claude/harness.json` ; elle est transmise à `K gate decide --autonomy` et aux skills enchaînés (AP-04). Défaut de chaque gate de ce skill en `auto`, avec sa justification d'une ligne (celle du catalogue `K gate list`) :

- `vibecode-audit.drop-security` → garder — security is the priority axis
- `vibecode-audit.order` → Gravité d'abord / Les détailler — marked default at :115; detailing loses nothing
- `vibecode-audit.final` → Écrire AUDIT-vibecode.md — the deliverable the audit was run for
