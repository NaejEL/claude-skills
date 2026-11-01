---
name: factory-batch
description: Lot de specs en parallèle — construit plusieurs specs à la fois, chacune dans son propre worktree git (jusqu'à 4 enfants headless), puis les livre une à la fois dans l'ordre de la file (rebase sur la cible, ship-pr, merge, nettoyage). À utiliser quand l'utilisateur veut dérouler plusieurs specs indépendantes plus vite que /factory-queue, sans toucher à ses propres worktrees.
disable-model-invocation: true
user-invocable: true
argument-hint: "<glob…> [--parallel N] [--target <branche>] [--autonomy gate|auto] [--resume <id>]"
---

# Factory batch — plusieurs specs en parallèle, un seul ship à la fois

Construire en parallèle les specs désignées par les globs, chacune dans un worktree git créé par le harnais, puis les livrer **une à la fois**. Aucun autre skill n'enchaîne ce skill (`disable-model-invocation: true`).

## Noyau déterministe

Code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : **FB-01** à **FB-08** (`hcore/batch.py`), **FQ** (`queue.py`), **WT** (`worktrees.py`), **CH** (`chain.py`), **SX** (`stops.py`). Appeler la CLI et suivre son JSON ; ne jamais réimplémenter. Exit 1 = arrêt explicite : afficher la ligne `STOP: … (see <fichier>)` de stderr telle quelle et s'arrêter ; le fichier `.harness/runs/STOP-*.md` donne la commande de reprise. Exit 2 = erreur d'usage (`--parallel` non entier ou < 1). `<PY>` : premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

## Déroulé

1. **Politique** : comme `/factory-queue run`, `auto` est exigée (FQ-09, FB-07) ; un seul coordinateur par dépôt (FQ-07).
2. `K batch run --root . <glob…> [--parallel N] [--target <cible>] --autonomy auto [--resume <id>]` (appel long : le lancer en arrière-plan avec l'outil Bash et suivre `.harness/runs/factory-batch-<horodatage>.jsonl`). `--parallel` : défaut 2, plafonné à 4. Le noyau développe et trie les globs, rapporte les specs inéligibles (`not_eligible`), puis pour chaque emplacement : worktree `<dépôt>.harness-wt/<slug>` sur la branche `factory/<slug>` depuis `origin/<cible>` (la spec y est transférée si elle diffère de la base, l'original est déplacé sous `.harness/runs/handoff/`), puis un enfant `factory-run <spec> --deliver-only`.
3. **Ship** : un seul à la fois, dans l'ordre de la file. Avant chaque ship, la branche locale (jamais poussée) est rebasée sur `origin/<cible>` ; un conflit trivial (artefacts régénérables de `.knowledge/`) est résolu, tout autre conflit annule le rebase, arrête les lancements, attend les enfants en cours puis arrête avec le type `conflict` (le worktree est conservé). Le ship est un enfant `ship-pr <cible> --spec <spec>` dans le worktree ; PR mergée → les journaux du worktree sont copiés sous `.harness/runs/wt-<slug>/`, puis le worktree et sa branche locale sont supprimés (jamais forcé) ; PR laissée ouverte → worktree conservé.
4. `--resume <id>` reprend un lot arrêté (état `.harness/runs/factory-batch-<horodatage>.state.json`).
5. Rapport : état de chaque spec (mergée, laissée ouverte, en échec, inéligible), chemins des worktrees conservés, du journal et des STOP.

## Défauts en politique `auto`

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement, n'écrit jamais `.claude/harness.json` et est transmise à chaque enfant (AP-04). Ce skill ne pose aucune gate lui-même.

## Règles impératives

- Le harnais ne touche jamais au worktree principal ni à ceux de l'utilisateur : toute opération exige que le chemin soit au registre **et** listé par `git worktree list`. Jamais de `prune`, de `remove --force`, ni de `move`, `lock`, `unlock`.
- Un dépôt dont la base `origin/<cible>` n'a pas `.claude/harness/` et `.claude/settings.json` s'arrête (`gate`) : « commit the harness files first ».
- Jamais de `/factory-batch` sur ce dépôt-ci sans demande explicite de l'utilisateur.
