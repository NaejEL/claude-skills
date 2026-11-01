---
name: software-factory
description: Installe l'usine multi-agents du projet courant, point d'entrée unique — détecte les profils applicables (logiciel, recherche IA, …) par un scout, génère les sous-agents, le skill d'orchestration /factory-run, les scripts CI, les règles d'économie de tokens et les tâches VS Code. À utiliser quand l'utilisateur demande d'initialiser ou d'installer son usine logicielle ou son labo de recherche dans un projet, ou de rechercher les profils nouveaux (--rescan).
context: fork
user-invocable: true
argument-hint: "[--profile p[;p] | --rescan | --upgrade [--convert]] [--autonomy gate|auto] [description optionnelle du premier besoin]"
---

# Software Factory — installation de l'usine, point d'entrée unique

Installer dans le projet courant l'usine multi-agents de chaque **profil** applicable (`software` : Planner, Builder, Verifier ; `research` : Director, Neuro, Math, Builder, Verifier), orchestrée par le skill projet `/factory-run`, en session comme en CI headless. L'utilisateur reste le Product Owner : aucune exigence n'est inventée à sa place, une gate humaine valide la spec avant toute construction. Un profil est un dossier de données sous `${CLAUDE_SKILL_DIR}/../_core/profiles/` (rôles, lentilles, orchestrateur, détection) : en ajouter un ne change aucun code.

Arguments (EP-01, `K sf args --arguments-file …`, fichier écrit par Write) : `--profile p[;p]` saute le scout et la gate (profil inconnu → exit 2) ; `--rescan` relance le scout ; les deux ensemble → exit 2 ; `--upgrade [--convert]` met à jour un projet équipé (section « Mode `--upgrade` », exclusif de `--profile` et `--rescan`). Le reste de `$ARGUMENTS` est le premier besoin, conservé tel quel, à rappeler au rapport final avec la commande `/factory-run` correspondante.

## Noyau déterministe

