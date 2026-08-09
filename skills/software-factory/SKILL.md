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

## Règles impératives (toutes les phases)

- **Aucun placeholder** : chaque fichier généré est complet et immédiatement opérationnel. Pas de TODO, pas de « à adapter », pas de pseudo-code, pas de commande inventée.
- **Fusion, jamais écrasement** : si `.claude/settings.json` ou `.vscode/tasks.json` existe, lire l'existant et fusionner (JSON valide, clés existantes préservées). Si un agent ou skill de l'usine existe déjà et diffère de ce qui serait généré, ne pas l'écraser : le signaler dans le rapport final.
- **Adapter à la stack** : chaque commande (test, build, lint) écrite dans un prompt ou un script doit provenir de la détection de la Phase 1, jamais d'une supposition.
- **Idempotence** : relancer ce skill sur un projet déjà équipé ne détruit rien et signale l'état de chaque fichier (créé / identique / personnalisé-conservé).

## Phase 1 — Détection de la stack

Scanner la racine du projet (et un niveau de sous-dossiers en cas de monorepo) à la recherche des marqueurs : `*.sln`/`*.csproj` (.NET), `pyproject.toml`/`requirements.txt`/`setup.py` (Python), `package.json` (Node/TS), `CMakeLists.txt`/`Makefile` (C/C++), `go.mod` (Go), `Cargo.toml` (Rust), `Dockerfile`/`docker-compose*.yml`/`compose*.yml` (conteneurs), `ansible.cfg`/`playbooks/`/`roles/` (Ansible), `*.tf` (Terraform). Lire les manifestes trouvés pour en extraire les scripts et dépendances réels.

Établir et retenir pour les phases suivantes :

- langages et frameworks présents ;
- **commande de build** réelle (ex. `dotnet build`, `npm run build`, `cmake --build build`, absente si non applicable) ;
- **commande de test** réelle (ex. `dotnet test`, `pytest`, `npm test`, `go test ./...`, `ansible-lint` + `molecule test` pour Ansible) ;
- **commande de lint/format** si configurée (`ruff`, `eslint`, `clang-format`, `dotnet format`…) ;
- conventions existantes : `CLAUDE.md`, `.editorconfig`, configuration de linters, structure des dossiers de tests.

Si aucune commande de test n'existe, le noter : le prompt du Builder devra exiger l'initialisation de l'outillage de test standard de la stack (ex. `pytest` pour Python, `xunit` pour .NET), et le rapport final le signalera à l'utilisateur.

## Phase 2 — Sous-agents natifs `.claude/agents/`

Créer trois fichiers d'agents. Chaque prompt système est rédigé intégralement, adapté à la stack détectée (nommer les langages, frameworks, commandes et conventions réels du projet), et contient : le rôle, le périmètre, les interdits, la méthode de travail, et le format de sortie exigé.

### `.claude/agents/factory-planner.md`

```yaml
---
name: factory-planner
description: Analyse un besoin et le code existant pour rédiger un brouillon de spécification avec critères d'acceptation testables et questions ouvertes. Lecture seule.
tools: Read, Glob, Grep
---
```

Le prompt système impose : analyser le besoin fourni et le code existant du projet ; produire en sortie un **brouillon de spec** en Markdown contenant obligatoirement les sections *Contexte*, *Périmètre*, *Critères d'acceptation* (chacun objectivement testable), *Hors-périmètre*, *Risques*, et une section *Questions ouvertes* listant tout point ambigu. Interdits : inventer une exigence non déductible du besoin ou du code ; modifier un fichier ; proposer une implémentation détaillée (c'est le rôle du Builder).

### `.claude/agents/factory-builder.md`

```yaml
---
name: factory-builder
description: Implémente strictement une spécification approuvée — architecture, code et tests dans un même contexte — puis exécute build et tests avant de rendre la main.
---
```

