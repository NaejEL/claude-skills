---
name: legacy-audit
description: Alias de /audit pour la dette d'accumulation d'un repo legacy (hygiène, portabilité, qualité, filet de sécurité) — produit désormais AUDIT.md et les specs LEG. À utiliser quand l'utilisateur veut auditer un repo legacy et obtenir une roadmap de remise à niveau.
user-invocable: true
argument-hint: "[REPO] [--categories \"hygiene;portabilite;qualite;filet\"] [--max-specs N] [--models \"role=modele;...\"]"
---

# Legacy audit — alias de `/audit`

`/legacy-audit` est un alias de `/audit`, conservé pendant la version 2.0.0 et retiré à la version suivante.

Afficher d'abord cette phrase mot pour mot, puis :

1. Écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.harness/runs/legacy-audit-arguments.txt` (jamais par le shell), puis appeler `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" audit alias-args --skill legacy-audit --arguments-file .harness/runs/legacy-audit-arguments.txt` (`<PY>` : voir `/software-factory`). Le champ `arguments` rendu traduit `--categories` en `--lenses`, force `--profile software` et ajoute `--via legacy-audit`.
2. Invoquer **en ligne** (sans sous-agent) l'outil Skill sur `audit` avec ces arguments. Repli si l'outil Skill est indisponible : lire `${CLAUDE_SKILL_DIR}/../audit/SKILL.md` et suivre ses instructions avec ces arguments.
