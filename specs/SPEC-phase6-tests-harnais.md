# SPEC — Phase 6 : tests du harnais

Statut : APPROUVEE (2026-10-17). Défauts des questions ouvertes retenus, Q6 compris (option de cible ajoutée aux deux installeurs).

Phase 6 de `specs/harness-v2/ROADMAP.md`. Cette spec suppose les Phases 1 à 5 livrées. `BASE6` désigne le commit de fin de la Phase 5, relevé au lot L0. Elle reprend les conventions des specs précédentes :
- `<PY>` : l'interpréteur détecté (`py -3` sur la machine de l'utilisateur) ;
- `T` : `cd skills/_core/tests && <PY> -B -m unittest discover -s . -t .` ;
- `K` : `<PY> skills/_core/harness.py` ;
- les recherches utilisent `grep`, parce que `rg` est absent du PATH de Git Bash.

Abréviations propres à cette spec :
- `S` = `specs/SPEC-phase6-tests-harnais.md` ;
- `R` = `bash ci/test-harness.sh` ;
- `P` = `pwsh -NoProfile -File ci/test-harness.ps1`.

Règle de l'utilisateur appliquée : **la ROADMAP fait foi**. Seuls les points impossibles techniquement ou contraires à la doc Claude Code sont remontés, avec les repères **[IMPOSSIBLE]** et **[DOC]**.

## Contexte

### Le besoin

La ROADMAP §6 demande :
- des fixtures `ci/fixtures/` : un ou deux projets jouets, et un dépôt git avec un remote factice ou un dépôt bare local ;
- huit scénarios exécutables, chacun avec un résultat vérifiable par script : installation à neuf ; `--upgrade` d'un projet installé à l'ancienne, personnalisations hors bloc conservées ; `factory-run` complet en `auto` jusqu'au Verifier ; `ship-pr` sans finding qui merge automatiquement ; hook qui bloque hors du diff ; `models.json` absent ; `lab-models.json` legacy ; arrêt propre à la 3e itération ;
- une évaluation de l'outillage d'évaluation de Claude Code, à défaut les scripts `ci/test-harness.sh|.ps1`.

### Point de départ (vérifié par lecture)

- **Tests unitaires et rejeux.**
  - `skills/_core/tests/` : `unittest`, rejeux scriptés par règle (`test_replay.py`, factory-run et ship-pr).
  - Faux `gh` : `fake_gh.py`. Il simule `auth status`, `repo view`, `pr list|create|view|diff|comment|merge`, `api graphql` et les réponses aux commentaires. Toute autre commande rend exit 2 avec `fake gh: command not simulated`. **Ni `gh pr checks` ni l'API de protection de branche ne sont simulés.**
  - Injection de commande : `HCORE_GH` / `HCORE_GIT`, honorés seulement avec `HCORE_TEST_MODE=1` (`hcore/proc.py`).
  - Le remote d'origine doit contenir `github.com` (`hcore/ghflow.py`). C'est pourquoi les rejeux placent le dépôt bare sous `<tmp>/github.com/acme/toy.git`.
- **Fixtures existantes (`tests/fixtures/`, Q13 du BACKLOG).**
  - `toy-project/` : Node. `npm test` = `node --test`, avec `specs/SPEC-somme.md` en `Statut : APPROUVEE`.
  - `merge-input/` et `merge-expected/`.
  - Les fixtures `profile-*`, `audit-*` et `profile-extraction/` de la Phase 2.
  - Convention (`tests/fixtures/README.md`) : aucun nom pointé, aucun `CLAUDE.md` ; les tests renomment dans un dossier temporaire (Phase 2, CA-30, [DOC] I6).
  - `helpers.py` saute les tests à fixtures quand le noyau est copié dans un projet.
- **`ci/`** ne contient que l'usine du dépôt : `ci/factory.sh` et `ci/factory.ps1`. Aucun test de bout en bout du harnais, aucun test des installeurs.
- **Installeurs.**
  - Cible fixée sur `$HOME/.claude/skills` (`install_skills.sh`, `install_skills.ps1`).
  - Bash : `ln -s` et `readlink`. PowerShell : jonctions.
  - Aucune option pour changer la cible.
- **Faits Claude Code (BACKLOG §5).**
  - `claude plugin eval` sait préparer une fixture (`scaffold_script`), mais aucun grader n'exécute de commande shell.
  - `claude -p --permission-prompts none` retire `AskUserQuestion`.
  - Un PreToolUse bloque par exit 2.
- **Recette R1** (BACKLOG §7) : des skills exposés par une jonction sous `<projet>/.claude/skills/` répondent en headless (`claude -p "/probe"`, avec `MSYS_NO_PATHCONV=1` sous Git Bash).
- **Machine** : le stub `python` du Microsoft Store ne répond pas, `py -3` donne 3.9.13, pytest est absent.

### Articulation des deux dossiers de fixtures

