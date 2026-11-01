# SPEC — Phase 3 : versioning, `--upgrade`, `/harness-doctor`

Statut : APPROUVEE (2026-10-17). Défauts des questions ouvertes retenus ; I7 à I12 traités comme proposé.

Phase 3 de `specs/harness-v2/ROADMAP.md`. Cette spec s'appuie sur trois specs APPROUVEES, livrées avant elle : `specs/SPEC-noyau-core-journal.md` (spec 0), `specs/SPEC-phase1-rebranchement.md` (Phase 1) et `specs/SPEC-phase2-profils-audit.md` (Phase 2). Elle en reprend les conventions : identifiants de règle, `<PY>`, `T`, `K`, rejeux scriptés, comparaison structurelle (D10), fixtures sans nom pointé. Elle utilise les règles suivantes : HJ-01 à HJ-06 (tampon), EP-01 à EP-07 (point d'entrée), PF-01 à PF-05 (profils), SC-02 (signaux déterministes), AR-02 (dérogation `auto`), GT-01 à GT-08 (gate), MD-05 (migration des modèles), RG-01 à RG-07 (registre projet), FU, BK et X3 (fusion, blocs), CX-01 à CX-16 (code-index), JR-01 à JR-03 (journal), LK-01 (verrou), ST-01 à ST-03 (stack).

Règle de l'utilisateur appliquée partout : **la ROADMAP fait foi**. Une règle héritée qui la contredit est modifiée ou retirée, et la spec le dit à l'endroit concerné. Les seuls points remontés sont des impossibilités techniques (**[IMPOSSIBLE]**) ou des écarts avec la doc Claude Code (**[DOC]**), dans la section *Risques*. Chaque question ouverte a une décision par défaut.

## Contexte

### Le besoin (ROADMAP Phase 3)

- **Tampon** `.claude/harness.json` dans chaque projet équipé. Il porte :
  - la version du dépôt claude-skills (tag git ou hash) ;
  - la date ;
  - les skills installés et leurs options ;
  - la politique d'autonomie ;
  - les profils actifs.
- **`--upgrade`** sur `/software-factory` (tous profils) et sur `/code-index`. Il :
  - lit le tampon ;
  - ne régénère que les blocs délimités ;
  - préserve tout le hors-bloc ;
  - migre les formats (`lab-models.json` → `models.json`, anciens registres) ;
  - montre le diff complet, puis applique.

  Il est idempotent : une relance sans changement produit zéro diff. Un projet sans tampon est détecté par ses fichiers générés, et le tampon est créé à la première mise à jour.
- **`/harness-doctor`**, en deux modes :
  - dans un projet, il compare la version installée à celle du dépôt et signale les blocs divergents, les fichiers manquants, les hooks rgkb déclarés mais absents, un `models.json` absent et un `gh` non authentifié ;
  - avec `--scan <racine>`, il affiche une ligne par projet équipé : version, retard, dernier cycle.

  Il propose `--upgrade`, et ne le lance que si la politique l'autorise.
- **En-tête de version** dans chaque fichier régénéré.
- La ROADMAP §2.2 ajoute un point : `/harness-doctor` **propose** `--rescan` quand il voit des signaux nouveaux.
- Le BACKLOG Q6 pose une question : le premier `--upgrade` d'un fichier généré sans bloc (D5).

### État du dépôt (vérifié par lecture)

**Version du noyau et du dépôt**
- `skills/_core/hcore/__init__.py:10` : `CORE_VERSION = "1.0.0"`. La Phase 2 le passe à `2.0.0`.
- `harness.py version` (`skills/_core/harness.py:127-129`) ne rend que `{"core_version"}`. Rien ne lit la version git du dépôt.
- `.git/refs/tags/` est vide et il n'y a pas de `packed-refs` : **le dépôt n'a aucun tag**. La version sera donc un hash tant qu'aucun tag n'est posé.
- `harness.py:21` : `HERE = Path(__file__).resolve().parent`. Le chemin du noyau est déjà résolu, jonctions et liens compris.
- La recette R1 (BACKLOG §5) a montré que `${CLAUDE_SKILL_DIR}` vaut le chemin du **lien**, sans résolution.

**Copie du noyau dans les projets**
- `fusion.copy_core` (`fusion.py:232-257`) copie `_core` tel quel sous `.claude/harness/`.
- Si un fichier déjà présent diffère, rien n'est copié : `blocked_by`, puis exit 1 (`harness.py:230-238`).
- Aucun manifeste n'est écrit et aucune mise à jour n'est possible. La Phase 1 l'a noté en risque (« Noyau mélangé », ai-lab contre software-factory), de même que la Phase 2 (EP-07, « Noyau bloqué sur les projets de la Phase 1 »).

**Blocs délimités**
- `hcore/blocks.py` fournit deux styles, `md` (`<!-- x:debut -->`) et `hash` (`# >>> x >>>`), avec insertion réentrante et `BlockError` si un bloc est mal formé.
- Utilisations prévues par les phases livrées avant celle-ci :
  - `model:` dans un bloc du frontmatter (X1, Phase 1) ;
  - blocs `harness.profile.<nom>` de l'orchestrateur (EP-06) ;
  - blocs `rgkb` de code-index (BK-01).
- Aucun fichier généré par software-factory ou ai-lab n'a de bloc à `BASE` (D5). Leur contenu est **rédigé par le LLM**, adapté à la stack (`software-factory/SKILL.md:39-45`, `ai-lab/SKILL.md:53-131`).
- Le contenu des blocs `rgkb` 6a à 6c est « rédigé pour l'agent concerné » (`code-index/SKILL.md:131`). La Phase 1 l'a laissé en prose.

**Tampon**
- La Phase 2 n'écrit que `profiles` (HJ-01), en dernier (HJ-05).
- `stamp resolve` infère `software` et `research` depuis les fichiers générés (HJ-04).
- GT-01 lit `autonomy`, sans jamais l'écrire.

**Fusions et listes d'outils hors bloc**
- code-index modifie hors bloc la liste `tools:` des agents et `--allowedTools` des scripts `ci/*` (D7, FU-05, FU-06).

**Hooks git rgkb**
- L'intention est dans `.knowledge/config.json`, clé `hooks` ∈ `off|auto|commit` (`rgkb.py:840-856`).
- Les blocs sont délimités par `# >>> rgkb >>>` (`rgkb.py:766-767`).
- Les hooks attendus sont `post-merge` et `post-rewrite`, plus `pre-commit` en mode `commit` (`rgkb.py:763-765`).
- Le dossier des hooks se trouve par `git rev-parse --git-path hooks` (`rgkb.py:804-817`).
- `rgkb.py doctor` (`:1214`) rapporte déjà l'état des hooks, mais seulement depuis la copie du projet.

**Modèles**
- MD-05 (Phase 1) migre `lab-models.json` vers `models.json` sans rien détruire.
- `skills/_core/hcore/models.py` est, à ce jour, le module non branché de la spec 0.

**Registres**
- D2 : registres de run `.harness/runs/ship-pr-<horodatage>.registry.jsonl` (exemple réel : `.harness/runs/ship-pr-20261017-131818.registry.jsonl`).
- RG-01 : registre projet `.claude/findings.jsonl`.
- RG-07 : les registres de run restent lisibles sans migration, mais rien ne les publie après coup dans le registre projet.

**gh**
- Message d'arrêt existant : `MSG_GH_AUTH = "gh not authenticated — run \`gh auth login\`"` (`skills/_core/hcore/ghflow.py:39`). Le préflight appelle `gh auth status` (`ghflow.py:67`).

**Journal**
- `journal.py:22-23` admet une liste fermée de noms (étendue par JR-01, puis par la Phase 2).
- Le nom de fichier est `<skill>-<AAAAMMJJ-HHMMSS>.jsonl` : la date du dernier cycle se lit dans le nom.

**Installeurs**
- Ils lient chaque sous-dossier de `skills/` (`install_skills.sh:176-197`). Un `skills/harness-doctor/` sera donc lié sans modification.

**Fixtures existantes**
- `tests/fixtures/toy-project/`, `merge-input/`, `merge-expected/`, plus celles de la Phase 2.
- Convention (`tests/fixtures/README.md`) : aucun nom pointé ; les tests renomment les fichiers dans un dossier temporaire.

**Référence.** `BASE3` = commit de merge de la Phase 2 sur `main`, relevé au lot L0.

## Périmètre

### 1. Version du dépôt — `VS`

- `VS-01` : `K version` rend `{core_version, repo: {commit, describe, dirty, path}, source: "git"}`.
  - `path` est le dossier réel du dépôt, obtenu par la résolution de `harness.py` (jonctions et liens résolus).
  - `commit` = `git -C <path> rev-parse HEAD`.
  - `describe` = `git describe --tags --always --dirty`, ce qui donne un tag s'il en existe un, sinon un hash court.
  - Si git est absent, si le dossier n'est pas un dépôt, ou si git ne répond pas en 5 s : `commit: null`, `describe: "core-<CORE_VERSION>"`, `dirty: null`, exit 0. La commande n'échoue jamais pour cette raison.
