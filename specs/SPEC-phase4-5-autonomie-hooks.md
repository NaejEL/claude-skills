# SPEC — Phases 4 et 5 : politique d'autonomie, boucle (file, lots, worktrees) et hooks Claude Code

Statut : APPROUVEE (2026-10-17). Défauts des questions ouvertes retenus, Q1 = enfant headless (CH-01).

Cette spec couvre les Phases 4 et 5 de `specs/harness-v2/ROADMAP.md` (§4.1 à §4.4, §5). Elle sera enregistrée sous `specs/SPEC-phase4-5-autonomie-hooks.md`. Elle suppose livrées la Phase 1 (`specs/SPEC-phase1-rebranchement.md`, APPROUVEE), la Phase 2 (`specs/SPEC-phase2-profils-audit.md`, APPROUVEE) et la Phase 3 (tampon `harness.json` complet, `--upgrade`, `/harness-doctor`), rédigée en parallèle. Elle reprend leurs conventions : identifiants de règle, `<PY>`, `T`, `K`, rejeux scriptés, comparaison structurelle (D10), fixtures inertes (I6 de la Phase 2).

Règle de l'utilisateur, appliquée partout : **la ROADMAP fait foi**. Une règle héritée qui la contredit est modifiée ou retirée, et la spec le dit à l'endroit concerné. Les seuls points remontés comme problèmes sont des impossibilités techniques (**[IMPOSSIBLE]**) et des points de la doc Claude Code à confirmer ou contredits (**[DOC]**), dans *Risques*. Le BACKLOG §5 sert de base de faits vérifiés.

## Contexte

### Le besoin

**Phase 4.** Passer de gates humaines partout à une boucle qui demande le moins possible :
- une politique `autonomy: gate|auto` déclarée dans `.claude/harness.json`, avec un override `--autonomy` ;
- `auto` comme défaut installé ;
- un défaut justifié pour chaque gate ;
- un arrêt seulement sur les gates (a) et les conditions d'arrêt de §4.3, chacun écrit dans un fichier `STOP-*.md` ;
- une spec `BLOQUEE` quand elle déclare des questions bloquantes, et sa reprise ;
- un merge automatique de ship-pr sous cinq conditions ;
- des enchaînements audit → factory-run → ship-pr ;
- une priorisation automatique des audits et un upgrade automatique quand seuls des blocs changent ;
- `/factory-queue`, `/factory-batch` et `/factory-run --worktree`, qui cohabitent avec les worktrees de l'utilisateur.

**Phase 5.** Rendre déterministes, par des hooks Claude Code, des garde-fous qui ne sont aujourd'hui que des consignes :
- linter en `PostToolUse` ;
- périmètre de la spec en `PreToolUse` pendant factory-run ;
- diff de la PR en `PreToolUse` pendant ship-pr ;
- commandes Bash destructrices bloquées en permanence.

Ces hooks s'activent selon le contexte, laissent passer en cas d'erreur interne, provoquent un arrêt (a) à la deuxième dérive, sont des scripts Python stdlib portables, et sont générés dans le `settings.json` fusionné.

### Gel levé

Le BACKLOG §2 gèle les incréments 7 (autonomie), 8 (hooks) et 12 (file et worktrees) jusqu'à l'analyse de 10 cycles. L'utilisateur a levé ce gel pour les Phases 1 et 2 et demande la livraison de toutes les phases. La levée est consignée au lot L12.

### Point de départ (vérifié par lecture)

**Gates**
- Phase 1, GT-01 à GT-08 (`SPEC-phase1-rebranchement.md:81-121`) :
  - `GT-02` : en `auto`, `ask` pour (a) ;
  - `GT-03` : `auto` est appliqué comme `gate` ;
  - catalogue de 27 gates, défauts déjà justifiés, plusieurs défauts « aucun ».
- Phase 2 :
  - `AR-02` (`SPEC-phase2-profils-audit.md:134-137`) déroge à GT-03 pour `software-factory.profiles` et `audit.profiles` (`phase2_auto: true`) ;
  - `AR-03` renvoie tout le reste, dont la priorisation des audits, à la Phase 4 ;
  - `E-I3` fusionne `ai-lab.code-index` dans `software-factory.code-index`.

**factory-run** (gabarit `skills/software-factory/SKILL.md`)
- Frontmatter `disable-model-invocation: true` (`:49`) : l'outil Skill ne peut pas l'invoquer (I3 de la Phase 2).
- Plan headless = arrêt (`:54`).
- « ne pas commiter à sa place » (`:63`).
- `hcore/factory.py:30-50` (FR-01) : seule une spec `Statut : APPROUVEE` passe en `build`. Un chemin vers une spec `PROPOSEE` est traité comme un besoin en texte libre (mode `plan`, avec le chemin pour besoin). C'est le cas des specs produites par les audits, dont la « prochaine action » est `/factory-run "specs/SPEC-leg-01-…"` (`skills/legacy-audit/SKILL.md:162`).

**ship-pr**
- Pas de `disable-model-invocation` (`skills/ship-pr/SKILL.md:1-7`) : l'outil Skill peut l'invoquer.
- Merge = gate (a) (`:95-99`).
- `shippr.merge_refusal` (`hcore/shippr.py:258-266`) refuse seulement si la boucle n'est pas finie ou si un thème n'est pas couvert.
- `ghflow.merge` (`hcore/ghflow.py:292-305`) fait `gh pr merge --merge --delete-branch`, puis `git checkout <cible>` et `git pull`. Cette séquence échoue dans un worktree lié quand la cible est extraite ailleurs.
- `ghflow.commit_round` fait `git add -A` (`:238`).

**Journal, runs et sous-processus**
- `hcore/journal.py:22-23` : noms fermés.
- `hcore/runs.py:32` : `.claude/runs/` relatif à la racine de l'arbre de travail, donc un dossier par worktree.
- `hcore/proc.py:37-54` : injection d'exécutables simulés en `HCORE_TEST_MODE=1`.
- `Runner` lance sans shell (`:65-83`).

**Fusion et copie du noyau**
- `hcore/fusion.py` n'écrit aucune clé `hooks`. Aucun hook Claude Code n'existe dans le dépôt : `.claude/settings.json` ne contient que `permissions.deny`.
- `STACK_DENY` (`fusion.py:37-43`) énumère les dossiers d'artefacts.
- `copy_core` copie récursivement tout `_core` (`fusion.py:241`) : un `skills/_core/hooks/` part donc dans `.claude/harness/hooks/` des projets.

**Formats de spec et skills existants**
- Les specs d'audit finissent par `## Questions ouvertes` / `Aucune` (`legacy-audit:150-151`). Aucun champ machine ne distingue une question bloquante.
- `brainstorm:101` : « Ne jamais lancer cette commande à la place de l'utilisateur ». La ROADMAP §4.2 le maintient : c'est le seul skill qui ne lance rien.
- ai-lab :
  - gate de pré-enregistrement (`skills/ai-lab/SKILL.md:180`) ;
  - consignation automatique « à relire » en headless (`:188`).
- `ci/factory.*` exige `Statut : APPROUVEE` (`software-factory:72`).
- Usine de ce dépôt : `.claude/skills/factory-run/SKILL.md:56` dit « Ne jamais commiter à sa place ». BACKLOG §1 (2026-10-16) : pas de `/ship-pr` ni de push sur ce dépôt sans demande explicite.

### Contrat supposé de la Phase 3 (à aligner au lot L0, voir Q25)

- `.claude/harness.json` porte `version`, `date`, `skills`, `options`, `autonomy` et `profiles` (HJ-01).
- `K upgrade plan --root R` rend `{changes: [{path, kind, block}], divergent_blocks: [...]}`, avec `kind` ∈ `block|outside|migration|new|removed|core|stamp`, et `core` qualifié `unmodified: true|false`.
- `/harness-doctor` existe, avec `--scan <racine>`.

## Périmètre

### 1. Politique d'autonomie — `AP`

- `AP-01` : la table GT-02 est remplacée.
  - Politique `gate` : `ask` pour (a), (b) et (c), avec le repli headless GT-06 inchangé.
  - Politique `auto` :
    - (b) et (c) → `default` ;
    - (b) ou (c) sans défaut → arrêt `gate` (SX) ;
    - (a) → le noyau évalue la condition `stop_when` déclarée au catalogue, sur les entrées fournies par le skill : vraie → arrêt (SX) ; fausse → `default`.
  - Gate de dialogue (`brainstorm.*`, GT-04) → `ask` toujours.