| Dossier | Rôle | Consommateur | Décision |
| --- | --- | --- | --- |
| `tests/fixtures/` | Données unitaires : entrées et attendus d'une règle | `T` | Inchangé. Q13 reste tranchée. |
| `ci/fixtures/` | Projets de scénario de bout en bout, plus les sorties d'agents simulés | `R` et `P` | Nouveau. Il **référence** `tests/fixtures/toy-project` au lieu de le copier : aucune fixture n'existe en double. |

## Périmètre

### 1. Fixtures `ci/fixtures/` — `FX`

- `FX-01` : **`toy-py/`**, projet jouet exécuté par les scénarios.
  - Python stdlib, tests en `unittest`. La seule dépendance est l'interpréteur, déjà exigé par le noyau.
  - Contenu : un module, un test vert, un `specs/` vide, un fichier `claude-md.txt` renommé `CLAUDE.md` à la copie.
  - Aucun corpus scientifique : le scout attendu retient `software` seul.
- `FX-02` : **`legacy-node/`**, projet installé « à l'ancienne », figé.
  - Sources : celles de `tests/fixtures/toy-project`, par référence déclarée dans `legacy-node/fixture.json`.
  - Fichiers générés d'avant la v2, sans bloc délimité ni tampon : `claude/agents/factory-*.md`, `claude/skills/factory-run/SKILL.md`, `ci/factory.sh|.ps1`, tels qu'ils sont dans ce dépôt au commit `7be1afb` (BASE de la spec 0, sortie réelle de software-factory).
  - `claude/settings.json`, `vscode/tasks.json`, `gitignore.txt`.
  - Un `claude/lab-models.json` au format d'ai-lab.
- `FX-03` : `legacy-node/customizations.json`. Il liste chaque personnalisation hors bloc semée : fichier, extrait exact, raison. Au minimum :
  - une consigne ajoutée au prompt de `factory-builder.md` ;
  - une section ajoutée à `factory-run/SKILL.md` ;
  - une règle `deny` et une clé tierce dans `settings.json` ;
  - une tâche utilisateur dans `tasks.json` ;
  - une ligne utilisateur dans `.gitignore` ;
  - une valeur non par défaut dans `lab-models.json`.
