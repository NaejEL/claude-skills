---
name: software-factory
description: Installe l'usine multi-agents du projet courant, point d'entrée unique — détecte les profils applicables (logiciel, recherche IA, …) par un scout, génère les sous-agents, le skill d'orchestration /factory-run, les scripts CI, les règles d'économie de tokens et les tâches VS Code. À utiliser quand l'utilisateur demande d'initialiser ou d'installer son usine logicielle ou son labo de recherche dans un projet, ou de rechercher les profils nouveaux (--rescan).
context: fork
user-invocable: true
argument-hint: "[--profile p[;p] | --rescan] [description optionnelle du premier besoin]"
---

# Software Factory — installation de l'usine, point d'entrée unique

Installer dans le projet courant l'usine multi-agents de chaque **profil** applicable (`software` : Planner, Builder, Verifier ; `research` : Director, Neuro, Math, Builder, Verifier), orchestrée par le skill projet `/factory-run`, en session comme en CI headless. L'utilisateur reste le Product Owner : aucune exigence n'est inventée à sa place, une gate humaine valide la spec avant toute construction. Un profil est un dossier de données sous `${CLAUDE_SKILL_DIR}/../_core/profiles/` (rôles, lentilles, orchestrateur, détection) : en ajouter un ne change aucun code.

Arguments (EP-01, `K sf args --arguments-file …`, fichier écrit par Write) : `--profile p[;p]` saute le scout et la gate (profil inconnu → exit 2) ; `--rescan` relance le scout ; les deux ensemble → exit 2. Le reste de `$ARGUMENTS` est le premier besoin, conservé tel quel, à rappeler au rapport final avec la commande `/factory-run` correspondante.

## Noyau déterministe

Les règles déterministes sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : CLI `harness.py`, paquet `hcore/`, profils `profiles/`. Ne jamais les réimplémenter : appeler la CLI et suivre sa sortie JSON. Règles : **PF** (`profiles.py`), **HJ** (`stamp.py`), **SC** (`scout.py`), **AR** (`gates.py`), **EP**, **LP** (`loop.py`), **SF-01** à **SF-04** (`fusion.py`), **ST-01** à **ST-04** (`stack.py`), **FR-01** à **FR-04**, **LR-01** à **LR-09**, **GT-01** à **GT-08**, **MD-01** à **MD-08**, **JR-01**, **JR-02**.

**Interpréteur** (règle D5, `hcore/interp.py`) : `<PY>` = le premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9, par `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`. Aucun candidat → s'arrêter : l'usine générée en dépend. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

## Règles impératives (toutes les phases)

- **Aucun placeholder** : chaque fichier généré est complet et opérationnel (pas de TODO, de pseudo-code, de commande inventée). Chaque commande écrite dans un prompt ou un script provient de la détection, jamais d'une supposition.
- **Fusion, jamais écrasement** : `.claude/settings.json`, `.vscode/tasks.json` et `.gitignore` sont créés ou fusionnés par le noyau (union additive, jamais éditée à la main). Un fichier existant illisible fait échouer la commande sans rien modifier.
- **Fichiers générés** (SF-04) : écrire chaque contenu tel quel avec l'outil Write sous `.harness/runs/`, puis `K sf install --dest <chemin> --source <ce fichier>` ; jamais par stdin ni shell (le contenu porte `$ARGUMENTS`, backticks, apostrophes). Le noyau crée, reconnaît l'identique, ou rend `personnalisé-conservé` (à signaler) ; il supprime le fichier de transit dès sa lecture.
- **Idempotence** : relancer ne détruit rien. Un profil ajouté n'écrit que ses fichiers, son bloc d'orchestrateur et l'union de ses entrées (EP-05) ; les fichiers d'un autre profil sont rendus `identique` ou `personnalisé-conservé`.

## Phase 1 — Profils (SC, AR, EP-02, EP-03)

`K stamp resolve --root .` : `stamp` ou `inferred` → profils lus, **pas de scout** ; `none` → scout. Avec `--rescan`, toujours le scout. Avec `--profile`, `K stamp add --root . --profiles "<p;p>" --by forced` plus tard (Phase 6).

**Scout.** `K scout signals --root .` rend les preuves déterministes et les critères `judgement`. Lancer l'outil Agent (`subagent_type: Explore`, lecture seule, paramètre `model` du rôle `harness.scout` quand `pass_param` est vrai) avec `${CLAUDE_SKILL_DIR}/../_core/scout/prompt.md`, les fragments `scout.md` de `K profile show <nom>` et ces critères ; il rend un bloc JSON `{"signals", "uncertainties"}`. Écrire ce bloc avec Write, puis `K scout verdict --root . --signals <fichier>` (preuves vérifiées, score, `proposal`, `clear`, verdict sous `.harness/runs/scout-*.json`). Agent mort ou sortie inexploitable : relancer **une fois**, puis `--scout-failed` (un scout muet n'est pas un scout d'accord).

**Gate `software-factory.profiles`** (une question à choix multiple par profil, score et statut dans le libellé, 4 choix au plus ; options « profils proposés » / « Abandonner »). `K gate decide --root . --id software-factory.profiles [--ambiguous --verdict <scout-*.json>]` : `--ambiguous` quand `clear` est faux. Autonomie `auto` et proposition nette → `default` ; proposition ambiguë → exit 1, avec le chemin du verdict et la reprise `/software-factory --profile <p>[;<p>]`. Puis `K gate answer … --answer-file`, ou `--default`, ou `--headless` (réponse `reask` → reposer la question). `--rescan` : `K stamp compare --root . --verdict <scout-*.json>` rend `added`, `kept`, `vanished` ; seuls les ajouts sont proposés, `vanished` est rapporté et jamais retiré ; rien à ajouter → aucune gate ni écriture, rapport « aucun profil nouveau ».

