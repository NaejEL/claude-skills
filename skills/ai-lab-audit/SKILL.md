---
name: ai-lab-audit
description: Alias de /audit pour un projet de recherche IA (fidélité, validité, fuites, analogies biologiques, feuille de route) — produit désormais AUDIT.md. À utiliser quand l'utilisateur veut une revue externe d'un projet de recherche IA.
user-invocable: true
argument-hint: "[REPO] [--lenses \"fidelite;validite;fuites;bio;route\"] [--max-questions N] [--models \"role=modele;...\"] [--autonomy gate|auto]"
---

# AI Lab audit — alias de `/audit`

`/ai-lab-audit` est un alias de `/audit`, conservé pendant la version 2.0.0 et retiré à la version suivante.

Afficher d'abord cette phrase mot pour mot, puis :

1. Écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.harness/runs/ai-lab-audit-arguments.txt` (jamais par le shell), puis appeler `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" audit alias-args --skill ai-lab-audit --arguments-file .harness/runs/ai-lab-audit-arguments.txt --skill-dir "${CLAUDE_SKILL_DIR}"` (`<PY>` : voir `/software-factory`). Le champ `arguments` rendu force `--profile research`, conserve `--lenses`, `--max-questions` et les alias courts de `--models`, et ajoute `--via ai-lab-audit` ; le champ `invoke` est le nom effectif de `audit` pour l'outil Skill.
2. Invoquer **en ligne** (sans sous-agent) l'outil Skill sur le skill nommé par `invoke` avec ces arguments. Repli si l'outil Skill est indisponible : lire `${CLAUDE_SKILL_DIR}/../audit/SKILL.md` et suivre ses instructions avec ces arguments.

## Défauts en politique `auto` (AP-09)

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement et n'écrit jamais `.claude/harness.json` ; elle est transmise à `K gate decide --autonomy` et aux skills enchaînés (AP-04). Défaut de chaque gate de ce skill en `auto`, avec sa justification d'une ligne (celle du catalogue `K gate list`) :

- `ai-lab-audit.framing` → specs / fiabiliser — specs when a factory is present, otherwise lister; make it reliable first
- `ai-lab-audit.selection` → Toutes — the cap applies afterwards
- `ai-lab-audit.final` → Écrire AUDIT-lab.md — the deliverable the audit was run for
