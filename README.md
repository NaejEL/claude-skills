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

Point d'entrée **unique** de l'installation d'une usine multi-agents dans n'importe quel projet. Il détecte les **profils** applicables (voir « Profils »), installe l'usine de chacun et note les profils retenus dans `.claude/harness.json` :

```text
/software-factory
/software-factory --profile "software;research"
/software-factory --rescan
/software-factory --upgrade
```

`--profile` force les profils et saute le scout ; `--rescan` relance le scout et ne propose que des **ajouts** (un profil disparu est rapporté, jamais retiré). Sans option, un projet déjà équipé est relu depuis `.claude/harness.json` (ou déduit de ses fichiers générés) sans nouveau scout.

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

### `harness-doctor`

Diagnostique l'installation du harnais d'un projet, ou d'une arborescence de projets. Dans un projet, il compare la version installée à celle du dépôt claude-skills (retard en commits), signale les blocs divergents (`edited`, `outdated`), les fichiers manquants, les hooks rgkb déclarés mais absents, un `models.json` absent, un `gh` non authentifié et les profils nouveaux (il **propose** `--rescan`, sans le lancer), puis propose `--upgrade` : il le lance (par l'outil Skill, `software-factory` puis `code-index`) quand le diff ne touche que des blocs et que la politique d'autonomie l'autorise.

```text
/harness-doctor
/harness-doctor --scan ~/projets --depth 3
```

Avec `--scan <racine>`, une ligne par projet équipé : version installée, retard, dernier cycle, commande d'upgrade. Le scan est en lecture seule et ne lance jamais d'upgrade.

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

### `factory-queue`

Liste les specs de `specs/` avec leur statut dérivé (proposée, bloquée, en cours, livrée, mergée), leurs dépendances (`Dépend de :`) et leur `Priorité :`, puis, avec `run`, les déroule l'une après l'autre : chaque spec éligible est confiée à un processus enfant headless (`claude -p "/factory-run <spec> --ship <cible>"`, contexte neuf), dont la PR est mergée avant de passer à la suivante. `run` exige la politique `auto` ; un enfant arrêté arrête la file. Aucun autre état n'est nécessaire : tout se déduit de `Statut :`, de git et de `.harness/runs/`.

```text
/factory-queue
/factory-queue run [--only "SPEC-a.md;SPEC-b.md"] [--target main] [--autonomy auto]
```

### `factory-batch`

Construit plusieurs specs **en parallèle** (`--parallel N`, défaut 2, plafond 4), chacune dans un worktree git créé et suivi par le harnais, puis les livre **une à la fois** : rebase de la branche locale sur la cible, `ship-pr`, merge, rassemblement des journaux du worktree, suppression. Un conflit non trivial arrête le lot (type `conflict`) en conservant le worktree. Non invocable par un autre skill.

```text
/factory-batch specs/SPEC-leg-*.md --parallel 3 --autonomy auto
/factory-batch --resume <id>
```

#### Coexistence avec vos worktrees

Le harnais ne touche jamais au worktree principal ni à ceux que vous créez vous-même (i3, Orca, `git worktree add`). Il ne crée que des worktrees `factory/<slug>` sous `<dépôt>.harness-wt/`, les inscrit dans un registre commun à tous les worktrees (`<git-common-dir>/harness/worktrees.json`, hors versionnement), et n'opère que sur un chemin **à la fois** inscrit au registre **et** listé par `git worktree list --porcelain` avec la branche enregistrée. Jamais de `git worktree prune`, de `remove --force`, de `move`, `lock` ou `unlock`. `git worktree list` est le seul moyen de voir les siens ; `/factory-run --worktree` construit une spec dans un worktree dédié, supprimé après le merge. Prérequis : `.claude/harness/` et `.claude/settings.json` doivent être commités sur la branche cible.

### `audit`

Audit **unifié et en lecture seule** d'un projet : cartographie, un auditeur par lentille, validation adversariale de chaque finding, priorisation interactive, puis **un seul livrable `AUDIT.md`** et des specs `specs/SPEC-*.md` au format factory.