Les règles déterministes sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : CLI `harness.py`, paquet `hcore/`, profils `profiles/`. Ne jamais les réimplémenter : appeler la CLI et suivre sa sortie JSON. Règles : **PF** (`profiles.py`), **HJ** (`stamp.py`), **VS** (`version.py`), **CO** (`history.py`), **RD**/**EN** (`render.py`), **UP** (`upgrade.py`), **MI** (`migrate.py`), **CV** (`convert.py`), **SC** (`scout.py`), **AR** (`gates.py`), **EP**, **LP** (`loop.py`), **SF-01** à **SF-04** (`fusion.py`), **ST-01** à **ST-04** (`stack.py`), **FR-01** à **FR-04**, **LR-01** à **LR-09**, **GT-01** à **GT-08**, **MD-01** à **MD-08**, **JR-01**, **JR-02**.

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

## Phases 3 à 5 — Génération déterministe (EP-11, RD-01 à RD-07)

Les sous-agents `.claude/agents/`, les orchestrateurs `.claude/skills/<orchestrateur>/SKILL.md`, les scripts `ci/*`, la copie du noyau `.claude/harness/` (avec `MANIFEST.json`), les fusions (`settings.json`, `tasks.json`, `.gitignore`), la migration de `lab-models.json` et le tampon `.claude/harness.json` sont produits **en un seul plan** par le noyau, sans que le LLM rédige un fichier : chaque fichier est écrit dans la mise en page **en-tête de version, blocs `harness.*`, zones libres hors bloc** (`harness.frontmatter`, `harness.body`, `harness.profile.<nom>`, `harness.ci`). Le contenu d'un bloc est une fonction pure du fragment du profil et des paramètres : les mêmes entrées donnent les mêmes octets, ce qui rend `--upgrade` idempotent.

1. **Paramètres** (RD-03, RD-04). Les paramètres `detected` (stacks, interpréteur) sont calculés par le noyau. Les paramètres `judgement` du profil (`params[]` de `K profile show <nom>` : commandes de build, de test, de lint, conventions citées, outils CI supplémentaires) sont **rédigés une seule fois** : lire les manifestes rendus par `K stack detect --root .`, écrire un objet JSON `{"test_command": "…", …}` avec Write dans `.harness/runs/sf-params.json`. Un paramètre déjà enregistré dans le tampon n'est jamais redemandé.
2. **Plan** : `K upgrade plan --root . --skill software-factory --profiles "<p;p>" --by scout|forced|inferred|fallback [--params-file .harness/runs/sf-params.json] --interpreter "<PY>"`. Un champ `action` valant `fill_params` (paramètres requis absents, rien d'écrit) renvoie à l'étape 1. Sinon la commande écrit `.harness/runs/upgrade-<horodatage>.plan.json` et `.diff`, sans toucher au projet.
3. **Copie du noyau** (D1, CO-04) : un fichier de `.claude/harness/` personnalisé arrête tout (exit 1, `core not upgraded`) ; rien n'est écrit, **sans tampon** (EP-07) ; le message donne la remise en état puis `/software-factory --upgrade`. Jamais de noyau mélangé.
4. **Apply** : `K upgrade apply --root . --plan <plan> [--decisions-file …]`. Tout ou rien, tampon en dernier. Un fichier existant sans bloc (installation antérieure) est converti sans perte s'il est resté tel que généré ou s'il n'a reçu qu'un ajout en fin de fichier ; sinon il est conservé tel quel et rapporté `legacy` (gate `upgrade.convert`, voir la section `--upgrade`).
5. **Orchestrateurs** (EP-06, LP) : le corps généré de `factory-run` route l'entrée (`H factory-run start` : artefact prêt → profil propriétaire en `build`, `suivant` → `research`, `--profile p`, texte libre → gate `factory-run.profile`, option « profil du besoin », défaut le premier profil du tampon), avec **un bloc `harness.profile.<nom>` par profil actif**. Gates du cycle : gate `factory-run.questions` (« options du brouillon »), gate `factory-run.approval` (« approbation » / « itérer »). Si `research` est actif, `lab-run` est la seconde instance du gabarit (`K factory-run start --orchestrator lab-run`). Gate `factory-run.ship` (CH-02, options « livrer et lancer ship-pr » / « ne pas livrer », défaut **livrer** en `auto`, repli headless : suggestion seule) après un cycle réussi. Chaque sous-agent y est consigné par `H factory-run record --run <run> --agent <nom> --duration-ms <ms> --tokens <n>` (sortie écrite avec Write ; `--dead` si mort ; `H journal amend` complète une mesure connue après l'appel). Le modèle de chaque agent vient de `.claude/models.json` (absent : `inherit`), écrit dans le bloc `harness.frontmatter`. Le noyau retire `--models "role=modele;…"` de l'entrée de `factory-run` (valable pour ce cycle seulement) : passer à chaque sous-agent le paramètre `model` du rôle quand `pass_param` est vrai, jamais pour `inherit`. Repli sans plan (SF-04, X1 : le noyau écrit alors le bloc `# >>> harness.model >>>`) : `K sf install --dest <chemin> --source <fichier écrit par Write> --model-role factory.planner|factory.builder|factory.verifier` installe un fichier rédigé à la main, sans jamais écraser ; le chemin normal est le plan ci-dessus.
6. **Fusions** (SF-01 à SF-03, union des profils) et gate `ai-lab.models` si `research` (voir `install_text`) font partie du même plan ; le rapport renvoie à `--upgrade` pour tout fichier conservé.

## Mode `--upgrade` (EP-08 à EP-11, UP, CV, MI, CO)

`/software-factory --upgrade [--convert]` met à jour un projet **déjà équipé**, pour **tous** les profils du tampon. Il exclut `--profile` et `--rescan` (exit 2), et tout autre contenu à côté de `--upgrade` (exit 2) ; `/ai-lab --upgrade` se traduit par `--upgrade` **sans** `--profile research`. Seuls les blocs délimités sont régénérés ; tout le hors-bloc est préservé (invariant vérifié avant l'écriture). Il est idempotent : relancé sans changement, il ne produit aucun diff.

1. `K version` (version du dépôt) puis `K stamp resolve --root .` : source `none` → s'arrêter, `project not equipped: run /software-factory`. Un projet sans tampon est détecté par ses fichiers générés (`generation` : `pre-core`, `core-<v>`, `stamp-phase2`) ; le tampon est créé à la fin du premier upgrade réussi (`inferred_from`).
2. `K upgrade plan --root . --skill software-factory [--convert] --interpreter "<PY>"` (étape `fill_params` de la section précédente si besoin). Un projet installé par un harnais plus récent que le dépôt est refusé (`newer harness`, exit 1) : pas de retour en arrière, mettre à jour claude-skills (`git pull`) d'abord.
3. **Afficher le diff complet** (`.diff`, sans troncature) avant l'apply, avec la classe de chaque modification : `header`, `block`, `merge`, `copy`, `create`, `convert`, `migrate`, `stamp`.
4. **Gate `upgrade.convert`** si le plan porte `gate.files` : fichiers générés avec modifications locales (`modified`) ou jamais commités (`untracked`). Options « Conserver tel quel » (défaut) / « Convertir (sauvegarde) ». `K gate decide --root . --id upgrade.convert`, AskUserQuestion, `K gate answer --run <run> --id upgrade.convert --answer "<option>"` ; écrire la décision avec Write dans `.harness/runs/upgrade-decisions.json` (`{"files": {"<chemin>": "keep|convert"}, "source": "user|headless|default"}`). `--convert` vaut « Convertir » pour tous ces fichiers (journalisé). Sans interaction : repli `default`.
5. `K upgrade apply --root . --plan <plan> [--decisions-file .harness/runs/upgrade-decisions.json]` : vérifie que le projet n'a pas changé depuis le plan (`plan is stale` sinon : replanifier), sauvegarde chaque fichier modifié sous `.harness/runs/upgrade-<horodatage>/backup/`, écrit tout ou rien, le tampon en dernier, et journalise un événement `upgrade` par fichier.
6. Rapport : état de chaque fichier et sa classe, chemin de la sauvegarde, nouvelle version, fichiers `legacy` restants (à convertir par `--convert`), anciens livrables d'audit « repris par le prochain /audit », fichiers `extra` de `.claude/harness/` (jamais supprimés). Ne lance pas `code-index --upgrade` : c'est le rôle de `/harness-doctor`.

Un bloc édité à la main est remplacé (sauvegarde) : la personnalisation se fait **hors bloc**.

## Phase 6 — Base de connaissance, tampon, rapport

Gate `software-factory.code-index` **une seule fois** quel que soit le nombre de profils : `K gate decide --root . --id software-factory.code-index`, AskUserQuestion (installer / refus, défaut refus), `K gate answer --run <run> … --answer "<installer|refus>"` ; accord → skill `code-index` ; headless : `--headless` (repli `skip`). Ne jamais installer sans accord.

**Autonomie et hooks** (AP-05, HK-06) : `K stamp autonomy --root . [--autonomy gate|auto]` écrit `"autonomy": "auto"` si la clé est absente (ou la valeur donnée) et ne remplace jamais une valeur existante ; la valeur retenue figure au rapport. Les hooks sont installés par `K hooks install --root . --py "<PY>" [--lint-file .harness/runs/lint.json]` (fusion additive de `.claude/settings.json`, JSONC conservé ; `--lint-file` = liste Write `[{"glob", "argv" avec `{file}`, "timeout_s"}]` des seules commandes de lint réellement configurées, en mode vérification) ; `--upgrade` les régénère. Dire au rapport que les hooks ne valent qu'à la session suivante (ou après revue dans `/hooks`).

**En dernier**, génération réussie : `K stamp add --root . --profiles "<p;p>" --by scout|forced|inferred|fallback` (HJ-05 ; jamais de retrait). Rapport : stack, interpréteur, profils et `by`, état de chaque fichier (créé / fusionné / identique / personnalisé-conservé) `.claude/harness/` compris, modèles, mode d'emploi (`/factory-run "besoin"` ; CI `ci/factory.sh specs/SPEC-x.md`) et, si `$ARGUMENTS` contenait un besoin, `/factory-run "<le besoin>"`.

## Défauts en politique `auto` (AP-09)

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement et n'écrit jamais `.claude/harness.json` ; elle est transmise à `K gate decide --autonomy` et aux skills enchaînés (AP-04). Défaut de chaque gate de ce skill en `auto`, avec sa justification d'une ligne (celle du catalogue `K gate list`) :

- `software-factory.code-index` → refus — the knowledge base adds a versioned folder; installation stays possible at any time
- `factory-run.need` → aucun (arrêt) — a need cannot be guessed
- `software-factory.profiles` → proposition — a clear scout proposal is taken; an ambiguous one is never guessed
- `upgrade.convert` → Conserver tel quel — a file with local changes is converted to blocks only when asked
