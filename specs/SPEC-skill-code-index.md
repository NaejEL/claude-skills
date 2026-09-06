# SPEC — Skill `code-index` : serveur de connaissance local adossé à ripgrep

Statut : APPROUVEE

## Contexte

Besoin exprimé par l'utilisateur, mot pour mot : « J'aurais besoin de pouvoir ajouter un petit serveur ripgrep local dans mes repos via software-factory et ai-lab qui serait utilisé par mes skills. Les artefacts de ripgrep (graph, son, sqlite, etc.) doivent etre versionnés dans le repo pour facilement partager la base de connaissance d'un utilisateur à l'autre. Idéalement je dois pouvoir facilement ajouter cette competence à mes repo qui ont deja la softwar-factory ou le lab ai deja installé ».

Quatre exigences en sortent : (a) un **serveur ripgrep local** installable dans un dépôt et consommé par les skills ; (b) des **artefacts versionnés** (graphe, json, sqlite) ; (c) leur finalité — **partager une base de connaissance** entre utilisateurs ; (d) une **installation facile sur un dépôt déjà équipé** de `/software-factory` ou de `/ai-lab`.

État du dépôt `C:\Users\fuzzz\claude-skills` :

- Six skills de premier niveau, aucun ne fournit d'indexation ni de recherche outillée : `software-factory`, `ship-pr`, `legacy-audit`, `ai-lab`, `ai-lab-audit`, `brainstorm`.
- `software-factory` et `ai-lab` installent des sous-agents `.claude/agents/*.md` et un skill projet (`/factory-run`, `/lab-run`), fusionnent `.claude/settings.json` et `.vscode/tasks.json`, génèrent des scripts headless `ci/*.sh` et `ci/*.ps1` avec une liste blanche `--allowedTools`. Les agents en lecture seule y portent un champ `tools` **limitatif** (`Read, Glob, Grep`), qui masque tout outil MCP non nommé.
- Conventions des `SKILL.md` de premier niveau : frontmatter à cinq clés (`name`, `description`, `context: fork`, `user-invocable: true`, `argument-hint`), titre H1 `# <Nom> — <sous-titre>`, paragraphe d'intention, section de parsing de `$ARGUMENTS`, `## Règles impératives (toutes les phases)`, phases numérotées, dernière phase = rapport final, français, voix impérative. `ai-lab` établit le précédent d'une phase intercalaire non renumérotante (`Phase 2b`).
- Règle transverse déjà présente dans les deux skills cibles : « Fusion, jamais écrasement » et idempotence avec état par fichier.
- `install_skills.sh` et `install_skills.ps1` énumèrent les sous-dossiers de `skills/` ; aucun nom n'y est codé en dur. Un nouveau skill est installable sans les modifier.
- Aucun test, aucun linter, aucun `.editorconfig`.
- Contrainte de l'environnement constatée : `rg` **n'est pas dans le `PATH`** de la machine de l'utilisateur (seules des copies embarquées par VS Code, Antigravity et Copilot existent). `python` (3.12) et `py` (3.9) répondent.

## Décisions

