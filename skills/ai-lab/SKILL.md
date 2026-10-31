---
name: ai-lab
description: Alias de /software-factory pour un projet de recherche IA — installe le laboratoire multi-agents (Directeur de recherche, experts Neurosciences et Maths, Builder, Verifier) et le skill /lab-run en forçant le profil research. À utiliser quand l'utilisateur veut initialiser ou installer son labo IA dans un projet de recherche (PoC d'architecture, mécanisme bio-inspiré, étude d'ablation).
user-invocable: true
argument-hint: "[question de recherche ou hypothèse à traiter en premier]"
---

# AI Lab — alias de `/software-factory --profile research`

Ce skill ne porte aucune règle : le laboratoire est le profil `research` de l'usine, installé par `/software-factory` (point d'entrée unique, Phase 2). Il est conservé sans échéance, pour ne rien casser.

## Exécution

1. Invoquer **en ligne** (sans sous-agent) l'outil Skill sur `software-factory` avec les arguments `--profile research` suivis de `$ARGUMENTS` tels quels (la question de recherche éventuelle devient le premier besoin).
2. Repli si l'outil Skill est indisponible : lire `${CLAUDE_SKILL_DIR}/../software-factory/SKILL.md` et suivre ses instructions avec ces mêmes arguments.
3. Sur un projet déjà équipé du profil `software`, le profil `research` est **ajouté** au tampon `.claude/harness.json`, rien n'est retiré.

Après l'installation, la boucle scientifique se lance par `/lab-run "<question>"` ou `/lab-run suivant`, et en headless par `ci/lab.sh experiments/EXP-x.md`.