(Pas de champ `tools` : le Builder hérite de tous les outils.) Le prompt système impose : lire la spec approuvée fournie en entrée et s'y tenir strictement ; concevoir puis implémenter (architecture et code dans le même contexte pour rester cohérent) ; écrire les tests couvrant chaque critère d'acceptation ; respecter les conventions du repo (les citer : linters, style, structure détectés en Phase 1) ; exécuter la commande de build puis la commande de test réelles du projet et **ne rendre la main que si elles passent**, sinon corriger d'abord ; en cas d'entrée contenant des issues d'un Verifier, corriger chaque issue sans régresser sur les critères déjà satisfaits. Interdits : étendre le périmètre au-delà de la spec ; désactiver ou ignorer un test ou un warning pour « faire passer » ; commiter.

### `.claude/agents/factory-verifier.md`

```yaml
---
name: factory-verifier
description: Vérification adversariale d'une implémentation par rapport à sa spec — exécute les tests, cherche à casser, rend un verdict JSON strict. Ne modifie jamais le code.
tools: Read, Glob, Grep, Bash
---
```

Le prompt système impose : partir de la spec et du diff (`git diff` + `git status`) sans aucun a priori favorable ; exécuter la commande de test réelle du projet et rapporter son exit code ; vérifier un à un chaque critère d'acceptation ; chercher activement à casser l'implémentation (cas limites, entrées invalides, erreurs d'intégration) ; terminer sa réponse par un unique bloc JSON, sans texte après :

```json
{"verdict": "APPROVED" | "CHANGES_REQUESTED", "tests_passed": true | false, "issues": [{"file": "chemin", "severity": "critical|major|minor", "description": "..."}]}
```

Interdits : modifier le moindre fichier ; approuver si les tests échouent ou si un critère d'acceptation n'est pas couvert ; rendre un verdict sans avoir exécuté les tests.

## Phase 3 — Skill d'orchestration `.claude/skills/factory-run/SKILL.md`

Créer le skill projet qui pilote un cycle complet. Frontmatter exact :

```yaml
---
name: factory-run
description: Lance un cycle de l'usine logicielle (Planner → gate humaine sur la spec → Builder → Verifier avec boucle de correction) sur un besoin ou une spec approuvée.
disable-model-invocation: true
argument-hint: "<besoin | chemin d'une spec approuvée>"
---
```

Le corps (rédigé intégralement, voix impérative, adapté à la stack) définit ce déroulé pour la session principale :

1. **Entrée** : si `$ARGUMENTS` est le chemin d'un fichier existant sous `specs/` dont la première ligne de statut vaut `Statut : APPROUVEE`, passer directement à l'étape 3. Sinon, traiter `$ARGUMENTS` comme un besoin.
2. **Phase Plan (gate humaine)** : lancer le sous-agent `factory-planner` avec le besoin ; à son retour, poser à l'utilisateur les *Questions ouvertes* du brouillon (AskUserQuestion) ; intégrer les réponses, écrire `specs/SPEC-<slug-du-besoin>.md` avec en tête `Statut : PROPOSEE` ; présenter la spec à l'utilisateur et demander son approbation explicite ; en cas d'approbation, passer le statut à `APPROUVEE` ; sinon itérer sur la spec. **Si aucune interaction n'est possible (exécution headless), s'arrêter en erreur explicite : un cycle CI exige le chemin d'une spec déjà approuvée.** Ne jamais construire sans spec approuvée.
3. **Phase Build** : lancer le sous-agent `factory-builder` (contexte frais) avec le chemin de la spec approuvée.
4. **Phase Verify — boucle de correction, 3 itérations maximum** :
   1. Lancer un sous-agent `factory-verifier` (contexte vierge, indépendant du Builder) avec le chemin de la spec ; récupérer son bloc JSON.
   2. Si `verdict` vaut `APPROVED` **et** `tests_passed` vaut `true` : sortir de la boucle, succès.
   3. Sinon : relancer `factory-builder` avec la spec **et la liste complète des `issues` du Verifier** (fichier, sévérité, description) et la consigne de corriger sans régresser ; puis reprendre à l'étape 1 avec un nouveau Verifier.
   4. Tenir le compteur d'itérations ; après la 3e itération non approuvée, **échouer explicitement** en publiant les issues restantes. Ne jamais approuver par épuisement.
5. **Rapport final** : fichiers modifiés (`git status`), résultat des tests, verdict, nombre d'itérations, prochaine action suggérée (revue du diff par l'utilisateur ; ne pas commiter à sa place).