- `FX-04` : **remote** : un dépôt bare local, **créé à l'exécution** dans le dossier temporaire du scénario, sous `<tmp>/github.com/acme/<projet>.git` (contrainte de `ghflow.py`). Jamais versionné (Q3).
- `FX-05` : `ci/fixtures/agents/<scénario>/` : sorties figées des agents simulés (SM-01) et correctifs du Builder simulé.
- `FX-06` : `ci/fixtures/expected/<scénario>/` : attendus déterministes (liste de fichiers, JSON fusionnés, extraits de `STOP-*.md`).
- `FX-07` : convention de `tests/fixtures/` étendue à `ci/fixtures/` : aucun nom pointé, aucun `CLAUDE.md`, renommage dans le dossier temporaire. `ci/fixtures/README.md` documente la provenance de chaque fichier (commit d'origine) et le renommage.

### 2. Rejeu déterministe : agents simulés et faux `gh` — `SM`

- `SM-01` : un **agent simulé** est une sortie figée (FX-05). Elle est écrite par le runner là où le SKILL.md prescrit l'outil Write (`.harness/runs/…`), puis passée au noyau par `--output`, exactement comme `test_replay.py`.
  - **Builder simulé** : applique un correctif figé (`git apply`).
  - **Verifier simulé** : exécute la **vraie** commande de test du projet (`<PY> -m unittest`). Son `tests_passed` reflète l'exit code réel.
  - **Scout simulé** : sortie figée au format SC-03 de la Phase 2.
- `SM-02` : le runner joue **la séquence d'appels au noyau prescrite par les SKILL.md** et par l'orchestrateur généré. Il appelle la copie installée `<tmp>/.claude/harness/harness.py` pour factory-run, et le noyau atteint par `${CLAUDE_SKILL_DIR}/../_core` pour ship-pr. Il ne rejoue pas le LLM orchestrateur : c'est impossible au mot près ([IMPOSSIBLE], D10).
- `SM-03` : faux `gh` = `skills/_core/tests/fake_gh.py`, injecté par `HCORE_GH` avec `HCORE_TEST_MODE=1`. Il est complété, si la Phase 4 ne l'a pas fait, de chaque commande que le merge automatique appelle : `gh pr checks` (vert, rouge, sans CI) et la requête de protection de branche retenue en Phase 4. L'état de chacune est réglable par le fichier `HCORE_FAKE_GH_STATE`. Une commande non simulée reste un exit 2, et fait donc échouer le scénario.
- `SM-04` : en mode déterministe, le runner place en tête du PATH des cales `gh` et `claude` qui comptent chaque appel et échouent. Tout appel au vrai `gh` ou au vrai `claude` est visible dans le rapport (`real_gh_calls`, `real_claude_calls`).
- `SM-05` : aucun scénario ne lit ni n'écrit hors de son dossier temporaire et du dossier temporaire servant de `HOME` : ni le vrai `~/.claude`, ni ce dépôt, ni le réseau.

### 3. Scénarios déterministes — `SC`

Chaque scénario part de ses fixtures, dans un dossier temporaire neuf, indépendamment des autres (Q10). Il rend une liste d'assertions identifiées `<scénario>.<n>`, toutes vérifiées par le runner et reportées dans le rapport (TH-04). Une installation rejouée (`install-fresh`, étapes 1 à 5) sert de préparation aux scénarios qui en ont besoin ; ses assertions ne sont comptées que dans `install-fresh`.

**`install-fresh`** — installation à neuf de `/software-factory` sur `toy-py`, rejouée (copy-core, scout simulé, arbitrage, `sf install` des fichiers figés, `sf apply`, hooks de la Phase 5, tampon) :
- `install-fresh.1` : l'ensemble des fichiers créés est égal à `expected/install-fresh/files.txt`.
- `install-fresh.2` : chaque fichier est rendu `créé` au premier passage.
- `install-fresh.3` : `diff -r -x __pycache__ skills/_core <tmp>/.claude/harness` est vide, et `harness.py version` y rend `CORE_VERSION`.
- `install-fresh.4` : `settings.json`, `tasks.json` et `.gitignore` sont égaux aux attendus (JSON parsé, ordre des clés compris).
- `install-fresh.5` : `.claude/harness.json` porte `autonomy: "auto"` (défaut installé, §4.1), `profiles` = `software` avec `by: scout`, et la version attendue par la Phase 3.
- `install-fresh.6` : `settings.json` déclare les hooks de la Phase 5, chacun pointant vers des scripts sous `.claude/harness/`.
- `install-fresh.7` : chaque fichier régénérable porte l'en-tête de version de la Phase 3.
- `install-fresh.8` : un second passage, après commit du premier dans le dépôt temporaire, rend tout `identique`, et `git status --porcelain` est vide.
- `install-fresh.9` : le journal d'installation passe `journal validate` et contient une ligne `agent: harness-scout`.

**`install-skills`** — installeurs globaux vers une cible temporaire (Q6) :
- `install-skills.1` : `install_skills.sh --skip-tools --target <tmp>` crée un lien par sous-dossier de `skills/`, `_core` compris.
- `install-skills.2` : `_core` lié ne contient pas de `SKILL.md`.
- `install-skills.3` : un second passage rend exit 0 et une ligne `[ok]` par lien.
- `install-skills.4` : un vrai dossier déjà présent à la cible rend `[skip]`, exit 1, et le dossier reste intact.
- `install-skills.5` : mêmes résultats pour `install_skills.ps1 -SkipTools -TargetRoot <tmp>`, en jonctions (Windows) ou en symlinks (pwsh hors Windows). Le jeu de noms liés est identique entre les deux scripts.
- `install-skills.6` : sous Git Bash sans symlinks natifs : `SKIP` motivé, jamais `PASS` (Q7).

**`upgrade-legacy`** — `--upgrade` sur `legacy-node` :
- `upgrade-legacy.1` : avant, `stamp resolve` rend `inferred` / `software`, et `/harness-doctor` (commande du noyau de la Phase 3) signale le tampon absent et propose `--upgrade`, sans le lancer en `gate`.
- `upgrade-legacy.2` : la sortie d'upgrade contient le diff complet. Il ne touche que des blocs délimités, des fichiers nouveaux, `harness.json` et `models.json`, ou les fichiers que la décision Q6 de la Phase 3 (premier upgrade sans blocs) autorise.
- `upgrade-legacy.3` : après application, chaque extrait de `customizations.json` est retrouvé à l'identique (`grep -F`) dans son fichier.
- `upgrade-legacy.4` : `harness.json` est créé, avec version et profils.
- `upgrade-legacy.5` : `models.json` est créé avec les clés `lab.*` aux valeurs de `lab-models.json`, et `lab-models.json` reste identique octet pour octet.
- `upgrade-legacy.6` : un second `--upgrade` produit zéro diff et l'annonce.
- `upgrade-legacy.7` : après upgrade, `factory-run start` sur une spec `APPROUVEE` rend `build` avec la copie `.claude/harness/` installée.
- `upgrade-legacy.8` : sur une copie non mise à jour, aucun fichier de la fixture n'est modifié par une réinstallation sans `--upgrade`. Les fichiers différents sont rendus `personnalisé-conservé` (rétrocompatibilité).

**`factory-auto`** — cycle `factory-run` complet en `auto` jusqu'au Verifier, sur `toy-py` installé :
- `factory-auto.1` : le besoin, écrit par Write, est routé par `start` en `plan`.
- `factory-auto.2` : le Planner simulé déclare zéro question ouverte bloquante (champ explicite de la Phase 4). La spec est écrite puis passe à `Statut : APPROUVEE` sans demande. Le journal porte les événements `gate` de `factory-run.approval` avec `source: default`.
- `factory-auto.3` : le Builder simulé applique son correctif.
- `factory-auto.4` : le Verifier simulé exécute les tests réels (exit 0), rend `APPROVED` avec `tests_passed: true`, et le noyau rend `success` à l'itération 1.
- `factory-auto.5` : le journal passe `journal validate`, avec la suite d'agents planner, builder, verifier.
- `factory-auto.6` : aucun événement `gate` n'a pour décision `ask`, et aucun `STOP-*.md` n'existe.
- `factory-auto.7` (contre-épreuve) : avec une question bloquante, la spec est `BLOQUEE`, un `STOP-*.md` est écrit, et le journal n'a aucune ligne Builder. Une fois la réponse écrite dans la spec, une relance reprend et atteint `success`.

**`shippr-automerge`** — `ship-pr` sans finding sur `toy-py`, branche `feature` poussée vers le bare, en `auto` :
- `shippr-automerge.1` : chaque relecteur simulé rend `{"findings": []}`, et `end-round` sort par `exhaustion` à la ronde 1, sans aucune ligne de validateur.
- `shippr-automerge.2` : les conditions de merge de §4.2 sont toutes vraies, et le faux `gh` a reçu `pr merge --merge --delete-branch`, jamais `--squash` ni `--rebase`.
- `shippr-automerge.3` : la branche `main` du bare contient le commit de `feature`, la branche locale est supprimée, et la branche courante est `main`.
- `shippr-automerge.4` : l'événement `gate` de `ship-pr.merge` porte `source: default`, et aucune question n'est posée.
- `shippr-automerge.5` (contre-épreuve) : `gh pr checks` rouge → aucun appel `pr merge`, raison dans le journal et dans un commentaire de PR (état du faux `gh`), sortie sans erreur.
- `shippr-automerge.6` (contre-épreuve) : branche cible protégée → même issue que `.5`.
- `shippr-automerge.7` (contre-épreuve) : un thème mort deux fois → merge refusé, même en `auto` (SP-05).

**`hook-diff`** — hook PreToolUse de `ship-pr`, exécuté **par la ligne de commande lue dans `.claude/settings.json`** du projet installé, avec une entrée JSON au format PreToolUse de la doc des hooks et `CLAUDE_PROJECT_DIR` posé :
- `hook-diff.1` : avec l'activation de la Phase 5 posée par `ship-pr start`, un `Edit` sur un fichier hors de `git diff --name-only main...HEAD` rend exit 2, avec un stderr qui nomme le fichier et rappelle le périmètre limité au diff.
- `hook-diff.2` : un `Write` d'un fichier nouveau hors du diff rend exit 2.
- `hook-diff.3` : un `Edit` sur un fichier du diff rend exit 0.
- `hook-diff.4` : sans activation, les trois cas rendent exit 0 (les éditions manuelles ne sont pas bloquées).
- `hook-diff.5` : erreur interne (entrée JSON invalide, ou `git` retiré du PATH) → exit 0 et un avertissement sur stderr.
- `hook-diff.6` : une seconde dérive bloquée dans le même cycle → arrêt (a) et `STOP-*.md` avec commande de reprise (Phase 5, §4.3).

**`models-absent`** — `models.json` absent :
- `models-absent.1` : chaque rôle du jeu fermé est résolu en `inherit` avec `pass_param: false`, sauf `harness.scout`, résolu en `haiku` (SC-04 de la Phase 2).
- `models-absent.2` : un rejeu factory-run journalise `model: "inherit"` pour chaque agent.
- `models-absent.3` : aucun `models.json` n'est créé par le cycle.
- `models-absent.4` : `/harness-doctor` signale `models.json` absent.
- `models-absent.5` : `--models "factory.verifier=haiku"` → `pass_param: true` pour le Verifier seul, et le fichier reste absent.

**`models-legacy`** — `lab-models.json` legacy :
- `models-legacy.1` : avec `lab-models.json` seul, `models.json` est créé avec les clés `lab.*`, et `lab-models.json` reste identique (`cmp`).
- `models-legacy.2` : une seconde résolution n'écrit rien (`cmp` de `models.json`).
- `models-legacy.3` : les deux fichiers présents → `lab-models.json` est ignoré avec un avertissement, et `models.json` est inchangé.
- `models-legacy.4` : une valeur inconnue dans `lab-models.json` suit la règle retenue en Phase 1 (décision X8 : erreur explicite).

**`stop-iteration3`** — arrêt propre à la 3e itération, en `auto` :
- `stop-iteration3.1` : 3 verdicts `CHANGES_REQUESTED` → `fail` à l'itération 3.
- `stop-iteration3.2` : un 4e `record` de Builder est refusé (exit ≠ 0).
- `stop-iteration3.3` : `.harness/runs/STOP-<horodatage>.md` existe. Il contient les rubriques de la Phase 4 (où, pourquoi, quoi faire, commande exacte), les issues restantes et le chemin de la spec.
- `stop-iteration3.4` : aucun journal `ship-pr-*`, et la spec n'est pas passée à un statut livré.
- `stop-iteration3.5` (contre-épreuve) : CR, CR, Verifier mort, APPROVED → `success` à l'itération 3. L'agent mort n'a pas consommé d'itération.

### 4. Mode headless réel, optionnel — `LV`

- `LV-01` : `--live` active trois scénarios LLM, jamais lancés sans ce drapeau : `live-install`, `live-factory`, `live-hook`. `ship-pr` réel est exclu, parce qu'il exige un vrai dépôt GitHub (Q8).
- `LV-02` : les skills sont exposés au projet temporaire par liens sous `<tmp>/.claude/skills/` (mécanisme de la recette R1), sans installeur et sans toucher `~/.claude`.
- `LV-03` : forme de l'appel :
  - `claude -p "<commande>" --output-format json --max-turns <borne> --permission-prompts none --permission-mode acceptEdits --allowedTools "<liste blanche>"`, avec `MSYS_NO_PATHCONV=1` sous Git Bash ;
  - jamais le drapeau qui contourne toutes les permissions.
- `LV-04` : assertions structurelles seulement (D10).
  - `live-install` : fichiers déterministes de `install-fresh.1` présents, `harness.json` valide, journal valide ; une seconde exécution laisse `git status --porcelain` vide.
  - `live-factory` : une **issue explicite** est exigée. Soit `success` et tests réels verts, soit `STOP-*.md`. Jamais `success` avec tests rouges, jamais une sortie sans l'un ni l'autre (Q9).
  - `live-hook` : sous activation `ship-pr`, une consigne d'éditer un fichier hors du diff laisse ce fichier identique (`cmp`).
- `LV-05` : `--live` sans `claude` dans le PATH → exit 1 avec `claude not found`. Sans `--live`, les scénarios `live-*` sont `SKIP (live not requested)`.

### 5. Conclusion sur `claude plugin eval` — `EV`

- `EV-01` : `claude plugin eval` **ne porte pas** ces scénarios ([DOC], BACKLOG §5). Il sait préparer une fixture (`scaffold_script`), mais aucun grader n'exécute de commande shell. Or chaque résultat attendu ici est un état observable par commande : exit code, octets d'un fichier, état git, état du faux `gh`, journal.
- `EV-02` : il suppose en outre un plugin, alors que la Phase 7 n'est pas décidée. Il est réexaminable pour des évaluations jugées par LLM (qualité d'une spec), hors périmètre.
- `EV-03` : la conclusion est écrite dans le README, section « Tester le harnais », avec la référence au BACKLOG §5.

