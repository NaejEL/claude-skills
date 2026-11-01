---
name: factory-queue
description: File des specs du projet — liste les specs de specs/ avec leur statut dérivé (proposée, bloquée, en cours, livrée, mergée), leurs dépendances et leur priorité, puis, avec `run`, construit et livre chaque spec éligible l'une après l'autre dans des processus enfants headless (factory-run puis ship-pr). À utiliser quand l'utilisateur veut voir où en sont ses specs, ou dérouler les specs en attente (par exemple celles écrites par /audit) sans intervenir.
user-invocable: true
argument-hint: "[run] [--only \"a;b\"] [--target <branche>] [--autonomy gate|auto]"
---

# Factory queue — dérouler les specs, une par une

Sans argument, **lister** les specs ; avec `run`, les **dérouler** séquentiellement. Le skill ne construit rien lui-même : chaque spec est confiée à un enfant `claude -p "/factory-run …"` (contexte neuf, aucune question possible), dont l'outil Skill ne peut pas se charger (`factory-run` n'est pas invocable par un autre skill).

## Noyau déterministe

Code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : **FQ-01** à **FQ-10** (`hcore/queue.py`), **CH** (`chain.py`), **WT** (`worktrees.py`), **SX** (`stops.py`), **AP** (`gates.py`). Appeler la CLI et suivre son JSON ; ne jamais réimplémenter. Exit 1 = arrêt explicite : afficher la ligne `STOP: … (see <fichier>)` de stderr telle quelle (le fichier `.harness/runs/STOP-*.md` dit quoi faire) et s'arrêter. Exit 2 = erreur d'usage. `<PY>` : premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

## Lister (sans argument)

`K queue list --root . [--target <branche>]` rend, pour chaque spec de `specs/*.md` de l'arbre courant et des worktrees du registre, dans l'ordre de la file (topologique, puis `Priorité`, puis nom) : `id`, `title`, `status`, `approved`, `depends_on` et `unsatisfied`, `priority`, `worktree`, `last_run`, `interrupted`, plus `errors` (cycle, dépendance inconnue : les specs concernées sont inéligibles) et `warnings` (échec du `git fetch` : la référence locale est utilisée). Statuts : **mergée** (`LIVREE` sur `origin/<cible>`), **livrée** (`LIVREE` localement ou dans un worktree), **en cours** (run actif depuis moins de 2 h ; au-delà `interrupted`), **bloquée** (`BLOQUEE` avec des questions sans réponse), **proposée** (ou « proposée (réponses prêtes) »). Afficher un tableau, les erreurs et les avertissements. `K queue next` rend la prochaine spec éligible.

## Dérouler (`run`)

1. **Politique** : `run` exige `auto` (FQ-09) — `--autonomy auto` ou tampon ; sinon arrêt `gate` « requires --autonomy auto » (les enfants ne peuvent poser aucune question). Gate `factory-run.approval` et cie : jamais posées ici.
2. **Cible** : `--target`, sinon `ship_pr.target` du tampon, sinon `origin/HEAD`.
3. `K queue run --root . --target <cible> [--only "a;b"] --autonomy auto` (appel long : le lancer en arrière-plan avec l'outil Bash et lire `.harness/runs/factory-queue-<horodatage>.jsonl`, ou suivre sa sortie). Le noyau vérifie (FQ-08) la factory installée, l'arbre propre, la branche courante ou basculable sur la cible ; prend le verrou du coordinateur (un seul par dépôt, FQ-07) ; puis boucle : prochaine spec éligible (proposée ou réponses prêtes, dépendances mergées, jamais tentée dans ce run) → enfant `factory-run <spec> --ship <cible>` (CH-01) → attente → `git checkout <cible>` et `git pull --ff-only` (arbre sale → arrêt `gate`). Une PR laissée ouverte n'arrête pas la file, ses dépendants restent inéligibles ; un enfant en échec ou arrêté arrête la file (arrêt `child`, la spec n'est pas relancée).
4. Rapport : specs construites, PR mergées ou laissées ouvertes, restes et raison de chacun (`left`), chemins du journal et des STOP.

## Défauts en politique `auto`

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement et n'écrit jamais `.claude/harness.json` ; elle est transmise à chaque enfant (AP-04). Ce skill ne pose aucune gate lui-même.

## Règles impératives

- Ne jamais lancer `factory-run` par l'outil Skill ni à la main : seul `K queue run` lance les enfants.
- Ne jamais supprimer ni déplacer un worktree ou un fichier `STOP-*.md` ; ne jamais commiter ni pousser à la place du noyau.
- Jamais de `/factory-queue run` sur ce dépôt-ci sans demande explicite de l'utilisateur.
