---
name: software-factory
description: Installe une usine logicielle multi-agents (Planner, Builder, Verifier) dans le projet courant — détecte la stack, génère les sous-agents adaptés, le skill d'orchestration /factory-run, les scripts CI, les règles d'économie de tokens et les tâches VS Code. À utiliser quand l'utilisateur demande d'initialiser ou d'installer son usine logicielle dans un projet.
context: fork
user-invocable: true
argument-hint: "[description optionnelle du premier besoin]"
---

# Software Factory — installation de l'usine logicielle

Installer dans le projet courant une usine logicielle multi-agents à trois rôles et contextes séparés — **Planner**, **Builder**, **Verifier** — orchestrée par un skill projet `/factory-run`, utilisable en session interactive comme en CI headless. L'utilisateur reste le Product Owner : aucune exigence n'est inventée à sa place, et une gate humaine valide la spec avant toute construction.

Si `$ARGUMENTS` est non vide, le conserver tel quel : c'est le premier besoin à traiter, à rappeler dans le rapport final avec la commande `/factory-run` correspondante.

## Noyau déterministe

Les règles déterministes de ce skill et du `factory-run` qu'il génère sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : CLI `harness.py`, paquet `hcore/`, tests `tests/`. Ne jamais les réimplémenter à la main : appeler la CLI et suivre sa sortie JSON. Règles portées : **SF-01** à **SF-04** (`hcore/fusion.py`), **FR-01** à **FR-04** (`hcore/factory.py`, avec `verdicts.py`, `counters.py`, `relaunch.py`).

**Interpréteur** (règle unique, reproduite et testée par `hcore/interp.py`) : retenir comme `<PY>` le premier de `python`, `python3`, `py -3`, cherché dans le PATH, qui répond en moins de 5 s avec une version ≥ 3.9, par cette boucle Bash portable (délai posé seulement si `timeout` existe ; absent, comme sur macOS, la lancer avec le délai de l'outil Bash) : `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`. Aucun candidat → s'arrêter en le disant : l'usine générée en dépend. Ci-dessous, `K` désigne `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

## Règles impératives (toutes les phases)

- **Aucun placeholder** : chaque fichier généré est complet et immédiatement opérationnel. Pas de TODO, pas de « à adapter », pas de pseudo-code, pas de commande inventée.
- **Fusion, jamais écrasement** (SF-01 à SF-03) : `.claude/settings.json`, `.vscode/tasks.json` et `.gitignore` sont créés ou fusionnés par le noyau (Phase 5), jamais édités à la main. JSONC (commentaires, virgules finales) et BOM sont acceptés, commentaires conservés. Un fichier existant illisible fait échouer la commande sans qu'aucun des trois fichiers soit modifié : le signaler, ne pas le réécrire.
- **Fichiers générés** (SF-04) : écrire le contenu de chaque agent, skill et script CI tel quel avec l'outil Write dans un fichier sous `.claude/runs/`, puis `K sf install --dest <chemin> --source <ce fichier>` ; jamais par stdin ni par une commande shell (heredoc, `echo`) : ce contenu porte `$ARGUMENTS`, `$1`, `$(date)`, backticks et apostrophes. Le noyau crée le fichier absent, reconnaît l'identique, et ne remplace jamais un fichier qui diffère : il le rend `personnalisé-conservé`, à signaler dans le rapport final.
- **Adapter à la stack** : chaque commande (test, build, lint) écrite dans un prompt ou un script doit provenir de la détection de la Phase 1, jamais d'une supposition.
- **Idempotence** (SF-04) : relancer ce skill sur un projet déjà équipé ne détruit rien et signale l'état de chaque fichier rendu par le noyau (créé / fusionné / identique / personnalisé-conservé).

## Phase 1 — Détection de la stack

Scanner la racine du projet (et un niveau de sous-dossiers en cas de monorepo) à la recherche des marqueurs : `*.sln`/`*.csproj` (.NET), `pyproject.toml`/`requirements.txt`/`setup.py` (Python), `package.json` (Node/TS), `CMakeLists.txt`/`Makefile` (C/C++), `go.mod` (Go), `Cargo.toml` (Rust), `Dockerfile`/`docker-compose*.yml`/`compose*.yml` (conteneurs), `ansible.cfg`/`playbooks/`/`roles/` (Ansible), `*.tf` (Terraform). Lire les manifestes trouvés pour en extraire les scripts et dépendances réels.

Établir et retenir pour les phases suivantes : langages et frameworks présents ; **commande de build** réelle (ex. `dotnet build`, `npm run build`, `cmake --build build`, absente si non applicable) ; **commande de test** réelle (ex. `dotnet test`, `pytest`, `npm test`, `go test ./...`, `ansible-lint` + `molecule test` pour Ansible) ; **commande de lint/format** si configurée (`ruff`, `eslint`, `clang-format`, `dotnet format`…) ; conventions existantes : `CLAUDE.md`, `.editorconfig`, configuration de linters, structure des dossiers de tests ; stacks du noyau présentes parmi `node`, `dotnet`, `python`, `cpp`, `rust`.

Si aucune commande de test n'existe, le noter : le prompt du Builder devra exiger l'initialisation de l'outillage de test standard de la stack (ex. `pytest` pour Python, `xunit` pour .NET), et le rapport final le signalera à l'utilisateur.

## Phase 2 — Sous-agents natifs `.claude/agents/`

Créer trois fichiers d'agents. Chaque prompt système est rédigé intégralement, adapté à la stack détectée (nommer les langages, frameworks, commandes et conventions réels du projet), et contient : le rôle, le périmètre, les interdits, la méthode de travail, et le format de sortie exigé.

**`.claude/agents/factory-planner.md`** — frontmatter : `name: factory-planner` ; `description: Analyse un besoin et le code existant pour rédiger un brouillon de spécification avec critères d'acceptation testables et questions ouvertes. Lecture seule.` ; `tools: Read, Glob, Grep`. Le prompt système impose : analyser le besoin fourni et le code existant du projet ; produire en sortie un **brouillon de spec** en Markdown contenant obligatoirement les sections *Contexte*, *Périmètre*, *Critères d'acceptation* (chacun objectivement testable), *Hors-périmètre*, *Risques*, et une section *Questions ouvertes* listant tout point ambigu. Interdits : inventer une exigence non déductible du besoin ou du code ; modifier un fichier ; proposer une implémentation détaillée (c'est le rôle du Builder).

