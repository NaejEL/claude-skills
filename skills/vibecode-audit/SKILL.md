---
name: vibecode-audit
description: Alias de /audit pour un projet généré par IA (accès, injection, métier, maintenabilité, évolutivité) — produit désormais AUDIT.md. À utiliser quand l'utilisateur veut savoir par où attaquer un projet généré par IA.
user-invocable: true
argument-hint: "[REPO] [--axes \"securite;maintenabilite;evolutivite\"] [--max-findings N] [--models \"role=modele;...\"]"
---

# Vibecode audit — alias de `/audit`

`/vibecode-audit` est un alias de `/audit`, conservé pendant la version 2.0.0 et retiré à la version suivante.

Afficher d'abord cette phrase mot pour mot, puis :

1. Écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.harness/runs/vibecode-audit-arguments.txt` (jamais par le shell), puis appeler `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" audit alias-args --skill vibecode-audit --arguments-file .harness/runs/vibecode-audit-arguments.txt` (`<PY>` : voir `/software-factory`). Le champ `arguments` rendu développe les axes de `--axes` en lentilles, force `--profile software` et ajoute `--via vibecode-audit`.
2. Invoquer **en ligne** (sans sous-agent) l'outil Skill sur `audit` avec ces arguments. Repli si l'outil Skill est indisponible : lire `${CLAUDE_SKILL_DIR}/../audit/SKILL.md` et suivre ses instructions avec ces arguments.