```text
/audit
/audit C:/chemin/projet --profile software --lenses "securite;evolutivite" --max-findings 10
/audit --profile research --max-questions 4
```

Les lentilles viennent des profils actifs : `software` (jeu `legacy` : hygiène, portabilité, qualité, filet de sécurité ; jeu `vibecode` : accès, injection, métier, maintenabilité, évolutivité) et `research` (fidélité, validité, fuites, analogies biologiques, feuille de route). `--lenses` accepte des noms de lentille ou d'axe (`securite` = accès, injection, métier) ; au plus 5 auditeurs en parallèle, par vagues. `AUDIT.md` regroupe l'en-tête (profils, lentilles, complet ou échantillonné), les sections de chaque jeu et une « Suite » ; les anciens livrables (`ROADMAP-legacy.md`, `AUDIT-vibecode.md`, `AUDIT-lab.md`) sont **repris une fois** (ligne `<!-- harness:import … -->`, statuts `FAIT`, `EN_COURS`, `TRANCHEE` préservés), jamais modifiés ni supprimés. Idempotent : mêmes entrées, même `AUDIT.md`.

### `legacy-audit`

Skill **alias** de `/audit --profile software` limité aux lentilles `hygiene`, `portabilite`, `qualite`, `filet` (`--categories` devient `--lenses`), conservé pendant la version 2.0.0 puis retiré. Écrit `AUDIT.md` et les specs `SPEC-leg-*`.

### `vibecode-audit`

Skill **alias** de `/audit --profile software` limité aux lentilles vibecode (`--axes` développé en lentilles), conservé pendant la version 2.0.0 puis retiré.

### `ai-lab`

Skill **alias** de `/software-factory --profile research`, conservé sans échéance « pour ne rien casser ». Installe le **laboratoire de recherche IA** (profil `research`) : Directeur de recherche, experts neurosciences et maths, Builder, Verifier, le skill `/lab-run` (seconde instance du gabarit d'orchestrateur, profil `research` imposé), `ci/lab.*`, la copie du noyau et l'affectation des modèles par rôle (`.claude/models.json`, clés `lab.*`). Sur un projet déjà équipé du profil `software`, `research` est **ajouté** au tampon `.claude/harness.json`, rien n'est retiré.

```text
/ai-lab
/lab-run "la lecture itérée CA3 améliore-t-elle le rappel par paraphrase ?"
/lab-run suivant
```

### `ai-lab-audit`

Skill **alias** de `/audit --profile research` (lentilles `fidelite`, `validite`, `fuites`, `bio`, `route`), conservé pendant la version 2.0.0 puis retiré. Les questions `Q-*` se lancent par `/factory-run --profile research "<question>"`.

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

Rebranché sur le noyau `_core` (`hcore/bs.py`) : arguments et plafond de tours, validation du JSON des lentilles, relance unique d'une lentille muette (qui désactive la sortie anticipée du tour), sortie anticipée, plafond de 5 pistes retenues, slug, reprise et rendu de la synthèse sont du code testé. **Aucune écriture avant la gate finale** : le noyau est sans état et la session lui passe le sien sur l'entrée standard ; le journal est écrit avec la synthèse.

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

`post-merge` (donc `git pull`) et `post-rewrite` (rebase) réindexent après coup ; `--with-commit` ajoute `pre-commit`, qui réindexe et met `.knowledge/` à l'index, de sorte que **tout commit porte un index cohérent avec son code**. Les hooks n'écrivent que si le contenu a changé et ne font jamais échouer une opération git ; `RGKB_NO_HOOK=1 git pull` les neutralise ponctuellement. Un hook existant est complété par un bloc délimité, jamais écrasé. `.git/hooks/` n'est pas versionné, mais l'**intention** l'est : `hooks install` écrit `"hooks": "commit"` dans `.knowledge/config.json`, et tout `status` ou `index` réconcilie les hooks locaux avec elle. Un utilisateur qui clone les obtient donc au premier cycle, sans rien lancer. `rgkb.py init` ne réécrit jamais un `config.json` existant, et `hooks install` ne remplace jamais un `config.json` illisible.

`post-checkout` est **volontairement absent** : réindexer après un changement de branche salit l'arbre à chaque fois et git refuse le checkout suivant. Avec `pre-commit`, il n'a de toute façon rien à faire.

Le câblage (sauf `--no-wire`) ajoute aux agents existants un bloc délimité `<!-- rgkb:debut -->` / `<!-- rgkb:fin -->`, réentrant, sans jamais réécrire leur prompt : fiche de fichier avant de lire un fichier entier, lecture des notes avant de formuler un avis, réindexation après modification pour le Builder, et à la consignation finale d'un cycle une proposition de note (1 à 3 par cycle, jamais ce que l'index retrouve seul). `/software-factory` et `/ai-lab` proposent son installation en fin de parcours (Phase 6b), toujours avec accord explicite.

