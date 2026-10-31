## Phase 1 — Détection de la stack

`K stack detect --root .` (ST-01 à ST-04) cherche à la racine du projet et à un niveau de sous-dossiers (monorepo) les marqueurs `*.sln`/`*.csproj` (.NET), `pyproject.toml`/`requirements.txt`/`setup.py`/`environment.yml`/`*.ipynb` (Python), `package.json` (Node/TS), `CMakeLists.txt`/`Makefile` (C/C++), `go.mod` (Go), `Cargo.toml` (Rust), `Dockerfile`/`docker-compose*.yml`/`compose*.yml` (conteneurs), `ansible.cfg`/`playbooks/`/`roles/` (Ansible), `*.tf` (Terraform), et rend `manifests` (chemins trouvés), `families` et `stacks`. Lire les manifestes rendus pour en extraire les scripts et dépendances réels : ce jugement reste au skill.

Établir et retenir pour les phases suivantes : langages et frameworks présents ; **commande de build** réelle (ex. `dotnet build`, `npm run build`, `cmake --build build`, absente si non applicable) ; **commande de test** réelle (ex. `dotnet test`, `pytest`, `npm test`, `go test ./...`, `ansible-lint` + `molecule test` pour Ansible) ; **commande de lint/format** si configurée (`ruff`, `eslint`, `clang-format`, `dotnet format`…) ; conventions existantes : `CLAUDE.md`, `.editorconfig`, configuration de linters, structure des dossiers de tests ; stacks du noyau : la liste `stacks` rendue par `stack detect` (parmi `node`, `dotnet`, `python`, `cpp`, `rust`).

Si aucune commande de test n'existe, le noter : le prompt du Builder devra exiger l'initialisation de l'outillage de test standard de la stack (ex. `pytest` pour Python, `xunit` pour .NET), et le rapport final le signalera à l'utilisateur.

## Phase 4 — Noyau `.claude/harness/` et scripts CI minces `ci/factory.sh` et `ci/factory.ps1`

Copier le noyau dans le projet par `K sf copy-core --root .` : `_core` tel quel sous `.claude/harness/`, avec sa constante `CORE_VERSION`, sans bytecode, versionné avec le projet. Rapporter l'état de chaque fichier rendu. Jamais de noyau mélangé : si un fichier déjà présent diffère, rien n'est copié et la commande sort en exit 1 (`copied` faux, `blocked_by` liste les fichiers en cause) : s'arrêter là en affichant son message, sans générer les scripts CI ni poursuivre l'installation, car le `factory-run` généré ne fonctionnerait pas.

Générer deux scripts complets et équivalents (bash avec `set -euo pipefail`, PowerShell avec `$ErrorActionPreference = 'Stop'`) qui :

- prennent en **argument obligatoire** le chemin d'une spec approuvée, et une **option `--yolo`** (`-Yolo` en PowerShell) ;
- vérifient que le fichier de spec existe et contient `Statut : APPROUVEE`, sinon échouent avec un message clair ;
- exportent `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` et `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` (sans elles, `claude -p` peut lancer les sous-agents en arrière-plan et sortir avant leur fin), puis construisent l'appel : `claude -p "/factory-run '<chemin-spec>'" --output-format json --max-turns 100`, complété par défaut de `--permission-mode acceptEdits --allowedTools "<liste blanche>"`, ou par `--dangerously-skip-permissions` si `--yolo` ;
- la **liste blanche** `--allowedTools` est construite depuis la Phase 1 : toujours `Read`, `Glob`, `Grep`, `Write`, `Edit`, `Bash(git *)`, l'interpréteur retenu pour le noyau (`Bash(python *)`, `Bash(python3 *)` ou `Bash(py *)`), plus les commandes réelles du projet (ex. `Bash(dotnet *)`, `Bash(pytest *)`, `Bash(npm *)`) — uniquement celles détectées ;
- écrivent la sortie dans `factory-logs/factory-<horodatage>.json` (créer le dossier ; horodatage `date +%Y%m%d-%H%M%S` en bash, `Get-Date -Format yyyyMMdd-HHmmss` en PowerShell) et **propagent l'exit code** de `claude`.

## Phase 5 — Économie de tokens `.claude/settings.json` et `.gitignore`

Un seul appel fusionne les fichiers des phases 5 et 6 et rend l'état de chacun : `K sf apply --root . --stacks <stacks rendues par stack detect en Phase 1, séparées par des virgules>`.

- **Économie de tokens** (SF-01) : règles `permissions.deny` en `Read(...)` couvrant les artefacts de la stack détectée uniquement, plus `Read(./factory-logs/**)` et `Read(./.git/objects/**)` ; table de correspondance `STACK_DENY` du noyau ; tableaux fusionnés sans doublon, toute clé existante préservée.
- **`.gitignore`** (SF-03) : `factory-logs/` et `.harness/runs/` (journaux de cycle), créé ou complété sans dupliquer une ligne.

## Phase 6 — Tâches VS Code `.vscode/tasks.json`

Fusion SF-02 : version `2.0.0`, input `factorySpec` (« Path of the approved spec (specs/SPEC-*.md) ») et trois tâches : **« Factory: CI run »** (`./ci/factory.sh ${input:factorySpec}`, variante `windows` en `pwsh -File ci/factory.ps1`), **« Factory: CI run (YOLO) »** (`--yolo` / `-Yolo`), **« Factory: nouvelle spec (session) »** (rappel `Open Claude Code and type: /factory-run "<your need>"`) ; tâches et inputs existants préservés, rien de dupliqué.

## Phase 6b — Base de connaissance du dépôt (optionnelle)

L'usine passe l'essentiel de son budget à redécouvrir le dépôt : chaque Planner repart d'un contexte vierge, chaque Verifier relit ce que le Builder vient d'écrire. Le skill `code-index` installe un serveur local adossé à ripgrep qui répond à ces questions depuis un index versionné sous `.knowledge/`, et qui porte en plus les **notes** que les cycles laissent derrière eux — décisions, pièges, zones sensibles — partagées par git avec les autres utilisateurs du dépôt.

Poser à l'utilisateur, en un appel `AskUserQuestion`, s'il veut l'installer maintenant : `K gate decide --root . --id software-factory.code-index` (ouvre le journal `.harness/runs/software-factory-<horodatage>.jsonl`), puis `K gate answer --run <run> --id software-factory.code-index --answer "<installer|refus>"`. En cas d'accord, invoquer le skill `code-index` : il détecte l'usine qui vient d'être installée et branche seul les trois agents et `/factory-run` dessus. En cas de refus, ne rien faire : l'usine fonctionne entièrement sans, et `code-index` s'installe à tout moment sur un dépôt déjà équipé. **Ne jamais installer sans accord** : la base ajoute un dossier versionné au dépôt, ce qui se décide. En exécution headless, ne pas poser la question : `K gate answer --run <run> --id software-factory.code-index --headless` (repli `skip`), et ne rien installer.

## Phase 7 — Rapport final

Terminer par un rapport structuré : stack détectée (langages, commandes retenues, interpréteur du noyau) ; liste des fichiers avec leur état rendu par le noyau (créé / fusionné / identique / personnalisé-conservé), `.claude/harness/` compris ; absence d'outillage de test le cas échéant ; mode d'emploi en deux lignes (session : `/factory-run "besoin"` ; CI : `ci/factory.sh specs/SPEC-x.md`). Si `$ARGUMENTS` contenait un besoin, conclure par la commande exacte à lancer : `/factory-run "<le besoin>"`.
