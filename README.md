# claude-skills

Skills globaux [Claude Code](https://code.claude.com/docs) personnels, versionnés pour être réutilisés sur plusieurs machines (Windows / Linux / macOS).

## Installation

Cloner le dépôt puis lier les skills dans `~/.claude/skills` :

```powershell
# Windows (jonctions, sans droits admin)
.\install_skills.ps1
```

```bash
# Linux / macOS (liens symboliques)
./install_skills.sh
```

Les scripts sont idempotents : relancer après un `git pull` ou l'ajout d'un skill ne casse rien. Les skills sont disponibles dans toute nouvelle session Claude Code.

Ils installent aussi les **outils externes** dont les skills ont besoin — aujourd'hui le seul est **ripgrep**, requis par `code-index` — en détectant le gestionnaire de paquets de la machine : `winget`, puis `scoop`, puis `chocolatey` sous Windows ; `brew` (ou MacPorts) sous macOS ; `apt`, `dnf`, `paru`/`yay`/`pacman`, `zypper`, `apk`, `xbps`, `nix` sous Linux ; `cargo install` en dernier recours. Le `PATH` de la session est rafraîchi après l'installation. Si rien n'aboutit, les skills restent installés et le script explique quoi faire, sans échouer.

```powershell
.\install_skills.ps1 -SkipTools   # lier les skills sans toucher aux paquets
```

```bash
./install_skills.sh --skip-tools
```

La détection du gestionnaire de paquets est **factorisée** et indépendante de ripgrep. Pour ajouter un outil demain : une entrée dans `tool_package` (bash) ou `Get-ToolPackage` (PowerShell), qui donne l'identifiant de paquet par gestionnaire, puis une ligne `ensure_tool` / `Install-ToolIfMissing` dans la section « Outils externes ».

## Skills

### `software-factory`

Initialise une **usine logicielle multi-agents** dans n'importe quel projet :

```text
/software-factory
```

Le skill détecte la stack du projet (C, C#, Python, Node, Docker, Ansible…) et génère :

| Fichier généré | Rôle |
| --- | --- |
| `.claude/agents/factory-planner.md` | Analyse le besoin + le code, rédige la spec, liste ses questions (lecture seule) |
| `.claude/agents/factory-builder.md` | Implémente strictement la spec approuvée, code + tests, build vert exigé |
| `.claude/agents/factory-verifier.md` | Vérification adversariale, exécute les tests, verdict JSON (jamais d'édition) |
| `.claude/skills/factory-run/SKILL.md` | Orchestrateur : Planner → gate humaine sur la spec → Builder → Verifier |
| `ci/factory.sh` + `ci/factory.ps1` | Entrée CI mince : `claude -p "/factory-run 'specs/SPEC-x.md'"` |
| `.claude/settings.json` | Règles `permissions.deny` pour économiser les tokens (fusionné) |
| `.vscode/tasks.json` | Tâches VS Code Factory (fusionné) |

Cycle d'un besoin :

```text
/factory-run "ajouter l'export CSV des rapports"
```

1. **Planner** (contexte séparé) analyse et pose ses questions — **vous êtes le Product Owner** ;
2. la spec `specs/SPEC-*.md` n'est construite qu'après **votre approbation explicite** ;
3. **Builder** (contexte frais) implémente code + tests et doit rendre un build vert ;
4. **Verifier** (contexte vierge, adversarial) exécute les tests et rend un verdict JSON ; en cas de `CHANGES_REQUESTED`, ses issues sont réinjectées au Builder — **3 itérations maximum**, puis échec explicite.

En CI : `ci/factory.sh specs/SPEC-x.md` (mode sûr `--permission-mode acceptEdits` + liste blanche d'outils) ou `--yolo` pour `--dangerously-skip-permissions`.

### `ship-pr`

Pilote le **cycle complet d'une pull request GitHub** depuis la branche courante jusqu'au merge :

```text
/ship-pr main
/ship-pr develop --rounds 2 --themes "logique;régressions"
```

1. **Préflight** : gh authentifié, remote GitHub, branche ≠ cible, working tree propre, push si nécessaire ;
2. **PR** créée automatiquement (titre + corps générés depuis les commits) ou reprise si elle existe ;
3. **Rondes de revue** (3 max, arrêt anticipé à épuisement) : 3 relecteurs parallèles en lecture seule (logique/cas limites, régressions/sites d'appel, cohérence du diff) → validation adversariale de chaque finding par un mini-agent → commentaire inline sur la PR → correctifs commités et poussés → réponse à chaque thread avec le hash du fix puis résolution ;
4. **Gate humaine** : validation explicite avant `gh pr merge --merge --delete-branch` (commit de merge, branche distante et locale supprimées).

Garde-fous anti-dérive : périmètre strictement limité au diff (pas de refacto, pas de durcissement sécurité spéculatif, pas de nitpick), « zéro finding » est une réponse acceptable, registre cumulatif empêchant un finding rejeté de ressusciter d'une ronde à l'autre.

### `legacy-audit`

Audite un **repo legacy en lecture seule** et en tire un plan d'assainissement exécutable par la factory :

```text
/legacy-audit
/legacy-audit C:/chemin/vieux-projet --categories "hygiene;qualite" --max-specs 10
```

1. **Cartographie** du repo (stack, taille, git présent ou non — l'absence de versioning est un finding) ;
2. **4 auditeurs parallèles** par familles de smells (hygiène du dépôt, portabilité/config, qualité du code, filet de sécurité : tests/doc) → **validation adversariale** de chaque finding par un mini-agent qui relit la preuve à la source ;
3. **Priorisation interactive** : nombre de jalons, critère dominant et affectation par thème décidés par l'utilisateur (AskUserQuestion) ;
4. **Livrables** : `ROADMAP-legacy.md` (jalons, estimations, dépendances) + une spec `specs/SPEC-leg-*.md` au format factory (statut proposé) par finding retenu — prêtes pour `/factory-run`.

Garde-fous : lecture seule stricte hors livrables (même un `.gitignore` manquant est un finding, pas une action), « zéro finding » est une réponse acceptable, estimation T-shirt (XS→XL, les XL sont découpés en specs chaînées), idempotent (reprise d'une roadmap existante, statuts FAIT préservés, specs jamais écrasées).

### `ai-lab`

Installe un **laboratoire de recherche IA multi-agents** dans un projet d'expérimentation (PoC d'architecture, mécanisme bio-inspiré, étude d'ablation) — le pendant scientifique de `software-factory` :

```text
/ai-lab
/ai-lab "le gating par surprise est-il nécessaire à l'échelle 1.5B ?"
```

Le skill détecte la stack (framework, venv, GPU réel), le **corpus scientifique** du projet (journal d'expériences et son format, architecture, feuille de route et tableau des résultats, documents figés, évals existantes, classe de config, contraintes non négociables) et génère :

| Fichier généré | Rôle |
| --- | --- |
| `.claude/agents/lab-director.md` | Directeur de recherche : cadre l'hypothèse, rédige le protocole pré-enregistré (prédictions chiffrées, contrôles, critères d'abandon), arbitre, tranche RETENU / REJETE / INCONCLUSIF, rédige l'entrée de journal (lecture seule) |
| `.claude/agents/lab-neuro.md` | Expert neurosciences/biologie : analogue biologique fidèle, prédictions que la bio impose, analogies de façade dénoncées (lecture seule) |
| `.claude/agents/lab-math.md` | Expert algèbre linéaire/optimisation/stats : formalisation, bornes (capacité, stabilité, interférence), puissance statistique, confondants, recalcul des chiffres (lecture seule) |
| `.claude/agents/lab-builder.md` | Implémente le protocole comme flag de config ablatable + tests + script d'éval, exécute l'expérience complète, rend les résultats bruts **sans interpréter** |
| `.claude/agents/lab-verifier.md` | Adversarial : conformité au protocole, fuites/confondants dans le code, ré-exécution d'au moins un run, recalcul, verdict JSON (jamais d'édition) |
| `.claude/skills/lab-run/SKILL.md` | Orchestrateur de la boucle scientifique |
| `.claude/lab-models.json` | Affectation d'un modèle par rôle, choisie à l'installation (gate humaine) |
| `ci/lab.sh` + `ci/lab.ps1` | Entrée headless : `claude -p "/lab-run 'experiments/EXP-x.md'"` |
| `.claude/settings.json` | `permissions.deny` : venv, caches, données, poids, résultats bruts (fusionné) |
| `.vscode/tasks.json` | Tâches VS Code Lab (fusionné) |

Cycle d'une expérience :

```text
/lab-run "la lecture itérée CA3 améliore-t-elle le rappel par paraphrase ?"
/lab-run suivant        # le Director choisit la prochaine expérience de la feuille de route
```

1. **Cadrage** : Director → brouillon de protocole ; **Neuro et Math en parallèle** ; Director consolide ;
2. **Gate humaine** : vous êtes le PI — le protocole `experiments/EXP-*.md` est **pré-enregistré** (prédictions et critères d'abandon gelés) après votre approbation explicite ;
3. **Builder** (contexte frais) implémente, fait passer les tests, exécute tous les runs (baseline, contrôles, seeds) et rend un compte rendu brut ;
4. **Verifier** (contexte vierge) contrôle le protocole, traque les fuites, ré-exécute, recalcule ; `CHANGES_REQUESTED` réinjecté au Builder — **3 itérations maximum**, puis échec explicite consigné ;
5. **Interprétation croisée** : Neuro et Math en parallèle, puis Director → verdict, entrée de journal au format du projet, ligne du tableau des résultats, prochaine expérience ;
6. **Gate humaine** avant écriture dans le journal. Les documents figés du projet ne sont jamais édités.

Un résultat négatif est un résultat : le cycle réussit quand la question a une réponse honnête, pas quand le code « marche ».

**Un modèle par rôle.** À l'installation, une gate humaine choisit quel modèle tient quel rôle (profils prêts : tout hérité / le plus capable sur les deux experts / le plus capable seulement sur l'interprétation / sur-mesure par rôle). Le choix est écrit dans `.claude/lab-models.json` et relu à chaque cycle ; `inherit` = le rôle suit le modèle de la session. Override ponctuel sans toucher au fichier :

```text
/lab-run "ma question" --models "math=fable;director.interpretation=fable;builder=sonnet"
```

Les rôles affectés à un modèle coûteux sont traités comme une ressource rare : jamais le journal entier ni les résultats bruts en entrée, pas de relance pour une reformulation, et l'interprétation croisée n'a lieu qu'une fois par cycle. L'entrée de journal consigne quel modèle a tenu quel rôle — condition de reproductibilité du jugement, au même titre que les seeds.

### `ai-lab-audit`

Revue externe d'un **projet de recherche IA en lecture seule** — le pendant scientifique de `legacy-audit`, qui alimente `/lab-run` au lieu de le détourner (auditer ≠ expérimenter : aucun run, aucun protocole) :

```text
/ai-lab-audit
/ai-lab-audit C:/chemin/projet --lenses "validite;fuites" --max-questions 4 --models "math=fable"
```

1. **Cartographie du corpus scientifique** (journal et format de ses entrées, architecture, feuille de route et tableau des résultats, documents figés, évals et leurs options réelles, contraintes non négociables) ; réutilise les agents `lab-*` s'ils sont installés ;
2. **5 auditeurs parallèles** par lentilles : `fidelite` (code ↔ maths de l'architecture), `validite` (conclusions plus fortes que leurs données : seeds, dispersion, chiffres incohérents entre documents), `fuites` (confondants dans les évals : état non réinitialisé, baseline à budget différent, écriture pendant le rappel…), `bio` (analogies de façade, déclencheurs observés mais mécanisme jamais essayé), `route` (désaccords état courant / journal / tableau, décisions « quasi closes » sans mesure) → **validation adversariale** de chaque finding, avec grep du journal pour vérifier que la réponse n'existe pas déjà ;
3. **Arbitrage humain** : sort des corrections (specs factory ou simple liste) et critère de priorité des questions (fiabiliser d'abord / le moins cher / ordre de la feuille de route) ;
4. **Livrable** `AUDIT-lab.md` : **corrections** `COR-*` (avec specs `specs/SPEC-lab-*.md` si la factory est présente) et **questions de recherche** `Q-*` — une phrase falsifiable, sa motivation chiffrée, ce qu'elle trancherait, son coût, sa dépendance éventuelle à une correction, et la commande `/lab-run "<question>"` exacte.

Garde-fous : « zéro finding » est une réponse acceptable, une question dont dépend un banc d'éval fuyant attend la correction du banc, idempotent (reprise, questions tranchées par une entrée de journal postérieure marquées `TRANCHEE`). L'audit lit la même affectation de modèles que `/lab-run` (`.claude/lab-models.json`) : les mini-validateurs restent sur un modèle économique, contester un extrait de trois lignes ne justifie pas le modèle le plus cher.

### `brainstorm`

Co-réfléchit à une idée en la **challengeant** au lieu de la valider, et **s'arrête** :

```text
/brainstorm "monter une offre d'audit technique pour des PME"
/brainstorm "remplacer notre file de messages par du polling" --rounds 2
```

1. **Ancrage** du sujet sur le répertoire courant, budget dur de 12 fichiers lus — reconnaissance écourtée et signalée si le sujet n'a aucun rapport avec le répertoire ; reprise d'un `BRAINSTORM-<slug>.md` antérieur pour ne pas reproposer une piste déjà écartée ;
2. **5 lentilles parallèles en contexte vierge** à chaque tour (hypothèses implicites, alternatives radicales, contre-exemples et cas limites, coût et faisabilité, effets de second ordre) — chaque piste marquée `[énoncé]` ou `[hors énoncé]`, au moins une piste hors énoncé exigée par tour ;
3. **Gate humaine à chaque tour** (AskUserQuestion) : creuser / écarter / amender chaque angle, le tour suivant part de vos réponses ;
4. **Convergence** : synthèse en conversation (idée après confrontation, angles retenus, angles écartés avec leur raison), puis gate finale proposant de l'écrire dans `BRAINSTORM-<slug>.md` — en cas de refus, rien n'est écrit.

**Condition de terminaison** : plafond dur de **3 tours** (`--rounds N` borné à `min(N, 3)`), passage forcé à la convergence au plafond, sortie anticipée observable dès qu'un tour ne produit plus aucun angle hors énoncé nouveau, et **5 pistes retenues au maximum** dans la synthèse. Le rapport final suggère `/factory-run` ou `/lab-run` quand un angle retenu est implémentable, sans jamais lancer la commande. Arrêt en erreur explicite en exécution headless : le skill est intrinsèquement dialogué.

### `code-index`

Installe un **serveur de connaissance local adossé à ripgrep** dans le projet courant, et branche dessus l'usine ou le labo déjà présents :

```text
/code-index
/code-index --reindex
/code-index --no-wire
```

Le serveur (`.claude/rgkb/rgkb.py`) est un programme Python de bibliothèque standard, **sans aucune dépendance à installer** ; seul `rg` doit être disponible. Il s'expose de deux façons équivalentes : un **serveur MCP stdio** déclaré dans `.mcp.json` (outils `mcp__rgkb__search`, `definition`, `symbols`, `neighbors`, `file_card`, `notes`, `note_add`, `status`, `reindex`) et une **CLI** utilisable en Bash comme en headless.

Tout vit sous `.knowledge/`, **versionné dans le dépôt** — c'est le point : un `git clone` transmet la base de connaissance d'un utilisateur à l'autre, sans rien à reconstruire.

| Fichier | Rôle | Vérité |
|---|---|---|
| `config.json` | périmètre de l'index (globs, exclusions, plafonds) | source |
| `config.local.json` | réglages propres à une machine, **seul fichier non versionné** | source |
| `notes.jsonl` | notes écrites par les humains et les agents | source |
| `files.jsonl` / `symbols.jsonl` | fichiers indexés, définitions trouvées par ripgrep | dérivé |
| `graph.json` | arêtes fichier → symbole mentionné | dérivé |
| `index.sqlite` | cache de requête, reconstruit depuis le texte | dérivé |

Les sources sont du **texte, une ligne par élément** : un conflit git se lit et se fusionne. `index.sqlite` est déclaré binaire dans `.knowledge/.gitattributes` — en cas de conflit on prend n'importe quel côté et on relance `index --force`, qui le régénère depuis les sources. Une réindexation sans changement de code ne produit **aucun diff**.

**Fraîcheur de l'index.** Pendant un cycle `/factory-run` ou `/lab-run`, elle est automatique : vérification avant la première phase qui dépense, réindexation par le Builder après ses modifications. Hors cycle, des **hooks git** s'en chargent :

```text
python .claude/rgkb/rgkb.py hooks install --with-commit
python .claude/rgkb/rgkb.py hooks status
python .claude/rgkb/rgkb.py hooks remove
```

`post-merge` (donc `git pull`) et `post-rewrite` (rebase) réindexent après coup ; `--with-commit` ajoute `pre-commit`, qui réindexe et met `.knowledge/` à l'index, de sorte que **tout commit porte un index cohérent avec son code**. Les hooks n'écrivent que si le contenu a changé et ne font jamais échouer une opération git ; `RGKB_NO_HOOK=1 git pull` les neutralise ponctuellement. Un hook existant est complété par un bloc délimité, jamais écrasé. `.git/hooks/` n'est pas versionné, mais l'**intention** l'est : `hooks install` écrit `"hooks": "commit"` dans `.knowledge/config.json`, et tout `status` ou `index` réconcilie les hooks locaux avec elle. Un utilisateur qui clone les obtient donc au premier cycle, sans rien lancer.

`post-checkout` est **volontairement absent** : réindexer après un changement de branche salit l'arbre à chaque fois et git refuse le checkout suivant. Avec `pre-commit`, il n'a de toute façon rien à faire.

Le câblage (sauf `--no-wire`) ajoute aux agents existants un bloc délimité `<!-- rgkb:debut -->` / `<!-- rgkb:fin -->`, réentrant, sans jamais réécrire leur prompt : fiche de fichier avant de lire un fichier entier, lecture des notes avant de formuler un avis, réindexation après modification pour le Builder, et à la consignation finale d'un cycle une proposition de note (1 à 3 par cycle, jamais ce que l'index retrouve seul). `/software-factory` et `/ai-lab` proposent son installation en fin de parcours (Phase 6b), toujours avec accord explicite.

## Ajouter un skill

Créer `skills/<nom>/SKILL.md` (frontmatter `name` + `description` minimum), relancer le script d'installation, commiter.