- **Q1 — Interface** : serveur **MCP stdio + CLI** partageant les mêmes fonctions. Le MCP sert les sous-agents sans alourdir leur prompt ; la CLI sert le Bash, le headless et les tâches VS Code.
- **Q2 — Format des artefacts** : **texte source, sqlite dérivé versionné**. `notes.jsonl` et `config.json` sont la vérité ; `files.jsonl`, `symbols.jsonl`, `graph.json`, `manifest.json` et `index.sqlite` sont dérivés et commités quand même, pour qu'un `git clone` donne une base immédiatement interrogeable. Le sqlite ne se fusionne pas : il se régénère.
- **Q3 — Packaging** : **skill autonome `code-index` + phase déléguée**. Le skill s'installe seul sur un dépôt déjà équipé et détecte l'usine ou le labo pour les câbler ; `software-factory` et `ai-lab` gagnent une `Phase 6b` qui propose son installation.
- **Q4 — Runtime** : **Python bibliothèque standard** (`sqlite3`, `json`, `argparse`, `subprocess`), zéro `pip install`, cohérent avec `ai-lab` déjà Python-centré. Node est écarté : `node:sqlite` n'existe qu'à partir de Node 22 et reste expérimental, ce qui imposerait une dépendance npm.
- **Q5 — Livraison du serveur** : **asset versionné dans le skill** (`skills/code-index/assets/rgkb.py`), copié tel quel, et non regénéré par le modèle à chaque installation. Un programme de ~900 lignes redécrit en prose diverge de sa documentation dès la deuxième installation.
- **Q6 — Réglages propres à une machine** : fichier `.knowledge/config.local.json`, fusionné par-dessus `config.json` et **seul fichier ignoré** du dossier. Rendu nécessaire par le constat que `rg` n'est pas dans le `PATH` : un chemin absolu dans un fichier versionné casserait la base pour les autres utilisateurs.
- **Q7 — Câblage non destructif** : bloc délimité par les marqueurs littéraux `<!-- rgkb:debut -->` / `<!-- rgkb:fin -->` dans les fichiers d'agents et de skills existants, remplacé et non dupliqué à la relance.
- **Q9 — Installation des outils externes** : portée par `install_skills.sh` / `install_skills.ps1`, avec **détection du gestionnaire de paquets** (winget → scoop → chocolatey sous Windows ; brew ou MacPorts sous macOS ; apt, dnf, paru/yay/pacman, zypper, apk, xbps, nix sous Linux ; `cargo install` en dernier recours). Objectif énoncé par l'utilisateur : « éviter au maximum les actions à faire par l'utilisateur ». L'échec d'une installation n'interrompt pas la liaison des skills et ne change pas le code de sortie du script.
- **Q10 — Factorisation** : la détection du gestionnaire et l'installation d'un paquet sont une **couche générique** indépendante de ripgrep (`detect_pkg_manager`, `pkg_install`, `ensure_tool` en bash ; `Get-PackageManager`, `Invoke-PackageInstall`, `Install-ToolIfMissing` en PowerShell). Les outils sont décrits par une table séparée (`tool_package` / `Get-ToolPackage`) qui donne l'identifiant de paquet **par gestionnaire**, l'identifiant ne coïncidant ni avec le nom de la commande ni d'un gestionnaire à l'autre. Ajouter un outil = une entrée de table + un appel. Bash 3.2 compatible (macOS) : pas de tableau associatif, `case` uniquement.
- **Q8 — Volume des notes** : plafond de 1 à 3 notes par cycle, et interdiction de consigner ce que l'index retrouve seul. Une base qui enregistre tout ne se lit plus.

- **Q11 — Fraîcheur hors cycle** : hooks git `post-merge` et `post-rewrite` par défaut, plus `pre-commit` en option `--with-commit`. **`post-checkout` est exclu par construction** : testé, il salit l'arbre de travail après chaque changement de branche et fait échouer le checkout suivant (« local changes would be overwritten »), parce qu'un commit ordinaire ne réindexe pas et que chaque branche porte donc un index périmé que le hook contredit aussitôt. `pre-commit` supprime la cause — tout commit porte un index cohérent — et rend `post-checkout` inutile. Les hooks reposent sur l'écriture conditionnelle (`write_if_changed`) : sans elle, ils produiraient un diff à chaque opération git.

- **Q12 — Propagation des hooks** : `.git/hooks/` n'est pas versionnable, mais l'**intention** l'est. La clé `hooks` de `.knowledge/config.json` (`off` / `auto` / `commit`) est écrite par `hooks install` et lue par `status` et `index`, qui réconcilient les hooks locaux avec elle. Un utilisateur qui clone les obtient au premier cycle sans aucun geste. Contrepartie assumée : cloner un dépôt qui déclare `hooks` puis lancer rgkb installe des hooks git locaux — acceptable ici parce que le hook ne lance que rgkb, lui-même déjà présent dans le dépôt et déjà exécuté par l'utilisateur.

## Périmètre

