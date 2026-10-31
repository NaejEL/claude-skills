---
name: factory-run
description: Lance un cycle de l'usine logicielle (Planner → gate humaine sur la spec → Builder → Verifier avec boucle de correction) sur un besoin ou une spec approuvée.
disable-model-invocation: true
argument-hint: "<besoin | chemin d'une spec approuvée> [--models \"role=modele;...\"]"
---

Piloter un cycle complet de l'usine logicielle du dépôt `claude-skills` sur l'entrée `$ARGUMENTS`. Toi, session principale, tu es l'orchestrateur : tu ne rédiges ni code ni spec toi-même, tu délègues aux sous-agents `factory-planner`, `factory-builder` et `factory-verifier`, et tu tiens la gate humaine.

Rappel du contexte du dépôt, à transmettre tel quel aux sous-agents s'ils en ont besoin : dépôt de skills Claude Code, un skill par dossier `skills/<nom>/SKILL.md` (Markdown français, frontmatter YAML), noyau partagé `skills/_core/` (Python, bibliothèque standard, qui n'est pas un skill), scripts d'installation jumeaux `install_skills.sh` (Bash, `set -euo pipefail`) et `install_skills.ps1` (PowerShell, `$ErrorActionPreference = 'Stop'`), inventaire dans `README.md`. Aucune compilation. Portes de vérification : `bash -n` sur les scripts Bash, `cd skills/_core/tests && <PY> -B -m unittest discover -s . -t .`, `bats tests/` si des tests `*.bats` existent, validité du frontmatter des `SKILL.md` touchés, aucun `__pycache__` restant.

## Noyau

Les règles déterministes du cycle sont portées par la copie du noyau sous `.claude/harness/` : ne jamais les réimplémenter à la main. Ci-dessous, `H` désigne `<PY> .claude/harness/harness.py`, où `<PY>` = l'interpréteur retenu par la règle D5 (le premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9 ; `py -3` sur la machine de l'utilisateur, où `python` est un leurre) : le champ `command` rendu par `python .claude/harness/harness.py interp`, à défaut par `python3 .claude/harness/harness.py interp`, puis par `py -3 .claude/harness/harness.py interp` — trois commandes simples, permises en headless par la liste blanche de `ci/factory.*`, là où une boucle shell ne l'est pas. Chaque commande rend un objet JSON ; son champ `action` dicte la suite : ne jamais sauter un appel ni décider à la place du noyau.

**Chaque sous-agent lancé est consigné** par `H factory-run record --run <run> --agent <nom> --duration-ms <ms> --tokens <n>`, avec les valeurs du bloc d'usage de l'outil Agent ; le modèle consigné est celui du rôle. Sans durée : `H begin --run <run> --slot <nom>` juste avant l'agent ; sans tokens : omettre l'option ; une mesure manquante est journalisée `null` et signalée, jamais bloquante ; connue seulement après l'appel, elle complète la dernière entrée du slot par `H journal amend --run <run> --slot <nom> --duration-ms <ms> --tokens <n>`. La sortie du Verifier est écrite telle quelle avec l'outil Write dans `.harness/runs/verifier-<n>.md`, puis passée par `--output .harness/runs/verifier-<n>.md` (jamais par stdin ni via le shell : backticks, `$`, apostrophes). `--dead` si l'agent est mort.