- `AP-02` : `GT-03` (garde de la Phase 1) est retiré, et la marque `phase2_auto` disparaît du catalogue : AR-02 devient le cas général. Les assertions concernées de la Phase 1 (CA-10 : « `auto` → `ask` avec avertissement ») et de la Phase 2 (CA-10, dernier point ; CA-23, dernier point) sont modifiées. C'est l'écart E-P4-8.
- `AP-03` : option `--autonomy gate|auto`.
  - Skills concernés : `software-factory`, `factory-run` (et l'instance `lab-run`), `ship-pr`, `audit` et ses trois alias (transmise par `audit alias-args`), `code-index`, `harness-doctor`, `factory-queue`, `factory-batch`.
  - Elle vaut pour l'exécution seulement, et n'écrit jamais `harness.json`.
  - Priorité : option > tampon > absent (= `gate`, GT-01 inchangé).
  - Valeur invalide → exit 2.
  - Journal : événement `autonomy` `{value, source: flag|stamp|absent}`.
- `AP-04` : la politique effective est transmise à tout skill enchaîné. Un skill invoqué par l'outil Skill reçoit `--autonomy <effective>`. Un processus enfant (CH-01) reçoit la même option.
- `AP-05` : défaut installé. À l'installation, `software-factory` écrit `"autonomy": "auto"` dans `.claude/harness.json` si la clé est absente, ou la valeur de `--autonomy` si elle est donnée. Une valeur existante n'est jamais remplacée. La valeur retenue figure au rapport final.
- `AP-06` : chaque décision automatique est journalisée (événements GT-07) avec `policy`, `decision`, `default`, `justification` et, pour une gate (a), `stop_when` et son résultat. Aucune décision silencieuse.
- `AP-07` : en `auto`, la décision est celle d'AP-01, que AskUserQuestion soit disponible ou non. Le repli headless ne s'applique qu'en `gate`.
- `AP-08` : ce dépôt reçoit `.claude/harness.json` avec `"autonomy": "gate"`. Raison : BACKLOG §1, le harnais ne s'auto-modifie pas en autonomie.
- `AP-09` : chaque SKILL.md (ou fragment de profil) qui pose une gate écrit son défaut `auto` avec sa justification d'une ligne, mot pour mot égale au champ `justification` du catalogue (ROADMAP §4.1).

### 2. Catalogue des gates : défauts et conditions d'arrêt — `AP-10`

`AP-10` : le catalogue (GT-08, étendu par les profils, PF-05) porte pour chaque gate son type, son défaut en `auto` avec une justification d'une ligne, sa condition d'arrêt pour le type (a), et son repli headless en `gate`.

| ID | Type | Défaut en `auto` — justification | `stop_when` (type a) | Repli headless (`gate`) |
| --- | --- | --- | --- | --- |
| `software-factory.code-index` | b | ne pas installer — la base ajoute un dossier versionné ; l'installation reste possible à tout moment | — | skip |
| `software-factory.profiles` | b | proposition du scout si `clear` — §2.2 ; sans proposition nette, aucun défaut → arrêt `profile` | — | default si `clear`, sinon stop |
| `factory-run.profile` | b | premier profil du tampon — le premier retenu à l'installation (LP-05) | — | stop |
| `factory-run.questions` | b | le `Défaut :` déclaré par le Planner pour chaque question non bloquante — rien n'est inventé par l'orchestrateur ; une question bloquante → `BLOQUEE` (BQ) | — | stop |
| `factory-run.approval` | c | approuver — §4.2 « sans approbation » | — | stop |
| `factory-run.need` (usine du dépôt) | c | aucun — un besoin ne se devine pas → arrêt `gate` | — | stop |
| `factory-run.ship` (nouvelle) | c | livrer et lancer `/ship-pr` si CH-02 est satisfait — §4.2 « à build vert » | — | skip (suggestion seule, comportement actuel) |
| `ship-pr.target` | c | `ship_pr.target` du tampon s'il existe, sinon aucun → arrêt `gate` — la cible ne se devine pas | — | stop |
| `ship-pr.dirty` | a | abandonner — c'est la seule option qui n'agit pas sur des changements inconnus | toujours vraie : committer ou stasher des changements non produits par le cycle sort du périmètre accepté | default (abandonner) |
| `ship-pr.conflict` | b | continuer la revue — non destructif ; la condition C5 laisse ensuite la PR ouverte | — | default |
| `ship-pr.merge` | a | décision par SM-01 : merge si et seulement si les 5 conditions sont vraies — §4.2 | jamais : une condition fausse laisse la PR ouverte, sans arrêt | default (laisser ouverte) |
| `code-index.rg-install` | c | ne pas installer, repli local signalé — dépendance système de la machine | — | skip |
| `code-index.hooks` | b | `hooks install` — le défaut écrit à `code-index:113` | — | skip |
| `ai-lab.models` | b | tout hérité — aucun surcoût | — | default |
| `lab-run.pi-questions` | b | même règle que `factory-run.questions` (BQ, statut `BLOQUE`) — même boucle (LP-04) | — | stop |
| `lab-run.preregistration` | a | pré-enregistrer — §4.2 appliqué à l'artefact du profil `research` (Q2) | le protocole déclare des questions bloquantes sans réponse | stop |
| `lab-run.consignation` | c | consigner avec la mention « (consignée automatiquement — à relire) » — c'est déjà le comportement headless (`ai-lab:188`) | — | default |
| `audit.profiles` | b | comme `software-factory.profiles` (AD-02) | — | comme AR-01 |
| `audit.software.framing` | b | calcul PZ-01 et PZ-02 (« fiabiliser d'abord », jalons calculés) — §4.2 | — | stop |
| `audit.software.assignment` | b | affectation PZ-02, rien n'est exclu — §4.2 | — | stop |
| `audit.research.framing` | b | specs si `software` est actif ou une factory inférée, sinon liste ; questions triées par PZ-04 — §4.2 | — | stop |
| `audit.research.selection` | b | toutes, puis le plafond `--max-questions` — on borne le livrable, jamais la détection | — | stop |
| `audit.drop-security` | b | garder `securite` — l'axe prioritaire | — | default |
| `audit.final` | c | écrire — l'audit n'existe que par son livrable | — | stop (legacy et research) ou default (vibecode), inchangé |
| `audit.chain` (nouvelle) | c | lancer `/factory-queue run` sur les specs écrites si une factory `software` est présente — §4.2 | — | skip |
| `harness-doctor.upgrade` (nouvelle, Q25) | b | appliquer si UA-01 est satisfait, sinon proposer — §4.2 | — | skip |
| `brainstorm.subject`, `.round`, `.write` | dialogue | aucun — intrinsèquement dialogué (§4.2, GT-04) | — | stop |

### 3. Arrêts et fichiers `STOP-*.md` — `SX`

- `SX-01` : types d'arrêt (ROADMAP §4.3, plus les arrêts explicites déjà existants) :
  - `destructive` : HG en cycle ;
  - `iterations` : FR-03 ;
  - `agent` : FR-04, agent mort deux fois ;
  - `blocked` : BQ ;
  - `profile` : AR-02 ;
  - `drift` : HR ;
  - `cost` : CH-01 ;
  - `secret` : Q15 ;
  - `gate` : gate sans défaut en `auto`, ou condition (a) vraie ;
  - `conflict` : FB-05 ;
  - `child` : arrêt d'un processus enfant.
- `SX-02` : `K stop write --root R --skill S --kind K [--run <run>] --details-file F` écrit `.claude/runs/STOP-<AAAAMMJJ-HHMMSS>.md`.
  - En cas de collision de nom, une seconde est ajoutée, comme dans `runs.create`.
  - `F` est écrit par Write et supprimé après lecture, comme les fichiers de transit.
- `SX-03` : format, lisible en 30 secondes.
  - Ligne 1 : `# STOP — <skill> — <kind>`.
  - Puis, dans cet ordre :
    - `## Where` : skill, phase, run, spec, branche, worktree ;
    - `## Why` : raison en 5 lignes au plus, puis 10 éléments au plus (questions, issues, conditions) ;
    - `## To resume` : 5 étapes numérotées au plus ;
    - `## Command` : un seul bloc de code avec la commande exacte.
  - 40 lignes au plus.
  - En anglais : c'est un message d'arrêt (BACKLOG §5, 2026-10-17 ; Q14).
- `SX-04` : commande de reprise par type, rendue par le noyau :

| Type | Commande de reprise |
| --- | --- |
| `blocked` | `/factory-run <spec>`, une fois les lignes `Réponse :` remplies |
| `iterations`, `agent` | `/factory-run <spec>` |
| `profile` | `/software-factory --profile <p>` |
| `drift` | `/factory-run <spec>`, après correction de `Périmètre fichiers` ou de l'implémentation |
| `destructive` | aucune commande d'agent : exécuter soi-même l'opération si elle est voulue, puis relancer la commande du cycle |
| `cost` | relancer sans la variable de facturation, ou poser `chain.allow_api_billing: true` |
| `gate` | relancer avec la valeur manquante ou `--autonomy gate` |
| `conflict` | résoudre dans `<worktree>`, puis `/factory-batch --resume <id>` |
| `child` | chemin du STOP de l'enfant, et sa commande |

- `SX-05` : tout arrêt produit trois sorties :
  - le fichier STOP ;
  - un événement de journal `stop` `{kind, path}` ;
  - un exit 1, avec sur stderr `STOP: <raison> (see <chemin>)`.
- `SX-06` : après un arrêt, toute commande du noyau sur le même run rend exit 1 et cite le STOP. Il n'y a ni 4e itération, ni poursuite silencieuse (§4.3).
- `SX-07` : les fichiers STOP vivent sous `.claude/runs/`, exclus de git (D3). Le harnais ne les supprime jamais.

### 4. Spec `BLOQUEE`, statuts et reprise — `BQ`

- `BQ-01` : bloc d'en-tête machine. Il suit immédiatement la ligne `Statut :`, en lignes contiguës, chacune facultative :
  - `Questions bloquantes : Q2, Q4`, ou `aucune` ;
  - `Périmètre fichiers : src/**, tests/**` (globs relatifs à la racine, séparés par des virgules) ;
  - `Dépend de : SPEC-leg-01-purge-secrets.md, SPEC-leg-02` ;
  - `Priorité : <entier ≥ 1>`.
- `BQ-02` : dans `## Questions ouvertes`, chaque question est un élément `- Q<n> — <texte>`.
  - Sous-lignes possibles : `Défaut : …`, obligatoire pour une question non bloquante produite par le Planner, et `Réponse : …`.
  - Une question est **répondue** si sa ligne `Réponse :` est non vide.
- `BQ-03` : `K spec check <fichier>` rend `{status, blocking[], unanswered[], perimeter[], depends_on[], priority, errors[]}`. Exit 2 si :
  - un id bloquant est absent de la section ;
  - `Priorité` n'est pas un entier ≥ 1 ;
  - un glob est vide ou absolu ;
  - la ligne `Statut :` manque ;
  - le statut est hors de BQ-04.
- `BQ-04` : statuts.
  - Profil `software` : `PROPOSEE`, `BLOQUEE`, `APPROUVEE`, `LIVREE`.
  - Profil `research` : `PROPOSE`, `BLOQUE`, `PRE-ENREGISTRE`, `TERMINE — <verdict>`.
  - Nouvelles clés d'artefact de profil (extension de PF-02) : `status_blocked` et `status_delivered`.
- `BQ-05` : en `auto`, une spec écrite avec au moins une question bloquante sans réponse reçoit `Statut : BLOQUEE`.
  - Le cycle s'arrête alors (SX `blocked`), avec un événement de journal `blocked` portant le texte des questions (§4.2).
  - En `gate`, les questions sont posées comme aujourd'hui, et `BLOQUEE` n'apparaît qu'en headless.
- `BQ-06` : en `auto`, chaque question non bloquante prend son `Défaut :`. La spec porte `Réponse : <défaut> (défaut appliqué automatiquement)`, et une seule décision `factory-run.questions` est journalisée avec la liste des défauts appliqués.
- `BQ-07` : FR-01 est étendu. `K factory-run start` rend `mode`.

| Entrée | Résultat |
| --- | --- |
| spec `APPROUVEE` | `build` |
| spec `PROPOSEE` | `approve` : gate `factory-run.approval`, puis `build` |
| spec `BLOQUEE` avec des questions sans réponse | exit 1, arrêt `blocked` (le STOP liste les questions) |
| spec `BLOQUEE` entièrement répondue | `approve` : la session intègre les réponses, comme aujourd'hui |
| spec `LIVREE` | exit 1, `STOP: spec already delivered` |
| fichier sous `specs/` à statut inconnu | exit 2 |
| texte libre | `plan` |

  En `auto`, un `plan` headless est donc possible. En `gate`, l'arrêt headless de `software-factory:54` est inchangé.
- `BQ-08` : `K spec set-status <fichier> <statut>` ne modifie que la ligne `Statut :` : l'écart octet par octet porte sur cette seule ligne. Transitions admises :
  - `PROPOSEE` → `APPROUVEE` ou `BLOQUEE` ;
  - `BLOQUEE` → `APPROUVEE` ou `PROPOSEE` ;
  - `APPROUVEE` → `LIVREE` ;
  - équivalents `research` ;
  - toute autre transition → exit 2.
- `BQ-09` : sur `success` (FR-02), la spec passe à `LIVREE`, journalisé, quelle que soit la politique (E-P4-2).
- `BQ-10` : les fragments `roles/factory-planner.md` et `roles/lab-director.md` (*Questions pour le PI*) imposent :
  - la classification `bloquante` ou non de chaque question ouverte : bloquante = la construction ne peut pas commencer sans la réponse, et aucune option par défaut n'est défendable ;
  - un `Défaut :` justifié pour chaque question non bloquante ;
  - `Périmètre fichiers` quand la spec peut le borner.
- `BQ-11` : FD-08 (finding → spec) écrit :
  - `Questions bloquantes : aucune` ;
  - `Dépend de :`, depuis `depends_on` ;
  - `Priorité :`, le rang dans l'ordre de PZ.

### 5. Merge automatique de ship-pr — `SM`

- `SM-01` : conditions, toutes évaluées et toutes rapportées, sans court-circuit :
  - **C1 — zéro finding validé restant.** Aucun CONFIRMED dont `outcome` ≠ `FIXED`, et aucun `UNVALIDATED` (Q3).
  - **C2 — tous les threads résolus.** Tous les `reviewThreads` de la PR, humains compris, ont `isResolved: true`. La lecture est paginée au-delà de 100.
  - **C3 — CI verte si le repo en a une.**
    - Source : `gh pr checks <n>` (sortie JSON).
    - Aucun check → vrai, avec le détail « no CI ».
    - Tous `pass` ou `skipping` → vrai ; un `fail` ou `cancel` → faux.
    - `pending` → relecture toutes les 30 s pendant `ship_pr.ci_wait_min` minutes (défaut 20), puis faux (Q5).
  - **C4 — cible non protégée contre le merge automatique.** `gh api repos/<o>/<r>/branches/<cible>` rend `protected: false`, **et** la cible est absente de `ship_pr.protected` du tampon. Une erreur d'API → faux, avec « protection unknown » (Q6).
  - **C5 — pas de conflit.** `mergeable` vaut `MERGEABLE`. `UNKNOWN` est relu 5 fois à 3 s d'intervalle, puis faux.
- `SM-02` : `K ship-pr merge --run <run> --auto` rend `{merge, conditions: {C1..C5: {ok, detail}}}`.
  - Le refus SP-05 (thème non couvert, boucle non finie) est évalué avant les conditions.
  - En `auto`, ce refus est traité comme une condition fausse : PR ouverte, raison au journal et en commentaire, aucune question.
- `SM-03` : selon le résultat.
  - Tout est vrai : un commentaire de PR « Automatic merge: all conditions met » avec les cinq détails est posté **avant** le merge, puis le merge est fait (SP-19 ou SM-06), avec un événement `merge_decision` `{merged: true, conditions}`.
  - Une condition est fausse : commentaire « Automatic merge not performed: » suivi de la liste des conditions fausses et de leur détail, événement `merge_decision` `{merged: false, …}`, aucune question. ship-pr se termine normalement (exit 0), PR « laissée ouverte » au rapport.
- `SM-04` : le corps du commentaire est en anglais. Il est écrit dans un fichier et posté par `gh pr comment <n> --body-file`. Son id est enregistré : une relance ne le reposte pas.
- `SM-05` : en `gate`, la question de `ship-pr:98` reste ; le résumé affiche les cinq conditions, à titre d'information.
- `SM-06` : mode worktree (WT-03 reconnaît un worktree enregistré).
  - `gh pr merge <n> --merge`, sans `--delete-branch`.
  - Puis suppression de la branche distante de la PR par le noyau.
  - Aucun `git checkout <cible>` ni `git pull`. Le nettoyage local relève de WT-07.
- `SM-07` : option `--spec <chemin>`, enregistrée dans l'état. C'est le lien vers la file.
- `SM-08` : la règle héritée « Jamais de merge sans validation explicite de l'utilisateur » (`ship-pr:39`) contredit §4.2. Elle devient « Jamais de merge sans validation explicite de l'utilisateur en politique `gate`, ni sans les cinq conditions de SM-01 en `auto` ». La sous-chaîne testée par CA-06 de la Phase 1 est conservée.

### 6. Enchaînements — `CH` (Q4 du BACKLOG)

- `CH-01` : mécanisme. `K chain spawn --root R --skill <factory-run|ship-pr> --args-file F --parent-run <run> [--autonomy X]` lance un **processus enfant headless**, `claude -p "/<skill> <arguments>"`.
  - Options de l'enfant : `--output-format json`, `--max-turns <n>`, `--permission-mode acceptEdits`, `--allowedTools "<liste>"`, `--permission-prompts none` (BACKLOG §5 : AskUserQuestion retiré, donc replis headless définis).
  - Exécution :
    - argv en liste, jamais de shell ;
    - `cwd = R` ;
    - processus détaché, dans un nouveau groupe ;
    - sorties vers `.claude/runs/chain-<id>.out.json` et `.err.txt` ;
    - fiche `.claude/runs/chain-<id>.json` `{id, skill, args, pid, root, parent_run, started, status}`.
  - Suivi : `K chain status --id` et `K chain wait --id --max-seconds 540`, appelé en boucle par le skill, sous la limite de l'outil Bash. Le résultat se lit dans l'état du run de l'enfant (retrouvé par `chain_id`), dans ses STOP et dans son code de sortie.
  - Contraintes :
    - liste blanche = `chain.allowed_tools` du tampon (liste blanche CI de l'installation), plus `Bash(gh *)` et `Skill` quand ship-pr est enchaîné ;
    - `--max-turns` = `chain.max_turns` : défaut 100 pour factory-run seul, 200 avec ship-pr (Q28) ;
    - `claude` absent du PATH → arrêt `child` ;
    - au-delà de `chain.timeout_min` (défaut 120), arbre de processus tué, puis arrêt `child`.
  - Environnement : variables du parent, plus `HARNESS_CHAIN_ID` et `HARNESS_PARENT_RUN`, moins `CLAUDECODE` ([DOC] D1).
  - **Garde de coût** : si l'une de `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_USE_BEDROCK` ou `CLAUDE_CODE_USE_VERTEX` est non vide, arrêt `cost` et rien n'est lancé, sauf `chain.allow_api_billing: true` (Q29).
  - Pourquoi ce mécanisme : un `/factory-run` dans le prompt de `claude -p` est une invocation utilisateur, déjà utilisée par `ci/factory.*` et vérifiée par la recette R1. `disable-model-invocation` ne bloque que l'outil Skill. Le champ reste donc sur factory-run, et le contexte de chaque cycle est neuf.
- `CH-02` : factory-run → ship-pr. Après `success`, gate `factory-run.ship`.
  - Conditions :
    - `dirty_at_start` faux, relevé par `start` ;
    - cible résolue, dans cet ordre : `--ship <cible>`, puis `ship_pr.target` du tampon, puis `refs/remotes/origin/HEAD` (Q21) ;
    - profil `software` (Q30).
  - `K factory-run deliver --run <run>` :
    - si la branche courante est la cible ou si `HEAD` est détaché, crée `factory/<slug de la spec>` (suffixe `-<horodatage>` si elle existe) ;
    - `git add -A` (sûr, l'arbre était propre au départ), puis commit `feat(factory): <titre de la spec>` avec trailers, sans push.
  - Ensuite, outil Skill : `ship-pr <cible> --autonomy <effective> --spec <spec>`.
  - Une condition fausse → ni commit ni ship, raisons journalisées, commande suggérée.
  - La règle héritée « ne pas commiter à sa place » (`software-factory:63`) est modifiée : elle reste vraie hors livraison CH-02 (E-P4-3).
- `CH-03` : options de factory-run :
  - `--ship <cible>` ;
  - `--no-ship` ;
  - `--deliver-only` : commit sans ship, utilisé par FB ;
  - `--worktree` : WT-08 ;
  - `--chained-from <run>` et `--chain-id <id>` : internes, enregistrés dans l'état.
- `CH-04` : audit → file.
  - Après `audit.final`, la gate `audit.chain` invoque par l'outil Skill `factory-queue run --only "<spec1;spec2;…>" --autonomy <effective>`, dans l'ordre PZ.
  - `factory-queue` n'a pas `disable-model-invocation`.
  - AD-10 est inchangé : l'audit n'écrit que ses livrables, l'exécution a lieu dans des enfants.
- `CH-05` : brainstorm ne lance rien ; `brainstorm:101` est conservé.
- `CH-06` : événements de journal `chain` `{id, skill, args, parent_run, result}`.

### 7. Priorisation automatique des audits — `PZ`

- `PZ-01` : critère « fiabiliser d'abord ».
  - Jeu `legacy` : « risque d'abord ».
  - Jeu `vibecode` : « Gravité d'abord… », mineurs « Les détailler ».
  - Questions `research` : PZ-04.
- `PZ-02` : jalons calculés.
  - Jalon 1 = `critical`, jalon 2 = `major`, jalon 3 = `minor`.
  - Clôture des dépendances : un prérequis remonte au jalon le plus tôt de ses dépendants.
  - Les jalons vides sont retirés et renumérotés : le nombre de jalons est donc compris entre 1 et 3 (Q13).
  - Intitulés : « Critiques », « Majeurs », « Mineurs ».
- `PZ-03` : `audit.software.assignment` en `auto` : affectation par finding selon PZ-02, rien d'exclu. `--max-specs` s'applique ensuite, dans l'ordre des jalons.
- `PZ-04` : questions `research` : sévérité décroissante, puis coût croissant (TS-03). Un `critical` porte sur une conclusion-titre (`ai-lab-audit:66`), ce qui correspond à « fiabiliser ».
- `PZ-05` : `K audit prioritize --run <run>` rend jalons, rangs et `Priorité`. La décision est journalisée avec les valeurs calculées.

### 8. Upgrade automatique — `UA`

- `UA-01` : `/harness-doctor` en mode projet et en `auto` lance l'upgrade si et seulement si :
  - le plan (Phase 3) est non vide ;
  - chaque changement est de type `block`, `stamp`, ou `core` avec `unmodified: true` ;
  - `divergent_blocks` est vide.

  Il invoque alors par l'outil Skill le `--upgrade` du skill propriétaire (`software-factory`, `code-index`), avec `--autonomy auto`.
- `UA-02` : sinon, la commande est proposée et non lancée, et le journal liste les changements en cause. En `gate`, la gate `harness-doctor.upgrade` est posée.
- `UA-03` : `--scan` ne fait que proposer, une ligne par projet (Q20).
- `UA-04` : un second passage après upgrade donne un plan vide : aucune action.

### 9. `/factory-queue` — `FQ`

- `FQ-01` : nouveau skill global `skills/factory-queue/SKILL.md` : `name: factory-queue`, sans `context: fork`, sans `disable-model-invocation`. Arguments : `[run] [--only "a;b"] [--target T] [--autonomy X]`.
- `FQ-02` : sans argument, `K queue list` rend une ligne par spec de `specs/*.md` de l'arbre courant et des worktrees du registre : id, titre, statut, `approved`, dépendances (et celles non satisfaites), priorité, worktree, dernier run, `interrupted`.
- `FQ-03` : statuts dérivés (ROADMAP §4.4).

| Statut | Règle |
| --- | --- |
| mergée | `LIVREE` sur `origin/<cible>` (`git show`, après un `git fetch origin <cible>` ; un échec réseau donne un avertissement et utilise la référence locale) |
| livrée | `LIVREE` localement ou dans un worktree, non mergée |
| en cours | run `running` dont `updated_at` date de moins de 2 h, ou enfant de lot actif ; au-delà, `interrupted: true` |
| bloquée | `BLOQUEE` avec des questions sans réponse ; entièrement répondue → « proposée (réponses prêtes) » |
| proposée | `PROPOSEE`, ou `APPROUVEE` inactive (`approved: true`) |

- `FQ-04` : `Dépend de` est résolu par nom de fichier ou préfixe d'id. Une dépendance inconnue ou un cycle rend les specs concernées inéligibles, avec une erreur listée.
- `FQ-05` : ordre : tri topologique, puis `Priorité` croissante (absente = dernière), puis nom de fichier.
- `FQ-06` : `run`, en boucle sur `K queue next` :
  - spec éligible : proposée ou réponses prêtes, toutes ses dépendances mergées, pas en échec dans ce run de file ;
  - lancement d'un enfant `factory-run <spec> --ship <cible>` dans l'arbre courant (CH-01), puis attente ;
  - au retour, si l'arbre est propre : `git checkout <cible>` et `git pull --ff-only` ; s'il est sale → arrêt `gate` ;
  - STOP ou échec de l'enfant → arrêt `child`, sans relancer cette spec ;
  - PR laissée ouverte → on continue, et ses dépendants restent inéligibles ;
  - fin quand plus rien n'est éligible, avec un rapport des restes et de leurs raisons.
- `FQ-07` : un seul coordinateur par dépôt : verrou OS `<git-common-dir>/harness/coordinator.lock`, partagé avec FB. Un second → exit 1.
- `FQ-08` : préalables : factory installée, arbre propre, branche courante = cible ou basculable proprement. Sinon arrêt `gate`.
- `FQ-09` : `run` exige une politique effective `auto`. Sinon arrêt `gate` (« requires --autonomy auto »). Raison : les enfants ne peuvent pas poser de question, et ce dépôt est en `gate` (AP-08).
- `FQ-10` : journal `.claude/runs/factory-queue-<horodatage>.jsonl`.

### 10. Worktrees — `WT`

- `WT-01` : registre `<git-common-dir>/harness/worktrees.json`, hors versionnement et commun à tous les worktrees : `{path, branch, base, spec, created_by, batch_id, created_at, state}`. Écriture atomique sous verrou.
- `WT-02` : création.
  - Chemin : `<parent de la racine du worktree principal>/<nom du dépôt>.harness-wt/<slug>`.
  - Branche `factory/<slug>` depuis `origin/<cible>`, après `git fetch origin <cible>`.
  - Un chemin ou une branche existants ne sont jamais réutilisés (suffixe d'horodatage).
  - Commande : `git worktree add -b`.
- `WT-03` : toute opération (commit, rebase, collecte, suppression) exige que le chemin soit au registre **et** listé par `git worktree list --porcelain` avec la branche enregistrée. Sinon exit 1 et rien n'est fait.
- `WT-04` : jamais :
  - `git worktree prune` ;
  - `git worktree remove --force` ;
  - `move`, `lock` ou `unlock` d'un worktree ;
  - une commande dans un worktree non enregistré.

  Le harnais ne touche jamais au worktree principal ni à ceux de l'utilisateur (i3, Orca), hors l'arbre depuis lequel l'utilisateur a lancé `/factory-queue run`.
- `WT-05` : transfert de la spec. Si `git show origin/<cible>:<spec>` diffère de la copie de l'arbre lanceur, ou n'existe pas :
  - la spec est copiée dans le worktree, au même chemin relatif ;
  - l'original est déplacé dans `.claude/runs/handoff/<horodatage>-<nom>` ;
  - le transfert est journalisé.

  Sans ce déplacement, le `git pull` après merge échouerait sur un fichier non suivi de même chemin.
- `WT-06` : collecte avant suppression.
  - `<wt>/.claude/runs/*` est copié vers `<principal>/.claude/runs/wt-<slug>/`.
  - `<wt>/.claude/findings.jsonl` est publié dans celui de l'arbre principal (RG-03, idempotent).
- `WT-07` : nettoyage après merge : collecte, puis `git worktree remove <path>` (non forcé ; s'il est sale, il est conservé et signalé), puis suppression de la branche locale du harnais, puis retrait du registre. Sans merge, le worktree est conservé et le rapport donne son chemin et la commande de reprise.
- `WT-08` : `/factory-run --worktree [--ship <cible>]`.
  - Un besoin passe d'abord par la phase Plan dans la session appelante.
  - Puis WT-02, WT-05, un enfant `factory-run <spec> --ship <cible>` avec `cwd = <wt>`, l'attente, le rapport, et WT-07 si la PR est mergée.
- `WT-09` : si `.claude/harness/` ou `.claude/settings.json` sont absents de `origin/<cible>`, arrêt `gate` : « commit the harness files first ». Un worktree sans eux n'aurait ni noyau ni hooks.
- `WT-10` : section README « Coexistence avec vos worktrees » : WT-03, WT-04, emplacement des worktrees, et `git worktree list` comme seul moyen de voir les siens.

### 11. `/factory-batch` — `FB`

- `FB-01` : nouveau skill global `skills/factory-batch/SKILL.md` : `name: factory-batch`, `disable-model-invocation: true` (aucun skill ne l'enchaîne). Arguments : `<glob…> [--parallel N] [--target T] [--autonomy X] [--resume <id>]`.
- `FB-02` : les globs sont développés par le noyau, puis triés. Éligibilité selon FQ. Les specs non éligibles sont rapportées.
- `FB-03` : `--parallel` : défaut 2, `min(N, 4)`. Une valeur non entière ou inférieure à 1 → exit 2 (D8).
- `FB-04` : N emplacements, chacun : WT-02, WT-05, puis un enfant `factory-run <spec> --deliver-only`. Une spec dont une dépendance est dans le lot devient éligible quand cette dépendance est mergée (FQ-04).
- `FB-05` : file de ship : **un seul ship à la fois**, dans l'ordre FQ-05 des specs livrées.
  - Avant chaque ship : `git fetch`, puis rebase de la branche locale, jamais poussée, sur `origin/<cible>`.
  - Conflit trivial (Q11) : résolu, puis réindexation.
  - Conflit non trivial : `git rebase --abort`, plus aucun lancement d'enfant, attente des enfants en cours, puis arrêt `conflict`.
  - Ship : enfant `ship-pr <cible> --spec <spec>` avec `cwd = <wt>`.
  - PR mergée → WT-07 ; PR laissée ouverte → worktree conservé, on passe à la suivante.
- `FB-06` : état `.claude/runs/factory-batch-<horodatage>.state.json` ; `--resume <id>` reprend.
- `FB-07` : FQ-07 et FQ-09 s'appliquent.
- `FB-08` : journal `factory-batch-*.jsonl`.

### 12. Hooks : infrastructure — `HK`

- `HK-01` : `skills/_core/hooks/hook.py`, stdlib, compatible 3.9, copié par `copy-core` sous `.claude/harness/hooks/`. Sous-commandes `pre-edit`, `pre-bash` et `post-edit`, avec l'entrée JSON du hook sur stdin.
- `HK-02` : `K hooks install --root R --py "<PY>"` fusionne la clé `hooks` de `.claude/settings.json`.
  - Entrées :
    - `PreToolUse`, `Edit|Write|MultiEdit|NotebookEdit` → `pre-edit`, timeout 10 s ;
    - `PreToolUse`, `Bash|PowerShell` → `pre-bash`, timeout 10 s ;
    - `PostToolUse`, `Edit|Write|MultiEdit` → `post-edit`, timeout 60 s, seulement si HL-01 est configuré.
  - Une entrée appartient au harnais si sa commande contient `.claude/harness/hooks/hook.py` : pas de blocs dans un JSON (I1 de la Phase 2).
  - Sémantique FU-01 : absente → ajoutée ; identique → `identique` ; différente → `personnalisé-conservé`. Les hooks de l'utilisateur sont intacts, le JSONC est conservé, la commande est idempotente.
- `HK-03` : la commande utilise `$CLAUDE_PROJECT_DIR` (documenté) et l'interpréteur détecté. Elle ne rend **jamais** exit 2 hors blocage voulu, même si le script ou l'interpréteur manquent : Python rend 2 sur un fichier introuvable, ce qui bloquerait tout outil.
- `HK-04` : une erreur interne fait toujours trois choses, sans jamais bloquer :
  - exit 0 ;
  - sur stdout, `{"systemMessage": "harness hook <nom>: internal error (<type>); action allowed"}` ;
  - une ligne `{ts, hook, tool, error}` dans `.claude/runs/hook-errors.jsonl`.

  Cas couverts : stdin invalide, marqueur illisible, échec de git, dépassement de 5 s de budget interne, exception quelconque. Jamais de traceback bloquant.
- `HK-05` : activation contextuelle (ROADMAP §5, mécanisme proposé).
  - `K activate --skill <factory-run|lab-run|ship-pr> --run <run> --session "${CLAUDE_SESSION_ID}"` écrit `.claude/runs/active/<session_id>.json`, en pile. Le contexte au sommet de la pile s'applique.
  - `K deactivate` le retire en fin de cycle : succès, échec ou arrêt.
  - Le hook lit `session_id` sur stdin. Pas de marqueur pour cette session → les hooks contextuels laissent passer.
  - Un marqueur est périmé si son run n'est plus `running` ou s'il date de plus de 12 h : il est ignoré, puis retiré au prochain `activate`.
  - Si la substitution n'a pas eu lieu (littéral `${`), repli sur `active/project.json`, avec un avertissement (Q17).
  - Justification :
    - une variable d'environnement est impossible en session interactive (I1) ;
    - un fichier est lisible par les hooks des sous-agents ;
    - le marqueur par session ne bloque pas les éditions manuelles de l'utilisateur dans une autre session ;
    - le marqueur est sous `.claude/runs/`, hors git.
- `HK-06` : `software-factory` installe les hooks (étape de fusion des settings), et `--upgrade` les régénère. La configuration du linter vit dans `harness.json`, clé `hooks.lint`.
- `HK-07` : chemins normalisés : séparateurs `\` et `/`, casse ignorée sous Windows, `..` résolus, relatifs à la racine du contexte.

### 13. Garde Bash permanente — `HG`

- `HG-01` : toujours active, quels que soient la politique, le contexte ou le sous-agent (« le filet sous la boucle »).
- `HG-02` : catégories bloquées :
  1. force-push : `-f`, `--force`, `--force-with-lease`, `--force-if-includes`, `--mirror`, refspec `+…` ;
  2. suppression de branche distante (`--delete`, `-d`, refspec `:b`) ou locale (`git branch -d|-D|--delete`). Celle de la PR mergée est faite par le noyau, hors outil Bash ;
  3. réécriture d'historique :
     - `git rebase`, `commit --amend` ;
     - `reset` avec `--hard`, `--keep`, `--merge`, ou vers un commit autre que `HEAD` ;
     - `filter-branch`, `filter-repo`, `replace`, `update-ref -d`, `reflog expire`, `gc --prune` ;
  4. destruction de travail :
     - `git clean -f…`, `checkout -- <chemins>` ou `checkout .` ;
     - `restore` sans `--staged` seul ;
     - `stash drop` ou `stash clear` ;
     - `worktree remove` ou `worktree prune` ;
  5. suppression de fichiers : `rm`, `rmdir`, `unlink`, `del`, `erase`, `rd`, `Remove-Item` ou `ri`, `find … -delete`, `find … -exec rm`, `xargs rm`, `git rm` sans `--cached`. La suppression n'est admise que si **chaque** cible est générée :
     - sous un dossier d'artefacts (`STACK_DENY`, `factory-logs/`, `lab-logs/`, `experiments/results/`, `.claude/runs/`, `__pycache__/`) ;
     - ou créée pendant le cycle actif (non suivie et absente de l'instantané de `start`) ;
     - ou dans le `Périmètre fichiers` de la spec active.

     Une cible qu'on ne peut pas résoudre (variable, glob ambigu) → bloquée.
- `HG-03` : analyse de la commande.
  - Découpage sur `;`, `&&`, `||`, `|`, `&` et les retours à la ligne.
  - Récursion dans `$( )`, les backticks, `bash -c`, `sh -c`, `env`, `sudo`, `command` et `xargs`.
  - Jetons par `shlex`. Options `git -C` et `-c` sautées. Syntaxe PowerShell pour l'outil `PowerShell`.
  - Commande impossible à analyser → HK-04 (laisse passer et signale).
- `HG-04` : blocage : exit 2, avec sur stderr `Blocked by harness guard: <category> (<fragment>). Destructive operations outside the accepted scope are never run by an agent; run it yourself in a terminal if intended.`
- `HG-05` : avec un contexte actif, un blocage écrit aussi un arrêt `destructive`, et SX-06 arrête le cycle. Sans contexte actif, il bloque seulement.

### 14. Hooks de périmètre et dérive — `HP`, `HD`, `HR`

- `HP-01` : actif quand le sommet du marqueur est `factory-run` ou `lab-run`, depuis la phase Build, et que la spec déclare `Périmètre fichiers`. Sans ce champ, tout passe (§5 : « si elle en déclare un »).
- `HP-02` : sont admis :
  - un chemin qui correspond à un glob du périmètre ;
  - `.claude/runs/**` ;
  - la spec active ;
  - un chemin hors de la racine (hors contenu du projet).
- `HP-03` : blocage : exit 2, avec `Blocked: <chemin> is outside the scope declared by <spec> (Périmètre fichiers: <globs>). Stay within the spec; if the spec is wrong, stop and report it.` Le compteur de dérives augmente.
- `HD-01` : actif quand le sommet du marqueur est `ship-pr`.
  - Admis : `git diff --name-only origin/<cible>...HEAD`, calculé à l'appel, et `.claude/runs/**`.
  - Blocage : exit 2, avec `Blocked: scope limited to the PR diff — <chemin> is not in git diff --name-only origin/<cible>...HEAD.` Le compteur de dérives augmente.
  - Le message est en anglais : ce sont des textes publiés (BACKLOG §5, qui prime).
- `HD-02` : un échec de git → HK-04.
- `HR-01` : dérives comptées par run, sous verrou, et journalisées (événement `drift`).
  - Première dérive : blocage seul ; l'agent reçoit le message et poursuit.
  - Deuxième dérive : blocage, arrêt `drift`, ajout de `"continue": false` ([DOC] D4), et message « second scope drift in this cycle: cycle stopped (see <STOP>) ».
- `HR-02` : `factory-run record` et toute commande `ship-pr` du run rendent exit 1 après un arrêt `drift` (SX-06), quelle que soit la façon dont l'outil traite `continue`.

### 15. Hook linter — `HL`

- `HL-01` : `harness.json`, clé `hooks.lint` : `[{glob, argv (avec {file}), timeout_s}]`. Seules y figurent les commandes de lint réellement configurées dans le projet, détectées en Phase 1 de software-factory, en mode vérification (Q18).
- `HL-02` : `post-edit` exécute les entrées qui correspondent au fichier édité.
  - Résumé : code de sortie, 20 premières lignes, 2000 caractères au plus, rendu dans `hookSpecificOutput.additionalContext` ([DOC] D4).
  - Jamais exit 2. Un linter absent ou en dépassement de délai est mentionné dans le résumé, avec exit 0.
- `HL-03` : toujours actif, non bloquant. Sans configuration : exit 0 immédiat.

### 16. Écarts de comportement assumés

| Écart | Contenu |
| --- | --- |
| E-P4-1 | `autonomy: "auto"` écrit à l'installation (AP-05) |
| E-P4-2 | ligne `Statut : LIVREE` écrite au succès, y compris en `gate` (BQ-09) |
| E-P4-3 | commits de livraison par factory-run (CH-02) |
| E-P4-4 | merge sans question en `auto` (SM) |
| E-P4-5 | commentaires de PR de décision de merge |
| E-P4-6 | hooks dans `settings.json`, garde Bash active aussi dans les sessions manuelles et chez les coéquipiers |
| E-P4-7 | fichiers `STOP-*.md` |
| E-P4-8 | GT-03 et `phase2_auto` retirés, assertions de tests correspondantes modifiées |
| E-P4-9 | phrase de `ship-pr:39` modifiée (SM-08) |
| E-P4-10 | plan headless possible en `auto` |
| E-P4-11 | champs d'en-tête et classification des questions dans les specs |
| E-P4-12 | un chemin vers une spec `PROPOSEE` passe en `approve`, et non plus en `plan` |

### 17. Découpage en lots (chacun passe `T` seul)

| Lot | Contenu | CA | Dépend de |
| --- | --- | --- | --- |
| L0 | Merge des Phases 1 à 3, `BASE4` relevé ; contrat Phase 3 aligné (Q25) ; recettes R12 à R16 | — | — |
| L1 | AP-01 à AP-10, SX-01 à SX-07, journal (`autonomy`, `stop`, `chain`, `merge_decision`, `drift`, `blocked`), noms `factory-queue` et `factory-batch` | 01-08, 12, 37 | L0 |
| L2 | BQ-01 à BQ-11 : `specfile.py`, entrée étendue, fragments du Planner et du Director, FD-08 | 09-11 | L1 |
| L3 | SM-01 à SM-08 : `automerge.py`, ghflow, SKILL.md de ship-pr | 13-15 | L1 |
| L4 | CH-01 à CH-06 : `chain.py`, `deliver`, `fake_claude.py`, gabarit factory-run | 16, 17 | L2, L3 |
| L5 | PZ-01 à PZ-05, CH-04 : audit | 18, 19 | L2, L4 |
| L6 | UA-01 à UA-04 : doctor | 20 | L1 |
| L7 | FQ-01 à FQ-10 | 21, 22 | L4 |
| L8 | WT-01 à WT-10 | 23, 25 | L4 |
| L9 | FB-01 à FB-08 | 24 | L7, L8 |
| L10 | HK-01 à HK-07, HG-01 à HG-05 | 26-29, 34, 36 | L1 |
| L11 | HP, HD, HR, HL | 30-33, 35 | L2, L10 |
| L12 | README, `tests/fixtures/README.md`, BACKLOG (Q4, Q5 et gel tranchés), `.claude/harness.json` de ce dépôt (AP-08), hooks de ce dépôt, `.claude/harness/` rafraîchi, passage complet des CA | 01-43 | tous |

### 18. Fichiers

**Créés**
- `skills/_core/hcore/` : `specfile.py`, `stops.py`, `automerge.py`, `chain.py`, `prioritize.py`, `autoupgrade.py`, `queue.py`, `worktrees.py`, `batch.py`, `hooks_install.py`, `guard.py`, `scope.py`
- `skills/_core/hooks/hook.py`
- `skills/_core/templates/stop.md`
- `skills/factory-queue/SKILL.md`, `skills/factory-batch/SKILL.md`
- `skills/_core/tests/` : `test_autonomy.py`, `test_specfile.py`, `test_stops.py`, `test_automerge.py`, `test_chain.py`, `test_prioritize.py`, `test_autoupgrade.py`, `test_queue.py`, `test_worktrees.py`, `test_batch.py`, `test_hooks_install.py`, `test_hook_guard.py`, `test_hook_scope.py`, `test_hook_lint.py`, `test_hook_errors.py`, `fake_claude.py`
- `.claude/harness.json` de ce dépôt

**Modifiés**
- Noyau :
  - `skills/_core/hcore/` : `gates.py`, `journal.py`, `factory.py`/`loop.py`, `ghflow.py`, `shippr.py`, `findings.py`, `audit.py`, `profiles.py`, `stamp.py`, `__init__.py` (`CORE_VERSION`) ;
  - `skills/_core/harness.py`.
- Profils : `skills/_core/profiles/{software,research}/` (`profile.json` : `status_blocked`, `status_delivered`, gates ; `orchestrator.md` ; `roles/factory-planner.md` ; `roles/lab-director.md`).
- Skills : `skills/software-factory/SKILL.md`, `skills/ship-pr/SKILL.md`, `skills/audit/SKILL.md`, les trois alias d'audit, `skills/code-index/SKILL.md` (`--autonomy`), `skills/harness-doctor/SKILL.md`.
- Documentation et usine du dépôt : `README.md`, `tests/fixtures/README.md`, `specs/harness-v2/BACKLOG.md`, `.claude/settings.json`, `.claude/harness/`.

**Inchangés** (CA-40) : `install_skills.sh`, `install_skills.ps1`, `skills/brainstorm/`, `ci/factory.*` des projets (gabarit inchangé).

### 19. Fixtures (`tests/fixtures/`, sans nom pointé, sans `CLAUDE.md`)

- `autonomy/` : `harness-gate.json`, `harness-auto.json`, `harness-absent-key.json`, `harness-invalid.json`.
- `specs-p4/` :
  - `SPEC-proposee.md`, `SPEC-bloquee-sans-reponse.md`, `SPEC-bloquee-repondue.md` ;
  - `SPEC-livree.md`, `SPEC-perimetre.md` ;
  - `SPEC-dep-a.md`, `SPEC-dep-b.md` (dépend de a), `SPEC-cycle-x.md` et `SPEC-cycle-y.md` ;
  - `SPEC-mal-formee/` : un cas par erreur de BQ-03.
- `stop-expected/` : un `STOP-*.md` attendu par type, à date fixée.
- `automerge/<scénario>.json` : réponses simulées de `gh` pour chaque condition vraie ou fausse (checks pass, fail, pending, absents ; threads ; `protected` ; `mergeable` CONFLICTING ou UNKNOWN ; erreur d'API).
- `bash-guard/commands.json` : au moins 60 commandes Bash et PowerShell, avec le résultat attendu (`allow` ou `deny`) et la catégorie.
- `hooks/` :
  - entrées stdin `pre-edit-*.json`, `pre-bash-*.json`, `post-edit-*.json` ;
  - `settings-input.json` (hooks de l'utilisateur, JSONC) et `settings-expected.json`.
- `upgrade-plans/` : `blocks-only.json`, `stamp-and-core.json`, `outside.json`, `divergent.json`, `migration.json`, `empty.json`.
- `prioritization/` : jeux de findings, et jalons et rangs attendus.
- Créés par les tests en dossier temporaire : dépôts git avec remote bare local, worktrees et branches.

## Critères d'acceptation

Notations :
- `<PY>` = l'interpréteur détecté ;
- `T` = `cd skills/_core/tests && <PY> -B -m unittest discover -s . -t .` ;
- `K` = `<PY> skills/_core/harness.py` ;
- `H` = `<PY> skills/_core/hooks/hook.py` ;
- `S` = `specs/SPEC-phase4-5-autonomie-hooks.md`.

Recherches par `grep`. Dossiers temporaires créés par les tests. Exécutables simulés (`gh`, `git` si besoin, `claude`) en `HCORE_TEST_MODE=1` seulement (`proc.py:37-54`).

**Socle**
- [ ] **CA-01 — Tests verts.** `T` → exit 0.
- [ ] **CA-02 — Stdlib seule, Python 3.9.** `cd skills/_core/tests && <PY> -B -I -S -m unittest discover -s . -t .` → exit 0, avec `<PY> --version` en 3.9.x.
- [ ] **CA-03 — Chaque règle est testée.** `for id in $(grep -oE '\b(AP|SX|BQ|SM|CH|PZ|UA|FQ|WT|FB|HK|HG|HP|HD|HR|HL)-[0-9]{2}\b' S | sort -u); do grep -rlq "$id" skills/_core/tests || echo "$id"; done` → aucune sortie.

**Politique d'autonomie et catalogue**
- [ ] **CA-04 — Table AP-01.** `test_autonomy` couvre :
  - `gate` × a, b et c → `ask` ;
  - `auto` × b et c → `default` ;
  - `auto` × b sans défaut → exit 1 et arrêt `gate` ;
  - `auto` × a avec `stop_when` vrai → arrêt ;
  - `auto` × a avec `stop_when` faux → `default` ;
  - dialogue → `ask` ;
  - aucune décision `auto` ne produit `ask` hors dialogue ;
  - `grep -rn "phase2_auto" skills/_core` → aucune sortie.
- [ ] **CA-05 — Override.** `K gate decide --id factory-run.approval --autonomy auto` dans un projet temporaire dont le tampon vaut `gate` → `default`, et le tampon est identique (`cmp`). `--autonomy maybe` → exit 2. L'événement `autonomy` porte `source: flag`.
- [ ] **CA-06 — Défaut installé.** Rejeu de l'installation `software` :
  - tampon absent → `"autonomy": "auto"` ;
  - tampon `{"autonomy": "gate"}` → valeur conservée, fichier identique (`cmp`) ;
  - `--autonomy gate` sur un tampon sans la clé → `gate`.
- [ ] **CA-07 — Catalogue.** `K gate list` :
  - chaque gate porte `kind` et `justification` non vide ;
  - chaque gate (a) porte `stop_when` ;
  - les ids `factory-run.ship`, `audit.chain` et `harness-doctor.upgrade` sont présents ;
  - pour chaque gate, `grep -rF "<id>"` trouve son skill ou son fragment de profil, et `grep -F "<justification>"` y trouve la justification (AP-09).
- [ ] **CA-08 — Ce dépôt reste en `gate`.** `<PY> -c "import json;print(json.load(open('.claude/harness.json'))['autonomy'])"` → `gate`.

**Spec BLOQUEE, statuts, arrêts**
- [ ] **CA-09 — BLOQUEE.**
  - `K spec check` sur `SPEC-bloquee-sans-reponse.md` → `unanswered` non vide.
  - `K factory-run start` sur cette spec → exit 1, un `STOP-*.md` de type `blocked` qui liste les questions, et un événement `blocked`.
  - Sur `SPEC-bloquee-repondue.md` → `mode: approve`.
  - Chaque cas de `SPEC-mal-formee/` → exit 2.
- [ ] **CA-10 — Entrée étendue.**
  - `PROPOSEE` → `approve` ; `APPROUVEE` → `build` ; texte libre → `plan` ; `LIVREE` → exit 1.
  - `K spec set-status` `PROPOSEE` → `APPROUVEE` : `diff` entre avant et après = une seule ligne.
  - `LIVREE` → `PROPOSEE` → exit 2.
- [ ] **CA-11 — LIVREE et défauts.**
  - Rejeu factory-run jusqu'à `success` → la spec porte `Statut : LIVREE`.
  - Rejeu `auto` avec deux questions non bloquantes → deux lignes `Réponse : … (défaut appliqué automatiquement)` et un seul événement `factory-run.questions`.
- [ ] **CA-12 — Fichier STOP.** Pour chaque type de SX-01, le fichier produit :
  - est égal à `stop-expected/<type>.md` (date fixée) ;
  - compte 40 lignes au plus ;
  - porte dans l'ordre `## Where`, `## Why`, `## To resume`, `## Command` ;
  - a un bloc de commande non vide.

  En plus : stderr contient `STOP-` ; le journal porte `stop` ; une commande suivante sur le run → exit 1 (SX-06).

**Merge automatique**
- [ ] **CA-13 — Cinq conditions.** Pour chaque scénario `automerge/` :
  - `K ship-pr merge --auto` rend les cinq conditions, avec `ok` et `detail` ;
  - le merge n'a lieu (`gh pr merge` présent dans le journal de `fake_gh`) que dans le scénario tout vrai ;
  - un `gh pr comment … --body-file` est posté dans chaque cas, et une relance ne le reposte pas ;
  - l'événement `merge_decision` porte `merged` et les cinq booleens ;
  - aucune question n'est posée.
- [ ] **CA-14 — Gate et SP-05 conservés.**
  - En `gate`, la décision est `ask`.
  - Un thème non couvert en `auto` → pas de merge, commentaire et journal, exit 0.
  - `grep -F "Jamais de merge sans validation explicite" skills/ship-pr/SKILL.md` ≥ 1.
- [ ] **CA-15 — Merge en worktree.** Dans un worktree enregistré (dépôt temporaire, remote bare) : aucun `git checkout <cible>` ni `git pull` dans le journal des commandes, la branche distante est supprimée, la branche locale et le worktree relèvent de WT-07.

**Enchaînements**
- [ ] **CA-16 — Lancement d'un enfant.** Avec `fake_claude` :
  - l'argv contient `-p`, `/factory-run`, `--permission-prompts none`, `--max-turns 100`, `--permission-mode acceptEdits`, et aucun shell (liste) ;
  - l'environnement de l'enfant n'a pas `CLAUDECODE` et porte `HARNESS_CHAIN_ID` ;
  - avec `ANTHROPIC_API_KEY=x`, exit 1, arrêt `cost`, aucun processus lancé ;
  - avec `chain.allow_api_billing: true`, l'enfant est lancé ;
  - timeout simulé → arrêt `child`.
- [ ] **CA-17 — Livraison.**
  - Arbre propre au départ, sur `main` → branche `factory/<slug>`, et le message de commit vérifie `^feat\(factory\): .+` puis les trailers.
  - Arbre sale au départ → aucun commit, raison au journal.
  - `grep -c "disable-model-invocation: true"` dans le gabarit de factory-run → 1.
  - `grep -F "Ne jamais lancer cette commande" skills/brainstorm/SKILL.md` ≥ 1.
- [ ] **CA-18 — Priorisation.**
  - Chaque jeu `prioritization/` donne les jalons et rangs attendus.
  - Un `minor` prérequis d'un `critical` passe au jalon 1.
  - Des findings tous `major` donnent un seul jalon.
- [ ] **CA-19 — Audit → file.** Le rejeu de `/audit` en `auto` sur `profile-software` écrit des specs portant `Questions bloquantes : aucune` et `Priorité :`. `K audit chain-plan` rend la liste ordonnée attendue, et l'événement `audit.chain` est `default`.

**Upgrade automatique**
- [ ] **CA-20 — Upgrade.** `K doctor auto-upgrade --plan <f>` :
  - `blocks-only` et `stamp-and-core` → `apply` ;
  - `outside`, `divergent` et `migration` → `propose`, avec les changements en cause ;
  - `empty` → `none` ;
  - en `gate` → `ask`.

**File, worktrees et lots**
- [ ] **CA-21 — Statuts de la file.** Dépôt temporaire avec remote bare : une spec par statut de FQ-03, dont une `mergée` (`LIVREE` poussée sur `origin/main`), une `livrée` locale et une `en cours` périmée (`interrupted: true`). `K queue list` rend les statuts attendus. Le cycle x/y et la dépendance inconnue sont listés en erreur.
- [ ] **CA-22 — `queue run`.** Avec `fake_claude` :
  - ordre topologique puis par priorité ;
  - b attend a mergée ;
  - un enfant en échec → arrêt `child`, et aucun second lancement pour cette spec ;
  - PR laissée ouverte → la file continue ;
  - politique `gate` → exit 1 ;
  - deux coordinateurs → le second rend exit 1.
- [ ] **CA-23 — Worktrees de l'utilisateur intacts.**
  - Un worktree créé par le test hors registre : `K worktree remove --path <lui>` → exit 1, et `git worktree list --porcelain` est identique avant et après.
  - Le journal des commandes ne contient jamais `worktree prune` ni `remove --force`.
  - Un chemin existant n'est pas réutilisé.
- [ ] **CA-24 — Lot.**
  - `--parallel 0` et `--parallel x` → exit 2 ; `--parallel 9` → 4.
  - Au plus N enfants de build simultanés (horodatages de `fake_claude`).
  - Aucun chevauchement entre deux enfants `ship-pr`.
  - Rebase avant chaque ship ; conflit non trivial → `rebase --abort` et arrêt `conflict`.
  - Les journaux des worktrees sont copiés sous `.claude/runs/wt-<slug>/` avant suppression.
- [ ] **CA-25 — `--worktree`.**
  - Spec non suivie → copiée dans le worktree, et original sous `.claude/runs/handoff/`.
  - Après merge simulé, le worktree et la branche locale sont supprimés, et le registre est vide.
  - Base sans `.claude/harness/` → arrêt `gate`.

**Hooks**
- [ ] **CA-26 — Fusion de `settings.json`.** `K hooks install` sur `settings-input.json` :
  - résultat égal à `settings-expected.json` (JSON parsé, ordre des clés compris) ;
  - hooks de l'utilisateur conservés, commentaires JSONC conservés ;
  - seconde application identique octet pour octet ;
  - entrée du harnais modifiée par l'utilisateur → `personnalisé-conservé`.
- [ ] **CA-27 — Jamais exit 2 par accident.** Les commandes générées, exécutées par `bash -c` avec `CLAUDE_PROJECT_DIR` vers un dossier sans `.claude/harness/` et une entrée stdin valide → code ≠ 2. Même résultat avec un interpréteur introuvable.
- [ ] **CA-28 — Garde Bash.** Pour chaque entrée de `bash-guard/commands.json`, `H pre-bash` sur l'entrée stdin construite :
  - `deny` → exit 2, avec la catégorie dans stderr ;
  - `allow` → exit 0.
  - La table couvre les catégories 1 à 5, les commandes composées, `$( )`, `bash -c`, PowerShell, `git -C`, et les suppressions admises (artefacts, fichiers créés dans le cycle, périmètre).
- [ ] **CA-29 — Garde permanente.** Sans aucun marqueur, `git push --force` → exit 2. Avec un marqueur actif → exit 2 et un arrêt `destructive`.
- [ ] **CA-30 — Périmètre factory-run.**
  - Marqueur avec `SPEC-perimetre.md` : fichier dans le périmètre → exit 0 ; hors périmètre → exit 2, avec le message HP-03.
  - Sont admis : `.claude/runs/x.md`, la spec active, un chemin hors de la racine, les variantes Windows de `\`.
  - Spec sans champ → exit 0. Aucun marqueur → exit 0.
- [ ] **CA-31 — Diff de ship-pr.** Dépôt temporaire avec une PR simulée : un fichier du diff → exit 0 ; un fichier hors diff → exit 2, et stderr contient `scope limited to the PR diff`.
- [ ] **CA-32 — Contexte par session.**
  - Un marqueur d'un autre `session_id` ne s'applique pas.
  - Un marqueur de plus de 12 h, ou dont le run n'est pas `running`, est ignoré.
  - Pile ship-pr sur factory-run : c'est HD qui s'applique.
  - Littéral `${CLAUDE_SESSION_ID}` → repli sur `project.json`, avec un avertissement.
- [ ] **CA-33 — Seconde dérive.**
  - 1re dérive → exit 2, pas de STOP.
  - 2e dérive dans le même run → exit 2, arrêt `drift`, et la sortie contient `"continue": false`.
  - `K factory-run record` suivant → exit 1.
  - Un nouveau run repart à zéro.
- [ ] **CA-34 — Erreur interne.** Les cas suivants rendent exit 0, un `systemMessage` sur stdout et une ligne ajoutée à `.claude/runs/hook-errors.jsonl`, pour `pre-edit`, `pre-bash` et `post-edit` :
  - stdin non JSON ;
  - marqueur corrompu ;
  - git absent ;
  - échec injecté (`HCORE_TEST_MODE=1 HCORE_HOOK_FAIL=1`).
- [ ] **CA-35 — Linter.**
  - Linter simulé en échec → exit 0, et `additionalContext` de 2000 caractères au plus.
  - Linter en dépassement de délai → exit 0, avec la mention.
  - Sans `hooks.lint` → exit 0, sortie vide.
- [ ] **CA-36 — Portabilité.** `grep -rnE "^\s*(import|from)\s+(?!\.|__future__)" skills/_core/hooks/hook.py` ne cite que des modules de la stdlib (liste figée dans le test). Les tests de chemins passent avec des entrées Windows (`C:\…`) et POSIX.

**Journal, skills, documentation, propreté**
- [ ] **CA-37 — Journal.** `K journal validate` → exit 0 sur tous les journaux des rejeux, avec les nouveaux événements. Les noms acceptent `factory-queue` et `factory-batch`. Un événement `stop` sans `path` → exit ≠ 0.
- [ ] **CA-38 — Frontmatter.**
  - `skills/factory-queue/SKILL.md` : `---`, `name: factory-queue`, `description:` non vide, `grep -c "disable-model-invocation"` = 0, `grep -c "context: fork"` = 0.
  - `skills/factory-batch/SKILL.md` : `name: factory-batch`, `disable-model-invocation: true`.
  - La ligne 2 des skills de `BASE4` est inchangée.
- [ ] **CA-39 — README.** `grep -F` trouve chacun des textes suivants : `## Politique d'autonomie`, `### \`factory-queue\``, `### \`factory-batch\``, `--worktree`, `Coexistence avec vos worktrees`, `## Hooks`, `STOP-`, `--autonomy`.
- [ ] **CA-40 — Fichiers hors périmètre intacts.** `git diff --exit-code <BASE4> -- install_skills.sh install_skills.ps1 skills/brainstorm` → exit 0.
- [ ] **CA-41 — Aucun artefact parasite.** `git status --porcelain` ne liste ni `__pycache__`, ni `.pyc`, ni journal, ni `STOP-*`, ni `chain-*`, ni `hook-errors.jsonl`, ni `active/`, ni fichier de transit.
- [ ] **CA-42 — Fixtures inertes.** CA-30 de la Phase 2 passe toujours.
- [ ] **CA-43 — Copie du noyau.** `diff -r -x __pycache__ skills/_core .claude/harness` est vide dans ce dépôt, `hooks/` compris.

**Recettes par l'utilisateur, hors portes du Verifier**
- **R12** : depuis une session interactive puis depuis un `claude -p`, l'outil Bash lance `K chain spawn` d'un `/probe`. Points à vérifier :
  - l'enfant tourne (`CLAUDECODE` retiré) ;
  - `--permission-prompts none` est accepté ;
  - l'outil Skill est autorisé par `--allowedTools` ;
  - la facturation reste celle de l'abonnement.
- **R13** : `${CLAUDE_SESSION_ID}` est substitué dans un SKILL.md, et `session_id` sur stdin d'un hook est égal pour la session et pour ses sous-agents.
- **R14** : sous Windows, identifier le shell qui exécute les commandes de hook et le nom de l'outil PowerShell ; CA-27 doit passer en réel.
- **R15** : vérifier que `additionalContext` de `PostToolUse` atteint le modèle, que `systemMessage` est visible, et l'effet de `continue: false` dans un sous-agent.
- **R16** : hooks ajoutés au `settings.json` en cours de session : actifs seulement après redémarrage ou après revue dans `/hooks`.
- **R17** : `/factory-queue run` réel sur `toy-project` avec deux specs dépendantes : deux PR mergées dans l'ordre, sur un dépôt GitHub jetable.
- **R18** : `/factory-batch` réel avec `--parallel 2` et un conflit provoqué : arrêt `conflict`, worktree conservé, worktree i3/Orca de l'utilisateur intact.

## Hors-périmètre

- Phase 6 : `ci/fixtures/` et `ci/test-harness.*`. Phase 7 : packaging.
- La file et les lots sur les protocoles `experiments/EXP-*.md` : seules les specs `specs/*.md` sont traitées.
- L'enchaînement ship-pr des cycles `research` (Q30).
- Le merge automatique natif de GitHub (`gh pr merge --auto`), plusieurs ships simultanés, une file inter-dépôts.
- La détection de secrets dans le contenu, et la lecture (`Read`) de fichiers sensibles, sauf Q15.
- Le retrait d'un profil, le retrait des alias d'audit, tout nouveau profil.
- La modification de `install_skills.*` et de `brainstorm`.
- La règle « code en anglais » dans les gabarits d'agents (BACKLOG §5).
- Tout commit, push, `/ship-pr`, `/factory-queue run` ou `/factory-batch` par le Builder sur ce dépôt.

## Risques

- **[IMPOSSIBLE] I1 — Variable d'environnement en session interactive.** Un skill ne peut pas modifier l'environnement du processus `claude`, ni donc celui de ses hooks. D'où le marqueur fichier (HK-05). Une variable n'est utilisable que pour les enfants lancés par CH-01.
- **[IMPOSSIBLE] I2 — Invoquer factory-run par l'outil Skill.** `disable-model-invocation` l'interdit. D'où l'enfant headless (CH-01). Coût : un processus et un contexte par cycle, et pas d'interaction dans l'enfant.
- **[IMPOSSIBLE] I3 — Analyse complète d'une commande shell.** C'est indécidable : `eval`, variables, alias, contenu de scripts appelés. HG est un filet au mieux, documenté comme tel. Les commandes `git` lancées par le noyau en sous-processus (merge, rebase de lot, suppression de la branche de PR) échappent aux hooks par construction, et c'est du code testé.
- **[IMPOSSIBLE] I4 — `git checkout <cible>` dans un worktree lié** quand la cible est extraite ailleurs, et force-push après rebase d'une PR déjà poussée. D'où SM-06 et FB-05 : la branche n'est poussée qu'à son tour de ship, après rebase.
- **[IMPOSSIBLE] I5 — Vivacité du processus `claude`.** Le noyau ne connaît pas son pid : les appels Bash sont éphémères. Le statut « en cours » repose donc sur `updated_at` (FQ-03). Un cycle tué reste « en cours » pendant 2 h au plus.
- **[DOC] D1 — `claude -p` imbriqué.** Lancer `claude` depuis une session Claude Code (variable `CLAUDECODE`) n'est pas documenté. Il est observé que Claude Code peut refuser ou avertir des ressources partagées. R12 tranche ; en cas d'échec, Q1 bascule sur l'option B. **Observé le 2026-10-17** (recette R1 du BACKLOG §7) : `claude -p` lancé depuis une session Claude Code 2.1.301 sous Windows fonctionne, skills projet compris ; R12 reste à faire pour un cycle complet.
- **[DOC] D2 — `${CLAUDE_SESSION_ID}` et `session_id` des sous-agents** : hors des faits du BACKLOG §5. R13 tranche ; le repli `project.json` (Q17) fait que des éditions manuelles dans une autre session du même arbre sont soumises au périmètre pendant un cycle.
- **[DOC] D3 — Shell des hooks sous Windows et nom de l'outil PowerShell.** Non vérifiés : R14. Le matcher `Bash|PowerShell` est sans effet si l'outil n'existe pas.
- **[DOC] D4 — Sorties JSON des hooks** (`additionalContext` en `PostToolUse`, `systemMessage`, `continue: false` dans un sous-agent). Seuls exit 2 et `permissionDecision: deny` sont vérifiés (BACKLOG §5). R15 ; HR-02 garantit l'arrêt indépendamment de `continue`.
- **[DOC] D5 — Prise en compte des hooks.** Les hooks sont probablement figés au démarrage de la session : les hooks installés ne valent qu'à la session suivante (R16, à dire au rapport de software-factory).
- **[DOC] D6 — Facturation de `claude -p`** quand une clé d'API est présente : la garde CH-01 est volontairement conservatrice (R12).
- **Interpréteur dans un `settings.json` versionné.** Un coéquipier sans `py` reçoit une erreur non bloquante à chaque outil : bruit, pas de blocage (HK-03).
- **Garde permanente.** Elle bloque aussi les demandes légitimes de l'utilisateur (force-push voulu) dans ses sessions manuelles ; il doit les exécuter lui-même (Q26).
- **Code rebasé non retesté** (FB-05, Q12) : sans CI, C3 est vrai, et le code rebasé est mergé sans exécution de tests.
- **Budget de tours** : ship-pr dans un enfant factory-run peut épuiser `--max-turns` (Q28). L'arrêt `child` le rend visible.
- **Contrat de la Phase 3 supposé** (UA, AP-05) : un écart de noms oblige à adapter le lot L6 (Q25).
- **Statut LIVREE dans l'arbre en `gate`** : la spec devient modifiée, donc l'arbre est sale pour un ship-pr manuel ultérieur (gate `ship-pr.dirty`).

## Questions ouvertes

Chaque question est tranchée par défaut ; la justification tient en une ligne.

- **Q1 — Mécanisme d'enchaînement (Q4 du BACKLOG).** Défaut : enfant headless lancé par le noyau (CH-01).
  - Option B : retirer `disable-model-invocation` de factory-run, avec garde de politique dans `start`.
  - Option C : lire le SKILL.md cible et le suivre en ligne.
  - Justification : seule option conforme à la doc du champ, déjà utilisée par `ci/factory.*`, qui donne un contexte neuf par cycle et rend possible le parallélisme.
- **Q2 — Pré-enregistrement du labo en `auto` (Q5 du BACKLOG).** Défaut : défaut `approve`, arrêt seulement si le protocole est `BLOQUE`. Justification : §4.2 vaut pour l'artefact de la boucle unique (LP-04), et le protocole reste pré-enregistré avant toute mesure.
- **Q3 — `UNVALIDATED` et C1.** Défaut : bloque le merge. Justification : SP-06 le dit « restant à trancher », et un silence de validateur ne vaut pas feu vert.
- **Q4 — Sortie `cap` et C1.** Défaut : ne bloque pas si tous les CONFIRMED sont `FIXED`. Justification : la ROADMAP énumère exactement cinq conditions ; le plafond est signalé dans le commentaire.
- **Q5 — CI `pending`.** Défaut : relecture toutes les 30 s pendant 20 min, puis faux. Justification : un état `pending` n'est pas vert, et l'attente est bornée.
- **Q6 — « Protégée ».** Défaut : `protected` de l'API branches, ou cible listée dans `ship_pr.protected`. Justification : ce champ est disponible sur tous les plans, et la liste permet un réglage sans API.
- **Q7 — `autonomy` à l'upgrade d'un projet existant.** Défaut : `--upgrade` ajoute `auto` si la clé manque, visible dans le diff. Ce n'est pas un changement `block`, donc jamais par UA. Justification : c'est le défaut voulu, sans bascule silencieuse.
- **Q8 — Branche de livraison.** Défaut : `factory/<slug>`, suffixe d'horodatage si elle existe. Justification : préfixe reconnaissable, aucune collision avec les branches de l'utilisateur.
- **Q9 — Base et emplacement des worktrees.** Défaut : `origin/<cible>`, dossier frère `<dépôt>.harness-wt/`. Justification : ship-pr vise la cible, et un dossier hors de l'arbre évite les scans en double et toute règle `.gitignore`.
- **Q10 — Parallélisme.** Défaut : 2, plafond 4. Justification : limites de débit de l'abonnement et charge machine ; même plafond que `--themes`.
- **Q11 — Conflit trivial.** Défaut : uniquement sur les artefacts régénérables de `.knowledge/` (hors `notes.jsonl` et `config.json`), résolus par la version de la cible puis une réindexation. Justification : ce sont les seuls fichiers dont la résolution ne demande aucun jugement.
- **Q12 — Retest après rebase.** Défaut : non. Justification : la ROADMAP ne le demande pas, et C3 couvre les dépôts avec CI.
- **Q13 — Calcul des jalons.** Défaut : un jalon par sévérité non vide, avec clôture des dépendances. Justification : c'est « fiabiliser d'abord » sous une forme déterministe.
- **Q14 — Langue des STOP.** Défaut : anglais. Justification : décision du 2026-10-17 sur les messages d'arrêt.
- **Q15 — Secrets.** Défaut : `pre-edit` bloque `Edit` et `Write` sur `.env`, `.env.*` (sauf `.env.example`), `*.pem`, `*.key`, `id_rsa*`, `*.p12` et `*.pfx` ; arrêt `secret` en cycle ; `Read` reste libre. Justification : §4.3 « toucherait un secret », et les audits doivent pouvoir lire pour détecter.
- **Q16 — Outil PowerShell.** Défaut : couvert par le matcher et l'analyse. Justification : l'environnement de l'utilisateur l'utilise en premier.
- **Q17 — Portée du marqueur.** Défaut : par session, avec repli projet. Justification : ne pas bloquer les éditions manuelles parallèles (§5).
- **Q18 — Linter.** Défaut : vérification seule, sans réécriture. Justification : une écriture hors outil échappe à HP et au journal.
- **Q19 — `settings.json` ou `settings.local.json`.** Défaut : `settings.json`, comme le dit la ROADMAP. Justification : texte explicite de §5 ; l'impact sur l'équipe est signalé (E-P4-6).
- **Q20 — `--scan`.** Défaut : proposer seulement. Justification : chaque upgrade relève de la session de son projet.
- **Q21 — Cible du ship enchaîné.** Défaut : `--ship`, puis `ship_pr.target`, puis `origin/HEAD`. Justification : du plus explicite au plus déterministe ; aucune devinette.
- **Q22 — BLOQUEE en cours de file.** Défaut : arrêt de la file. Justification : lecture littérale de §4.3 et §4.4.
- **Q23 — Skills de file et de lot.** Défaut : globaux, sous `skills/`. Justification : rien à régénérer dans les projets, liés sans toucher aux installeurs.
- **Q24 — Tentative destructive en cycle.** Défaut : arrêt immédiat. Justification : §4.3 la range dans les arrêts, sans tolérance d'une première fois.
- **Q25 — Alignement sur la Phase 3** (format du plan, id de gate de l'upgrade, clés du tampon). Défaut : contrat supposé du Contexte, ajusté au lot L0. Justification : la Phase 3 est rédigée en parallèle.
- **Q26 — Échappatoire de la garde.** Défaut : aucune. Justification : un filet désactivable par l'agent n'est plus un filet ; l'utilisateur exécute lui-même.
- **Q27 — LIVREE en `gate`.** Défaut : écrit. Justification : la file en dépend, et c'est une écriture de statut, pas une gate.
- **Q28 — Tours et délai des enfants.** Défaut : 100 tours (factory-run), 200 (avec ship-pr), 120 min. Justification : 100 est la valeur actuelle de la CI ; ship-pr ajoute ses rondes.
- **Q29 — Facturation API.** Défaut : refus, avec option `chain.allow_api_billing: true`. Justification : §4.3, avec une sortie explicite pour un utilisateur sans abonnement.
- **Q30 — Ship des cycles `research`.** Défaut : non. Justification : §4.2 nomme factory-run et la spec, et le cycle de recherche finit par la consignation.

---

Fichiers lus pour cette spec :
- `C:\Users\fuzzz\claude-skills\specs\harness-v2\ROADMAP.md`
- `C:\Users\fuzzz\claude-skills\specs\harness-v2\BACKLOG.md`
- `C:\Users\fuzzz\claude-skills\specs\SPEC-noyau-core-journal.md`
- `C:\Users\fuzzz\claude-skills\specs\SPEC-phase1-rebranchement.md`
- `C:\Users\fuzzz\claude-skills\specs\SPEC-phase2-profils-audit.md`
- `C:\Users\fuzzz\claude-skills\skills\*\SKILL.md` (les 8)
- `C:\Users\fuzzz\claude-skills\skills\_core\harness.py`
- `C:\Users\fuzzz\claude-skills\skills\_core\hcore\` : `factory.py`, `fusion.py`, `ghflow.py`, `shippr.py`, `runs.py`, `journal.py`, `blocks.py`, `counters.py`, `relaunch.py`, `proc.py`, `models.py`, `__init__.py`
- `C:\Users\fuzzz\claude-skills\.claude\settings.json`
- `C:\Users\fuzzz\claude-skills\.claude\skills\factory-run\SKILL.md`
- `C:\Users\fuzzz\claude-skills\tests\fixtures\README.md`

Avant d'utiliser cette spec, trois points sont à savoir :
- Sur `v2/phase-1-core`, `gates.py`, `findings.py`, `audit.py`, `profiles.py` et `stamp.py` n'existent pas encore. La spec les suppose livrés par les Phases 1 à 3 (lot L0).
- Les points [DOC] D1 à D6 reposent sur des comportements de Claude Code qui ne figurent pas dans le BACKLOG §5. Ils sont tranchés par les recettes R12 à R16 avant les lots L4 et L10.
- Le BACKLOG §2 gèle encore les incréments 7, 8 et 12. La spec applique la levée annoncée pour les Phases 1 et 2, et la consigne au lot L12.