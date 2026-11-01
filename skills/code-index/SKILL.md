---
name: code-index
description: Installe dans le projet courant un serveur de connaissance local adossé à ripgrep — index de code (symboles, graphe, notes, cache sqlite) versionné sous .knowledge/ pour se transmettre d'un utilisateur à l'autre par git — exposé aux agents par un serveur MCP stdio et par une CLI équivalente. Détecte une usine logicielle (/factory-run) ou un laboratoire IA (/lab-run) déjà installé et branche leurs agents dessus sans les réécrire. À utiliser quand l'utilisateur veut ajouter la recherche indexée et la base de connaissance partagée à un dépôt, neuf ou déjà équipé.
context: fork
user-invocable: true
argument-hint: "[--reindex] [--no-wire] [--upgrade] [--autonomy gate|auto]"
---

# Code Index — serveur de connaissance local adossé à ripgrep

Installer dans le projet courant **rgkb**, une base de connaissance locale du dépôt : ripgrep indexe le code, les artefacts qui en sortent (fichiers, symboles, graphe de mentions, cache sqlite) et les **notes écrites par les humains et par les agents** vivent sous `.knowledge/`, **versionné dans le dépôt**. Un `git clone` suffit donc à récupérer la connaissance accumulée par les autres utilisateurs : rien à reconstruire, rien à réapprendre.

Le serveur (`assets/rgkb.py`, bibliothèque standard, aucune dépendance) s'expose en **serveur MCP stdio** pour les sous-agents et en **CLI** pour Bash et le headless. Ce skill l'installe, l'enregistre, l'indexe, et **branche dessus les agents déjà présents** (usine logicielle, laboratoire IA) sans réécrire leurs prompts.

La règle qui justifie l'ensemble : *l'index se régénère, les notes ne se régénèrent pas*. Un symbole perdu se retrouve en réindexant ; la raison pour laquelle une fonction ne doit pas être appelée deux fois ne se retrouve que si quelqu'un l'a écrite. Le premier rôle de rgkb est de faire descendre dans le dépôt ce que chaque session redécouvre.

## Noyau déterministe

Les règles déterministes sont du code Python (bibliothèque standard, **≥ 3.9 : prérequis de ce skill**, X9) dans `${CLAUDE_SKILL_DIR}/../_core/` : CLI `harness.py`, paquet `hcore/`. Ne jamais les réimplémenter : appeler la CLI et suivre sa sortie JSON. Règles : **CX-01** à **CX-16** (`hcore/cx.py`, sur `fusion.py` FU-01 à FU-06, `blocks.py` BK-01, `stack.py` ST-01 à ST-03), **GT-01** à **GT-08** (gates), **JR-01**, **JR-02** (journal).