## Phase 2 — Détection

`K stack detect --root .` (ST-01 à ST-04) rend manifestes, `families` et `stacks`. Lire les manifestes pour les commandes réelles de build, test et lint ; puis suivre `install_text` de `K profile show <nom>` pour chaque profil retenu (détection propre au profil : corpus et matériel pour `research`). Le noyau est copié en Phase 5 ; sans commande de test, le Builder initialisera l'outillage standard (à signaler).

## Phase 3 — Sous-agents `.claude/agents/`

Pour chaque rôle de `K profile show <nom>` (`roles[]`, `mission_text`), rédiger intégralement le prompt système adapté au projet (rôle, périmètre, interdits, méthode, format de sortie) et installer par `K sf install … --model-role <model_role>` (`--model-role factory.planner`, `factory.builder`, `factory.verifier` pour le profil `software`) : le noyau écrit le bloc `# >>> harness.model >>>` (`model:` tiré de `.claude/models.json`, absent → `inherit`) ; ne jamais écrire `model:` à la main ; un agent personnalisé dont seul ce bloc est réécrit est rendu `bloc-mis-à-jour`. Frontmatter : `name`, `description`, `tools` (`read_only` : lecture seule, pas de champ `tools` pour un Builder).

## Phase 4 — Orchestrateurs (EP-06, LP)

`.claude/skills/factory-run/SKILL.md` : `name: factory-run`, `disable-model-invocation: true`, `argument-hint: "<besoin | chemin d'un artefact prêt> [--profile p] [--models \"role=modele;...\"]"`. Corps : `H` = `<PY> .claude/harness/harness.py` ; `H factory-run start --arguments-file …` route l'entrée (artefact prêt → profil propriétaire en `build`, `suivant` → `research`, `--profile p`, texte libre → gate `factory-run.profile`, option « profil du besoin », défaut le premier profil du tampon) ; puis **un bloc `<!-- harness.profile.<nom>:debut -->` … `<!-- harness.profile.<nom>:fin -->` par profil actif**, contenant `orchestrator_text` adapté au projet (`K block` pour insérer ou remplacer ; texte hors bloc inchangé). Chaque sous-agent est consigné par `H factory-run record --run <run> --agent <nom> [--mode …] --duration-ms <ms> --tokens <n> --output .harness/runs/<x>.md` (sortie écrite avec Write ; `--dead` si mort ; `H journal amend` complète une mesure connue après l'appel). Le noyau retire `--models "role=modele;…"` de l'entrée (rôles `factory.planner`, `factory.builder`, `factory.verifier`, …) : passer à chaque sous-agent le paramètre `model` du rôle quand `pass_param` est vrai, jamais pour `inherit`. Gates du cycle : gate `factory-run.questions` (« options du brouillon »), gate `factory-run.approval` (« approbation » / « itérer »). Si `research` est actif, générer aussi `.claude/skills/lab-run/SKILL.md` (seconde instance du gabarit, `K factory-run start --orchestrator lab-run`). Un orchestrateur existant **sans** blocs n'est pas réécrit (`personnalisé-conservé`, renvoi à `--upgrade`).

## Phase 5 — Noyau, CI et fusions

`K sf copy-core --root .` copie `_core` (profils compris) sous `.claude/harness/`. Si un fichier diffère : exit 1, s'arrêter là en affichant le message, sans CI, sans fusion, **sans tampon** (EP-07). Scripts `ci/factory.sh` / `ci/factory.ps1` (profil `software`, `ci` de `K profile show`) et `ci/lab.*` (`K lab ci`) : argument obligatoire, `--yolo`, contrôle de la ligne de statut `ci.status_line`, `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, `--max-turns` du profil, liste blanche détectée, journal sous `ci.logs_dir`, exit code propagé (bash `set -euo pipefail`, PowerShell `$ErrorActionPreference = 'Stop'`). Fusions : `K sf apply --root . --stacks <stacks> --profiles "<p;p>" [--test-command "…"]` (SF-01 à SF-03, union des profils). Gate `ai-lab.models` si `research` (voir `install_text`).

## Phase 6 — Base de connaissance, tampon, rapport

Gate `software-factory.code-index` **une seule fois** quel que soit le nombre de profils : `K gate decide --root . --id software-factory.code-index`, AskUserQuestion (installer / refus, défaut refus), `K gate answer --run <run> … --answer "<installer|refus>"` ; accord → skill `code-index` ; headless : `--headless` (repli `skip`). Ne jamais installer sans accord.

**En dernier**, génération réussie : `K stamp add --root . --profiles "<p;p>" --by scout|forced|inferred|fallback` (HJ-05 ; jamais de retrait). Rapport : stack, interpréteur, profils et `by`, état de chaque fichier (créé / fusionné / identique / personnalisé-conservé) `.claude/harness/` compris, modèles, mode d'emploi (`/factory-run "besoin"` ; CI `ci/factory.sh specs/SPEC-x.md`) et, si `$ARGUMENTS` contenait un besoin, `/factory-run "<le besoin>"`.