## Phase 4 — Scripts CI minces `ci/factory.sh` et `ci/factory.ps1`

Générer deux scripts complets et équivalents (bash avec `set -euo pipefail`, PowerShell avec `$ErrorActionPreference = 'Stop'`) qui :

- prennent en **argument obligatoire** le chemin d'une spec approuvée, et une **option `--yolo`** (`-Yolo` en PowerShell) ;
- vérifient que le fichier de spec existe et contient `Statut : APPROUVEE`, sinon échouent avec un message clair ;
- construisent l'appel : `claude -p "/factory-run '<chemin-spec>'" --output-format json --max-turns 100`, complété par défaut de `--permission-mode acceptEdits --allowedTools "<liste blanche>"`, ou par `--dangerously-skip-permissions` si `--yolo` ;
- la **liste blanche** `--allowedTools` est construite depuis la Phase 1 : toujours `Read`, `Glob`, `Grep`, `Write`, `Edit`, `Bash(git *)`, plus les commandes réelles du projet (ex. `Bash(dotnet *)`, `Bash(pytest *)`, `Bash(npm *)`) — uniquement celles détectées ;
- écrivent la sortie dans `factory-logs/factory-<horodatage>.json` (créer le dossier ; horodatage `date +%Y%m%d-%H%M%S` en bash, `Get-Date -Format yyyyMMdd-HHmmss` en PowerShell) et **propagent l'exit code** de `claude`.

Ajouter `factory-logs/` au `.gitignore` du projet (le créer ou compléter sans dupliquer la ligne).

## Phase 5 — Économie de tokens `.claude/settings.json`

Créer ou fusionner `.claude/settings.json` avec des règles `permissions.deny` en `Read(...)` couvrant les artefacts de la stack détectée uniquement (fusionner les tableaux sans doublon, préserver toute clé existante). Correspondances : Node → `Read(./node_modules/**)`, `Read(./dist/**)` ; .NET → `Read(./**/bin/**)`, `Read(./**/obj/**)` ; Python → `Read(./.venv/**)`, `Read(./**/__pycache__/**)`, `Read(./.pytest_cache/**)` ; C/C++ → `Read(./build/**)` ; Rust → `Read(./target/**)` ; générique → `Read(./factory-logs/**)`, `Read(./.git/objects/**)`. N'inclure que ce qui correspond à la stack, plus les règles génériques.

## Phase 6 — Tâches VS Code `.vscode/tasks.json`

Créer ou fusionner `.vscode/tasks.json` (version `2.0.0`) avec :

- une entrée `inputs` de type `promptString`, id `factorySpec`, décrivant « Chemin de la spec approuvée (specs/SPEC-*.md) » ;
- une tâche **« Factory: CI run »** exécutant `./ci/factory.sh ${input:factorySpec}` avec la variante `windows` exécutant `pwsh -File ci/factory.ps1 ${input:factorySpec}` ;
- une tâche **« Factory: CI run (YOLO) »** identique avec l'option `--yolo` / `-Yolo` ;
- une tâche **« Factory: nouvelle spec (session) »** de type shell qui affiche simplement le rappel : `Ouvrir Claude Code et taper : /factory-run "<votre besoin>"`.

En cas de fusion, préserver les tâches et inputs existants ; ne pas dupliquer si les tâches Factory existent déjà.

## Phase 7 — Rapport final

Terminer par un rapport structuré : stack détectée (langages, commandes retenues) ; liste des fichiers avec leur état (créé / fusionné / identique / personnalisé-conservé) ; absence d'outillage de test le cas échéant ; mode d'emploi en deux lignes (session : `/factory-run "besoin"` ; CI : `ci/factory.sh specs/SPEC-x.md`). Si `$ARGUMENTS` contenait un besoin, conclure par la commande exacte à lancer : `/factory-run "<le besoin>"`.