### 6. Scripts `ci/test-harness.sh` et `ci/test-harness.ps1` — `TH`

- `TH-01` : deux lanceurs minces et équivalents :
  - Bash : `set -euo pipefail`. PowerShell : `$ErrorActionPreference = 'Stop'`.
  - Ils détectent l'interpréteur par la règle D5 (5 s, ≥ 3.9), transmettent les options au runner Python stdlib commun (Q1, Q2) et propagent son exit code.
  - Messages en ASCII sans accent.
- `TH-02` : options : `--list`, `--scenario <id>` (répétable), `--live`, `--keep` (garde les dossiers temporaires et affiche leur chemin), `--fixtures <dossier>` (défaut `ci/fixtures`), `--report <fichier>`, `-h`. Pendants PowerShell : `-List`, `-Scenario`, `-Live`, `-Keep`, `-Fixtures`, `-Report`.
- `TH-03` : sortie : une ligne par scénario, `PASS|FAIL|SKIP <id> <durée ms> [raison]`, puis le chemin du rapport. Exit codes :
  - 0 : tout `PASS` ou `SKIP` motivé ;
  - 1 : au moins un `FAIL`, ou `--live` demandé sans `claude` ;
  - 2 : option ou scénario inconnu.
- `TH-04` : rapport JSON : `{"scenarios": [{"id", "status", "duration_ms", "assertions": [{"id", "ok", "detail"}], "real_gh_calls", "real_claude_calls"}], "core_version", "interpreter"}`. Il est écrit dans le dossier temporaire, sauf avec `--report`.
- `TH-05` : `--list --verbose` liste, par scénario, les sous-commandes du noyau appelées et le fichier SKILL.md ou gabarit qui les prescrit.
- `TH-06` : aucune trace dans ce dépôt après exécution : pas de `__pycache__` (`-B`), pas de journal, pas de rapport hors de `--report`.