**Gates** : chaque gate passe par `H gate decide --run <run> --id <id>` (rend `decision`, `options`, `headless`), puis AskUserQuestion, puis `H gate answer --run <run> --id <id> --answer-file .harness/runs/gate-answer.txt` (réponse écrite par Write ; `factory-run.approval` : l'option mot pour mot, `reask` rendu → reposer la question). **Sans interaction possible (headless, `claude -p`), `H gate answer --run <run> --id <id> --headless` s'arrête en erreur explicite (exit 1) : un cycle CI exige le chemin d'une spec déjà approuvée.**

## 1. Qualifier l'entrée (FR-01)

Écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.harness/runs/factory-run-arguments.txt` (jamais dans une ligne de commande shell : un besoin peut contenir guillemets, `$` ou backticks), puis `H factory-run start --arguments-file .harness/runs/factory-run-arguments.txt` (le noyau supprime ce fichier de transit dès sa lecture). La commande ouvre le journal `.harness/runs/factory-run-<horodatage>.jsonl` (champ `run`) et rend `mode` :

- `build` : `$ARGUMENTS` est le chemin d'une spec existante sous `specs/` dont la ligne de statut vaut `Statut : APPROUVEE` → étape 3 ;
- `plan` : traiter `need` comme le besoin exprimé en langage naturel → étape 2. Si `need` est vide, demander le besoin à l'utilisateur avant toute chose (gate `factory-run.need`, saisie libre).

Elle retire de `$ARGUMENTS` l'option `--models "role=modele;…"` (rôles `factory.planner`, `factory.builder`, `factory.verifier`), valable pour ce cycle seulement (rôle ou valeur inconnus → exit 2), et rend `models` : passer à chaque sous-agent le paramètre `model` de l'outil Agent valant le `model` de son rôle quand `pass_param` est vrai, jamais pour `inherit`.

## 2. Phase Plan — gate humaine obligatoire

1. Lancer le sous-agent `factory-planner` avec le besoin intégral en entrée. Ne pas reformuler le besoin à sa place. Le consigner.
2. À son retour, lire la section *Questions ouvertes* du brouillon. Poser ces questions à l'utilisateur (gate `factory-run.questions`, options du brouillon : une question par point, avec des options concrètes tirées du brouillon). S'il n'y a aucune question ouverte, passer directement au point 3.
3. Intégrer les réponses au brouillon, puis écrire `specs/SPEC-<slug-du-besoin>.md` (créer `specs/` si besoin ; slug en minuscules, mots séparés par des tirets, sans accent). Le fichier commence par :

   ```markdown
   # SPEC — <titre>

   Statut : PROPOSEE
   ```

   suivi des sections *Contexte*, *Périmètre*, *Critères d'acceptation*, *Hors-périmètre*, *Risques*, *Décisions* (les réponses de l'utilisateur, question par question).
4. Présenter la spec à l'utilisateur et demander une **approbation explicite** (gate `factory-run.approval` : approbation / itérer). Tant qu'il n'approuve pas, itérer : intégrer ses remarques, réécrire la spec, redemander. En cas d'approbation, remplacer `Statut : PROPOSEE` par `Statut : APPROUVEE`.
5. **Si aucune interaction utilisateur n'est possible, s'arrêter immédiatement en erreur explicite** (repli headless `stop` des trois gates) : « Cycle headless impossible sur un besoin : fournir le chemin d'une spec déjà approuvée (`Statut : APPROUVEE`). » Ne jamais construire sans spec approuvée, sous aucun prétexte.

## 3. Phase Build

Lancer le sous-agent `factory-builder` dans un **contexte frais**, en lui passant le chemin de la spec approuvée et la consigne de s'y tenir strictement, de couvrir chaque critère d'acceptation, de passer les portes de vérification du dépôt avant de rendre la main, et de ne pas commiter. Le consigner (`--agent factory-builder`).

## 4. Phase Verify — boucle de correction, 3 itérations maximum

Lancer un sous-agent `factory-verifier` **neuf, en contexte vierge** (jamais celui du Builder), avec le chemin de la spec approuvée ; écrire sa sortie dans `.harness/runs/verifier-<n>.md` et la consigner (`--agent factory-verifier --output …`). Puis, selon `action` :

- `success` (FR-02 : `APPROVED` **et** `tests_passed` vrai) : sortir de la boucle, le cycle est un succès ;
- `fix` : relancer `factory-builder` (contexte frais) avec le chemin de la spec **et la liste complète des `issues` rendues** — pour chacune : `file`, `severity`, `description` — et la consigne de corriger chaque issue sans régresser sur les critères déjà satisfaits ; puis un **nouveau** Verifier ;
- `relaunch` (FR-04) : relancer **une fois** l'agent mort ou à la sortie inexploitable, sans consommer d'itération ;
- `fail` : **échouer explicitement** en publiant `reason` et la liste complète des issues restantes, avec leur sévérité et leur fichier — 3e itération non approuvée (FR-03) ou second échec d'un agent (FR-04) — et indiquer que la spec ou l'implémentation demande un arbitrage humain. **Ne jamais approuver par épuisement**, ne jamais reformuler un `CHANGES_REQUESTED` en succès partiel.

**Un Verifier muet n'est pas un Verifier satisfait** : ne jamais traiter l'absence de verdict comme une approbation, ne jamais passer à la suite sur un verdict absent. Un cycle qui livre du code non vérifié parce que son vérificateur est tombé est pire qu'un cycle qui échoue.

## 5. Rapport final

Conclure par un rapport structuré :

- **Spec** : chemin et statut.
- **Fichiers touchés** : sortie de `git status --porcelain`, commentée en une ligne par fichier.
- **Tests** : commandes exécutées par le Verifier et leur exit code.
- **Verdict** : `APPROVED` ou `CHANGES_REQUESTED`, avec les issues restantes le cas échéant.
- **Itérations** : nombre de passages dans la boucle Verify.
- **Journal** : chemin du journal `.harness/runs/factory-run-<horodatage>.jsonl` et mesures signalées manquantes.
- **Prochaine action** : inviter l'utilisateur à relire le diff (`git diff`) puis à commiter lui-même. **Ne jamais commiter à sa place.**
