---
name: code-index
description: Installe dans le projet courant un serveur de connaissance local adossé à ripgrep — index de code (symboles, graphe, notes, cache sqlite) versionné sous .knowledge/ pour se transmettre d'un utilisateur à l'autre par git — exposé aux agents par un serveur MCP stdio et par une CLI équivalente. Détecte une usine logicielle (/factory-run) ou un laboratoire IA (/lab-run) déjà installé et branche leurs agents dessus sans les réécrire. À utiliser quand l'utilisateur veut ajouter la recherche indexée et la base de connaissance partagée à un dépôt, neuf ou déjà équipé.
context: fork
user-invocable: true
argument-hint: "[--reindex] [--no-wire]"
---

# Code Index — serveur de connaissance local adossé à ripgrep

Installer dans le projet courant **rgkb**, une base de connaissance locale du dépôt : ripgrep indexe le code, les artefacts qui en sortent (fichiers, symboles, graphe de mentions, cache sqlite) et les **notes écrites par les humains et par les agents** vivent sous `.knowledge/`, **versionné dans le dépôt**. Un `git clone` suffit donc à récupérer la connaissance accumulée par les autres utilisateurs : rien à reconstruire, rien à réapprendre.

Le serveur est un programme Python de bibliothèque standard, sans aucune dépendance à installer, livré avec ce skill (`assets/rgkb.py`). Il s'expose de deux façons équivalentes : un **serveur MCP stdio** que les sous-agents interrogent comme n'importe quel outil, et une **CLI** utilisable en Bash et en headless. Ce skill installe le serveur, l'enregistre, l'indexe une première fois, et **branche dessus les agents déjà présents** — usine logicielle ou laboratoire IA — sans réécrire leurs prompts.

La règle qui justifie l'ensemble : *l'index se régénère, les notes ne se régénèrent pas*. Un symbole perdu se retrouve en réindexant ; la raison pour laquelle une fonction ne doit pas être appelée deux fois, elle, ne se retrouve que si quelqu'un l'a écrite. Le premier rôle de rgkb est de faire descendre dans le dépôt ce que chaque session redécouvre.

## Parsing de `$ARGUMENTS`