### 7. Installeurs — `IN`

- `IN-01` : `install_skills.sh --target <dossier>` et `install_skills.ps1 -TargetRoot <dossier>` remplacent la cible `~/.claude/skills`. Sans l'option, le comportement est inchangé octet pour octet en sortie.
- `IN-02` : les deux options restent fonctionnellement équivalentes, et leurs messages sont sans accent.

### Découpage en lots

| Lot | Contenu | CA | Dépend de |
| --- | --- | --- | --- |
| L0 | Phases 1 à 5 livrées ; `BASE6` relevé ; relevé des noms réels des commandes des Phases 3 à 5 (upgrade, doctor, STOP, activation des hooks, conditions de merge) ; tout manque est listé comme écart | — | Phases 1 à 5 |
| L1 | Runner, `ci/test-harness.sh|.ps1`, `--list`, rapport, cales SM-04, isolation SM-05 | 02, 04 à 07, 10, 19 | L0 |
| L2 | Fixtures FX-01 à FX-07, `ci/fixtures/README.md` | 11, 12 | L1 |
| L3 | IN-01, IN-02 ; scénarios `install-fresh`, `install-skills`, `models-absent`, `models-legacy` | 08, 13, 14, 20 | L2 |
| L4 | `upgrade-legacy` | 08, 09 | L3 |
| L5 | `factory-auto`, `stop-iteration3` | 08 | L3 |
| L6 | SM-03 (faux `gh` complété) ; `shippr-automerge` | 08 | L3 |
| L7 | `hook-diff` | 08 | L3 |
| L8 | Mode `--live` (LV-01 à LV-05) | 15, 16 | L3 à L7 |
| L9 | README (« Tester le harnais », conclusion EV), BACKLOG, passage complet des CA | 01 à 21 | tous |