Le skill s'appuie sur le noyau `_core` (`hcore/cx.py`) pour tout ce qui est déterministe : arguments, commande d'installation de `rg`, état du dépôt, copie versionnée du serveur, fusion de `.mcp.json`, `settings.json`, `tasks.json` et de l'exclusion de `config.json`, blocs réentrants, `tools` et `--allowedTools` complétés sans rien retirer. Il exige Python ≥ 3.9.

## Politique d'autonomie

La clé `autonomy` de `.claude/harness.json` vaut `gate` (chaque décision humaine est posée) ou `auto` (défaut installé par `/software-factory`). L'option `--autonomy gate|auto` des skills la remplace pour une exécution, sans jamais écrire le tampon ; la politique effective est transmise aux skills enchaînés. En `auto`, une gate de type (b) ou (c) prend son défaut justifié, journalisé (la justification figure dans le skill qui pose la gate et dans `harness.py gate list`) ; une gate de type (a) s'évalue sur sa condition d'arrêt. Une boucle `auto` ne demande rien d'autre que ses conditions d'arrêt : spec `BLOQUEE` (question bloquante sans défaut), trois itérations sans approbation, agent mort deux fois, dérive de périmètre répétée, opération destructive, secret, enfant en échec, gate sans défaut.

Chaque arrêt écrit un fichier `.harness/runs/STOP-<horodatage>.md` (en anglais, 40 lignes au plus : où, pourquoi, comment reprendre, la commande exacte), un événement `stop` au journal et sort en code 1 ; le harnais ne les supprime jamais. Les enchaînements : `/audit` → `/factory-queue run` (les specs écrites, dans l'ordre de priorité calculé), `/factory-run` → `/ship-pr` (commit de livraison puis PR), et `/ship-pr` merge **sans question** si cinq conditions sont vraies (aucun finding validé restant, tous les threads résolus, CI verte, cible non protégée, pas de conflit), en postant la décision en commentaire de la PR ; sinon la PR reste ouverte. `/brainstorm` ne lance rien. Ce dépôt reste en `gate` : le harnais ne s'auto-modifie pas en autonomie.

## Hooks

`/software-factory` installe dans `.claude/settings.json` (fusion additive, vos hooks et commentaires sont conservés) trois hooks Python stdlib, copiés avec le noyau sous `.claude/harness/hooks/` : un filet Bash/PowerShell **permanent** qui bloque `git push --force`, la suppression de branche, la réécriture d'historique, la destruction de travail non committé et les suppressions de fichiers hors artefacts générés (c'est un filet au mieux, pas une preuve : exécutez-vous-même l'opération voulue dans un terminal) ; pendant `/factory-run`, le contrôle du `Périmètre fichiers :` de la spec (la seconde dérive arrête le cycle) ; pendant `/ship-pr`, la limitation au diff de la PR ; et, si le projet configure un linter (`hooks.lint` de `.claude/harness.json`), un `PostToolUse` de vérification, jamais bloquant. Une erreur interne d'un hook laisse passer l'action et le dit. Les hooks ne valent qu'à la session suivante (ou après revue dans `/hooks`).

## Profils

Un **profil** est un dossier de données sous `skills/_core/profiles/<nom>/` (manifeste `profile.json` plus fragments Markdown : rôles, lentilles, orchestrateur, détection) ; il ne contient aucun code. Deux profils sont livrés : `software` (usine logicielle, profil de repli) et `research` (laboratoire de recherche IA). Ajouter un profil = ajouter un dossier ; `harness.py profile validate <dossier>` le contrôle (schéma : `skills/_core/profiles/SCHEMA.md`).

Un agent `harness-scout` (sous-agent Explore en lecture seule, modèle économique) détecte les profils applicables : le noyau relève les signaux déterministes et vérifie les preuves de l'agent. Les profils retenus sont notés dans `.claude/harness.json` (clé `profiles`) ; le noyau ne fait qu'ajouter. Une proposition nette est prise par défaut en autonomie `auto`, une proposition ambiguë arrête avec la commande de reprise `--profile`.

## Mettre à jour un projet équipé

Chaque projet équipé porte un tampon **versionné** `.claude/harness.json` : version du dépôt claude-skills qui l'a produit (tag git ou hash), date, skills installés et leurs options, politique d'autonomie, profils actifs, fichiers générés avec le hachage de leurs blocs (`skills/_core/STAMP.md`). Chaque fichier généré commence par un en-tête `harness: claude-skills <version>`, suivi de **blocs délimités** (`harness.frontmatter`, `harness.body`, `harness.profile.<nom>`, `harness.ci`, `rgkb`) ; tout ce qui est hors bloc appartient à l'utilisateur.

```text
/software-factory --upgrade [--convert]
/code-index --upgrade
/harness-doctor
```

`--upgrade` ne régénère que les blocs, préserve tout le hors-bloc (invariant vérifié avant l'écriture), migre les formats (`lab-models.json` vers `models.json`, anciens registres de run vers `.claude/findings.jsonl`), met à jour la copie du noyau `.claude/harness/` dans le même plan que les blocs de tous les profils, **montre le diff complet** puis l'applique, tout ou rien, avec sauvegarde sous `.harness/runs/upgrade-<horodatage>/backup/`. Il est idempotent : relancé sans changement, il ne produit aucun diff. Un fichier généré avant le noyau (sans bloc) est converti sans perte s'il est resté tel que généré ou s'il n'a reçu qu'un ajout en fin de fichier ; sinon la gate `upgrade.convert` propose de le conserver (défaut) ou de le convertir avec sauvegarde (`--convert` pour tous). Un projet sans tampon est détecté par ses fichiers générés, et le tampon est créé à la première mise à jour. Pas de retour en arrière : un projet installé par un harnais plus récent que le dépôt est refusé.

## Noyau `skills/_core/`

`skills/_core/` n'est pas un skill (il n'a pas de `SKILL.md`) : c'est le noyau déterministe partagé, en Python de bibliothèque standard (≥ 3.9), exposé par une CLI unique `harness.py` et testé par `py -3 -B -m unittest discover -s skills/_core/tests` (ou `python3`). Il porte ce qui ne relève pas du jugement — parsing des blocs JSON de verdict, compteurs d'itérations et de rondes, relance d'un agent mort, fusions de fichiers, séquences `gh`/`git` de `ship-pr`, et pour tous les skills : la primitive de **gate** (politique d'autonomie, catalogue des gates, repli headless), le schéma unique de **finding** (adaptateurs, validateur, conversions en spec, note ou commentaire) avec son registre projet local **`.claude/findings.jsonl`** (exclu de git, une ligne par finding), la détection de **stack** et ses bornes, les tailles et tris **tshirt**, les modèles par rôle (`.claude/models.json`, avec migration de `lab-models.json`), le moteur commun des audits — et écrit le journal de cycle `.harness/runs/<skill>-<horodatage>.jsonl`, exclu de git. Le script d'installation le lie comme les skills, en `~/.claude/skills/_core`, où `ship-pr` l'appelle par `${CLAUDE_SKILL_DIR}/../_core` ; `software-factory` le copie dans chaque projet équipé sous `.claude/harness/` (avec un `MANIFEST.json`, et `history.json` qui reconnaît ses états successifs : `harness.py core history --check`), que le `/factory-run` généré et la CI appellent.

## Ajouter un skill

Créer `skills/<nom>/SKILL.md` (frontmatter `name` + `description` minimum), relancer le script d'installation, commiter.
