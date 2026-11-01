---
name: harness-doctor
description: Diagnostique l'installation du harnais (usine logicielle, labo, base de connaissance) d'un projet — version installée contre celle du dépôt claude-skills, blocs divergents, fichiers manquants, hooks rgkb absents, models.json absent, gh non authentifié, profils nouveaux — et propose `--upgrade` ; avec `--scan <racine>`, une ligne par projet équipé (version, retard, dernier cycle). À utiliser quand l'utilisateur demande l'état de son harnais, une mise à jour, ou un inventaire de ses projets équipés.
user-invocable: true
argument-hint: "[--scan <racine>] [--depth N] [--autonomy gate|auto]"
---

# Harness doctor — état et mise à jour des projets équipés

Diagnostiquer l'installation du harnais du projet courant, ou d'une arborescence de projets avec `--scan`. Ce skill **ne modifie rien** lui-même : il lit, il rapporte, il propose, et il ne lance une mise à jour que par les skills `software-factory` et `code-index` (`--upgrade`).

## Noyau déterministe

Toutes les règles sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : ne jamais les réimplémenter, appeler la CLI et suivre sa sortie JSON. Règles : **VS** (`version.py`), **DR** (`doctor.py`), **SN** (`scan.py`), **UP** (`upgrade.py`), **PR** (propositions), **GT-09**, **JR-04**.

**Interpréteur** (règle D5, `hcore/interp.py`) : `<PY>` = le premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9 ; en pratique `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" interp` sous chacune de ces trois commandes simples, la première qui rend `command`. Aucun candidat → s'arrêter. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`. Le noyau utilisé est **celui du dépôt** (global), jamais la copie du projet : c'est lui qui connaît la version courante.

## Mode projet (sans argument)

1. `K doctor --root .` rend un JSON : `equipped` (`stamp`, `inferred` ou `none`), `version` (installée, dépôt, retard : `up_to_date`, `behind`, `ahead`, `diverged`, `unknown`), `core` (copie `.claude/harness/`, `mixed`, `customized`), `blocks` (chaque bloc `ok`, `edited`, `outdated`, `edited+outdated` ou `missing_block`), `legacy_files`, `missing`, `hooks`, `models`, `gh`, `signals`, `upgrade` (`changes`, `blocks_only`, `by_skill`), un `status` `ok`/`warn`/`error` par contrôle, et `proposal`. Projet `none` : le dire (`/software-factory` installe) et ne rien écrire.
2. Présenter le rapport par contrôle, avec le statut et, pour chaque anomalie, la cause et le remède en une ligne :
   - `edited` : bloc modifié à la main, il sera remplacé par l'upgrade (sauvegarde) ; la personnalisation se fait **hors bloc** ;
   - `hooks.missing` : `post-merge`, `post-rewrite` (et `pre-commit`) déclarés dans `.knowledge/config.json` mais absents — l'upgrade de `code-index` les réinstalle ;
   - `models.migration_available` : `lab-models.json` à migrer, ce que fait `--upgrade` ;
   - `gh` : `gh auth login` ;
   - `signals.propose_rescan` : **proposer** `/software-factory --rescan` ; ne jamais le lancer.
3. **Proposition d'upgrade** (PR-01) : si `upgrade.changes` n'est pas nul, `proposal.gate` vaut `harness-doctor.upgrade-blocks` (le diff ne touche que des blocs, des fusions par union, la copie du noyau et le tampon) ou `harness-doctor.upgrade-other` (conversions, fichiers recréés, migrations). `proposal.decision` dit s'il faut `ask` ou `default`.
   - Gate `harness-doctor.upgrade-blocks` (options « Lancer l'upgrade » / « Ne rien faire », défaut **Lancer**) ; gate `harness-doctor.upgrade-other` (mêmes options, défaut **Ne rien faire** : rapporter la commande et les classes de `proposal.blockers`). `K gate decide --root . --id <gate>` puis, après AskUserQuestion, `K gate answer --run <run> --id <gate> --answer-file …` (réponse écrite par Write) ; sans interaction (headless) `--headless`, repli `default`.
   - **Politique `auto`** (UA-01, UA-02) : `K upgrade plan --root . --skill software-factory --interpreter "<PY>"` (puis `code-index`) écrit le plan sans toucher au projet, et `K doctor auto-upgrade --plan <plan.json> --autonomy auto` rend `action` : `apply` (plan non vide dont chaque changement est un bloc, une fusion par union, la copie du noyau ou le tampon, sans bloc divergent) → lancer l'upgrade sans question ; `propose` → ne rien lancer, afficher la commande et les changements en cause (`causes`) ; `none` → rien à faire (un second passage après upgrade donne un plan vide, UA-04). En `gate`, `action` = `ask` : poser la gate `harness-doctor.upgrade`. Le changement de `autonomy` (clé absente) n'est jamais un bloc : visible dans le diff, jamais appliqué par ce chemin.
4. Si l'upgrade est lancé : obtenir le nom effectif de chaque skill par `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" plugin skill-name --skill <skill> --skill-dir "${CLAUDE_SKILL_DIR}"` (champ `name` : `harness:<skill>` depuis le plugin, `<skill>` sinon), puis invoquer par l'outil Skill `software-factory` avec l'argument `--upgrade` puis, dans cet ordre, `code-index` avec `--upgrade`, chacun **seulement si son plan n'est pas vide** (`proposal.commands`). Si l'invocation d'un skill par l'outil Skill échoue, afficher les commandes à lancer, sans lancement automatique. Relancer ensuite `K doctor --root .` : le rapport final montre `upgrade.changes` à 0.

Le doctor n'écrit que son journal `.harness/runs/harness-doctor-<horodatage>.jsonl` (événements `doctor` et `gate`).

## Mode `--scan <racine> [--depth N]`

`K doctor scan --root <racine> [--depth N]` (profondeur 3 par défaut ; `N` entier ≥ 0, sinon exit 2) rend une ligne JSON par projet équipé, triée par chemin : `path`, `equipped_by`, `skills` (version installée par skill), `lag` (`status`, `commits`), `last_cycle` (skill, date, verdict, d'après l'horodatage **du nom** du journal), `next` (la commande d'upgrade si le projet est en retard). Afficher **une ligne de tableau par projet**. Le scan est en lecture seule absolue et ne lance **jamais** d'upgrade, même en `auto` (UA-03) : une ligne par projet, donner la commande `next` à lancer dans le projet concerné.

## Règles impératives

- Ne jamais modifier un fichier du projet autrement que par les skills d'upgrade ; ne jamais appeler `K upgrade apply` depuis ce skill.
- Ne jamais lancer `--rescan` : seulement le proposer.
- Les gates passent toutes par `K gate decide` / `K gate answer`, jamais décidées à la main.

## Défauts en politique `auto` (AP-09)

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement et n'écrit jamais `.claude/harness.json` ; elle est transmise à `K gate decide --autonomy` et aux skills enchaînés (AP-04). Défaut de chaque gate de ce skill en `auto`, avec sa justification d'une ligne (celle du catalogue `K gate list`) :

- `harness-doctor.upgrade-blocks` → Lancer l'upgrade — roadmap 4.2: a diff that only touches harness blocks is applied
- `harness-doctor.upgrade-other` → Ne rien faire — roadmap 4.2 reserves the automatic launch to diffs of blocks
- `harness-doctor.upgrade` → Lancer l'upgrade — applied when UA-01 holds (blocks, stamp or untouched core only), otherwise proposed