- `VS-02` : lancé depuis une copie de projet (`.claude/harness/harness.py version`), `repo` est lu dans `.claude/harness/MANIFEST.json` (CO-02), avec `source: "manifest"`. C'est la version qui a produit la copie, pas celle d'un dépôt git voisin.
- `VS-03` : retard = `lag(installed_commit)` → `{status, commits}`, avec `status` ∈ :
  - `up_to_date` ;
  - `behind` : `git merge-base --is-ancestor installed HEAD`, et `commits` = `git rev-list --count installed..HEAD` ;
  - `ahead` : `HEAD` est ancêtre du commit installé ;
  - `diverged` ;
  - `unknown` : commit `null`, ou absent du dépôt local. Dans ce cas, repli sur la comparaison semver des `core_version`, avec `commits: null`.
- `VS-04` : `CORE_VERSION` passe à `3.0.0`.

### 2. Tampon complet — `HJ` (suite de HJ-01 à HJ-06)

- `HJ-07` : schéma `schema_version: 1`, documenté dans `skills/_core/STAMP.md`. Clés :
  - `schema_version` ;
  - `autonomy` (GT-01) ;
  - `profiles[]` (HJ-01, inchangé) ;
  - `skills` : objet indexé par skill installant, `software-factory` et/ou `code-index` (ai-lab s'installe comme profil `research` de software-factory, AX-01) ;
  - `migrations[]` (HJ-13) ;
  - `inferred_from` (DT-04), facultatif.
- `HJ-08` : écriture par-dessus un tampon de Phase 2 (`profiles` seul, sans `schema_version`).
  - Toutes les clés existantes sont conservées, clés inconnues comprises, dans leur ordre ; les nouvelles clés sont ajoutées après.
  - JSON strict, indentation 2, écriture atomique.
  - Un JSON illisible → exit 2, fichier inchangé (HJ-02).
- `HJ-09` : `autonomy` absente lors d'une écriture par l'installation ou l'upgrade → `"auto"` (ROADMAP §4.1 : « Le défaut installé pour moi est `auto` »). Une valeur existante n'est **jamais** modifiée par l'installation ni par l'upgrade. Tant que la Phase 4 n'est pas livrée, GT-03 continue de faire appliquer `auto` comme `gate`, sauf pour les gates exemptées (AR-02, PR-02).
- `HJ-10` : entrée `skills.<skill>` :
  - `repo_commit`, `repo_describe`, `repo_dirty` (VS-01) ;
  - `core_version` (software-factory) ou `tool_version` (code-index, `TOOL_VERSION` de rgkb) ;
  - `installed_at`, fixé à la première écriture ;
  - `updated_at`, mis à jour seulement par un apply qui change quelque chose ;
  - `options` : pour software-factory, `stacks`, `interpreter`, `ci`, `code_index_offered` ; pour code-index, `no_wire`, `hooks`, `interpreter` ;
  - `params` (RD-03, software-factory) ;
  - `contributes` (RD-05, code-index) ;
  - `files` : `{"<chemin relatif>": {kind: generated|merged|copied|legacy, blocks: {"<nom>": "<sha256>"}}}`.
- `HJ-11` : dates au format ISO 8601, heure locale avec décalage, à la seconde. Un apply sans changement ne touche pas le tampon, qui reste identique octet pour octet.
- `HJ-12` : rien de propre à une machine. Le tampon est **versionné**. `stamp validate` refuse (exit 2) :
  - toute valeur de chaîne qui est un chemin absolu (`^[A-Za-z]:[\\/]` ou `^/`) ;
  - toute clé `rg_path`.
- `HJ-13` : `migrations[]` = `{id, at, sources: [{path, sha256}]}`, en ajout seulement.
- `HJ-14` : HJ-05 s'étend à l'upgrade. Le tampon est écrit en dernier, après tous les autres fichiers ; un arrêt le laisse inchangé.
- `HJ-15` : `K stamp validate <fichier>` et `K stamp show --root R`. `stamp resolve` (HJ-04) est étendu par DT-01.

### 3. Copie du noyau `.claude/harness/` — `CO`

- `CO-01` : nouveau fichier de données `skills/_core/history.json`.
  - Une entrée par état distinct de `skills/_core/` dans l'historique git : `{id, commit, core_version, files: {"<rel>": "<sha256 du contenu, fins de ligne normalisées en LF>"}}`.
  - `id` = sha256 de la table `files` triée. `commit` vaut `null` pour l'état courant pas encore commité.
  - Sont exclus : `history.json`, `MANIFEST.json`, `__pycache__/`, `*.pyc`.
  - `K core history --rebuild` régénère le fichier depuis git ; c'est un outil de développement de ce dépôt.
  - `K core history --check` rend exit 0 si la table de l'arbre courant est une entrée du fichier, sinon exit 1 avec la liste des fichiers en cause.
- `CO-02` : `copy-core` écrit `.claude/harness/MANIFEST.json` : `{core_version, repo: {commit, describe, dirty}, entry, files: {rel: sha256}}`.
- `CO-03` : état de chaque fichier de la copie :
  - `pristine` : hash égal à celui du MANIFEST, ou, sans MANIFEST, présent dans `history.json` pour ce chemin ;
  - `customized` : tout autre contenu ;
  - `missing` ;
  - `extra` : présent dans le projet, absent de toute entrée et du nouveau noyau. Il n'est jamais supprimé et il est rapporté.
- `CO-04` : mise à jour de la copie (dans un plan UP seulement, voir CO-06).
  - Les fichiers `pristine` et `missing` sont remplacés ou créés.
  - Un fichier `pristine` absent du nouveau noyau est supprimé : c'est un fichier généré.
  - Un seul fichier `customized` suffit à ne rien écrire du tout (noyau, blocs, tampon) : exit 1, `STOP: core not upgraded: customized files in .claude/harness/: <liste>; move your changes out of .claude/harness/ or restore these files, then run the upgrade again`.
  - Jamais de noyau mélangé en sortie.
- `CO-05` : version installée d'une copie sans MANIFEST :
  - dernière entrée d'historique dont tous les fichiers correspondent → `{core_version, exact: true}` ;
  - fichiers correspondant à des entrées différentes → `{mixed: true, entries: [...]}`. Le cas est rapporté, et reste mis à jour par CO-04 puisque tous ses fichiers sont `pristine`.
- `CO-06` : **une seule copie par projet**, partagée par tous les orchestrateurs (`factory-run`, `lab-run`, LP-06). La copie n'est jamais mise à jour seule : elle l'est dans le même plan que les blocs de **tous** les profils actifs, appliqué en tout ou rien. Cela règle la version mélangée entre ai-lab et software-factory.
- `CO-07` : le message d'EP-07 (installation bloquée par un noyau différent) donne la commande `/software-factory --upgrade`.

### 4. Rendu déterministe et mise en page des fichiers générés — `RD`

- `RD-01` : à partir de cette phase, chaque fichier **généré** est écrit avec la mise en page suivante : en-tête (EN), blocs du harnais, zones libres hors bloc. Les fichiers concernés sont les agents `.claude/agents/*.md`, les orchestrateurs `.claude/skills/{factory-run,lab-run}/SKILL.md` et les scripts `ci/{factory,lab}.{sh,ps1}`. Noms de bloc :
  - `harness.frontmatter`, style `hash`, à l'intérieur du frontmatter YAML : `name`, `description`, `tools`, `model` (X1) et, pour les skills, `disable-model-invocation` et `argument-hint` ;
  - `harness.body`, style `md` ;
  - `harness.profile.<p>`, style `md` (EP-06) ;
  - `harness.ci`, style `hash`, pour les scripts.
- `RD-02` : le contenu d'un bloc vaut `render(fragment, params, contributions)`. C'est une fonction pure, sans appel au LLM : les mêmes entrées donnent les mêmes octets (LF). Les fragments sont ceux des profils (PF-01) et les gabarits de code-index (RD-06).
- `RD-03` : `profile.json` reçoit une clé `params[]` = `{name, source: detected|judgement, required}`, validée par PF-03.
  - Les paramètres `detected` (commandes de test, de build et de lint, stacks, interpréteur) sont calculés par le noyau (ST).
  - Les paramètres `judgement` (adaptation au projet : conventions citées, corpus, contraintes recopiées) sont rédigés **une fois** par le skill dans un fichier écrit par Write, puis enregistrés dans `skills.software-factory.params`.
  - Un paramètre déjà présent n'est jamais redemandé.
- `RD-04` : un paramètre requis absent au moment du plan → `{"action": "fill_params", "missing": [...]}`, exit 0, rien n'est écrit.
- `RD-05` : contributions. La liste `tools:` d'un agent et `--allowedTools` d'un script valent l'union des outils du profil et des `skills.*.contributes` du tampon : d'abord ceux du profil, puis les contributions dans l'ordre de déclaration, sans doublon.
  - code-index déclare ses 7 outils de lecture et `Bash(<py> .claude/rgkb/rgkb.py *)`, pour les agents à `tools` limitatif et pour les scripts `ci/*`.
  - Pour les fichiers dans la mise en page RD-01, FU-05 et FU-06 sont remplacées par ce mécanisme. Elles restent appliquées aux fichiers `legacy` (CV-04).
- `RD-06` : les blocs `rgkb` de code-index (6a, 6b, 6c) deviennent des gabarits, `skills/code-index/assets/blocks/{read-only,builder,orchestrator}.md`, paramétrés par l'interpréteur et le nom de l'agent. **Règle modifiée** : « rédigé pour l'agent concerné » (`code-index/SKILL.md:131`, laissé en prose par la Phase 1) est retiré, parce que l'idempotence de l'upgrade (ROADMAP Phase 3) l'exige (voir I7).
- `RD-07` : `strip_blocks(text)` rend le texte privé de tous les blocs `harness.*` et `rgkb` et de la ligne d'en-tête. Cette fonction définit le « hors-bloc ».

### 5. En-tête de version — `EN`

- `EN-01` : une seule ligne, en anglais (texte produit par le code) : `harness: claude-skills <describe> (core <core_version>)`. Emplacement :
  - Markdown à frontmatter (agents, `SKILL.md`) : ligne 2, en commentaire YAML `# harness: …`, juste après le `---` d'ouverture. La ligne 1 reste `---`.
  - `.sh` : ligne 2, après le shebang (ligne 1 s'il n'y a pas de shebang).
  - `.ps1` : ligne 1, en `# harness: …`.
  - Bloc `rgkb` : première ligne intérieure `<!-- rgkb: claude-skills <describe> (rgkb <TOOL_VERSION>) -->`.
- `EN-02` : l'en-tête appartient au harnais. Il est reconnu par son préfixe, remplacé lors d'un upgrade, et classé `header` (UP-07).
- `EN-03` : pas d'en-tête dans les JSON (`settings.json`, `tasks.json`, `.mcp.json`, `config.json`), dans `.gitignore`, dans les fichiers copiés (`.claude/harness/**`, `.claude/rgkb/rgkb.py`) ni dans `.git/hooks/*`. Leur version est dans le tampon, dans `MANIFEST.json` ou dans `TOOL_VERSION` (I8).
- `EN-04` : l'en-tête ne porte pas de date (elle est dans le tampon), ce qui garde l'idempotence.

### 6. Projet sans tampon — `DT`

- `DT-01` : `stamp resolve` (HJ-04) rend aussi `skills`, déduits des fichiers présents :
  - `software-factory` : fichiers `factory-*` ou `lab-*` de HJ-04 ;
  - `code-index` : `.claude/rgkb/rgkb.py`, ou `mcpServers.rgkb` dans `.mcp.json`, ou `.knowledge/manifest.json`.
- `DT-02` : génération estimée :
  - `pre-core` : aucune copie `.claude/harness/` ;
  - `core-<v>` : estimée par CO-05, `mixed` compris ;
  - `stamp-phase2` : tampon réduit à `profiles`.
- `DT-03` : options déduites.
  - `stacks` : par ST.
  - `interpreter` : par `.mcp.json` (`command`, et `-3` en tête de `args`) ou par l'interpréteur de `--allowedTools` des scripts `ci/*`, sinon par la détection D5.
  - `no_wire` : `false` si un bloc `rgkb` existe dans un agent.
  - `hooks` : lu dans `.knowledge/config.json`.
- `DT-04` : le tampon est créé à la fin du premier upgrade réussi (HJ-14), avec `inferred_from: "<génération DT-02>"`.

### 7. Moteur d'upgrade — `UP`

- `UP-01` : `K upgrade plan --root R --skill software-factory|code-index [--params-file F] [--convert]` calcule toutes les modifications **sans écrire dans le projet**. Il n'écrit que sous `.harness/runs/` : `upgrade-<horodatage>.plan.json` et `upgrade-<horodatage>.diff`.
- `UP-02` : contenu du plan.
  - **software-factory** : fichiers générés de tous les profils actifs, blocs d'orchestrateur, scripts CI, fusions (FU, SF-01 à SF-03, AL-01 à AL-03), copie du noyau (CO), migrations (MI), en-têtes, tampon.
  - **code-index** : `rgkb.py` (CX-05), blocs `rgkb` des fichiers câblés, fusions CX-06 à CX-08 et CX-15, `contributes`, hooks locaux (CX-21), tampon.
- `UP-03` : **invariant hors bloc.** Pour tout fichier modifié qui n'est pas converti (CV), `strip_blocks(avant) == strip_blocks(après)` octet pour octet. Le moteur le vérifie avant toute écriture ; une violation → exit 1, rien n'est écrit. Pour une fusion JSON ou `.gitignore`, l'invariant est : aucune clé, entrée ou ligne existante n'est modifiée ou retirée.
- `UP-04` : **diff complet.**
  - Diff unifié de chaque fichier créé, modifié ou supprimé, sans troncature, avec des chemins relatifs en `/`.
  - Appliqué par `git apply` sur l'état d'avant, il redonne exactement l'état d'après.
  - Les hooks git locaux y figurent sous `.git/hooks/<nom>`.
  - Le skill affiche le diff **en entier** avant l'apply.
- `UP-05` : `K upgrade apply --plan P [--decisions-file F]`.
  - Il revérifie le sha256 de chaque fichier d'avant. Un seul écart → exit 1, `STOP: upgrade plan is stale, the project changed since it was shown; plan again`, rien n'est écrit.
  - Il écrit en tout ou rien (fichier temporaire puis remplacement), le tampon en dernier.
  - Chaque fichier modifié ou supprimé est sauvegardé d'abord sous `.harness/runs/upgrade-<horodatage>/backup/<rel>`.
- `UP-06` : **idempotence.** Un nouveau plan juste après l'apply rend `changes: []`. L'apply d'un plan vide n'écrit rien, tampon compris.
- `UP-07` : chaque modification est classée parmi `header`, `block`, `merge` (ajout par union), `copy` (noyau `pristine`, `rgkb.py`), `create` (fichier généré manquant), `convert`, `migrate`, `stamp` et `local` (bloc `rgkb` d'un hook git). On a `blocks_only = true` si et seulement si toutes les modifications sont dans `{header, block, merge, copy, stamp, local}` (Q3).
- `UP-08` : pas de retour en arrière. Un commit installé `ahead` ou `diverged` (VS-03), ou un `core_version` installé supérieur à celui du dépôt → exit 1, `STOP: project installed by a newer harness (<installé>) than this repository (<dépôt>); update claude-skills first (git pull)`.
- `UP-09` : un seul upgrade à la fois par projet. Le verrou `.harness/runs/upgrade.lock` suit le mécanisme de LK-01.
- `UP-10` : chaque modification appliquée est journalisée par un événement `{"event": "upgrade", "file", "kind", "from", "to"}` dans `.harness/runs/<skill>-<horodatage>.jsonl` (JR-04).
- `UP-11` : l'upgrade ne lance aucun sous-agent et ne fait réécrire aucun bloc par le LLM. La seule exception est le remplissage des paramètres manquants (RD-04).
- `UP-12` : un skill ne modifie jamais les blocs d'un autre. software-factory ne touche pas aux blocs `rgkb`, et code-index ne touche pas aux blocs `harness.*`. Seules les listes d'outils passent de l'un à l'autre, par les contributions (RD-05).
- `UP-13` : un fichier généré attendu mais manquant est recréé, avec la classe `create` (Q13).

### 8. Migrations — `MI`

- `MI-01` : la migration des modèles MD-05 est appelée par le plan software-factory et classée `migrate`. `lab-models.json` reste identique octet pour octet.
- `MI-02` : les anciens registres de run `.harness/runs/*.registry.jsonl` (format D2, `DUPLICATE` compris) sont publiés dans `.claude/findings.jsonl` selon RG-03, avec deux nuances :
  - `CONFIRMED` n'est pas publié, puisque le livrable porteur est inconnu ;
  - chaque registre source est enregistré dans `migrations[]` par son sha256 et n'est plus jamais republié.

  Les registres sources ne sont pas modifiés.
- `MI-03` : un tampon de Phase 2 passe au schéma 1 (HJ-08).
- `MI-04` : un orchestrateur sans blocs de profil (EP-06, `personnalisé-conservé`) passe par la conversion CV.
- `MI-05` : les anciens livrables d'audit (`ROADMAP-legacy.md`, `AUDIT-vibecode.md`, `AUDIT-lab.md`) ne sont pas migrés par l'upgrade. Ils sont rapportés avec la mention « repris par le prochain /audit (MG-01) ».
- `MI-06` : les lignes `.gitignore` manquantes d'une installation antérieure, comme `.harness/runs/` sur un projet `pre-core`, sont ajoutées par FU-03 (classe `merge`).
- `MI-07` : chaque migration est idempotente et ne modifie ni ne supprime aucun fichier source.

### 9. Premier upgrade d'un fichier sans bloc (BACKLOG Q6) — `CV`

- `CV-01` : classement d'un fichier généré sans bloc `harness.*`.
  - On retire d'abord les blocs étrangers (`rgkb`) du fichier courant et de sa **base**. La base est le contenu au plus ancien commit qui a ajouté le fichier (`git log --diff-filter=A`).
  - Classes :
    - `pristine` : fichier courant égal à la base ;
    - `suffix` : le fichier courant commence par la base, et le reste n'est qu'un ajout en fin de fichier ;
    - `modified` : tout autre cas ;
    - `untracked` : pas de git, ou fichier jamais commité.
- `CV-02` : `pristine` → converti : rendu RD, puis blocs étrangers repris tels quels après les blocs du harnais, dans leur ordre d'origine. Classe `convert`.
- `CV-03` : `suffix` → converti. Le suffixe ajouté par l'utilisateur est conservé octet pour octet **hors bloc**, après les blocs du harnais, et l'ordre relatif entre suffixe et blocs étrangers est conservé. C'est le scénario « personnalisations hors bloc qui survivent » de la ROADMAP (Phase 6).
- `CV-04` : `modified` ou `untracked` → gate `upgrade.convert`, de type b.
  - Options : « Conserver tel quel » / « Convertir (sauvegarde) ». Défaut : **Conserver tel quel**.
  - Repli headless : `default`.
  - `--convert` vaut la réponse « Convertir » pour tous ces fichiers, et c'est journalisé.
  - Un fichier conservé est enregistré dans le tampon avec `kind: legacy`, et le doctor le signale.
- `CV-05` : une conversion est toujours sauvegardée (UP-05), figure dans le diff, et n'est jamais `blocks_only`.

### 10. `/software-factory --upgrade` — `EP` (suite de EP-01 à EP-07)

- `EP-08` : arguments `--upgrade [--convert]`. Ils excluent `--profile` et `--rescan` (exit 2). Tout autre contenu à côté de `--upgrade` → exit 2.
- `EP-09` : déroulé.
  1. `K version`.
  2. `stamp resolve`. La source `none` → arrêt, `STOP: project not equipped: run /software-factory`.
  3. Plan pour tous les profils actifs.
  4. `fill_params` si nécessaire.
  5. Affichage du diff complet.
  6. Gate `upgrade.convert` si nécessaire.
  7. `apply`.
  8. Rapport : état de chaque fichier, classes, chemin de la sauvegarde, nouvelle version, `legacy` restants.
- `EP-10` : `/ai-lab --upgrade` se traduit en `software-factory --upgrade`, **sans** `--profile research` (exception à AX-01). Tous les profils du tampon sont mis à jour.
- `EP-11` : une installation neuve (sans option) écrit dès cette phase la mise en page RD-01, l'en-tête, `MANIFEST.json` et le tampon complet. Le traitement des fichiers existants reste celui de SF-04 et EP-02, et le rapport renvoie à `--upgrade`.

### 11. `/code-index --upgrade` — `CX` (suite de CX-01 à CX-16)

- `CX-17` : `--upgrade` exclut `--reindex` (exit 2). `no_wire` est lu dans le tampon (ou déduit par DT-03), jamais redemandé.
- `CX-18` : `rgkb.py` suit CX-05, classe `copy`. Un `TOOL_VERSION` du projet supérieur à celui de l'asset est conservé et rapporté, sans arrêt.
- `CX-19` : les blocs `rgkb` sont rendus depuis les gabarits RD-06 dans chaque fichier câblé, et `contributes` est mis à jour. Les fichiers `legacy` reçoivent l'union FU-05 et FU-06 comme aujourd'hui.
- `CX-20` : `.knowledge/config.json` reçoit seulement la fusion CX-08. Il n'est jamais réécrit (D8).
- `CX-21` : hooks déclarés (`auto` ou `commit`) mais absents → réinstallés par le bloc `rgkb` de `rgkb.py hooks install [--with-commit]`. Classe `local`.
- `CX-22` : l'index `.knowledge/` n'est pas reconstruit (c'est le rôle de `--reindex`). L'état `stale` de `rgkb.py status` est rapporté.

### 12. `/harness-doctor` dans un projet — `DR`

- `DR-01` : nouveau skill `skills/harness-doctor/SKILL.md`.
  - `name: harness-doctor`, `description:` non vide, `user-invocable: true`, `argument-hint: "[--scan <racine>] [--depth N]"`.
  - **Ni** `context: fork` **ni** `disable-model-invocation`, pour pouvoir invoquer les upgrades par l'outil Skill (PR-04, Q12).
- `DR-02` : `K doctor --root R` rend un JSON avec les clés suivantes :
  - `equipped` (`stamp|inferred|none`) ;
  - `version` : par skill, version installée, version du dépôt (lue par le noyau **global**, VS-01) et retard (VS-03) ;
  - `core` : MANIFEST ou CO-05, comparé au dépôt, avec `mixed` et `customized[]` ;
  - `blocks[]` : `{file, block, state}`, avec `state` ∈ `ok|edited|outdated|edited+outdated|missing_block` ;
  - `legacy_files[]` ;
  - `missing[]` ;
  - `hooks` : `{declared, expected[], missing[]}` ;
  - `models` : `{models_json, lab_models_json, migration_available}` ;
  - `gh` : `{installed, authenticated, message}` ;
  - `signals` ;
  - `upgrade` : `{changes, blocks_only, by_skill}` ;
  - pour chaque contrôle, un `status` ∈ `ok|warn|error`.
- `DR-03` : un bloc est `edited` si son hash diffère de celui du tampon, et `outdated` si son rendu par le dépôt actuel diffère du contenu présent (plan UP-01).
- `DR-04` : fichiers attendus = fichiers du tampon ∪ fichiers générés des profils actifs ∪ fichiers du MANIFEST ∪, si code-index est installé, `.claude/rgkb/rgkb.py`, l'entrée `rgkb` de `.mcp.json` et `.knowledge/config.json`.
- `DR-05` : hooks.
  - Déclarés = `.knowledge/config.json`, clé `hooks` ∈ `auto|commit`.
  - Attendus : `post-merge` et `post-rewrite`, plus `pre-commit` en `commit`.
  - Présent = le fichier existe dans `git rev-parse --git-path hooks` et contient `# >>> rgkb >>>`.
  - Projet sans git → `n/a`.
- `DR-06` : `models.json` absent → `warn`. Si `lab-models.json` est présent : `migration_available: true`, avec le renvoi à `--upgrade` (MI-01).
- `DR-07` : `gh`.
  - Absent du PATH → `gh: absent`, `warn`.
  - `gh auth status` en échec → message `MSG_GH_AUTH`, `warn`.
  - Délai de 10 s. Jamais bloquant.
- `DR-08` : signaux. Un profil absent du tampon dont le statut sur les seuls signaux déterministes (SC-02, SC-05 sans `judgement`) n'est pas `rejected` → `signals.propose_rescan: true`, avec la commande `/software-factory --rescan`. Le rescan n'est jamais lancé (ROADMAP §2.2 : « propose »).
- `DR-09` : écritures du doctor : uniquement son journal `.harness/runs/harness-doctor-<horodatage>.jsonl` et les fichiers de plan UP-01. Sur un projet `none`, rien n'est écrit.
- `DR-10` : codes de sortie : exit 0 quand le rapport est produit, exit 2 si la racine est inexistante.

### 13. `/harness-doctor --scan <racine>` — `SN`

- `SN-01` : `K doctor scan --root R [--depth N]`. Profondeur par défaut : 3. `N` doit être un entier ≥ 0, sinon exit 2 ; une racine inexistante → exit 2.
- `SN-02` : un projet équipé est reconnu par un tampon ou par les marqueurs DT-01.
  - Ne sont pas parcourus : `.git/`, `.claude/`, les dossiers d'artefacts de ST-03, les liens et les jonctions (aucun n'est suivi).
  - Le parcours continue sous un projet équipé (monorepo).
- `SN-03` : une ligne JSON par projet, triée par chemin relatif : `{path, equipped_by, skills: {"<skill>": "<describe>"}, lag: {status, commits}, last_cycle: {skill, at, verdict} | null, next}`. `next` est la commande d'upgrade si le projet est en retard. Le skill affiche une ligne de tableau par projet.
- `SN-04` : le dernier cycle est le fichier `.harness/runs/<nom>-<AAAAMMJJ-HHMMSS>.jsonl` le plus récent **d'après l'horodatage du nom**, pas d'après la date de modification. `verdict` = celui de la dernière ligne qui en porte un. Les fichiers `.registry.jsonl`, `.state.json`, `.plan.json`, `.diff` et `.lock` sont ignorés.
- `SN-05` : lecture seule absolue. Aucun fichier n'est créé ou modifié sous `R` : ni journal, ni plan.
- `SN-06` : le scan ne lance jamais d'upgrade (Q7).

### 14. Proposition d'upgrade — `PR`

- `PR-01` : un plan non vide déclenche une gate :
  - `harness-doctor.upgrade-blocks` si `blocks_only` ;
  - `harness-doctor.upgrade-other` sinon.
- `PR-02` : `harness-doctor.upgrade-blocks`, type b.
  - Options : « Lancer l'upgrade » / « Ne rien faire ». Défaut : **Lancer** (ROADMAP §4.2 : en `auto`, le doctor lance `--upgrade` quand le diff ne touche que des blocs).
  - `phase3_auto: true` : exemptée de GT-03, sur le modèle d'AR-02.
  - Repli headless : `default`.
- `PR-03` : `harness-doctor.upgrade-other`, type b.
  - Défaut : **Ne rien faire** (§4.2 réserve le lancement automatique aux diffs de blocs).
  - En `auto` (une fois la Phase 4 livrée), défaut pris : le rapport donne la commande et la liste des classes qui empêchent le lancement. En `gate`, la question est posée.
  - Repli headless : `default`.
- `PR-04` : lancer l'upgrade = outil Skill sur `software-factory --upgrade`, puis sur `code-index --upgrade`, chacun seulement si son plan n'est pas vide, et dans cet ordre (les contributions sont relues). `K doctor` est ensuite relancé, et le rapport final montre `upgrade.changes = 0`.
- `PR-05` : journal. Chaque décision fait l'objet d'un événement `gate` (GT-07) dans le journal du doctor.

### 15. Catalogue et journal — `GT`, `JR`

- `GT-09` : ajout au catalogue GT-08 de `upgrade.convert`, `harness-doctor.upgrade-blocks` et `harness-doctor.upgrade-other`. GT-03 exempte aussi les gates `phase3_auto: true`.
- `JR-04` : `harness-doctor` s'ajoute aux noms admis. Nouveaux événements typés : `upgrade` (UP-10) et `doctor` (`{event, checks: {<contrôle>: <status>}}`).

### Découpage en lots (chacun testable seul par `T`)

| Lot | Contenu | CA | Dépend de |
| --- | --- | --- | --- |
| L0 | `BASE3` relevé ; recettes R12 (version par le lien installé) et R14 (commentaires YAML dans le frontmatter) | — | Phase 2 |
| L1 | VS-01 à VS-04, HJ-07 à HJ-15 : `hcore/version.py`, extension de `stamp.py`, `STAMP.md` | 04, 05, 06 | L0 |
| L2 | CO-01 à CO-07 : `history.json`, `core history`, MANIFEST, états et mise à jour de la copie | 07, 08 | L1 |
| L3 | RD-01 à RD-07, EN-01 à EN-04, EP-11 : `hcore/render.py`, `params[]` des profils, gabarits rgkb, installation neuve dans la nouvelle mise en page | 09, 10, 11 | L1 |
| L4 | UP-01 à UP-13, MI-01 à MI-07, DT-01 à DT-04, CV-01 à CV-05 : `hcore/upgrade.py`, `hcore/migrate.py` | 12 à 18 | L2, L3 |
| L5 | EP-08 à EP-10 : `software-factory` et alias `ai-lab` | 19 | L4 |
| L6 | CX-17 à CX-22 : `code-index` | 20 | L4 |
| L7 | DR-01 à DR-10, JR-04 : `hcore/doctor.py`, `skills/harness-doctor/SKILL.md` | 21, 22 | L4 |
| L8 | SN-01 à SN-06 : `hcore/scan.py` | 23 | L7 |
| L9 | PR-01 à PR-05, GT-09 : gates et enchaînement doctor → upgrade | 24 | L5, L6, L7 |
| L10 | README, `tests/fixtures/README.md`, BACKLOG (Q6 tranchée), rafraîchissement de `.claude/harness/` de ce dépôt, passage complet des CA | 01 à 31 | tous |

Au minimum un commit par lot, et un commit par skill touché : software-factory, ai-lab, code-index, harness-doctor.

### Fichiers concernés

**Créés**
- `skills/harness-doctor/SKILL.md`
- `skills/_core/STAMP.md`, `skills/_core/history.json`
- `skills/_core/hcore/version.py`, `render.py`, `upgrade.py`, `migrate.py`, `doctor.py`, `scan.py`
- `skills/code-index/assets/blocks/read-only.md`, `builder.md`, `orchestrator.md`
- `skills/_core/tests/` : `test_version.py`, `test_stamp_full.py`, `test_core_copy.py`, `test_render.py`, `test_upgrade.py`, `test_migrate.py`, `test_convert.py`, `test_doctor.py`, `test_scan.py`, `test_upgrade_gates.py`
- les fixtures listées ci-dessous

**Modifiés**
- `skills/_core/hcore/__init__.py` (`CORE_VERSION` 3.0.0), `fusion.py` (`copy_core` : MANIFEST et mise à jour), `stamp.py`, `blocks.py` (`strip_blocks`), `gates.py` (catalogue, `phase3_auto`), `journal.py` (JR-04), `profiles.py` (`params[]`), `skills/_core/harness.py`
- `skills/_core/profiles/software/profile.json`, `skills/_core/profiles/research/profile.json` et `SCHEMA.md` (`params[]`)
- `skills/software-factory/SKILL.md`, `skills/ai-lab/SKILL.md`, `skills/code-index/SKILL.md`
- `README.md`, `tests/fixtures/README.md`, `specs/harness-v2/BACKLOG.md`
- `.claude/harness/` de ce dépôt (copie identique de `skills/_core/`)

**Inchangés** (vérifié par CA-28) : `install_skills.sh`, `install_skills.ps1`, `skills/ship-pr/`, `skills/brainstorm/`, `skills/audit/`, `skills/code-index/assets/rgkb.py`.

### Fixtures (`tests/fixtures/`, sans nom pointé ni `CLAUDE.md`)

- **`upgrade-legacy/` : projet installé « à l'ancienne », figé.** Il est écrit à la main, conforme aux `SKILL.md` de `BASE=7be1afb` (avant le noyau, sans tampon ni bloc `harness.*`). Les tests le montent en dépôt git à deux commits.
  - `installed/` (commit 1, « installation ») :
    - le projet jouet de `toy-project/` ;
    - `claude/agents/factory-{planner,builder,verifier}.md` et `lab-{director,neuro,math,builder,verifier}.md` ;
    - `claude/skills/factory-run/SKILL.md` et `claude/skills/lab-run/SKILL.md` ;
    - `ci/factory.sh`, `ci/factory.ps1`, `ci/lab.sh` ;
    - `claude/settings.json`, `vscode/tasks.json`, `gitignore.txt`, `mcp.json` (avec `rgkb` et un serveur tiers) ;
    - `claude/rgkb/rgkb.py` (copie de l'asset à `7be1afb`, `TOOL_VERSION` 1.0.0) ;
    - `knowledge/config.json`, `knowledge/notes.jsonl` (une note) ;
    - `claude/lab-models.json` ;
    - `claude/runs/ship-pr-20261001-101010.registry.jsonl` (un finding `REJECTED`, un `FIXED`, un `CONFIRMED`) ;
    - des blocs `rgkb` dans `factory-planner`, `factory-builder` et `factory-run`, les outils rgkb dans `tools:`, et rgkb dans `--allowedTools` de `ci/factory.sh`.
  - `customized/` (commit 2, personnalisations hors bloc) :
    - `factory-planner.md` : section « ## Règles maison » ajoutée en fin de fichier (cas CV-03 `suffix`) ;
    - `factory-builder.md` : une ligne du milieu modifiée (cas CV-04 `modified`) ;
    - `ci/factory.sh` : `export FACTORY_EXTRA=1` ajouté en fin de fichier (`suffix`) ;
    - `settings.json` : clé utilisateur `env` et une règle `deny` utilisateur ;
    - `tasks.json` : une tâche utilisateur ;
    - `gitignore.txt` : deux lignes utilisateur ;
    - `knowledge/config.json` : une exclusion utilisateur et `"hooks": "auto"`, sans hook installé.
  - `untracked/`, copié après les commits : `ci/lab.ps1` (cas `untracked`).
  - `factory-verifier.md` et les agents `lab-*` sont `pristine`.
- **`upgrade-phase1/`** : un projet de Phase 1. Il porte une copie `.claude/harness/` égale à une entrée de `history.json` sans MANIFEST, pas de tampon, et pas de bloc hors `rgkb`. Les tests l'assemblent depuis `upgrade-legacy/installed/`, plus le noyau de l'entrée choisie (`old-core/`, uniquement les fichiers qui diffèrent du noyau courant).
- **`upgrade-mixed-core/`** : ai-lab et software-factory installés depuis deux versions différentes. `old-core-a/` et `old-core-b/` portent les seuls fichiers qui diffèrent, chacun égal à une entrée d'historique. `lab-run` et `factory-run` sont présents.
- **`upgrade-core-custom/`** : un fichier de `old-core-a/` modifié d'un octet (cas CO-04 bloquant).
- **`upgrade-blocks/`** : un projet déjà dans la mise en page RD-01, rendu par `profile-v1/` (un profil jouet). Chaque type de fichier porte des personnalisations hors bloc (agent `.md`, `SKILL.md`, `.sh`, `.ps1`, JSON, `.gitignore`). `profile-v2/` = le même profil avec des fragments modifiés.
- **`upgrade-stamp-phase2/`** : `harness.json` égal à `{"profiles":[…], "autonomy":"gate", "x":1}`.
- **`upgrade-expected/<fixture>/`** : arbres attendus après upgrade, à date fixée, avec le fichier `.diff` attendu.
- **`doctor-*` et arbres de `--scan`** : fabriqués par les tests dans un dossier temporaire, à partir des fixtures ci-dessus et de défauts semés : fichier supprimé, bloc édité, `models.json` absent, `gh` simulé non authentifié (`fake_gh.py`), marqueur `research` ajouté, `node_modules/` contenant un faux `harness.json`, jonction ou lien vers un projet.

## Critères d'acceptation

`<PY>` = l'interpréteur détecté. `T` = `cd skills/_core/tests && <PY> -B -m unittest discover -s . -t .`. `K` = `<PY> skills/_core/harness.py`. `S` = `specs/SPEC-phase3-upgrade-doctor.md`. Les recherches utilisent `grep` (`rg` est absent du PATH de Git Bash). Les dossiers temporaires sont créés par les tests.

- [ ] **CA-01 — Tests verts.** `T` → exit 0.
- [ ] **CA-02 — Stdlib seule, Python 3.9.** `cd skills/_core/tests && <PY> -B -I -S -m unittest discover -s . -t .` → exit 0, avec `<PY> --version` en 3.9.x.
- [ ] **CA-03 — Chaque règle est testée.** `for id in $(grep -oE '\b(VS|HJ|CO|RD|EN|DT|UP|MI|CV|EP|CX|DR|SN|PR|GT|JR)-[0-9]{2}\b' S | sort -u); do grep -rlq "$id" skills/_core/tests || echo "$id"; done` → aucune sortie.
- [ ] **CA-04 — Version du dépôt.**
  - `K version` → `repo.commit` = `git rev-parse HEAD`, `repo.describe` = `git describe --tags --always --dirty`, `source: "git"`.
  - `test_version.LinkTest` : depuis une jonction (Windows, `mklink /J`) ou un lien symbolique (POSIX) vers `skills/` créé dans un dossier temporaire, `<PY> <lien>/_core/harness.py version` rend le même `commit`.
  - Avec git rendu introuvable (substitution de `proc`) : `commit: null`, `describe: "core-3.0.0"`, exit 0.
  - `.claude/harness/harness.py version` d'une copie → `source: "manifest"`.
- [ ] **CA-05 — Retard.** Dans un dépôt jetable à 3 commits : installé au commit 1 → `behind`, `commits: 2` ; au HEAD → `up_to_date` ; commit inconnu → `unknown` avec repli semver ; HEAD ancêtre de l'installé → `ahead`.
- [ ] **CA-06 — Tampon.**
  - `K stamp validate` → exit 0 sur `upgrade-expected/*/claude/harness.json`.
  - exit 2 sur : chemin absolu, clé `rg_path`, `schema_version` inconnu.
  - Sur `upgrade-stamp-phase2` : après upgrade, `autonomy` vaut toujours `"gate"`, `x` vaut toujours 1, l'ordre des clés d'origine est conservé.
  - Sans `autonomy` : la valeur écrite est `"auto"`.
  - Un second apply → `cmp` identique (date non modifiée).
- [ ] **CA-07 — Historique du noyau.**
  - `K core history --check` → exit 0 sur l'arbre courant.
  - Dans une copie temporaire de `skills/_core` où un octet d'un fichier a changé → exit 1, et le fichier est nommé.
- [ ] **CA-08 — Copie du noyau.**
  - `copy-core` écrit `MANIFEST.json`, dont la table `files` est égale aux sha256 des fichiers copiés.
  - `upgrade-phase1` → copie mise à jour, et `diff -r -x __pycache__ -x MANIFEST.json skills/_core <tmp>/.claude/harness` est vide.
  - `upgrade-mixed-core` → `mixed: true` au doctor, puis copie mise à jour.
  - `upgrade-core-custom` → exit 1, message `core not upgraded`, et tous les fichiers du projet restent identiques (`cmp`), tampon compris.
  - Un fichier `extra` est conservé et rapporté.
- [ ] **CA-09 — Rendu déterministe.**
  - Deux rendus du même fragment avec les mêmes paramètres sont identiques (`cmp`).
  - Un paramètre requis manquant → `action: fill_params`, et aucun fichier hors `.harness/runs/` ne change.
- [ ] **CA-10 — En-tête.**
  - Pour chaque fichier généré de `upgrade-expected/*` : `sed -n 1p` = `---` et `sed -n 2p` commence par `# harness: claude-skills ` (fichiers `.md` à frontmatter) ; ligne 2 pour `.sh`, ligne 1 pour `.ps1`.
  - `grep -L "harness: claude-skills"` sur ces fichiers → aucune sortie.
  - `grep -c "harness:" ` vaut 0 dans `settings.json`, `tasks.json` et `.mcp.json`.
- [ ] **CA-11 — Contributions et idempotence croisée.** Sur `upgrade-blocks` avec code-index installé, la suite `upgrade software-factory` → `upgrade code-index` → `upgrade software-factory` → `upgrade code-index` donne des plans vides aux étapes 3 et 4. `tools:` des agents à `tools` limitatif contient les 7 outils `mcp__rgkb__*`, et `bash -n ci/factory.sh` passe.
- [ ] **CA-12 — Hors bloc préservé.** Sur `upgrade-blocks` (v1 → v2), pour chaque fichier modifié, `strip_blocks(avant) == strip_blocks(après)` (test). Les clés, tâches et lignes utilisateur des JSON et du `.gitignore` sont présentes et inchangées. Seuls les blocs diffèrent, et ils sont égaux à `upgrade-expected/upgrade-blocks/`.
- [ ] **CA-13 — Idempotence.** Sur chaque fixture `upgrade-*` (sauf `core-custom`), après apply, un nouveau plan → `changes: []`. Un second apply ne modifie aucun fichier (`cmp` de tout l'arbre, `harness.json` compris).
- [ ] **CA-14 — Diff complet et fidèle.** Dans le dépôt temporaire, `git apply --check <diff>` sur l'état d'avant → exit 0. Une fois appliqué, `diff -r` contre l'état produit par `apply` est vide. Le diff contient un en-tête `+++` par fichier listé dans `changes`.
- [ ] **CA-15 — Plan périmé.** Modifier un fichier entre `plan` et `apply` → exit 1, `plan is stale`, et aucune écriture.
- [ ] **CA-16 — Migrations.** Sur `upgrade-legacy` :
  - `claude/models.json` est créé avec les clés `lab.*`, et `cmp` de `lab-models.json` contre la fixture donne 0 ;
  - `.claude/findings.jsonl` contient le `REJECTED` et le `FIXED`, mais pas le `CONFIRMED` ;
  - le registre source est inchangé (`cmp`) ;
  - `migrations[]` porte son sha256 ;
  - un second upgrade ne republie rien (`cmp` de `findings.jsonl`).
- [ ] **CA-17 — Projet sans tampon.**
  - `K stamp resolve` sur `upgrade-legacy` → `source: inferred`, `skills` ⊇ {`software-factory`, `code-index`}, profils {`software`, `research`}, génération `pre-core`.
  - Après le premier upgrade, le tampon existe, avec `inferred_from: "pre-core"`.
  - Un arrêt simulé avant la fin (échec d'écriture injecté) → pas de tampon. La relance aboutit.
- [ ] **CA-18 — Conversion (Q6).** Sur `upgrade-legacy`, défauts appliqués :
  - `factory-verifier.md` (`pristine`) est converti, et son bloc `rgkb` est conservé à l'identique ;
  - `factory-planner.md` (`suffix`) est converti, et `grep -F "## Règles maison"` le trouve hors des blocs (test `strip_blocks`) ;
  - `ci/factory.sh` (`suffix`) contient `export FACTORY_EXTRA=1` hors bloc ;
  - `factory-builder.md` (`modified`) et `ci/lab.ps1` (`untracked`) sont identiques (`cmp`), avec `kind: legacy` au tampon et deux événements `gate` `upgrade.convert` au journal ;
  - avec `--convert`, ils sont convertis, et leur original se trouve dans `.harness/runs/upgrade-*/backup/` (`cmp`) ;
  - le plan des conversions a `blocks_only: false`.
- [ ] **CA-19 — `/software-factory --upgrade`.**
  - `grep -F -- "--upgrade" skills/software-factory/SKILL.md skills/ai-lab/SKILL.md` ≥ 1 pour chacun.
  - `test_upgrade.ArgsTest` : `--upgrade --profile x` → exit 2 ; `--upgrade --rescan` → exit 2 ; `--upgrade texte` → exit 2 ; la traduction d'`/ai-lab --upgrade` ne contient pas `--profile`.
  - Un projet `none` → exit 1, `not equipped`.
  - Un projet installé par un commit `ahead` → exit 1, `newer harness`.
- [ ] **CA-20 — `/code-index --upgrade`.**
  - `grep -F -- "--upgrade" skills/code-index/SKILL.md` ≥ 1.
  - Sur `upgrade-legacy` : `rgkb.py` est mis à jour (`TOOL_VERSION` de l'asset) ; les blocs `rgkb` sont égaux aux gabarits rendus ; l'exclusion utilisateur de `config.json` est présente ; `post-merge` et `post-rewrite` contiennent `# >>> rgkb >>>` ; `--upgrade --reindex` → exit 2.
  - Un second passage donne un plan vide.
- [ ] **CA-21 — Doctor dans un projet.** Sur un projet temporaire où chaque défaut est semé, `K doctor --root` rend :
  - `missing` contenant le fichier supprimé ;
  - un bloc `edited` ;
  - un bloc `outdated` (dépôt v2) ;
  - `hooks.missing` = `["post-merge","post-rewrite"]` ;
  - `models.models_json: false` avec `migration_available: true` ;
  - `gh.authenticated: false`, avec le message `gh not authenticated` ;
  - `signals.propose_rescan: true`.

  Sur `upgrade-expected/upgrade-blocks`, tous les contrôles sont `ok` (sauf `gh` simulé authentifié). Racine inexistante → exit 2. Projet `none` → aucun fichier créé.
- [ ] **CA-22 — Skill doctor.**
  - `sed -n 1p skills/harness-doctor/SKILL.md` = `---`.
  - `sed -n 2p` = `name: harness-doctor`.
  - `grep -c "^description: ." ` = 1.
  - `grep -cE "context: fork|disable-model-invocation" skills/harness-doctor/SKILL.md` = 0.
  - `grep -F -- "--scan"` ≥ 1.
- [ ] **CA-23 — Scan.** Arbre temporaire contenant : un projet à jour, un projet en retard de 2 commits, un projet sans tampon, un dossier non équipé, un `node_modules/x/.claude/harness.json`, une jonction ou un lien vers le premier projet, et un projet à profondeur 4.
  - `K doctor scan --root` → exactement 3 lignes, triées. Le projet en retard a `lag.status: behind` et `commits: 2`.
  - `last_cycle` est tiré du nom de journal le plus récent (`factory-run-20261010-120000.jsonl` l'emporte sur `ship-pr-20261009-…` même avec une date de modification plus récente), avec le `verdict` de sa dernière ligne.
  - `--depth 4` → 4 lignes ; `--depth -1` → exit 2.
  - Un relevé `find <racine> -newer <témoin>` après le scan est vide (SN-05).
- [ ] **CA-24 — Proposition d'upgrade.** Tests de gate :
  - plan `blocks_only` et `autonomy: auto` → `harness-doctor.upgrade-blocks` rend `default`, événement `gate` `source: default`, et l'upgrade est déclenché (rejeu) ;
  - même plan en `gate` → `ask` ;
  - plan avec `convert` en `auto` → `harness-doctor.upgrade-other`, upgrade non lancé, et le rapport contient la commande et la classe `convert` ;
  - repli headless : `default` dans les deux cas ;
  - `K gate list` montre `phase3_auto: true` pour `upgrade-blocks` seulement.
- [ ] **CA-25 — Journal.**
  - `K journal validate` → exit 0 sur les journaux des rejeux d'upgrade (`software-factory-*`, `code-index-*`) et du doctor (`harness-doctor-*`).
  - Les noms suivent JR-01, plus `harness-doctor`.
  - Chaque fichier modifié a son événement `upgrade`.
- [ ] **CA-26 — Noyau partagé, versions mélangées.** Sur `upgrade-mixed-core`, un seul apply met à jour la copie et les blocs de `factory-run` et de `lab-run`. Un échec d'écriture injecté sur le second orchestrateur → aucun fichier modifié (`cmp` de tout l'arbre) et pas de tampon. La relance aboutit.
- [ ] **CA-27 — README.**
  - `grep -F "## Mettre à jour un projet équipé" README.md` ≥ 1.
  - `grep -F "### \`harness-doctor\`" README.md` ≥ 1.
  - `grep -F -- "--upgrade" README.md` ≥ 2.
  - `grep -F "harness.json" README.md` ≥ 1.
- [ ] **CA-28 — Fichiers hors périmètre intacts.** `git diff --exit-code <BASE3> -- install_skills.sh install_skills.ps1 skills/ship-pr skills/brainstorm skills/audit skills/code-index/assets/rgkb.py` → exit 0.
- [ ] **CA-29 — Copie du dépôt.** `diff -r -x __pycache__ -x MANIFEST.json skills/_core .claude/harness` est vide, et `K core history --check` → exit 0.
- [ ] **CA-30 — Aucun artefact parasite.** `git status --porcelain` ne liste ni `__pycache__`, ni `.pyc`, ni journal, ni `*.plan.json`, ni `*.diff`, ni `backup/`, ni `findings.jsonl`.
- [ ] **CA-31 — Fixtures inertes.** `find tests/fixtures \( -name CLAUDE.md -o -name '.*' \) -not -path tests/fixtures` → aucune sortie.

**Recettes par l'utilisateur, hors portes du Verifier :**
- **R12** (L0) : après `install_skills.*`, `<PY> ~/.claude/skills/_core/harness.py version` rend le commit du clone, sous Windows (jonction) comme sous POSIX.
- **R13** (L9) : `/harness-doctor` invoque `software-factory --upgrade` par l'outil Skill, en interactif puis en headless (même mécanisme que R8 de la Phase 2).
- **R14** (L0) : un agent et un `SKILL.md` dont la ligne 2 du frontmatter est un commentaire YAML (`# harness: …`) et qui portent des marqueurs `# >>> harness.frontmatter >>>` sont chargés par Claude Code : l'agent apparaît dans `/agents` et `/factory-run` est disponible.
- **R15** : `/software-factory --upgrade` puis `/code-index --upgrade` sur une copie d'un vrai projet équipé avant le noyau ; relance → zéro diff.
- **R16** : `/harness-doctor --scan <racine des projets>` sur la machine de l'utilisateur.

## Hors-périmètre

- Politique d'autonomie effective au-delà des gates `phase2_auto` et `phase3_auto` : `--autonomy`, fichiers `STOP-*.md`, état `BLOQUEE`, enchaînements audit → factory-run → ship-pr (Phase 4).
- Hooks Claude Code (Phase 5), tests d'intégration de la Phase 6 hors des fixtures de cette spec, packaging (Phase 7).
- Le retour en arrière d'une version (`UP-08` refuse), le retrait d'un profil du tampon, la suppression des sauvegardes d'upgrade.
- La mise à jour du dépôt claude-skills lui-même (`git pull`) et des liens globaux.
- La migration des anciens livrables d'audit, qui relève de MG-01 (`/audit`).
- Le lancement de `--rescan` par le doctor (proposé seulement) et le lancement d'upgrades depuis `--scan`.
- L'upgrade de `ship-pr`, `brainstorm` et `audit` : ils sont globaux et n'installent rien dans les projets.
- La reconstruction de l'index `.knowledge/` par l'upgrade (`--reindex`).
- Tout commit, push, `/ship-pr` ou exécution de `install_skills.*` par le Builder.

## Risques

- **[IMPOSSIBLE] I7 — Idempotence d'un contenu rédigé par un LLM.** « Relancer sans changement produit zéro diff » ne peut pas valoir pour des blocs que le LLM réécrit à chaque passage : deux rédactions ne sont jamais identiques octet pour octet (D10).
  - Remplacement : rendu déterministe RD-02, avec l'adaptation au projet figée dans `params` (RD-03).
  - Conséquences : les blocs `rgkb` deviennent des gabarits (RD-06, règle de code-index modifiée), et l'installation de la Phase 2 (EP-04) doit enregistrer ses paramètres. Les fichiers attendus de la Phase 2 (`profile-expected/*`, CA-13 de la Phase 2) changent : en-tête, blocs, MANIFEST. Ils sont régénérés au lot L3, et l'écart est documenté dans `tests/fixtures/README.md`.
- **[IMPOSSIBLE] I8 — En-tête dans les JSON stricts et les fichiers copiés.** Un JSON strict n'a pas de commentaire. Un fichier copié « tel quel » (noyau, `rgkb.py`, CX-05) ne peut pas recevoir d'en-tête sans cesser d'être identique à sa source. La version passe donc par le tampon, `MANIFEST.json` et `TOOL_VERSION` (EN-03).
- **[IMPOSSIBLE] I9 — « Régénérer uniquement les blocs » d'un fichier qui n'en a pas.** Un fichier sans bloc est entièrement hors bloc : sans conversion, il ne serait jamais mis à jour (D5, X1 de la Phase 1). CV en est la seule voie. Elle est sûre dans les cas `pristine` et `suffix`, et soumise à une gate dans les autres.
- **[DOC] I10 — Commentaires YAML et marqueurs dans le frontmatter.** La doc ne dit pas explicitement que Claude Code accepte des commentaires dans le frontmatter des agents et des skills. Un parseur YAML standard les ignore ; R14 le vérifie. En cas d'échec, l'en-tête et le bloc `harness.frontmatter` passent juste après le `---` de fermeture, et la spec est corrigée.
- **[DOC] I11 — Version depuis un skill installé par lien.** `${CLAUDE_SKILL_DIR}` donne le chemin du lien (R1). La version repose sur la résolution Python du chemin de `harness.py` (`Path.resolve`, jonctions comprises), puis sur `git -C`. R12 le vérifie.
- **[DOC] I12 — Doctor qui invoque un autre skill.** L'invocation par l'outil Skill depuis un skill en ligne repose sur la recette R8 de la Phase 2, et R13 la refait. En cas d'échec, le doctor affiche les commandes à lancer, sans lancement automatique.
- **`history.json` oublié.** Un commit qui touche `_core` sans régénérer l'historique rend les copies ultérieures `customized`, donc bloquées. CA-07 et CA-29 le détectent dans `T`, et la porte du Builder de ce dépôt doit lancer `core history --check`.
- **Base git approximative (CV-01).** Le plus ancien commit d'un fichier peut déjà contenir des personnalisations, puisque l'installation ne commite rien. Une telle personnalisation est alors vue comme du contenu généré et se retrouve, après conversion, seulement dans la sauvegarde. Le diff complet (UP-04) la rend visible avant l'apply.
- **Tampon versionné.** `updated_at` et les hashes de blocs peuvent entrer en conflit entre branches d'équipe. Le fichier est petit et à clés stables ; un conflit s'y résout à la main.
- **Retard en commits.** VS-03 n'a de sens que sur une même lignée du dépôt. Un clone d'une autre branche ou une réécriture d'historique donnent `diverged` ou `unknown`, avec un repli semver grossier.
- **Noyau global et noyau du projet.** ship-pr et `/audit` utilisent le noyau global et écrivent `.claude/findings.jsonl` et `.harness/runs/` dans des projets dont la copie peut être plus ancienne. Le doctor signale l'écart (DR-02 `core`), mais aucune version de format n'est portée par `findings.jsonl`.
- **Diffs volumineux.** Le premier upgrade d'un projet `pre-core` (conversions, copie complète du noyau) produit un long diff à afficher en conversation. C'est assumé : la ROADMAP exige le diff complet.
- **Coût du scan.** Une racine vaste multiplie les appels git pour le retard. La profondeur par défaut est bornée (SN-01), et liens et artefacts sont exclus.

## Questions ouvertes

Chaque question est tranchée par défaut ; la justification tient en une ligne.

- **Q1 — Source de la version.** Défaut : `git describe --tags --always --dirty` plus le commit, avec `CORE_VERSION` en repli. Justification : la ROADMAP demande « tag git ou hash », et le dépôt n'a aucun tag aujourd'hui.
- **Q2 — Premier upgrade d'un fichier sans bloc (BACKLOG Q6).** Défaut : CV. Conversion automatique si le fichier est `pristine` ou `suffix`, sinon gate `upgrade.convert` avec « Conserver » par défaut et `--convert` pour forcer. Justification : c'est le seul classement déterministe qui ne perd aucune personnalisation sans la montrer.
- **Q3 — Fusions et copie comptées comme « blocs seulement ».** Défaut : oui pour `merge` (ajout par union), `copy` (`pristine`), `header`, `stamp` et `local`. Justification : l'union FU a remplacé les blocs dans les JSON (I1 de la Phase 2), et aucune de ces classes ne modifie un contenu de l'utilisateur.
- **Q4 — Bloc édité à la main.** Défaut : remplacé par l'upgrade, avec sauvegarde, et signalé `edited` par le doctor. Justification : la ROADMAP fait des blocs la propriété du harnais ; la personnalisation se fait hors bloc.
- **Q5 — `autonomy` absente.** Défaut : `"auto"` écrit à la première écriture du tampon, jamais une valeur existante remplacée. Justification : ROADMAP §4.1, « le défaut installé pour moi est `auto` ».
- **Q6 — Profondeur du scan.** Défaut : 3, avec `--depth N`. Justification : elle couvre `<racine>/<groupe>/<projet>/<sous-projet>` sans parcourir tout un disque.
- **Q7 — Upgrades lancés par `--scan`.** Défaut : jamais ; la commande est affichée par projet. Justification : chaque upgrade exige son diff affiché dans son propre projet (UP-04).
- **Q8 — Confirmation avant l'apply.** Défaut : aucune gate. Le plan haché (UP-05) garantit que seul le diff montré est appliqué. Justification : la ROADMAP dit « montre le diff complet, applique », et l'utilisateur a lui-même demandé `--upgrade`.
- **Q9 — Emplacement des sauvegardes.** Défaut : `.harness/runs/upgrade-<horodatage>/backup/`. Justification : le dossier est déjà exclu de git (D3), et aucune nouvelle ligne `.gitignore` n'est nécessaire.
- **Q10 — `software-factory --upgrade` lance-t-il `code-index --upgrade` ?** Défaut : non. Le doctor enchaîne les deux (PR-04). Justification : les enchaînements entre skills relèvent de la Phase 4, sauf celui que la Phase 3 nomme (doctor → upgrade).
- **Q11 — Blocs `rgkb` rédigés ou en gabarit.** Défaut : en gabarit (RD-06). Justification : l'idempotence de la ROADMAP prime sur « rédigé pour l'agent concerné » (I7).
- **Q12 — `context: fork` pour le doctor.** Défaut : non. Justification : le rapport doit rester dans la conversation, et l'invocation de skills en ligne est le mécanisme validé (R8).
- **Q13 — Fichier généré manquant.** Défaut : recréé par l'upgrade (classe `create`, jamais `blocks_only`). Justification : l'orchestrateur en dépend, et la classe empêche une recréation automatique par le doctor.
- **Q14 — Upgrade depuis un dépôt claude-skills modifié non commité.** Défaut : autorisé, avec `repo_dirty: true` au tampon et un `warn` au doctor. Justification : le refuser bloquerait le développement du harnais sur ses propres fixtures.
- **Q15 — Reconnaissance d'un ancien noyau.** Défaut : par `history.json` versionné, plutôt que par `git log --find-object` à l'exécution. Justification : cela fonctionne sans git, depuis une copie de projet et sur un clone superficiel.
- **Q16 — Versionner `harness.json`.** Défaut : oui, sans aucune donnée propre à une machine (HJ-12). Justification : l'équipe partage l'installation, comme `.mcp.json` et `.knowledge/config.json`.
- **Q17 — Langue de l'en-tête.** Défaut : anglais. Justification : c'est une chaîne produite par le code (décision du 2026-10-17) ; seuls les marqueurs `debut`/`fin` restent en français, parce qu'ils sont un format partagé.

---

Notes pour l'appelant :
- Fichiers lus : `C:\Users\fuzzz\claude-skills\specs\harness-v2\ROADMAP.md`, `C:\Users\fuzzz\claude-skills\specs\harness-v2\BACKLOG.md`, `C:\Users\fuzzz\claude-skills\specs\SPEC-noyau-core-journal.md`, `C:\Users\fuzzz\claude-skills\specs\SPEC-phase1-rebranchement.md` (en entier), `C:\Users\fuzzz\claude-skills\specs\SPEC-phase2-profils-audit.md` (en entier), `C:\Users\fuzzz\claude-skills\skills\software-factory\SKILL.md`, `C:\Users\fuzzz\claude-skills\skills\code-index\SKILL.md`, `C:\Users\fuzzz\claude-skills\skills\ai-lab\SKILL.md`, `C:\Users\fuzzz\claude-skills\skills\_core\harness.py`, `C:\Users\fuzzz\claude-skills\skills\_core\hcore\{__init__,fusion,blocks,models,runs,journal,ghflow}.py`, `C:\Users\fuzzz\claude-skills\skills\code-index\assets\rgkb.py` (hooks, config, doctor), `C:\Users\fuzzz\claude-skills\install_skills.sh`, `C:\Users\fuzzz\claude-skills\README.md`, `C:\Users\fuzzz\claude-skills\tests\fixtures\README.md`.
- Non lus en détail : `ship-pr`, `brainstorm`, les trois `SKILL.md` d'audit et `install_skills.ps1`. Seuls les faits utiles ont été vérifiés par Grep : le message `gh`, et la liaison des sous-dossiers par les installeurs, établie par `install_skills.sh:176` et par les specs précédentes.
- Deux choix de cette spec retouchent le comportement de phases déjà approuvées :
  - **RD/EP-11** : l'installation de la Phase 2 doit écrire des blocs et des `params`.
  - **RD-06** : les blocs rgkb passent en gabarits.

  Tous deux découlent de l'exigence d'idempotence de la ROADMAP (I7) et sont signalés à l'endroit concerné.
- Fait vérifié qui conditionne Q1 : le dépôt n'a aucun tag git (`.git/refs/tags` vide, pas de `packed-refs`).