1. Créer `skills/code-index/assets/rgkb.py` : programme Python autonome (indexation ripgrep, artefacts `.knowledge/`, cache sqlite, notes, serveur MCP stdio, CLI).
2. Créer `skills/code-index/SKILL.md` conforme aux conventions des skills de premier niveau, avec phases d'installation, de câblage et de rapport.
3. Ajouter une `## Phase 6b` à `skills/software-factory/SKILL.md` et à `skills/ai-lab/SKILL.md`, proposant l'installation sous gate humaine, sans renuméroter les phases existantes.
4. Ajouter la sous-section `### \`code-index\`` dans `## Skills` de `README.md`, et documenter dans `## Installation` l'installation automatique de ripgrep.
5. Ajouter à `install_skills.sh` et `install_skills.ps1` une couche générique d'installation d'outils externes par détection du gestionnaire de paquets, avec une table d'outils séparée (ripgrep pour seule entrée) et une option de désactivation (`--skip-tools` / `-SkipTools`).

## Critères d'acceptation

- [x] CA1 — `skills/code-index/SKILL.md` et `skills/code-index/assets/rgkb.py` existent.
- [x] CA2 — Le frontmatter du skill porte `name: code-index` (identique au nom du dossier), `context: fork`, `user-invocable: true`, `argument-hint`, et une `description` en français mentionnant ripgrep, le versionnement des artefacts et le partage entre utilisateurs.
- [x] CA3 — Le corps contient `## Règles impératives (toutes les phases)`, une section de parsing de `$ARGUMENTS` couvrant `--reindex` et `--no-wire`, des phases numérotées consécutives et un rapport final en dernière phase.
- [x] CA4 — `rgkb.py` n'importe que la bibliothèque standard.
- [x] CA5 — `rgkb.py init` crée `.knowledge/` avec `config.json`, `notes.jsonl`, `README.md`, `.gitattributes` (déclarant `index.sqlite` binaire) et `.gitignore` (n'excluant que `config.local.json`).
- [x] CA6 — `rgkb.py index` produit `files.jsonl`, `symbols.jsonl`, `graph.json`, `manifest.json` et `index.sqlite`, et rend les compteurs.
- [x] CA7 — Une seconde exécution d'`index` sans changement de code ne réécrit aucun fichier (`changed: []`) : pas de churn git.
- [x] CA8 — `manifest.json` ne contient ni horodatage, ni chemin absolu, ni version de `rg` : deux utilisateurs indexant le même arbre obtiennent le même manifeste.
- [x] CA9 — `rgkb.py status` détecte les fichiers ajoutés, modifiés et supprimés depuis l'indexation, et `status --check` sort en code 1 si l'index est périmé.
- [x] CA10 — `config.local.json` est fusionné par-dessus `config.json`, permet de renseigner `rg_path`, et n'influence pas `config_digest` du manifeste.
- [x] CA11 — L'absence de `rg` produit un message d'erreur nommant les commandes d'installation par plateforme et les deux échappatoires (`rg_path`, `RGKB_RG`), et un code de sortie non nul, jamais une trace Python.
- [x] CA12 — Le serveur MCP répond à `initialize`, `tools/list` et `tools/call` en JSON-RPC ligne par ligne sur stdio, expose les 9 outils (`search`, `definition`, `symbols`, `neighbors`, `file_card`, `notes`, `note_add`, `status`, `reindex`), et rend une erreur d'outil en `isError: true` sans arrêter le serveur.
- [x] CA13 — Aucune écriture sur `stdout` en mode MCP hors messages du protocole.
- [x] CA14 — `note_add` ajoute une ligne triée à `notes.jsonl`, refuse un doublon exact (même sujet, même texte) et reconstruit le cache sqlite.
- [x] CA15 — Les règles impératives du skill interdisent d'ajouter `.knowledge/` au `.gitignore` et imposent de vérifier qu'aucune règle existante ne l'exclut par ricochet, avec contre-règle `!.knowledge/**` signalée dans le rapport.
- [x] CA16 — Les règles impératives interdisent tout chemin absolu dans `.mcp.json` et `.knowledge/config.json`, et renvoient les réglages locaux vers `config.local.json`.
- [x] CA17 — La phase d'enregistrement MCP fusionne `.mcp.json` en préservant les serveurs existants, ajoute `rgkb` à `enabledMcpjsonServers`, autorise les 7 outils de lecture, et **laisse hors autorisation automatique** `note_add` et `reindex` (seuls outils qui écrivent dans des fichiers versionnés).
- [x] CA18 — La phase de câblage impose d'ajouter nommément les outils `mcp__rgkb__*` au champ `tools` des agents en lecture seule, et rappelle qu'un joker n'y fonctionne pas.
- [x] CA19 — Le câblage se fait par bloc délimité `<!-- rgkb:debut -->` / `<!-- rgkb:fin -->`, remplacé et non dupliqué à la relance.
- [x] CA20 — Le câblage de `/factory-run` et `/lab-run` définit deux ancrages : vérification de fraîcheur avant la première phase qui dépense, proposition de note à la consignation finale, plafonnée à 3 notes par cycle.
- [x] CA21 — `--no-wire` saute la phase de câblage et le rapport final le signale ; `--reindex` force la réindexation.
- [x] CA22 — Le rapport final énumère les fichiers avec leur état, la liste exacte des chemins à commiter, la prise en main pour un second utilisateur, et le rappel qu'un redémarrage est nécessaire pour charger le serveur MCP.
- [x] CA23 — `skills/software-factory/SKILL.md` et `skills/ai-lab/SKILL.md` contiennent chacun une `## Phase 6b` proposant l'installation sous `AskUserQuestion`, interdisant l'installation sans accord et l'interdisant en headless ; aucune phase existante n'est renumérotée.
- [x] CA24 — `README.md` contient `### \`code-index\`` entre `## Skills` et `## Ajouter un skill`, avec un bloc `text` d'invocation, le tableau source/dérivé des artefacts et la procédure de conflit git.
- [x] CA25 — `install_skills.sh` et `install_skills.ps1` installent ripgrep quand `rg` est absent, en détectant le gestionnaire de paquets de la machine ; `rg` déjà présent est signalé et rien n'est installé.
- [x] CA25a — `--skip-tools` (bash) et `-SkipTools` (PowerShell) sautent cette installation ; les anciens noms `--skip-ripgrep` / `-SkipRipgrep` restent acceptés ; un argument inconnu est refusé avec un message clair.
- [x] CA25e — La détection du gestionnaire et l'installation d'un paquet ne mentionnent nulle part ripgrep : elles prennent un identifiant de paquet en paramètre. La table des outils est le seul endroit où ripgrep apparaît, et un outil absent de la table est refusé proprement (code 1 / `$null`) sans installer quoi que ce soit.
- [x] CA25b — L'échec de l'installation de ripgrep n'empêche pas la liaison des skills et ne change pas le code de sortie ; il produit un avertissement nommant les deux issues (installation manuelle, `rg_path` dans `config.local.json`).
- [x] CA25c — Sous Windows, le `PATH` de la session est rafraîchi depuis le registre après l'installation, avant de reconclure à la présence de `rg`.
- [x] CA25d — `bash -n install_skills.sh` sort en code 0 et `install_skills.ps1` passe l'analyse syntaxique PowerShell (non-régression).
- [x] CA26a — `rgkb hooks install` installe `post-merge` et `post-rewrite` ; `--with-commit` ajoute `pre-commit` ; `hooks status` et `hooks remove` couvrent les trois. Hors dépôt git, la commande rend `ok: false` avec une raison, sans trace Python.
- [x] CA26b — Les hooks sont réentrants : une seconde installation rend `identique` pour chaque hook, sans réécrire le fichier.
- [x] CA26c — Un hook préexistant écrit par un tiers est **complété** par un bloc délimité `# >>> rgkb >>>` / `# <<< rgkb <<<`, jamais écrasé ; `hooks remove` retire le bloc et conserve le reste, ou supprime le fichier s'il ne restait que le shebang.
- [x] CA26d — `RGKB_NO_HOOK=1` neutralise les hooks ; un hook n'échoue jamais l'opération git ; les fins de ligne écrites sont LF y compris sous Windows.
- [x] CA26e — Avec `pre-commit` installé, un aller-retour de branche laisse l'arbre de travail propre et aucun checkout n'est refusé.
- [x] CA26f — `hooks install` / `remove` écrivent la clé `hooks` de `config.json` ; `status` et `index` réconcilient les hooks locaux avec elle et ne rapportent que ce qui a changé. Avec `hooks: off` (défaut), rien n'est installé.
- [x] CA26g — Scénario à deux utilisateurs vérifié : A active les hooks et commite ; B clone et, sans lancer autre chose que `status`, obtient les trois hooks, puis son commit embarque `.knowledge/` et laisse l'arbre propre.
- [x] CA26 — Aucun `skills/*/SKILL.md` existant n'est modifié en dehors de l'ajout de la `Phase 6b` dans les deux skills cibles.

## Hors-périmètre

- Toute modification de `install_skills.sh` et `install_skills.ps1` **au-delà de l'installation de ripgrep** : la logique de liaison des skills est inchangée.
- Toute modification de `ship-pr`, `legacy-audit`, `ai-lab-audit`, `brainstorm`.
- L'installation d'un gestionnaire de paquets : les scripts utilisent celui qui est présent, ils n'en installent pas (pas de `scoop`/`brew` installé en douce).
- Le remplissage de la table d'outils au-delà de ripgrep : la couche est faite pour accueillir `fd`, `jq` ou autre, aucun n'est ajouté tant qu'un skill n'en a pas besoin.
- Une analyse syntaxique réelle (AST, LSP, tree-sitter) : l'extraction reste à base d'expressions régulières ripgrep, avec les faux positifs et les manques que cela implique. Le skill impose de signaler `symbols: 0` sur un projet qui a du code plutôt que de laisser croire à un index utile.
- Un index incrémental : la réindexation est complète. Elle est rapide parce que ripgrep l'est — mesuré seulement sur des projets de quelques fichiers, non sur un gros dépôt.
- La recherche sémantique, les embeddings, tout serveur distant.
- Le commit : le skill indique quoi commiter, l'utilisateur décide.

## Risques

- **Absence de `rg` sur la machine** — constatée ici. Traitée en amont par les scripts d'installation, qui l'installent via le gestionnaire de paquets détecté (Q9), et en aval par la Phase 1 du skill, qui détecte, propose et **exécute** la commande adaptée plutôt que de la faire taper. Repli local par `config.local.json`. Risque résiduel : sous Windows, `rg` peut n'apparaître dans le `PATH` qu'au terminal suivant — les deux chemins rafraîchissent le `PATH` puis revérifient, et le disent au lieu de conclure à un échec.
- **Binaire dans git** — `index.sqlite` ne se fusionne pas. Atténué par : sources en texte, `.gitattributes` marquant le fichier binaire, procédure de conflit documentée dans `.knowledge/README.md` et dans le `README.md` du dépôt, régénération par `index --force`.
- **Churn git à chaque réindexation** — annulerait le bénéfice du versionnement. Traité par CA7 et CA8 : aucun horodatage dans les artefacts, écriture uniquement si le contenu change, sqlite reconstruit seulement si l'empreinte diffère. Reste un churn inhérent : décaler des lignes dans un fichier déplace les numéros de ligne de ses symboles.
- **Interpréteur Python dans un `.mcp.json` versionné** — un venv ou un chemin absolu casserait le fichier pour les autres. Traité par CA16 et par la Phase 1, qui n'accepte qu'une commande résolue par le `PATH`.
- **Outils MCP invisibles pour les agents à `tools` limitatif** — panne silencieuse : l'agent retombe sur `Grep` sans rien signaler. Traité par CA18.
- **Dérive de l'asset et de sa documentation** — traitée par la règle « copié tel quel » et par la comparaison de `TOOL_VERSION` en Phase 2, qui refuse d'écraser un fichier de version supérieure.
- **Base de connaissance qui devient un dépotoir** — une base illisible ne sera plus lue et l'exigence de partage tombe. Traitée par le plafond de 3 notes par cycle et l'interdiction de consigner ce que l'index retrouve seul.
- **Recouvrement de `description` avec les skills existants** — `code-index` installe une capacité, comme `software-factory` et `ai-lab`. Sa `description` insiste sur ripgrep, l'index et le partage par git, termes absents des autres.