Un commit par lot au minimum.

### Fichiers créés ou modifiés

**Créés**
- `ci/test-harness.sh`, `ci/test-harness.ps1` ;
- `ci/scenarios/` (runner, un module par scénario) ;
- `ci/fixtures/` : `README.md`, `toy-py/`, `legacy-node/` (avec `fixture.json` et `customizations.json`), `agents/`, `expected/`.

**Modifiés**
- `install_skills.sh`, `install_skills.ps1` : IN ;
- `skills/_core/tests/fake_gh.py` : SM-03, seulement si la Phase 4 ne l'a pas fait ;
- `README.md`, `specs/harness-v2/BACKLOG.md`.

**Inchangés** (CA-17) : `skills/*/SKILL.md`, `skills/_core/hcore/`, `skills/_core/harness.py`, `tests/fixtures/`.

## Critères d'acceptation

- [ ] **CA-01 — Non-régression unitaire.** `T` → exit 0.
- [ ] **CA-02 — Syntaxe des lanceurs.**
  - `bash -n ci/test-harness.sh` → exit 0.
  - `pwsh -NoProfile -Command "[scriptblock]::Create((Get-Content ci/test-harness.ps1 -Raw)) | Out-Null"` → exit 0.
  - `LC_ALL=C grep -n '[^ -~]' ci/test-harness.sh ci/test-harness.ps1` → aucune sortie.
- [ ] **CA-03 — Stdlib seule, Python 3.9.** `<PY> -B -I -S ci/scenarios/run.py --list` → exit 0, avec `<PY> --version` en 3.9.x. `grep -rnE '^\s*(import|from)\s+(pytest|yaml|requests)' ci/scenarios` → aucune sortie.
- [ ] **CA-04 — Passage complet en Bash.** `R` → exit 0. La sortie contient exactement une ligne `PASS` par scénario parmi `install-fresh`, `install-skills`, `upgrade-legacy`, `factory-auto`, `shippr-automerge`, `hook-diff`, `models-absent` et `models-legacy`. `install-skills` peut seul être en `SKIP` motivé (Q7). La sortie contient aussi `SKIP live-install`, `SKIP live-factory` et `SKIP live-hook`, avec `live not requested`.
- [ ] **CA-05 — Équivalence PowerShell.**
  - `P` → exit 0.
  - `diff <(R --list) <(P -List)` est vide.
  - Pour chaque id, le statut rendu par `P` est égal à celui de `R`. Seule exception admise : `install-skills`, `SKIP` sous Git Bash et `PASS` sous `P`.
- [ ] **CA-06 — Usage.** `R --scenario zzz` → exit 2 ; `R --bogus` → exit 2 ; idem pour `P -Scenario zzz`.
- [ ] **CA-07 — Assertions couvertes.** `R --report /tmp/r.json` puis `for id in $(grep -oE '\b(install-fresh|install-skills|upgrade-legacy|factory-auto|shippr-automerge|hook-diff|models-absent|models-legacy|stop-iteration3)\.[0-9]+\b' S | sort -u); do grep -q "\"$id\"" /tmp/r.json || echo "$id"; done` → aucune sortie. Dans `/tmp/r.json`, chaque assertion d'un scénario `PASS` porte `"ok": true`.
- [ ] **CA-08 — Un CA par scénario.** Pour chaque id de la liste de CA-04, plus `stop-iteration3`, `R --scenario <id>` → exit 0 et ligne `PASS <id>` (ou `SKIP` motivé pour `install-skills`).
- [ ] **CA-09 — Les scénarios peuvent échouer.** On copie `ci/fixtures` dans un dossier temporaire, puis on y altère un caractère :
  - d'un extrait de `legacy-node/customizations.json` : `R --scenario upgrade-legacy --fixtures <copie>` → exit 1 et `FAIL upgrade-legacy` ;
  - d'une sortie figée du Verifier de `stop-iteration3` (`CHANGES_REQUESTED` → `APPROVED`) : `R --scenario stop-iteration3 --fixtures <copie>` → exit 1.