- `--reindex` : forcer une réindexation complète même si `.knowledge/` est déjà à jour (Phase 4 s'exécute avec `index --force`).
- `--no-wire` : n'installer que le serveur et les artefacts ; ne pas modifier les agents ni les skills d'orchestration existants (Phase 6 est sautée et le rapport final le signale).
- Tout autre contenu : le rappeler dans le rapport final sans l'interpréter. Ce skill n'a pas d'autre paramètre.

## Règles impératives (toutes les phases)

- **Aucun placeholder** : chaque fichier généré ou modifié est complet et immédiatement opérationnel. Pas de TODO, pas de « à adapter », pas de commande inventée.
- **Fusion, jamais écrasement** : `.mcp.json`, `.claude/settings.json`, `.vscode/tasks.json`, `.gitignore` et les fichiers d'agents existants sont lus puis fusionnés. Aucune clé existante n'est supprimée, aucune tâche existante n'est perdue, aucun prompt d'agent n'est réécrit — on **ajoute** une section délimitée, identifiable et réentrante.
- **`assets/rgkb.py` est copié tel quel**, sans retouche. C'est un programme testé : le modifier à l'installation le désaligne des artefacts qu'il produit et de la documentation de ce skill. Si une adaptation semble nécessaire, la signaler dans le rapport final au lieu de l'appliquer.
- **`.knowledge/` est versionné.** Ne jamais l'ajouter au `.gitignore`, et **vérifier activement** qu'aucune règle existante ne l'exclut déjà (`.knowledge`, `*.sqlite`, `*.db`, `*.jsonl`, `data/`). Si une règle l'exclut, ne pas la supprimer en silence : ajouter une contre-règle explicite `!.knowledge/**` et le dire dans le rapport. Le seul fichier non versionné du dossier est `config.local.json`, exclu par le `.gitignore` que `rgkb init` écrit dans `.knowledge/`.
- **Rien de propre à une machine dans un fichier versionné.** `.mcp.json` et `.knowledge/config.json` sont partagés : ils ne contiennent que des commandes résolues par le `PATH`, jamais un chemin absolu. Tout réglage local (chemin de `rg`, exclusions personnelles) va dans `.knowledge/config.local.json`.
- **Ne jamais commiter** : ni les artefacts, ni les fichiers de configuration. Le rapport final indique quoi commiter, l'utilisateur décide.
- **Idempotence** : relancer ce skill sur un projet déjà équipé ne détruit rien. Chaque fichier est rapporté avec son état (créé / fusionné / identique / personnalisé-conservé).

## Phase 1 — Prérequis

**ripgrep.** Exécuter `rg --version`. C'est la seule dépendance externe, et elle est bloquante pour l'indexation.

- Si la commande répond, retenir la version.
- Si elle échoue, **détecter le gestionnaire de paquets de la machine et proposer l'installation**, exactement comme le fait `install_skills.ps1` / `install_skills.sh` du dépôt de skills : Windows → `winget install --id BurntSushi.ripgrep.MSVC -e --source winget --silent --accept-package-agreements --accept-source-agreements`, sinon `scoop install ripgrep`, sinon `choco install ripgrep -y` ; macOS → `brew install ripgrep` ; Debian/Ubuntu → `apt-get install -y ripgrep` ; Fedora → `dnf install -y ripgrep` ; Arch → `paru`/`yay`, sinon `pacman -S --needed ripgrep` ; openSUSE → `zypper`, Alpine → `apk`, Void → `xbps-install`, Nix → `nix-env -iA nixpkgs.ripgrep` ; en dernier recours `cargo install ripgrep`. Soumettre la commande retenue à l'utilisateur en un appel `AskUserQuestion` (installer une dépendance système se décide), puis **l'exécuter soi-même** — ne pas la lui faire taper. Sous Windows, `rg` n'apparaît dans le `PATH` de la session qu'après rafraîchissement : revérifier avec `rg --version` et, si la commande ne répond toujours pas, le signaler comme nécessitant un nouveau terminal plutôt que comme un échec.
- Ne jamais chercher un binaire embarqué par un autre logiciel (VS Code, Copilot) pour le figer dans un fichier versionné : ce serait un chemin absolu imposé à toute l'équipe. Si l'installation échoue ou est refusée, proposer le repli **local** : `.knowledge/config.local.json` avec `{"rg_path": "..."}`, valable pour cette machine seulement. Poursuivre l'installation dans tous les cas ; en l'absence de `rg` utilisable, les phases 4 et suivantes s'arrêtent proprement et le rapport final donne la commande à relancer.

**Interpréteur Python.** Chercher, dans cet ordre, une commande **résolue par le `PATH`** qui réponde à `--version` : `python`, `python3`, `py -3`. Retenir la première qui répond. Ne pas retenir le chemin d'un environnement virtuel du projet : `.mcp.json` est versionné, et le venv d'un utilisateur n'existe pas chez les autres. Si aucune ne répond, le signaler comme bloquant pour le serveur MCP — la CLI reste utilisable avec l'interpréteur que l'utilisateur choisira — et poursuivre.

**État du dépôt.** Relever, sans rien modifier :

- présence d'un dépôt git (`.git/`) et contenu du `.gitignore` racine ;
- présence d'une **usine logicielle** : `.claude/agents/factory-planner.md`, `factory-builder.md`, `factory-verifier.md`, `.claude/skills/factory-run/SKILL.md` ;
- présence d'un **laboratoire IA** : `.claude/agents/lab-director.md`, `lab-neuro.md`, `lab-math.md`, `lab-builder.md`, `lab-verifier.md`, `.claude/skills/lab-run/SKILL.md` ;
- présence d'une installation antérieure de rgkb : `.claude/rgkb/rgkb.py`, `.knowledge/manifest.json`, entrée `rgkb` dans `.mcp.json` ;
- stack du projet (les mêmes marqueurs que l'usine logicielle : `*.csproj`, `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `CMakeLists.txt`, `*.tf`, `ansible.cfg`) et **dossiers volumineux** qui n'ont rien à faire dans l'index (`node_modules/`, `.venv/`, `bin/`, `obj/`, `dist/`, `build/`, `target/`, `data/`, `checkpoints/`, `models/`, `wandb/`, `runs/`, `experiments/results/`, `factory-logs/`, `lab-logs/`).

## Phase 2 — Installation du serveur

Copier `assets/rgkb.py` — le fichier voisin de ce `SKILL.md`, dans le dossier de ce skill — vers `.claude/rgkb/rgkb.py` du projet, en créant le dossier.

- Si le fichier de destination n'existe pas : le créer, état *créé*.
- S'il existe et est **identique** octet pour octet : ne rien faire, état *identique*.
- S'il existe et **diffère** : comparer la constante `TOOL_VERSION` des deux fichiers. Si celle de l'asset est plus récente ou égale, écraser (c'est une mise à jour du serveur, dont les artefacts restent lisibles : le schéma est versionné dans `manifest.json`) et l'annoncer. Si le fichier du projet porte une version **supérieure** à celle de l'asset, ne pas écraser : état *personnalisé-conservé*, signalé dans le rapport.

Ne jamais modifier le contenu copié.

## Phase 3 — Enregistrement du serveur MCP

**`.mcp.json` à la racine du projet** (créer s'il est absent, fusionner sinon — préserver tous les serveurs déjà déclarés) :

```json
{
  "mcpServers": {
    "rgkb": {
      "command": "python",
      "args": [".claude/rgkb/rgkb.py", "mcp"]
    }
  }
}
```

`command` prend la commande retenue en Phase 1 (`python`, `python3`, ou `py` avec `-3` inséré en tête de `args`). Ce fichier est versionné : il ne contient jamais un chemin absolu.

**`.claude/settings.json`** (créer ou fusionner, en préservant toute clé existante et sans doublon dans les tableaux) :

- `enabledMcpjsonServers` : ajouter `"rgkb"`, pour que le serveur du projet soit actif sans validation manuelle à chaque session ;
- `permissions.allow` : ajouter les outils de **lecture** — `mcp__rgkb__search`, `mcp__rgkb__definition`, `mcp__rgkb__symbols`, `mcp__rgkb__neighbors`, `mcp__rgkb__file_card`, `mcp__rgkb__notes`, `mcp__rgkb__status` — et la CLI en lecture : `Bash(python .claude/rgkb/rgkb.py *)` (avec la commande d'interpréteur retenue). Ne **pas** mettre `mcp__rgkb__note_add` ni `mcp__rgkb__reindex` en autorisation automatique : ce sont les deux seuls outils qui écrivent dans des fichiers versionnés, ils passent par la validation habituelle ;
- `permissions.deny` : ajouter `Read(./.knowledge/index.sqlite)` et `Read(./.knowledge/graph.json)`. Ces deux fichiers sont faits pour être **interrogés** par les outils rgkb, pas chargés en contexte ; les lire entiers coûte cher et n'apprend rien de plus. `symbols.jsonl`, `files.jsonl` et `notes.jsonl` restent lisibles : ce sont des fichiers texte qu'on a parfois de bonnes raisons d'ouvrir.

## Phase 4 — Périmètre de l'index et première indexation

Exécuter `python .claude/rgkb/rgkb.py init`, qui crée `.knowledge/` avec `config.json`, `notes.jsonl`, `README.md`, `.gitattributes` (déclare `index.sqlite` binaire pour que git ne tente jamais de le fusionner ligne à ligne) et `.gitignore` (exclut le seul `config.local.json`).

Ajuster ensuite `.knowledge/config.json` à partir de la Phase 1, en **fusionnant** avec ce que `init` a écrit :

- ajouter à `exclude` une entrée `"!<dossier>/**"` pour chaque dossier volumineux détecté qui n'y figure pas déjà (les artefacts de l'usine et du labo en font partie : `factory-logs/`, `lab-logs/`, `experiments/results/`) ;
- ne rien retirer des exclusions par défaut ;
- laisser `rg_path` à `null` : un chemin va dans `config.local.json`, jamais ici.

Lancer l'indexation : `python .claude/rgkb/rgkb.py index` (avec `--force` si `--reindex` a été passé). Relever les compteurs rendus (fichiers, symboles, arêtes, notes) et la liste des langages détectés.

Contrôles à faire à ce stade, et à rapporter :

- si le nombre de fichiers indexés dépasse largement la taille attendue du projet, une exclusion manque : le dire, avec le dossier fautif que `python .claude/rgkb/rgkb.py symbols --limit 20` rend visible ;
- si `symbols` vaut 0 alors que le projet a du code, le langage n'est pas couvert par les motifs de `rgkb.py` : le signaler franchement plutôt que de laisser croire à un index utile.

Vérifier enfin la fraîcheur : `python .claude/rgkb/rgkb.py status` doit rendre `"stale": false`.

## Phase 5 — Versionnement des artefacts

C'est la raison d'être de l'installation : la base doit voyager avec le dépôt.

- Ouvrir le `.gitignore` racine et **vérifier qu'aucune règle n'exclut `.knowledge/`**, directement ou par ricochet (`*.sqlite`, `*.db`, `*.jsonl`, `.knowledge`, un `data/` trop large). Si c'est le cas, ajouter en fin de fichier la contre-règle `!.knowledge/**` précédée d'un commentaire d'une ligne expliquant que la base de connaissance est partagée volontairement — et le signaler dans le rapport, car annuler une exclusion voulue par quelqu'un d'autre mérite d'être vu.
- Ne rien ajouter d'autre au `.gitignore` : `.knowledge/.gitignore` gère déjà le seul fichier local.
- Ne pas commiter. Le rapport final donne la liste exacte des chemins à ajouter à l'index git.

### Hooks git de réindexation

Proposer à l'utilisateur, en un appel `AskUserQuestion`, l'installation des hooks git : `python .claude/rgkb/rgkb.py hooks install` (par défaut) ou `hooks install --with-commit`. En cas d'accord, exécuter la commande et rapporter l'état rendu pour chaque hook. En headless, ne rien installer.

- **Par défaut** : `post-merge` (donc `git pull`) et `post-rewrite` (rebase) réindexent après coup. Ils n'écrivent que si le contenu a changé et ne font jamais échouer l'opération git.
- **`--with-commit`** ajoute `pre-commit`, qui réindexe et met `.knowledge/` à l'index avant chaque commit. C'est ce qui garantit que **tout commit porte un index cohérent avec son code**, et donc qu'un changement de branche ne salit jamais l'arbre de travail. Le présenter comme tel : c'est l'option cohérente, au prix d'un hook qui ajoute des fichiers à chaque commit.
- **`post-checkout` n'est pas installé**, et ce n'est pas un oubli : réindexer après un changement de branche salit l'arbre à chaque fois, et git refuse ensuite le checkout suivant (« local changes would be overwritten »). Sans `pre-commit`, chaque branche porte un index périmé que le hook contredirait aussitôt ; avec `pre-commit`, il n'a plus rien à faire. Ne jamais l'ajouter à la demande d'un agent.

Les hooks vivent dans `.git/hooks/`, qui **n'est pas versionné**. Ce n'est pourtant pas un geste à refaire à la main : `hooks install` écrit l'**intention** dans `.knowledge/config.json` (clé `hooks` : `off` / `auto` / `commit`), qui est versionnée. Tout appel ultérieur à `status` ou à `index` réconcilie les hooks locaux avec cette intention — donc le premier cycle `/factory-run` ou `/lab-run` d'un utilisateur qui vient de cloner les installe chez lui, sans qu'il lance quoi que ce soit. `hooks remove` remet la clé à `off` et désactive de la même façon pour tout le monde. Le bloc installé est délimité par `# >>> rgkb >>>` / `# <<< rgkb <<<` : un hook existant écrit par quelqu'un d'autre est **complété, jamais écrasé**, et `hooks remove` retire le seul bloc rgkb. `RGKB_NO_HOOK=1` neutralise ponctuellement les hooks (`RGKB_NO_HOOK=1 git pull`).

## Phase 6 — Câblage des agents et skills existants

Sautée si `--no-wire`. Sinon, appliquer à ce qui a été détecté en Phase 1. Le principe est constant : **ajouter une section délimitée**, jamais réécrire un prompt. Chaque fichier touché reçoit un bloc encadré par les deux marqueurs littéraux `<!-- rgkb:debut -->` et `<!-- rgkb:fin -->` ; si ces marqueurs sont déjà présents, remplacer leur contenu au lieu d'ajouter un second bloc (c'est ce qui rend le skill relançable).

### 6a. Agents en lecture seule

Concernés : `factory-planner`, `factory-verifier`, `lab-director`, `lab-neuro`, `lab-math`, `lab-verifier` — tous ceux dont le frontmatter porte un champ `tools` limitatif.

Dans le **frontmatter**, ajouter à la liste `tools` les outils de lecture, sans retirer les outils déjà présents : `mcp__rgkb__search`, `mcp__rgkb__definition`, `mcp__rgkb__symbols`, `mcp__rgkb__neighbors`, `mcp__rgkb__file_card`, `mcp__rgkb__notes`, `mcp__rgkb__status`. Un agent dont le `tools` est limitatif ne voit pas les outils MCP s'ils n'y figurent pas nommément : ne pas compter sur un joker.

Dans le **corps**, ajouter le bloc marqué, rédigé pour l'agent concerné, imposant :

- commencer par `mcp__rgkb__status` ; si l'index est périmé, en tenir compte dans ses réponses (les lignes citées peuvent avoir bougé) et le dire, sans le réindexer lui-même ;
- avant de lire un fichier en entier, demander sa fiche (`mcp__rgkb__file_card`) : elle donne les symboles définis, ce que le fichier mentionne, qui en dépend et les notes qui lui sont attachées, pour une fraction du coût ;
- avant de conclure qu'un symbole n'existe pas ou n'est utilisé nulle part, le vérifier avec `mcp__rgkb__definition` puis `mcp__rgkb__neighbors` — un `Grep` qui ne trouve rien ne prouve rien sur un dépôt qu'on ne connaît pas ;
- consulter `mcp__rgkb__notes` sur le sujet traité **avant** de formuler un avis : une note peut porter une décision déjà prise, un piège déjà payé ou un résultat déjà mesuré, et le rappeler évite de refaire le chemin ;
- citer, quand un avis repose sur une note, son identifiant `n-…`, comme on cite une entrée de journal.

Ces agents n'écrivent jamais de note : ils sont en lecture seule, et `note_add` écrit dans un fichier versionné.

### 6b. Agents qui touchent au code

Concernés : `factory-builder`, `lab-builder` (pas de champ `tools` : ils héritent de tout, y compris des outils MCP — ne rien ajouter au frontmatter).

Ajouter le bloc marqué imposant :

- se situer avant d'écrire : `mcp__rgkb__definition` et `mcp__rgkb__neighbors` sur les symboles que la spec ou le protocole nomme, pour trouver le point d'insertion réel et les appelants existants plutôt que de créer un doublon ;
- lire `mcp__rgkb__notes` sur les fichiers qu'il s'apprête à modifier : les pièges connus y sont, et les redécouvrir coûte un cycle ;
- après une modification, **réindexer** (`mcp__rgkb__reindex`, ou `python .claude/rgkb/rgkb.py index`) pour que le Verifier travaille sur un index à jour ;
- ne consigner **aucune interprétation** en note : le Builder rapporte, il ne conclut pas.

### 6c. Skills d'orchestration

Dans `.claude/skills/factory-run/SKILL.md` et `.claude/skills/lab-run/SKILL.md`, ajouter le bloc marqué décrivant deux points d'ancrage dans le déroulé existant, sans renuméroter les étapes :

- **avant la première phase qui dépense** (Plan pour l'usine, Cadrage pour le labo) : exécuter `python .claude/rgkb/rgkb.py status` ; si l'index est périmé, lancer `index` avant de lancer le moindre sous-agent. Un cadrage fondé sur un index périmé produit un plan faux, et c'est l'erreur la plus chère de la chaîne ;
- **à la consignation finale** (rapport de l'usine, entrée de journal du labo), après approbation de l'utilisateur : proposer une note `mcp__rgkb__note_add` pour ce que le cycle a appris et que le code ne dit pas — décision d'architecture et sa raison, piège rencontré, résultat acquis et son chiffre, zone du dépôt à ne pas toucher sans précaution. `subject` = le chemin de fichier ou le nom de symbole concerné quand il y en a un, sinon un sujet libre stable ; `source` = le nom de la spec ou du protocole (`SPEC-x.md`, `EXP-2026-09-06-y.md`) ; un ou deux `tags`. **Une à trois notes par cycle, pas davantage** : une base de connaissance qui enregistre tout ne se lit plus, et la valeur d'une note tient à ce qu'elle survit à la session, pas à son volume. Ne jamais consigner ce que l'index retrouve seul (« la classe X est dans le fichier Y ») ;
- **dans le rapport final** : mentionner les notes ajoutées avec leur identifiant, et rappeler que `.knowledge/` fait partie des fichiers à commiter.

### 6d. Listes blanches headless

Si `ci/factory.sh`, `ci/factory.ps1`, `ci/lab.sh` ou `ci/lab.ps1` existent, ajouter à leur liste `--allowedTools` les outils de lecture rgkb et `Bash(python .claude/rgkb/rgkb.py *)`, sans retirer une entrée existante. Un cycle headless qui ne peut pas interroger l'index retombe sur `Grep`, ce qui fonctionne mais annule le bénéfice.

## Phase 7 — Tâches VS Code

Créer ou fusionner `.vscode/tasks.json` (version `2.0.0`), en préservant les tâches et `inputs` existants et sans dupliquer si les tâches rgkb sont déjà là :

- une entrée `inputs` de type `promptString`, id `rgkbQuery`, décrivant « Motif ou nom de symbole à chercher » ;
- **« Index: réindexer »** — `python .claude/rgkb/rgkb.py index` ;
- **« Index: état »** — `python .claude/rgkb/rgkb.py status` ;
- **« Index: chercher »** — `python .claude/rgkb/rgkb.py search "${input:rgkbQuery}"` ;
- **« Index: diagnostic »** — `python .claude/rgkb/rgkb.py doctor` ;
- **« Index: hooks git »** — `python .claude/rgkb/rgkb.py hooks status`.

Sur Windows, la variante `windows` reprend la même commande avec l'interpréteur retenu en Phase 1.

## Phase 8 — Rapport final

Terminer par un rapport structuré :

- **prérequis** : version de ripgrep (ou l'action à faire pour l'obtenir), interpréteur Python retenu ;
- **fichiers** avec leur état (créé / fusionné / identique / personnalisé-conservé) : `.claude/rgkb/rgkb.py`, `.mcp.json`, `.claude/settings.json`, `.knowledge/*`, `.vscode/tasks.json`, agents et skills câblés ;
- **index** : nombre de fichiers, de symboles, d'arêtes, langages couverts, et le cas échéant l'avertissement de la Phase 4 (exclusion manquante, langage non couvert) ;
- **câblage** : la liste nominative des agents et skills modifiés, ou la mention que `--no-wire` l'a sauté ;
- **à commiter** : `.knowledge/` (sauf `config.local.json`, déjà exclu), `.claude/rgkb/rgkb.py`, `.mcp.json`, et les fichiers de configuration fusionnés — avec le rappel que c'est cette liste, et elle seule, qui fait voyager la base d'un utilisateur à l'autre ;
- **prise en main pour le second utilisateur**, en trois lignes : après un `git clone`, la base est déjà interrogeable et il n'y a rien à reconstruire ; les hooks git s'installent seuls chez lui au premier `status` ou `index` si le dépôt les déclare ; la seule chose qui puisse lui manquer est `rg` dans son `PATH`, auquel cas il crée `.knowledge/config.local.json` avec son propre `rg_path` ;
- **mode d'emploi** en trois lignes : les agents utilisent les outils `mcp__rgkb__*` sans rien avoir à taper ; en session, `python .claude/rgkb/rgkb.py search "motif"` et `… neighbors <symbole>` ; avec les hooks installés, la réindexation après `git pull` ou commit est automatique, sinon `… index` à la main.

Rappeler enfin, en une phrase, qu'un redémarrage de Claude Code est nécessaire pour que le serveur MCP déclaré dans `.mcp.json` soit chargé, et que la CLI, elle, fonctionne immédiatement.