**`.claude/agents/factory-builder.md`** — frontmatter : `name: factory-builder` ; `description: Implémente strictement une spécification approuvée — architecture, code et tests dans un même contexte — puis exécute build et tests avant de rendre la main.` ; pas de champ `tools` (le Builder hérite de tous les outils). Le prompt système impose : lire la spec approuvée fournie en entrée et s'y tenir strictement ; concevoir puis implémenter (architecture et code dans le même contexte pour rester cohérent) ; écrire les tests couvrant chaque critère d'acceptation ; respecter les conventions du repo (les citer : linters, style, structure détectés en Phase 1) ; exécuter la commande de build puis la commande de test réelles du projet et **ne rendre la main que si elles passent**, sinon corriger d'abord ; en cas d'entrée contenant des issues d'un Verifier, corriger chaque issue sans régresser sur les critères déjà satisfaits. Interdits : étendre le périmètre au-delà de la spec ; désactiver ou ignorer un test ou un warning pour « faire passer » ; commiter.

**`.claude/agents/factory-verifier.md`** — frontmatter : `name: factory-verifier` ; `description: Vérification adversariale d'une implémentation par rapport à sa spec — exécute les tests, cherche à casser, rend un verdict JSON strict. Ne modifie jamais le code.` ; `tools: Read, Glob, Grep, Bash`. Le prompt système impose : partir de la spec et du diff (`git diff` + `git status`) sans aucun a priori favorable ; exécuter la commande de test réelle du projet et rapporter son exit code ; vérifier un à un chaque critère d'acceptation ; chercher activement à casser l'implémentation (cas limites, entrées invalides, erreurs d'intégration) ; terminer sa réponse par un unique bloc JSON, sans texte après : `{"verdict": "APPROVED" | "CHANGES_REQUESTED", "tests_passed": true | false, "issues": [{"file": "chemin", "severity": "critical|major|minor", "description": "..."}]}`. Interdits : modifier le moindre fichier ; approuver si les tests échouent ou si un critère d'acceptation n'est pas couvert ; rendre un verdict sans avoir exécuté les tests.

## Phase 3 — Skill d'orchestration `.claude/skills/factory-run/SKILL.md`

Créer le skill projet qui pilote un cycle complet. Frontmatter exact, une clé par ligne : `name: factory-run` ; `description: Lance un cycle de l'usine logicielle (Planner → gate humaine sur la spec → Builder → Verifier avec boucle de correction) sur un besoin ou une spec approuvée.` ; `disable-model-invocation: true` ; `argument-hint: "<besoin | chemin d'une spec approuvée>"`.

Le corps (rédigé intégralement, voix impérative, adapté à la stack) écrit en clair `H` = `<PY> .claude/harness/harness.py` (copie du noyau, Phase 4) et impose : **chaque sous-agent lancé est consigné** par `H factory-run record --run <run> --agent <nom> --model <modèle ou inherit> --duration-ms <ms> --tokens <n>`, valeurs du bloc d'usage de l'outil Agent (sans durée : `H begin --run <run> --slot <nom>` juste avant l'agent ; sans tokens : omettre l'option ; une mesure manquante est journalisée `null` et signalée, jamais bloquante) ; `--output .claude/runs/verifier-<n>.md`, fichier où la sortie du Verifier est écrite telle quelle avec l'outil Write (jamais par stdin ni via le shell : backticks, `$`, apostrophes) ; `--dead` si l'agent est mort. Le champ `action` du JSON rendu dicte la suite ; ne jamais sauter un appel ni décider à la place du noyau. Déroulé pour la session principale :

1. **Entrée** (FR-01) : écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.claude/runs/factory-run-arguments.txt` (jamais dans une ligne de commande shell : un besoin peut contenir guillemets, `$` ou backticks), puis `H factory-run start --arguments-file .claude/runs/factory-run-arguments.txt` ouvre le journal `.claude/runs/factory-run-<horodatage>.jsonl` et rend `mode` : `build` (spec existante sous `specs/` dont la ligne de statut vaut `Statut : APPROUVEE`) → étape 3 ; `plan` → traiter `$ARGUMENTS` comme un besoin.
2. **Phase Plan (gate humaine)** : lancer le sous-agent `factory-planner` avec le besoin ; à son retour, poser à l'utilisateur les *Questions ouvertes* du brouillon (AskUserQuestion) ; intégrer les réponses, écrire `specs/SPEC-<slug-du-besoin>.md` avec en tête `Statut : PROPOSEE` ; présenter la spec à l'utilisateur et demander son approbation explicite ; en cas d'approbation, passer le statut à `APPROUVEE` ; sinon itérer sur la spec. **Si aucune interaction n'est possible (exécution headless), s'arrêter en erreur explicite : un cycle CI exige le chemin d'une spec déjà approuvée.** Ne jamais construire sans spec approuvée.
3. **Phase Build** : lancer le sous-agent `factory-builder` (contexte frais) avec le chemin de la spec approuvée.
4. **Phase Verify — boucle de correction, 3 itérations maximum** : lancer un sous-agent `factory-verifier` (contexte vierge, indépendant du Builder) avec le chemin de la spec, consigner son bloc JSON, puis selon `action` :
   - `success` (FR-02 : `APPROVED` **et** `tests_passed` vrai) : sortir de la boucle ;
   - `fix` : relancer `factory-builder` avec la spec **et la liste complète des `issues` rendues** (fichier, sévérité, description) et la consigne de corriger sans régresser ; puis un nouveau Verifier ;
   - `relaunch` (FR-04) : relancer **une fois** l'agent mort ou à la sortie inexploitable, sans consommer d'itération ;
   - `fail` : **échouer explicitement** en publiant `reason` et les issues restantes — 3e itération non approuvée (FR-03) ou second échec d'un agent (FR-04). Ne jamais approuver par épuisement.

   **Un Verifier muet n'est pas un Verifier satisfait** : ne jamais traiter l'absence de verdict comme une approbation, ne jamais passer à la suite sur un verdict absent. Un cycle qui livre du code non vérifié parce que son vérificateur est tombé est pire qu'un cycle qui échoue.
5. **Rapport final** : fichiers modifiés (`git status`), résultat des tests, verdict, nombre d'itérations, chemin du journal, prochaine action suggérée (revue du diff par l'utilisateur ; ne pas commiter à sa place).

## Phase 4 — Noyau `.claude/harness/` et scripts CI minces `ci/factory.sh` et `ci/factory.ps1`

Copier le noyau dans le projet par `K sf copy-core --root .` : `_core` tel quel sous `.claude/harness/`, avec sa constante `CORE_VERSION`, sans bytecode, versionné avec le projet. Rapporter l'état de chaque fichier rendu. Jamais de noyau mélangé : si un fichier déjà présent diffère (`copied` faux, `blocked_by`), rien n'est copié ; le signaler dans le rapport final.

Générer deux scripts complets et équivalents (bash avec `set -euo pipefail`, PowerShell avec `$ErrorActionPreference = 'Stop'`) qui :

- prennent en **argument obligatoire** le chemin d'une spec approuvée, et une **option `--yolo`** (`-Yolo` en PowerShell) ;
- vérifient que le fichier de spec existe et contient `Statut : APPROUVEE`, sinon échouent avec un message clair ;
- construisent l'appel : `claude -p "/factory-run '<chemin-spec>'" --output-format json --max-turns 100`, complété par défaut de `--permission-mode acceptEdits --allowedTools "<liste blanche>"`, ou par `--dangerously-skip-permissions` si `--yolo` ;
- la **liste blanche** `--allowedTools` est construite depuis la Phase 1 : toujours `Read`, `Glob`, `Grep`, `Write`, `Edit`, `Bash(git *)`, l'interpréteur retenu pour le noyau (`Bash(python *)`, `Bash(python3 *)` ou `Bash(py *)`), plus les commandes réelles du projet (ex. `Bash(dotnet *)`, `Bash(pytest *)`, `Bash(npm *)`) — uniquement celles détectées ;
- écrivent la sortie dans `factory-logs/factory-<horodatage>.json` (créer le dossier ; horodatage `date +%Y%m%d-%H%M%S` en bash, `Get-Date -Format yyyyMMdd-HHmmss` en PowerShell) et **propagent l'exit code** de `claude`.

## Phase 5 — Économie de tokens `.claude/settings.json` et `.gitignore`

Un seul appel fusionne les fichiers des phases 5 et 6 et rend l'état de chacun : `K sf apply --root . --stacks <stacks de la Phase 1, séparées par des virgules>`.

- **Économie de tokens** (SF-01) : règles `permissions.deny` en `Read(...)` couvrant les artefacts de la stack détectée uniquement, plus `Read(./factory-logs/**)` et `Read(./.git/objects/**)` ; table de correspondance `STACK_DENY` du noyau ; tableaux fusionnés sans doublon, toute clé existante préservée.
- **`.gitignore`** (SF-03) : `factory-logs/` et `.claude/runs/` (journaux de cycle), créé ou complété sans dupliquer une ligne.

## Phase 6 — Tâches VS Code `.vscode/tasks.json`

Fusion SF-02 : version `2.0.0`, input `factorySpec` (« Chemin de la spec approuvée (specs/SPEC-*.md) ») et trois tâches : **« Factory: CI run »** (`./ci/factory.sh ${input:factorySpec}`, variante `windows` en `pwsh -File ci/factory.ps1`), **« Factory: CI run (YOLO) »** (`--yolo` / `-Yolo`), **« Factory: nouvelle spec (session) »** (rappel `Ouvrir Claude Code et taper : /factory-run "<votre besoin>"`) ; tâches et inputs existants préservés, rien de dupliqué.

## Phase 6b — Base de connaissance du dépôt (optionnelle)

L'usine passe l'essentiel de son budget à redécouvrir le dépôt : chaque Planner repart d'un contexte vierge, chaque Verifier relit ce que le Builder vient d'écrire. Le skill `code-index` installe un serveur local adossé à ripgrep qui répond à ces questions depuis un index versionné sous `.knowledge/`, et qui porte en plus les **notes** que les cycles laissent derrière eux — décisions, pièges, zones sensibles — partagées par git avec les autres utilisateurs du dépôt.

Poser à l'utilisateur, en un appel `AskUserQuestion`, s'il veut l'installer maintenant. En cas d'accord, invoquer le skill `code-index` : il détecte l'usine qui vient d'être installée et branche seul les trois agents et `/factory-run` dessus. En cas de refus, ne rien faire : l'usine fonctionne entièrement sans, et `code-index` s'installe à tout moment sur un dépôt déjà équipé. **Ne jamais installer sans accord** : la base ajoute un dossier versionné au dépôt, ce qui se décide. En exécution headless, ne pas poser la question et ne rien installer.

## Phase 7 — Rapport final

Terminer par un rapport structuré : stack détectée (langages, commandes retenues, interpréteur du noyau) ; liste des fichiers avec leur état rendu par le noyau (créé / fusionné / identique / personnalisé-conservé), `.claude/harness/` compris ; absence d'outillage de test le cas échéant ; mode d'emploi en deux lignes (session : `/factory-run "besoin"` ; CI : `ci/factory.sh specs/SPEC-x.md`). Si `$ARGUMENTS` contenait un besoin, conclure par la commande exacte à lancer : `/factory-run "<le besoin>"`.