- [ ] **CA-10 — Aucun effet de bord.**
  - Une empreinte de `ls -laR ~/.claude/skills` prise avant `R` est identique après.
  - `git status --porcelain` de ce dépôt est vide après `R`.
  - Dans le rapport, `real_gh_calls` et `real_claude_calls` valent 0 pour chaque scénario.
- [ ] **CA-11 — Fixtures inertes.** `find ci/fixtures \( -name 'CLAUDE.md' -o -name '.*' \) -not -path ci/fixtures` → aucune sortie.
- [ ] **CA-12 — Provenance de la fixture legacy.** Pour chaque fichier marqué `"from": "7be1afb:<chemin>"` dans `legacy-node/fixture.json`, `git show 7be1afb:<chemin> | cmp - ci/fixtures/legacy-node/<fichier>` → exit 0, sauf pour les fichiers listés dans `customizations.json`. Pour ceux-là, le seul écart admis est l'ajout des extraits déclarés.
- [ ] **CA-13 — Prescriptions.** Pour chaque couple (sous-commande, fichier) rendu par `R --list --verbose`, `grep -F "<sous-commande>" <fichier>` trouve une correspondance.
- [ ] **CA-14 — Installeurs.**
  - `bash -n install_skills.sh` passe, et le contrôle de syntaxe PowerShell de CA-02 passe sur `install_skills.ps1`.
  - `install_skills.sh --skip-tools --target <tmp>` lancé deux fois : la seconde exécution rend exit 0 avec seulement des lignes `[ok]`.
  - Idem pour `install_skills.ps1 -SkipTools -TargetRoot <tmp>`.
  - `diff <(ls <tmp-sh>) <(ls <tmp-ps1>)` est vide.
  - Sans l'option, la sortie standard d'une exécution sur une cible déjà liée est identique à celle de `BASE6`.
- [ ] **CA-15 — Live sans `claude`.** Avec un PATH sans `claude` : `R --live` → exit 1, et stderr contient `claude not found`.
- [ ] **CA-16 — Live sûr.** Aucun lanceur ni scénario ne contient le drapeau qui contourne toutes les permissions (`grep -rn "skip-permissions" ci/test-harness.sh ci/test-harness.ps1 ci/scenarios` → aucune sortie). `grep -rn -- "--max-turns" ci/scenarios` ≥ 1.
- [ ] **CA-17 — Code du harnais intact.** `git diff --exit-code BASE6 -- skills/ ':!skills/_core/tests/fake_gh.py' tests/fixtures` → exit 0.
- [ ] **CA-18 — README.** `grep -F "## Tester le harnais" README.md` ≥ 1, `grep -F "ci/test-harness.sh" README.md` ≥ 1, `grep -F "claude plugin eval" README.md` ≥ 1, `grep -F -- "--live" README.md` ≥ 1.
- [ ] **CA-19 — Aucun artefact parasite.** `git status --porcelain` ne liste ni `__pycache__`, ni `.pyc`, ni journal, ni rapport, ni dossier temporaire.
- [ ] **CA-20 — Fixtures existantes réutilisées, pas copiées.** `grep -F "tests/fixtures/toy-project" ci/fixtures/legacy-node/fixture.json` ≥ 1, et `find ci/fixtures -name sum.js` → aucune sortie.
- [ ] **CA-21 — BACKLOG.** `grep -F "Phase 6" specs/harness-v2/BACKLOG.md` ≥ 1, avec un statut et la mention de `ci/fixtures/` à côté de Q13.

**Recettes par l'utilisateur, hors portes du Verifier :**
- **R12** : `R --live`, puis `P -Live`, sur sa machine, avec les écarts listés un par un.
- **R13** : `ship-pr` réel sur un dépôt GitHub jetable avec CI verte, puis rouge : merge automatique, puis PR laissée ouverte avec un commentaire.

## Hors-périmètre

- Corriger un défaut révélé par un scénario. Le scénario reste en `FAIL` et le défaut part dans une spec corrective. Aucune modification de `skills/` hors SM-03.
- La non-régression des audits (NR de la Phase 2) : elle reste dans `T`, sur `tests/fixtures/`.
- `ship-pr` en headless réel, les enchaînements factory-run → ship-pr, `/factory-queue` et `/factory-batch`, les hooks autres que celui du diff : couverts par les tests unitaires de leurs phases.
- Le scénario de plugin (`claude plugin validate`, `--plugin-dir`) : Phase 7, s'il est décidé.
- L'ajout de `ci/test-harness.*` aux portes du Builder et du Verifier de l'usine de ce dépôt.
- Tout commit, push, `/ship-pr` ou exécution de `install_skills.*` hors d'une cible temporaire par le Builder.

