---
name: ai-lab
description: Alias de /software-factory pour un projet de recherche IA — installe le laboratoire multi-agents (Directeur de recherche, experts Neurosciences et Maths, Builder, Verifier) et le skill /lab-run en forçant le profil research. À utiliser quand l'utilisateur veut initialiser ou installer son labo IA dans un projet de recherche (PoC d'architecture, mécanisme bio-inspiré, étude d'ablation).
user-invocable: true
argument-hint: "[question de recherche ou hypothèse à traiter en premier | --upgrade [--convert]]"
---

# AI Lab — alias de `/software-factory --profile research`

Ce skill ne porte aucune règle : le laboratoire est le profil `research` de l'usine, installé par `/software-factory` (point d'entrée unique, Phase 2). Il est conservé sans échéance, pour ne rien casser.

## Exécution

0. **`--upgrade [--convert]`** (EP-10) : `K sf args --via ai-lab --arguments-file …` (arguments écrits par Write) rend `translated` ; invoquer `software-factory` avec cette traduction, **sans** `--profile research` : tous les profils du tampon sont mis à jour. Les mises à jour du laboratoire passent donc par `/software-factory --upgrade`.
1. Obtenir le nom effectif de `software-factory` : `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" plugin skill-name --skill software-factory --skill-dir "${CLAUDE_SKILL_DIR}"` (champ `name`), à utiliser aussi à l'étape 0. Invoquer **en ligne** (sans sous-agent) l'outil Skill sur ce nom avec les arguments `--profile research` suivis de `$ARGUMENTS` tels quels (la question de recherche éventuelle devient le premier besoin).
2. Repli si l'outil Skill est indisponible : lire `${CLAUDE_SKILL_DIR}/../software-factory/SKILL.md` et suivre ses instructions avec ces mêmes arguments.
3. Sur un projet déjà équipé du profil `software`, le profil `research` est **ajouté** au tampon `.claude/harness.json`, rien n'est retiré.

Après l'installation, la boucle scientifique se lance par `/lab-run "<question>"` ou `/lab-run suivant`, et en headless par `ci/lab.sh experiments/EXP-x.md`.

## Défauts en politique `auto` (AP-09)

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement et n'écrit jamais `.claude/harness.json` ; elle est transmise à `K gate decide --autonomy` et aux skills enchaînés (AP-04). Défaut de chaque gate de ce skill en `auto`, avec sa justification d'une ligne (celle du catalogue `K gate list`) :

- `ai-lab.models` → Tout hérité — no extra cost
- `ai-lab.code-index` → refus — the knowledge base adds a versioned folder
- `lab-run.pi-questions` → aucun (arrêt) — nothing to invent in the PI's place
- `lab-run.preregistration` → approbation — arrêt si `stop_when` = input:blocking_unanswered — roadmap 4.2 applied to the research artefact: pre-registered unless the protocol declares an unanswered blocking question
- `lab-run.consignation` → approbation — logged, marked 'to be reviewed' (ai-lab:188)
