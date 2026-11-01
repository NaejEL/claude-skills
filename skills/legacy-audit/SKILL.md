---
name: legacy-audit
description: Alias de /audit pour la dette d'accumulation d'un repo legacy (hygiène, portabilité, qualité, filet de sécurité) — produit désormais AUDIT.md et les specs LEG. À utiliser quand l'utilisateur veut auditer un repo legacy et obtenir une roadmap de remise à niveau.
user-invocable: true
argument-hint: "[REPO] [--categories \"hygiene;portabilite;qualite;filet\"] [--max-specs N] [--models \"role=modele;...\"] [--autonomy gate|auto]"
---

# Legacy audit — alias de `/audit`

`/legacy-audit` est un alias de `/audit`, conservé pendant la version 2.0.0 et retiré à la version suivante.

Afficher d'abord cette phrase mot pour mot, puis :

1. Écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.harness/runs/legacy-audit-arguments.txt` (jamais par le shell), puis appeler `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" audit alias-args --skill legacy-audit --arguments-file .harness/runs/legacy-audit-arguments.txt --skill-dir "${CLAUDE_SKILL_DIR}"` (`<PY>` : voir `/software-factory`). Le champ `arguments` rendu traduit `--categories` en `--lenses`, force `--profile software` et ajoute `--via legacy-audit` ; le champ `invoke` est le nom effectif de `audit` pour l'outil Skill.
2. Invoquer **en ligne** (sans sous-agent) l'outil Skill sur le skill nommé par `invoke` avec ces arguments. Repli si l'outil Skill est indisponible : lire `${CLAUDE_SKILL_DIR}/../audit/SKILL.md` et suivre ses instructions avec ces arguments.

## Défauts en politique `auto` (AP-09)

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement et n'écrit jamais `.claude/harness.json` ; elle est transmise à `K gate decide --autonomy` et aux skills enchaînés (AP-04). Défaut de chaque gate de ce skill en `auto`, avec sa justification d'une ligne (celle du catalogue `K gate list`) :

- `legacy-audit.framing` → 3 / risque d'abord — close to 'make it reliable first' (roadmap 4.2)
- `legacy-audit.assignment` → aucun (arrêt) — the computation belongs to Phase 4
- `legacy-audit.final` → Générer roadmap + specs — the deliverable the audit was run for