## Risques

- **[IMPOSSIBLE] Rejeu du LLM orchestrateur.** On rejoue la séquence prescrite, pas la session (D10). Un SKILL.md qui dérive de ses prescriptions n'est attrapé que par CA-13 et par `--live`.
- **[IMPOSSIBLE] `$HOME` constant en PowerShell.** Sans IN-01, `install-skills` ne peut pas tourner sans écrire dans le vrai profil.
- **[DOC] `claude plugin eval`** : aucun grader shell (EV-01). Si l'outil évolue, la conclusion est à revoir.
- **[DOC] Headless.** Seul `--permission-prompts none` est documenté pour retirer `AskUserQuestion`. Sans ce drapeau, le comportement n'est pas défini, d'où LV-03.
- **Symlinks sous Git Bash.** Sans symlinks natifs, `ln -s` copie le dossier (à vérifier). La seconde passe de l'installeur rend alors « dossier réel » et exit 1. C'est un défaut potentiel de `install_skills.sh` sous Windows, signalé par `install-skills.6`, non corrigé ici.
- **Faux `gh` qui diverge du vrai.** Formats de `gh pr checks` et de l'API de protection simulés : un changement côté GitHub ne se voit qu'en R13.
- **Dépendance aux Phases 3 à 5.** Les noms de commandes, rubriques de `STOP-*.md`, mécanisme d'activation des hooks et champ « questions bloquantes » viennent de leurs specs. L0 les relève ; un manque bloque le lot concerné.
- **Durée.** L'installation rejouée en préparation de plusieurs scénarios allonge la durée totale. Le rapport la mesure, sans seuil (Q12).
- **Coût du mode live.** Il consomme l'abonnement. Il n'est jamais lancé par défaut, ni par la CI du dépôt (§4.3 : rien qui coûte hors abonnement).
- **Snapshot `7be1afb`.** Il représente l'usine de ce dépôt (stack Bash), pas un projet Node réel. Il suffit pour éprouver la préservation hors bloc, pas la détection de stack.

## Questions ouvertes

Chaque question porte une décision par défaut, justifiée en une ligne.

- **Q1 — Forme du runner.** Défaut : scénarios écrits une seule fois en Python stdlib ; `.sh` et `.ps1` ne sont que des lanceurs. Justification : l'équivalence entre les deux scripts est alors garantie par construction, et Python est déjà un prérequis du noyau.
- **Q2 — Emplacement du runner.** Défaut : `ci/scenarios/`, pas `skills/_core/tests/`. Justification : `copy-core` copie tout `_core` dans les projets.
- **Q3 — Dépôt bare.** Défaut : créé à l'exécution, jamais versionné. Justification : un dépôt bare commité est opaque, et `ghflow.py` impose de toute façon un chemin `github.com` construit à la volée.
- **Q4 — Stack du projet exécuté.** Défaut : Python `unittest` (`toy-py`) ; le Node de `toy-project` ne sert qu'au snapshot legacy. Justification : aucune dépendance au-delà de l'interpréteur ; `node` n'est pas garanti sur la machine.
- **Q5 — Source de l'installation « à l'ancienne ».** Défaut : les fichiers de ce dépôt à `7be1afb`, plus les personnalisations déclarées. Justification : c'est une sortie réelle de software-factory d'avant la v2, plutôt qu'une reconstitution.
- **Q6 — Cible des installeurs.** Défaut : ajouter `--target` / `-TargetRoot` aux deux installeurs. Justification : `$HOME` est constant en PowerShell, et un test ne doit jamais toucher le vrai profil.
- **Q7 — Git Bash sans symlinks natifs.** Défaut : `SKIP` motivé, la couverture Windows passant par `P`. Justification : la Phase 6 constate, elle ne corrige pas l'installeur.
- **Q8 — Périmètre du mode live.** Défaut : `live-install`, `live-factory` et `live-hook` ; `ship-pr` réel en recette R13. Justification : un vrai dépôt GitHub est hors de portée d'un script local.
- **Q9 — Critère de succès en live.** Défaut : une issue explicite (`success` avec tests verts, ou `STOP-*.md`). Justification : exiger le succès d'un LLM rendrait le test aléatoire ; exiger l'explicite teste le filet.
- **Q10 — Indépendance des scénarios.** Défaut : chacun repart de ses fixtures. Justification : un échec ne se propage pas en cascade, et `--scenario` reste utilisable seul.
- **Q11 — Portes de l'usine du dépôt.** Défaut : `ci/test-harness.*` n'y est pas ajouté dans cette phase. Justification : ce serait une régénération de l'usine, hors du besoin de la Phase 6.
- **Q12 — Budget de durée.** Défaut : mesuré dans le rapport, sans seuil. Justification : rien dans la ROADMAP ne fixe de durée.
- **Q13 — Emplacement du rapport.** Défaut : dossier temporaire, sauf `--report`. Justification : CA-19 ; ce dépôt ne doit pas se salir en se testant.