**Interpréteur** (CX-03 : un nom résolu par le PATH, **jamais** le venv du projet, `.mcp.json` étant versionné) : `<PY>` = le premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9 : `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`. Aucun candidat : le dire ; bloquant pour le serveur MCP, la CLI reste utilisable. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`, `R` = `<PY> .claude/rgkb/rgkb.py`.

**Gates** : `K gate decide --root . --id <id>` (rend `decision`), AskUserQuestion, puis `K gate answer --run <run> --id <id> --answer "<option>"` ; sans interaction possible (headless) : `--headless`, et appliquer le repli rendu.

## Règles impératives (toutes les phases)

- **Aucun placeholder** : chaque fichier généré ou modifié est complet et opérationnel. Pas de TODO, pas de commande inventée.
- **Fusion, jamais écrasement** (FU-01) : `.mcp.json`, `.claude/settings.json`, `.vscode/tasks.json`, `.gitignore` et les agents existants sont fusionnés par le noyau, jamais édités à la main : aucune clé supprimée, aucune tâche perdue, aucun prompt réécrit — on **ajoute** une section délimitée et réentrante. JSONC et commentaires sont conservés ; un fichier illisible fait échouer la commande sans rien modifier : le signaler.
- **`assets/rgkb.py` est copié tel quel** (CX-05). Si une adaptation semble nécessaire, la signaler au rapport au lieu de l'appliquer.
- **`.knowledge/` est versionné.** Ne jamais l'ajouter au `.gitignore` ; si une règle existante l'exclut, `K cx scope` ajoute la contre-règle `!.knowledge/**` (CX-10) : le dire au rapport. Le seul fichier non versionné du dossier est `config.local.json`.
- **Rien de propre à une machine dans un fichier versionné** : `.mcp.json` et `.knowledge/config.json` ne portent que des commandes résolues par le PATH, jamais un chemin absolu. Tout réglage local (chemin de `rg`, exclusions personnelles) va dans `.knowledge/config.local.json`.
- **Ne jamais commiter.** Le rapport final dit quoi commiter, l'utilisateur décide.
- **Idempotence** : relancer sur un projet équipé ne détruit rien ; chaque fichier est rapporté avec l'état rendu par le noyau (créé / fusionné / identique / personnalisé-conservé, CX-16).

## Mode `--upgrade` (CX-17 à CX-22)

`/code-index --upgrade` met à jour une installation existante, sans reconstruire l'index. Il exclut `--reindex` (exit 2) ; `no_wire` est lu dans le tampon (ou déduit des blocs présents), jamais redemandé. `K cx args --arguments-file …` rend `upgrade`.

1. `K upgrade plan --root . --skill code-index --interpreter "<PY>"` : `rgkb.py` suit CX-05 (un `TOOL_VERSION` du projet plus récent est conservé et rapporté), les blocs `rgkb` des fichiers câblés sont **rendus depuis les gabarits** `assets/blocks/{read-only,builder,orchestrator}.md` (RD-06) et remplacés en place, les fusions CX-06 à CX-08 et CX-15 sont complétées, `config.json` ne reçoit que la fusion CX-08 (jamais réécrit), les hooks git déclarés (`auto` ou `commit`) mais absents sont réinstallés (classe `local`), et `contributes` (les 7 outils `mcp__rgkb__*` et la CLI) est mis à jour au tampon. Les listes d'outils des fichiers dans la mise en page du harnais viennent de `contributes` (rendu par `/software-factory --upgrade`) ; les fichiers `legacy` reçoivent l'union FU-05 et FU-06 comme à l'installation.
2. **Afficher le diff complet** du plan, puis `K upgrade apply --root . --plan <plan>`. Un second passage donne un plan vide.
3. L'index `.knowledge/` n'est pas reconstruit (c'est `--reindex`) : rapporter l'état `stale` de `R status`.

## Phase 1 — Prérequis et état du dépôt

1. **Arguments** (CX-01) : écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.harness/runs/code-index-arguments.txt`, puis `K cx args --arguments-file .harness/runs/code-index-arguments.txt` rend `reindex` (Phase 4 avec `index --force`), `no_wire` (Phase 6 sautée et signalée) et `extra` : tout autre contenu est rappelé au rapport sans être interprété.
2. **ripgrep** : `K cx rg` (CX-02) rend la version, ou la commande d'installation du gestionnaire de paquets de la machine. Absent : gate `code-index.rg-install` (options *commande retenue* / *repli local*) ; sur accord, **exécuter soi-même** la commande rendue. Sous Windows, `rg` n'apparaît qu'après rafraîchissement du PATH : revérifier, et signaler « nouveau terminal requis » plutôt qu'un échec. Ne jamais figer le binaire d'un autre logiciel (VS Code, Copilot) dans un fichier versionné ; en cas de refus ou d'échec, repli **local** : `.knowledge/config.local.json` avec `{"rg_path": "..."}`. Poursuivre dans tous les cas ; sans `rg`, les phases 4 et suivantes s'arrêtent proprement et le rapport donne la commande à relancer.
3. **Interpréteur** : `<PY>` (voir plus haut), ou `K interp`.
4. **État** (CX-04) : `K cx survey --root .` rend, sans rien modifier, git et `.gitignore`, usine et labo présents, installation antérieure, marqueurs de stack et dossiers volumineux.

## Phase 2 — Installation du serveur (CX-05)

`K cx install --root . --asset "${CLAUDE_SKILL_DIR}/assets/rgkb.py"` copie vers `.claude/rgkb/rgkb.py` : absent → *créé* ; identique → rien ; `TOOL_VERSION` de l'asset supérieure ou égale → écrasé et **annoncé** (les artefacts restent lisibles, le schéma est versionné dans `manifest.json`) ; version du projet supérieure → *personnalisé-conservé*, signalé.

## Phase 3 — Enregistrement du serveur MCP (CX-06, CX-07, CX-15)

`K cx register --root . --interp "<PY>"` fusionne en une fois : `.mcp.json` (`mcpServers.rgkb`, `py -3` → `-3` en tête de `args`, jamais de chemin absolu) ; `.claude/settings.json` (`enabledMcpjsonServers` += `rgkb` ; `permissions.allow` += les 7 outils de **lecture** `mcp__rgkb__*` et `Bash(<PY> .claude/rgkb/rgkb.py *)` ; `permissions.deny` += `index.sqlite` et `graph.json`, faits pour être interrogés, pas chargés en contexte) ; `.vscode/tasks.json` (input `rgkbQuery` et cinq tâches « Index: … », variante `windows`). Jamais `note_add` ni `reindex` en autorisation automatique : ce sont les deux seuls outils qui écrivent dans des fichiers versionnés.

## Phase 4 — Périmètre de l'index et première indexation

`R init` crée `.knowledge/` (`config.json`, `notes.jsonl`, `README.md`, `.gitattributes`, `.gitignore`) et **ne réécrit jamais un `config.json` existant** (CX-09). Puis `K cx scope --root .` (CX-08) complète `exclude` avec `!<dossier>/**` pour chaque dossier volumineux détecté, sans rien retirer, `rg_path` restant `null`. Indexer : `R index` (`--force` si `--reindex`) ; relever fichiers, symboles, arêtes, notes, langages. Contrôles à rapporter :

- nombre de fichiers très supérieur à la taille attendue : une exclusion manque — le dire, avec le dossier fautif que `R symbols --limit 20` rend visible ;
- `symbols` à 0 alors que le projet a du code : langage non couvert par les motifs de `rgkb.py` — le signaler franchement ;
- `R status` doit rendre `"stale": false`.

## Phase 5 — Versionnement et hooks git

La contre-règle `!.knowledge/**` est posée par `K cx scope` (CX-10) ; rien d'autre n'est ajouté au `.gitignore`. Ne pas commiter : le rapport donne la liste exacte des chemins.

**Hooks de réindexation** — gate `code-index.hooks` (options `hooks install` / `--with-commit` / refus ; headless : rien d'installé) : `R hooks install` (par défaut) ou `R hooks install --with-commit`, puis rapporter l'état de chaque hook.

- **Par défaut** : `post-merge` (`git pull`) et `post-rewrite` (rebase) réindexent après coup, n'écrivent que si le contenu a changé et ne font jamais échouer git.
- **`--with-commit`** ajoute `pre-commit` : il réindexe et met `.knowledge/` à l'index avant chaque commit, donc **tout commit porte un index cohérent avec son code** et un changement de branche ne salit jamais l'arbre. C'est l'option cohérente, au prix d'un hook qui ajoute des fichiers à chaque commit.
- **`post-checkout` n'est pas installé**, et ce n'est pas un oubli : réindexer après un changement de branche salit l'arbre à chaque fois, et git refuse ensuite le checkout suivant (« local changes would be overwritten »). Avec `pre-commit` il n'a plus rien à faire. Ne jamais l'ajouter à la demande d'un agent.

`.git/hooks/` n'est pas versionné, mais `hooks install` écrit l'**intention** dans `.knowledge/config.json` (clé `hooks` : `off` / `auto` / `commit`), versionnée : `status` et `index` réconcilient les hooks locaux avec elle, donc le premier cycle d'un utilisateur qui vient de cloner les installe chez lui. `hooks remove` remet `off`. Le bloc est délimité par `# >>> rgkb >>>` / `# <<< rgkb <<<` : un hook d'un tiers est complété, jamais écrasé (BK-02). `RGKB_NO_HOOK=1` neutralise ponctuellement.

## Phase 6 — Câblage des agents et skills existants (CX-12 à CX-14)

Sautée si `--no-wire`. Le contenu des blocs vient des **gabarits** `assets/blocks/{read-only,builder,orchestrator}.md` (RD-06, paramétrés par l'interpréteur et le nom de l'agent : plus rien n'est rédigé pour l'agent concerné, ce qui rend `--upgrade` idempotent) : `K cx wire --root . --interp "<PY>"`, sans `--blocks-file` (cibles présentes dans `survey` : `factory-planner`, `factory-verifier`, `lab-director`, `lab-neuro`, `lab-math`, `lab-verifier`, `factory-builder`, `lab-builder`, `factory-run`, `lab-run`). Le noyau pose un bloc `<!-- rgkb:debut -->` … `<!-- rgkb:fin -->` réentrant par cible (le remplace s'il existe), complète `tools` des agents à liste limitative avec les 7 outils de lecture (un agent ne voit pas les outils MCP qui n'y figurent pas nommément ; sans champ `tools`, rien n'est ajouté) et la liste `--allowedTools` de `ci/factory.*` et `ci/lab.*`, sans rien retirer.

**6a. Agents en lecture seule** (`factory-planner`, `factory-verifier`, `lab-director`, `lab-neuro`, `lab-math`, `lab-verifier`) — le bloc impose : commencer par `mcp__rgkb__status` (index périmé : en tenir compte et le dire, sans réindexer) ; demander la fiche d'un fichier (`mcp__rgkb__file_card`) avant de le lire en entier ; avant de conclure qu'un symbole n'existe pas ou n'est utilisé nulle part, `mcp__rgkb__definition` puis `mcp__rgkb__neighbors` (un `Grep` vide ne prouve rien) ; consulter `mcp__rgkb__notes` **avant** de formuler un avis et citer l'identifiant `n-…` d'une note sur laquelle il repose. Ces agents n'écrivent jamais de note.

**6b. Agents qui touchent au code** (`factory-builder`, `lab-builder`, sans `tools`) — le bloc impose : se situer avant d'écrire (`definition`, `neighbors` sur les symboles que la spec ou le protocole nomme) ; lire `notes` sur les fichiers à modifier ; réindexer après modification (`mcp__rgkb__reindex` ou `R index`) pour que le Verifier travaille sur un index à jour ; ne consigner **aucune interprétation** en note : le Builder rapporte, il ne conclut pas.

**6c. Skills d'orchestration** (`factory-run`, `lab-run`) — deux points d'ancrage, sans renuméroter les étapes : **avant la première phase qui dépense** (Plan, Cadrage), `R status` puis `R index` si périmé (un cadrage sur index périmé produit un plan faux, l'erreur la plus chère de la chaîne) ; **à la consignation finale**, après approbation, proposer des notes `mcp__rgkb__note_add` pour ce que le code ne dit pas (décision et sa raison, piège, résultat chiffré, zone sensible) : `subject` = chemin de fichier ou symbole, sinon sujet libre stable ; `source` = la spec ou le protocole ; un ou deux `tags`. **Une à trois notes par cycle, pas davantage** : une base qui enregistre tout ne se lit plus. Ne jamais consigner ce que l'index retrouve seul. Le rapport final cite les notes ajoutées et rappelle que `.knowledge/` se commite.

## Phase 7 — Rapport final

- **prérequis** : version de ripgrep (ou l'action pour l'obtenir), interpréteur retenu ;
- **fichiers** et leur état (CX-16) : serveur, `.mcp.json`, `settings.json`, `.knowledge/*`, `tasks.json`, agents et skills câblés ;
- **index** : fichiers, symboles, arêtes, langages, avertissements de la Phase 4 ; **câblage** : liste nominative, ou `--no-wire` ;
- **à commiter** : `.knowledge/` (sauf `config.local.json`), `.claude/rgkb/rgkb.py`, `.mcp.json` et les configurations fusionnées — c'est cette liste, et elle seule, qui fait voyager la base ;
- **second utilisateur**, en trois lignes : après `git clone` la base est interrogeable sans rien reconstruire ; les hooks s'installent seuls au premier `status` ou `index` si le dépôt les déclare ; seul `rg` peut lui manquer — il crée alors son `config.local.json` avec son `rg_path` ;
- **mode d'emploi** : les agents utilisent `mcp__rgkb__*` sans rien taper ; en session `R search "motif"`, `R neighbors <symbole>` ; sans hooks, `R index` à la main.

Rappeler qu'un redémarrage de Claude Code est nécessaire pour charger le serveur MCP de `.mcp.json`, la CLI fonctionnant immédiatement.

## Défauts en politique `auto` (AP-09)

L'option `--autonomy gate|auto` (AP-03) vaut pour cette exécution seulement et n'écrit jamais `.claude/harness.json` ; elle est transmise à `K gate decide --autonomy` et aux skills enchaînés (AP-04). Défaut de chaque gate de ce skill en `auto`, avec sa justification d'une ligne (celle du catalogue `K gate list`) :

- `code-index.rg-install` → repli local — a system dependency is not installed unasked; local fallback reported
- `code-index.hooks` → hooks install — the default stated by code-index:113
