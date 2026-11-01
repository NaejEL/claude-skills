# SPEC — Phase 2 : profils, scout, `/software-factory` point d'entrée unique, `/audit` unifié

Statut : APPROUVEE (2026-10-17). Défauts des questions ouvertes retenus ; I1 à I3 résolus comme proposé (fusion par clés de settings.json, scout en sous-agent dynamique, /lab-run en seconde instance du gabarit).

Phase 2 de `specs/harness-v2/ROADMAP.md` (§2.1 à §2.3). L'utilisateur a levé le gel du BACKLOG (§2, incréments 9, 10, 11 gelés « jusqu'à 10 cycles »), comme il l'avait fait pour la Phase 1. Cette spec s'appuie sur ce que livre `specs/SPEC-phase1-rebranchement.md` (APPROUVEE) et en reprend les conventions : identifiants de règle, `<PY>`, `T`, rejeux scriptés, comparaison structurelle (D10). Elle utilise les règles suivantes de la Phase 1 : AU-01 à AU-16 (moteur d'audit), FD-01 à FD-11 (finding), RG-01 à RG-07 (registre projet), MD-01 à MD-08 (modèles), GT-01 à GT-08 (gate), ST-01 à ST-05 (stack), TS-01 à TS-05 (T-shirt), FU et BK (fusion, blocs).

Règle de l'utilisateur appliquée partout : **la ROADMAP fait foi**. Une règle héritée qui la contredit est modifiée ou retirée, et cette spec le dit à l'endroit concerné. Les seuls points remontés comme problèmes sont des impossibilités techniques ou des contradictions avec la doc Claude Code (section *Risques*, repères **[IMPOSSIBLE]** et **[DOC]**).

## Contexte

### Le besoin

Les mêmes boucles existent aujourd'hui en plusieurs exemplaires :
- `software-factory` et `ai-lab` déroulent la même boucle (planifier → gate → construire → vérifier → consigner) avec des rôles différents ;
- `legacy-audit`, `vibecode-audit` et `ai-lab-audit` déroulent le même audit (cartographier → auditeurs par lentille → validation adversariale → priorisation → livrables) avec des lentilles différentes.

La Phase 2 garde **une seule implémentation de chaque boucle** et met les différences dans des **profils**. Un profil est un ensemble de fichiers de données sous `skills/_core/profiles/<nom>/`, sans code. Le reste de la phase :
- un agent `harness-scout` qui détecte les profils applicables ;
- `/software-factory` devient le point d'entrée unique, avec `--rescan` ;
- `/ai-lab` devient un alias qui force `research` ;
- `/audit` remplace les trois audits ; ceux-ci restent une version comme alias avec avertissement ;
- un seul livrable `AUDIT.md` ;
- la reprise idempotente des anciens livrables ;
- une non-régression sur fixtures, avec les écarts listés un par un.

### Point de départ (vérifié par lecture)

`BASE2` désigne le commit de merge de la Phase 1 sur `main`, relevé au lot L0. Au moment de cette lecture, la Phase 1 est en cours de livraison sur `v2/phase-1-core`. Les modules `gates.py`, `findings.py`, `audit.py`, `stack.py`, `tshirt.py` et `labrun.py` n'existent pas encore. Les SKILL.md des audits et d'ai-lab ne sont pas encore rebranchés (`legacy-audit` fait encore 163 lignes). La Phase 2 **ne démarre qu'après le merge de la Phase 1**.

Ce qui, dans le noyau, est propre à un type de projet et codé en dur :
- `skills/_core/hcore/fusion.py:37-74` : `STACK_DENY`, `GENERIC_DENY`, `GITIGNORE_LINES`, `FACTORY_INPUT`, `FACTORY_TASKS` (règles de la factory) ;
- `skills/_core/hcore/factory.py:19-23` : noms `factory-planner|builder|verifier` et ligne `Statut : APPROUVEE` ;
- `skills/_core/hcore/journal.py:22-23` : liste fermée des noms de skill ;
- `skills/_core/hcore/models.py:16` : alias de modèles. Les préréglages d'ai-lab y arriveront en Phase 1 (MD-08, X10), ainsi que le jeu fermé de rôles (MD-01).

En Phase 1, le catalogue des gates (GT-08), la liste des chaînes interdites (FD-11) et les schémas des Verifiers (`verdicts.py`, LR-09) seront aussi fermés dans le code.

Faits sur les skills :
- Les rôles de boucle sont en prose : `skills/software-factory/SKILL.md:41-45` (3 agents), `skills/ai-lab/SKILL.md:55-131` (5 agents, Director à deux modes).
- Les lentilles sont en prose : `legacy-audit:45-59` (4 familles), `vibecode-audit:55-78` (5 familles, règles de remplissage), `ai-lab-audit:49-66` (5 lentilles, natures, barème GPU).
- `factory-run` porte `disable-model-invocation: true` (`software-factory:49`). Le `lab-run` généré le porte aussi (`ai-lab:170`).
- `ci/factory.*` utilise `--max-turns 100` et `Statut : APPROUVEE` (`software-factory:72-73`). `ci/lab.*` utilise `--max-turns 150` et `Statut : PRE-ENREGISTRE` (`ai-lab:198-199`).
- Les trois livrables actuels sont `ROADMAP-legacy.md` (`legacy-audit:93`), `AUDIT-vibecode.md` (`vibecode-audit:124`) et `AUDIT-lab.md` (`ai-lab-audit:101`). AU-09 sait déjà les relire vers le registre de run.
- `.claude/harness.json` n'est **écrit par aucun skill**. GT-01 (Phase 1) le lit seulement, pour la clé `autonomy`. Aucune occurrence de `harness.json`, `profiles` ou `scout` hors de `specs/` (grep).
- Les installeurs lient chaque sous-dossier de `skills/` (`install_skills.sh:176`, `install_skills.ps1:168`). Un nouveau `skills/audit/` est donc lié sans modifier les installeurs.
- `fusion.copy_core` copie récursivement tout `_core` (`fusion.py:241`). Un sous-dossier `profiles/` part donc dans `.claude/harness/` des projets. Un noyau différent déjà présent bloque la copie (exit 1).
- Fixtures existantes : `tests/fixtures/toy-project/` (Node), `merge-input/` et `merge-expected/`. Convention (`tests/fixtures/README.md`) : un fichier à nom pointé est stocké sans le point et renommé par les tests dans un dossier temporaire.

## Périmètre

### 1. Format des profils — `PF`

- `PF-01` : un profil = un dossier `skills/_core/profiles/<nom>/`. Il contient un manifeste `profile.json` (JSON strict, UTF-8) et des fragments Markdown en français, référencés par chemin relatif depuis le manifeste : `roles/<rôle>.md`, `lenses/<lentille>.md`, `orchestrator.md`, `install.md`, `scout.md`. Aucun fichier `.py` dans un profil. JSON est retenu parce que la stdlib n'a pas de YAML, ce qui tranche la Q10 du BACKLOG.
- `PF-02` : clés du manifeste (schéma documenté dans `skills/_core/profiles/SCHEMA.md`) :
  - `name` : identique au nom du dossier.
  - `schema_version`.
  - `fallback` : booléen, un seul profil à `true`.
  - `roles[]` : `{name, mission (fragment), read_only, tools, model_role, model_default, agent_file}`.
  - `model_roles[]` : rôles de modèle déclarés par le profil (extension de MD-01).
  - `model_presets` : préréglages, dont les quatre d'ai-lab (MD-08).
  - `loop` : machine de boucle, voir LP.
  - `artefacts[]` : `{kind, dir, glob, status_proposed, status_ready, status_done}`. Exemples : spec factory (`specs/SPEC-*.md`, `Statut : PROPOSEE` → `Statut : APPROUVEE`) ; protocole (`experiments/EXP-*.md`, `PROPOSE` → `PRE-ENREGISTRE` → `TERMINE — <verdict>`) ; journal d'expériences ; tableau des résultats.
  - `verifier` : `{required_true[], issue_kinds[]}`. Pour `software` : `tests_passed`. Pour `research` : `tests_passed`, `protocol_followed`, `rerun_consistent`, avec `kind` ∈ protocol|leak|stats|code|convention.
  - `deterministic_checks[]` : par exemple vulnérabilités et secrets côté `software` ; fuites, confondants et seeds côté `research`.
  - `settings` : `{deny_by_stack, deny_generic, deny_if_present}`.
  - `gitignore[]`, `tasks` : `{inputs, tasks}`.
  - `ci` : `{script, command, max_turns, status_line, logs_dir}`.
  - `orchestrator` : `{name, alias_of}`.
  - `gates[]` : entrées au format GT-08.
  - `journal_names[]`.
  - `lens_sets[]` : `{name, lenses[], plan, deliverable_section, spec_prefix, cap_option, cap, cap_default, statuses[], gates[]}`.
  - `lenses[]` : voir LN.
  - `detection` : voir SC.
  - `audit_sections[]` : gabarits d'`AUDIT.md`.
- `PF-03` : `harness.py profile validate <dossier>` rend exit 0 si le profil est conforme. Il rend exit 2, avec la liste des erreurs, pour : clé obligatoire absente, fragment référencé introuvable, `kind` de phase inconnu du moteur (LP-02), id de gate hors de l'espace de noms du profil (`<orchestrator>.`, `ai-lab.`, `audit.<profil>.`), nom de lentille ou de rôle de modèle déjà déclaré par un autre profil, deux profils `fallback`.
- `PF-04` : `harness.py profile list` rend les profils trouvés, triés par nom, avec leurs lentilles et leurs rôles.
- `PF-05` : **ajouter un profil = ajouter un dossier.** Les jeux fermés de la Phase 1 deviennent « noyau ∪ profils » : rôles de modèle (MD-01), gates (GT-08), noms de journal (JR-01), chaînes interdites (FD-11, construites depuis `artefacts[].status_ready`), schéma du Verifier (LR-09, FR-02), règles `deny`, tâches et lignes `.gitignore` (SF-01 à SF-03, AL-01 à AL-03). Aucun nom propre à un profil ne reste dans `skills/_core/hcore/*.py` ni dans `harness.py`.
- `PF-06` : `ship-pr`, `brainstorm` et `code-index` ne sont pas des profils (défaut de Q14, maintenu). Leurs gates, rôles et noms de journal restent dans le catalogue du noyau.

### 2. Extraction sans perte — `PX`

- `PX-01` : profil `software`, extrait de `software-factory` (Phases 1 à 4, 5, 6 et 6b à `BASE2`) et des lentilles de `legacy-audit` et `vibecode-audit`. Il porte deux jeux de lentilles : `legacy` (hygiene, portabilite, qualite, filet) et `vibecode` (acces, injection, metier, maintenabilite, evolutivite). `fallback: true`.
- `PX-02` : profil `research`, extrait d'`ai-lab` (Phases 1a à 1c, 2, 2b, 3, 4, 5, 6) et des lentilles d'`ai-lab-audit` (fidelite, validite, fuites, bio, route ; natures correction/question ; barème GPU).
- `PX-03` : **sans perte, vérifiable mot pour mot.**
  - Pour chaque section listée dans `tests/fixtures/profile-extraction/sections.json`, chaque phrase des SKILL.md à `BASE2` se retrouve soit dans un fragment de profil, soit dans le SKILL.md actuel, après normalisation des blancs et découpage sur `. ` et `;`.
  - Les SKILL.md à `BASE2` sont copiés tels quels sous `tests/fixtures/profile-extraction/base2/`.
  - Une phrase retirée parce que la ROADMAP la contredit figure dans `retired.json`, avec la règle ROADMAP qui la contredit. Exemple : « le passage à l'exécution appartient à `/legacy-audit` en aval » (`vibecode-audit:13`), remplacée par §2.3.
- `PX-04` : les données aujourd'hui dans le code passent dans `profile.json` sans changer de valeur : `STACK_DENY`, `GENERIC_DENY`, `GITIGNORE_LINES`, `FACTORY_INPUT`, `FACTORY_TASKS`, règles AL-01 à AL-03, préréglages MD-08. `sf apply` reste égal octet pour octet sur `tests/fixtures/merge-*`.
- `PX-05` : les gabarits de livrables de la Phase 1 (`skills/_core/templates/`) restent la source des sections d'`AUDIT.md` (SO). Le profil les référence, il ne les recopie pas.

### 3. Cumul de profils et tampon `.claude/harness.json` — `HJ`

- `HJ-01` : la Phase 2 écrit dans `.claude/harness.json` la seule clé `profiles`, liste ordonnée de `{name, added, by}` avec `by` ∈ `scout|forced|inferred|fallback`. Toutes les autres clés sont conservées telles quelles, `autonomy` comprise (GT-01). Écriture atomique, JSON strict, indentation 2, clés dans l'ordre d'origine. Le tampon complet (version, date, skills, options) relève de la Phase 3.
- `HJ-02` : JSON illisible, ou `profiles` qui n'est pas une liste → exit 2, fichier non réécrit.
- `HJ-03` : le noyau ne fait qu'**ajouter**. Aucune sous-commande ne retire un profil (ROADMAP §2.2 : « jamais d'en retirer sans accord explicite »). Un profil déjà présent n'est pas dupliqué, et son `added` est conservé. Une seconde écriture sans ajout produit un fichier identique octet pour octet.
- `HJ-04` : `harness.py stamp resolve --root R` rend `{source, profiles}`, par ordre de priorité :
  1. `stamp` : tampon présent et `profiles` non vide ;
  2. `inferred` : fichiers générés d'une installation antérieure à la Phase 2 (`.claude/skills/factory-run/SKILL.md` ou `.claude/agents/factory-*.md` → `software` ; `.claude/skills/lab-run/SKILL.md` ou `.claude/agents/lab-*.md` → `research`) ;
  3. `none`.
- `HJ-05` : le tampon est écrit **en dernier**, après la génération réussie de tous les fichiers. Un arrêt, par exemple `copy-core` bloqué, le laisse inchangé.
- `HJ-06` : profils cumulés.
  - Rôles et fichiers d'agents : union. Deux profils ne déclarent jamais le même `agent_file` (PF-03).
  - Lentilles de `/audit` : union.
  - `deny`, tâches et `.gitignore` : union par FU-01.
  - Orchestrateur : un bloc par profil (EP-06).

### 4. Agent `harness-scout` — `SC`

- `SC-01` : `detection` d'un profil = `{accept, reject, criteria[]}`. Chaque critère porte `{id, kind, weight, …}`. Les `kind` admis :
  - `glob` : motif à la racine et à un niveau de profondeur, comme ST-01 ;
  - `dir` : présence d'un dossier ;
  - `dependency` : nom de dépendance dans `requirements.txt`, `pyproject.toml` (`[project].dependencies`), `environment.yml` ou `package.json` ;
  - `content` : expression régulière dans les fichiers d'un glob, 200 Ko lus au plus par fichier ;
  - `judgement` : critère évalué par l'agent, avec une question en français et une preuve exigée.
- `SC-02` : `harness.py scout signals --root R` évalue tous les critères non-`judgement` de tous les profils. Il rend, par profil, les critères trouvés et leurs preuves (`file`, `line`, `excerpt`). Les dossiers d'artefacts sont exclus (ST-03).
- `SC-03` : l'agent `harness-scout` est un sous-agent **dynamique** : outil Agent, `subagent_type: Explore` (lecture seule), prompt `skills/_core/scout/prompt.md`, plus les fragments `scout.md` des profils et la sortie de SC-02.
  - Il ne reçoit que les critères `judgement`. Exemples : corpus scientifique (journal daté, document d'architecture, tableau des résultats, détection 1b et 1c d'ai-lab), GPU déclaré, vrai paquet logiciel autour d'un labo.
  - Il rend un unique bloc JSON final : `{"signals": [{"profile", "criterion", "found", "evidence": {"file", "lines": {"start", "end"}, "excerpt"}}], "uncertainties": ["…"]}`.
- `SC-04` : modèle économique. Le rôle `harness.scout` est ajouté au noyau, avec le défaut `haiku` quand `models.json` est absent ou n'a pas la clé. C'est une dérogation à MD-02, voulue par la ROADMAP (« modèle économique »). `--models "harness.scout=…"` le remplace pour l'appel. Le journal porte `agent: harness-scout`.
- `SC-05` : `harness.py scout verdict --root R --signals <fichier écrit par Write>`.
  - Il vérifie chaque preuve d'un `judgement` : fichier existant, lignes dans le fichier, extrait présent à ces lignes après normalisation des blancs. Une preuve invérifiable est écartée et listée dans `rejected_signals`.
  - Il calcule `score` = somme des poids trouvés, et `status` : `retained` si score ≥ `accept`, `rejected` si score < `reject`, sinon `uncertain`.
  - Il rend `{profiles[], proposal[], clear, uncertainties[], rejected_signals[]}`, avec `clear` = aucun profil `uncertain`.
- `SC-06` : un agent mort ou une sortie inexploitable → une relance (`relaunch.py`). Au second échec, le verdict est calculé sur les seuls signaux déterministes, avec `clear: false` et l'incertitude « scout non recueilli ». Un scout muet n'est pas un scout d'accord.
- `SC-07` : aucun profil `retained`, aucun `uncertain` → `proposal = [<profil fallback>]`, `by: fallback`, `clear: true`. Cela reproduit l'existant : `/software-factory` installe une factory même sans marqueur (`software-factory:35`).
- `SC-08` : verdict écrit sous `.harness/runs/scout-<horodatage>.json`, journalisé, jamais versionné.

### 5. Arbitrage `auto` / `gate` — `AR`

- `AR-01` : nouvelle gate `software-factory.profiles`, de type b.
  - Question à choix multiple : un choix par profil, avec score et statut dans le libellé, 4 choix au plus par question et 4 questions au plus par appel. Option « Abandonner ».
  - Défaut : `proposal` si `clear`, sinon **aucun**.
  - Repli headless : `default` si `clear`, sinon `stop`.
- `AR-02` : **la ROADMAP §2.2 définit le comportement `auto` de cette gate dans la Phase 2 elle-même.** Elle est donc appliquée dès cette phase, par dérogation à GT-03, limitée aux gates marquées `phase2_auto: true` dans le catalogue, c'est-à-dire `software-factory.profiles` et `audit.profiles`.
  - En `auto` : proposition nette → défaut pris et journalisé (événement `gate`, `source: default`).
  - Proposition ambiguë → GT-05 : arrêt exit 1, avec sur stderr le chemin du verdict SC-08 et la commande de reprise (`/software-factory --profile <p>[;<p>]`).
  - Le fichier `STOP-*.md` relève de la Phase 4.
- `AR-03` : toutes les autres gates de la Phase 2 suivent GT-03 : `auto` est appliqué comme `gate`, avec avertissement journalisé. C'est le cas de la priorisation des audits, dont le comportement `auto` (« fiabiliser d'abord », jalons calculés) est défini en Phase 4 (§4.2).
- `AR-04` : `--profile p[;p]` saute le scout et la gate (`by: forced`). Profil inconnu → exit 2.

### 6. `/software-factory`, point d'entrée unique — `EP`

- `EP-01` : arguments `[--profile p[;p] | --rescan] [premier besoin]`. `--profile` et `--rescan` ensemble → exit 2. Le premier besoin est conservé tel quel, comme aujourd'hui (`software-factory:13`).
- `EP-02` : sans option, le skill appelle `stamp resolve`.
  - `stamp` ou `inferred` → profils lus, **pas de scout**. C'est une réinstallation idempotente, comme aujourd'hui. Avec `inferred`, le tampon est créé en fin d'installation (HJ-05).
  - `none` → scout (SC), puis arbitrage (AR).
- `EP-03` : `--rescan` relance le scout et compare au tampon : `added` (retenus et absents du tampon), `kept`, `vanished` (dans le tampon et rejetés maintenant).
  - La gate `software-factory.profiles` ne propose que des **ajouts**.
  - `vanished` est rapporté, jamais retiré (HJ-03).
  - Rien à ajouter → aucune gate, aucune écriture, rapport « aucun profil nouveau ».
- `EP-04` : la génération par profil retenu reprend les phases d'aujourd'hui, pilotées par les données du profil :
  - détection (ST, plus `install.md`) ;
  - agents (`roles[]`, écrits par `sf install`, avec le bloc `model:` décidé en X1 de la Phase 1) ;
  - orchestrateur (LP) ;
  - CI (`ci`) ;
  - fusions (`settings`, `tasks`, `gitignore`) ;
  - phases propres au profil déclarées dans `install.md`, par exemple la Phase 2b des modèles d'ai-lab (gate `ai-lab.models`) ;
  - gate `software-factory.code-index`, posée une seule fois quel que soit le nombre de profils ;
  - rapport final.
- `EP-05` : ajout d'un profil, par `--rescan` ou par un `--profile` qui ajoute à un tampon existant. Seuls sont écrits :
  - les fichiers propres au nouveau profil ;
  - son bloc dans l'orchestrateur ;
  - l'union additive de ses entrées dans `settings.json`, `tasks.json` et `.gitignore`.

  Tout fichier existant d'un autre profil est rendu `identique` ou `personnalisé-conservé`. Le texte hors bloc de l'orchestrateur est inchangé octet pour octet.
- `EP-06` : orchestrateur partagé `.claude/skills/factory-run/SKILL.md`.
  - Le corps commun est généré depuis le gabarit de software-factory.
  - Il contient un bloc `<!-- harness.profile.<nom>:debut -->` / `<!-- harness.profile.<nom>:fin -->` par profil actif, avec le contenu de `orchestrator.md` adapté au projet.
  - Un orchestrateur existant **sans** ces blocs (installation antérieure) n'est pas réécrit : état `personnalisé-conservé`, signalé au rapport, avec le renvoi à `--upgrade` (Phase 3).
- `EP-07` : `copy-core` reste bloquant (exit 1) si `.claude/harness/` contient un noyau différent. Le skill s'arrête alors avant la génération et avant le tampon.

### 7. Boucle unique et orchestrateurs — `LP`

- `LP-01` : `hcore/loop.py` remplace les machines de `factory.py` et `labrun.py`, paramétrée par `profile.loop`. `factory.py` et `labrun.py` restent des façades fines, pour que les tests FR-* et LR-* de `BASE2` passent sans changer leurs assertions.
- `LP-02` : types de phase connus du moteur : `plan`, `consult` (conseillers en parallèle, relance unique, « expertise non recueillie »), `consolidate`, `gate`, `build`, `verify` (bornes FR-03 et FR-04, succès = verdict `APPROVED` et tous les `verifier.required_true` vrais), `interpret` (une seule fois, après approbation), `record`. Un profil qui déclare un autre type est refusé (PF-03).
- `LP-03` : `software` déclare `plan → gate(factory-run.questions, factory-run.approval) → build → verify → record`.
- `LP-04` : `research` déclare `plan(director.cadrage) → consult(neuro, math) → consolidate → gate(lab-run.pi-questions, lab-run.preregistration) → build → verify → interpret(neuro, math, director.interpretation) → gate(lab-run.consignation) → record`. Les ids de gate de la Phase 1 sont conservés.
- `LP-05` : `H factory-run start --arguments-file F` route l'entrée.
  - Chemin d'un artefact d'un profil actif, avec le statut `status_ready` → profil propriétaire, mode `build`.
  - `suivant` → `research`, mode `plan`.
  - `--profile p` → `p`, mode `plan`. Profil inactif → exit 1 (`STOP: profile <p> is not active`) ; profil inconnu → exit 2.
  - Texte libre avec un seul profil actif → ce profil.
  - Texte libre avec plusieurs profils actifs → gate `factory-run.profile` (b). Défaut : premier profil du tampon (le premier retenu à l'installation). Repli headless : `stop`, déjà le comportement d'un plan headless (`software-factory:54`).
- `LP-06` : `/lab-run` n'est **pas** un alias par invocation, parce que `factory-run` porte `disable-model-invocation: true` (voir [IMPOSSIBLE] I3). C'est une **seconde instance du même gabarit**, profil `research` imposé (`orchestrator.alias_of: factory-run`), générée seulement quand `research` est actif. `ci/lab.*` continue d'appeler `/lab-run`.
- `LP-07` : journal. Le fichier porte le nom de l'orchestrateur invoqué (`factory-run-*` ou `lab-run-*`), et chaque ligne porte `profile`.

### 8. Alias `/ai-lab` — `AX` (installation)

- `AX-01` : `skills/ai-lab/SKILL.md` devient un alias léger, **sans** `context: fork`. Il exécute en ligne l'outil Skill sur `software-factory` avec les arguments `--profile research <$ARGUMENTS tels quels>`. Repli si l'outil Skill est indisponible : lire `${CLAUDE_SKILL_DIR}/../software-factory/SKILL.md` et suivre ses instructions avec ces arguments (même mécanisme que la recette R1).
- `AX-02` : pas d'avertissement de retrait pour `/ai-lab`. La ROADMAP §2.2 le garde « pour ne rien casser », sans échéance ; cette règle particulière prime sur la règle commune « une version ».
- `AX-03` : `/ai-lab` sur un projet déjà équipé `software` **ajoute** `research` au tampon, sans rien retirer (HJ-03).

### 9. `/audit` unifié — `AD`

- `AD-01` : nouveau skill `skills/audit/SKILL.md`, avec `name: audit`, `context: fork`, `user-invocable: true`, et **sans** `disable-model-invocation`, parce que les alias l'invoquent (AX-04).
  - Arguments : `[REPO] [--profile p[;p]] [--lenses "l;…"] [--max-specs N] [--max-findings N] [--max-questions N] [--models "r=m;…"]`.
  - Option interne `--via <alias>`.
  - AU-01 à AU-03 s'appliquent. Option inconnue → exit 2.
- `AD-02` : profils actifs, par ordre de priorité :
  1. `--profile` ;
  2. tampon ;
  3. `inferred` ;
  4. sinon scout en lecture seule. Son verdict sert à cet audit et **n'est pas écrit** dans le tampon, parce que l'audit est en lecture seule sur le projet. Gate `audit.profiles`, même sémantique que AR-01 et AR-02.
- `AD-03` : lentilles.
  - Défaut : union des lentilles des profils actifs.
  - `--lenses` accepte des noms de lentille ou d'axe. Un axe se développe en ses lentilles : `securite` → `acces;injection;metier`.
  - Une lentille hors des profils actifs, ou inconnue → exit 2.
  - Exemple de la ROADMAP : `--lenses "securite;fuites"` → `acces, injection, metier, fuites`, et les profils `software` et `research` sont requis actifs.
- `AD-04` : un auditeur par lentille, jamais deux lentilles dans un même auditeur. Au plus 5 en parallèle (le maximum actuel, ai-lab-audit et vibecode-audit). Au-delà, vagues successives de 5 au plus, dans l'ordre profil → jeu → lentille. 14 lentilles donnent des vagues de 5, 5 et 4.
- `AD-05` : cartographie commune = union des étapes déclarées par les jeux actifs.
  - Git et `GIT_ABSENT` (AU-12), stack (ST), bornes (ST-04, ST-05), présence de la factory et du labo.
  - Corpus scientifique (`research`).
  - Frontières de confiance, signaux de génération, paires de réimplémentation, vérifications déterministes, artefact de distribution (jeu `vibecode`).
  - Reprise (MG).
- `AD-06` : validation adversariale par le noyau (FD-06, AU-05). Les champs de verdict admis sont ceux de la **lentille** (LN-02), plus ceux de la source.
- `AD-07` : dédup avant validateur (AU-06) contre le registre de run, la reprise et `.claude/findings.jsonl` (RG-04), **tous jeux de lentilles confondus**, avec la clé RG-02. La fusion de doublons entre auditeurs (VA-07) s'étend à toutes les lentilles d'un même profil.
- `AD-08` : priorisation par jeu actif. Les gates de chaque jeu sont conservées, avec 4 questions au plus par appel :
  - `audit.software.framing` : jalons et critère dominant si `legacy` est actif ; ordre d'attaque et sort des mineurs si `vibecode` est actif ; jusqu'à 4 questions en un appel ;
  - `audit.software.assignment` : 3 appels au plus ;
  - `audit.research.framing` ;
  - `audit.research.selection` : 2 appels au plus ;
  - `audit.drop-security` (b) : posée seulement si le jeu `vibecode` est partiellement sélectionné et exclut l'axe `securite` ;
  - `audit.final` (c) : « Écrire AUDIT.md (+ specs) » / « Réajuster » (une fois, AU-15) / « Abandonner ».

  Les replis headless reprennent ceux de la Phase 1 gate par gate : `stop` pour les gates legacy et research, `default` signalé en tête pour les gates vibecode. Une gate `stop` atteinte arrête tout l'audit avant l'écriture.
- `AD-09` : plafonds par jeu.
  - `--max-specs` : `legacy`, `min(N, 25)`, défaut 15, appliqué aux specs LEG et VIB.
  - `--max-findings` : `vibecode`, `min(N, 30)`, défaut 15.
  - `--max-questions` : `research`, `min(N, 12)`, défaut 6.
  - Une option dont le jeu est inactif → exit 2.
- `AD-10` : seules écritures : `AUDIT.md`, les specs (`specs/SPEC-leg-*`, `SPEC-vib-*`, `SPEC-lab-*`) et `.harness/runs/` (X5 de la Phase 1).
- `AD-11` : modèles. Lentilles `legacy` et `vibecode` → `audit.auditor` ; validateurs → `audit.validator`. Lentilles `research` → `lens.model_role` (AA-06) ; validateurs → `lab.validator`.
- `AD-12` : journal `.harness/runs/audit-<horodatage>.jsonl`. `--via` est journalisé (`event: alias`).

### 10. Propriétés de lentille — `LN`

- `LN-01` : la liste exacte de la ROADMAP §2.3 devient six clés de lentille.

| Propriété ROADMAP | Clé | Valeurs, par lentille | Effet déterministe |
| --- | --- | --- | --- |
| dette d'accumulation vs dette de génération | `debt` | `accumulation` (legacy), `generation` (vibecode), `none` (research) | Le fragment d'auditeur porte le cadrage de sa dette. Les sections d'`AUDIT.md` sont groupées par dette, avec le texte de distinction de `vibecode-audit:15`. |
| motif à N occurrences | `shape` | `pattern` (vibecode), `occurrence` (les autres) | `pattern` : schéma `{pattern, occurrences[≤5], count, sampled}` (VA-04), clé `::<motif>` (RG-02), `SPLIT`, `false_occurrences` et `corrected_count` admis. `occurrence` : ces champs sont refusés (FD-06). |
| gravité prime sur l'axe | `ordering`, `axis`, `axis_rank` | `critical_first` (vibecode, TS-03 VIB), `severity_size` (legacy, COR), `severity_cost` (Q) | Tri TS-03 selon la lentille ; critiques d'un autre axe signalés (VA-10). `regression_risk` n'entre dans aucun tri. |
| « ce qui ne peut pas être audité est un finding » | `unauditable` | `finding` (vibecode), `mark` (legacy, research) | Lentille morte deux fois → `finding` : « surface non auditable », major, `bruts = échec` ; `mark` : « non auditée », `échec` (AU-04). Outil de détection absent → finding si `finding`. |
| aucun run ni protocole pour les lentilles de recherche | `no_run`, `no_protocol`, `allowed_exec` | `true`, `true`, `["test-cpu"]` pour fidelite seulement (research) | Le fragment d'auditeur porte l'interdiction. La fiche `Q-*` est rendue depuis un JSON à champs fermés (Question, Motivation, Ce qu'elle trancherait, Coût estimé, Dépend de, Lancer, Statut) ; une clé de plus → refus de rendu, exit 2. |
| grep du journal pour les questions déjà tranchées | `journal_check` | `true` pour validite, route, bio | Le prompt du validateur porte la consigne de grep du journal. `TRANCHEE (journal <date>)` est posé par comparaison de dates (AA-10). |

- `LN-02` : autres propriétés nécessaires à l'extraction sans perte (PX-03). Le profil les porte, et le noyau ne connaît que leur clé :
  - `prefix` ;
  - `nature` (correction|question) ;
  - `size_scale` : `dev`, ou `gpu` pour les questions (`ai-lab-audit:66`) ;
  - `critical_definition` (fragment) ;
  - `subagent_type` si le labo est présent (AA-05) ;
  - `model_role` ;
  - `stack_agnostic` (vibecode : « Aucune adhérence à une pile technique ») ;
  - `dedup_key` (LA-06, AA-08, VA) ;
  - `evidence_kinds` ;
  - `receives` (`trust_map` pour acces, injection et metier ; `reimpl_pairs` pour maintenabilite) ;
  - `validator_fields` (`size_correction`, `nature_correction`, `severity_correction`, `axis_correction`, `difficulty_correction`) ;
  - `deliverable` (section, statuts AU-10).

### 11. Sorties dans un seul `AUDIT.md` — `SO`

- `SO-01` : un seul livrable, `<REPO>/AUDIT.md`. Liens relatifs en `/`.
  - En-tête : « Généré par /audit le <date> », profils, lentilles, complet ou échantillonné, « Repris depuis » (MG-02).
  - Puis, dans cet ordre :
    - l'encadré « Portée et limites » (`vibecode-audit:131-142`), si une lentille `debt: generation` est active ;
    - « Surfaces non auditables » ;
    - « Lentilles non auditées » ;
    - les sections de chaque jeu actif, dans l'ordre du tampon ;
    - « Findings non retenus dans ce cycle » ;
    - « Findings rejetés à la validation » ;
    - « Suite ».
- `SO-02` : profil `software`.
  - Jeu `legacy` : section « Roadmap » (jalons, tableau LEG, statuts `A_FAIRE`/`EN_COURS`/`FAIT`/`REPORTE`).
  - Jeu `vibecode` : sections « Par où attaquer » (tableau VIB, gains rapides, critiques remontés) et « Motifs détaillés ».
  - Si les deux jeux sont actifs, les thèmes VIB entrent dans `audit.software.assignment`. Un motif affecté à un jalon donne une spec `SPEC-vib-<nn>-<slug>.md` (FD-08).
  - Si seul `vibecode` est actif, il n'y a ni roadmap ni spec, comme pour l'ancien `/vibecode-audit`.
- `SO-03` : profil `research` : « Corrections à faire » (`COR-*`), « Questions de recherche retenues » (`Q-*`) et « Questions non retenues ».
  - La ligne « Lancer » vaut `/factory-run --profile research "<question>"` (ROADMAP §2.3, D9).
  - Les specs `SPEC-lab-*` ne sont écrites que si `software` est actif, ou si une factory est présente (`inferred`), et que la gate de framing le choisit.
  - Les deux critères d'acceptation imposés à `fuites` sont conservés (AA-12).
- `SO-04` : FD-11, construit depuis les profils (PF-05), est appliqué à `AUDIT.md` et à chaque spec écrite. Une spec existante n'est jamais écrasée (AU-14).
- `SO-05` : `ROADMAP-legacy.md`, `AUDIT-vibecode.md` et `AUDIT-lab.md` ne sont **jamais écrits** par `/audit`, alias compris.

### 12. Reprise idempotente des anciens livrables — `MG`

- `MG-01` : au démarrage, `/audit` lit `AUDIT.md` s'il existe. Il lit aussi chaque ancien livrable présent (`ROADMAP-legacy.md`, `AUDIT-vibecode.md`, `AUDIT-lab.md`) dont le sha256 n'est pas déjà enregistré dans `AUDIT.md`. Ces fichiers sont relus vers le registre de run par AU-09.
- `MG-02` : chaque import est enregistré dans `AUDIT.md`, sur une ligne `<!-- harness:import <fichier> sha256=<hash> -->` suivie de la ligne visible « Repris depuis : <fichier> ».
  - Un fichier déjà importé dont le hash a changé n'est pas réimporté : avertissement au rapport, `AUDIT.md` prime.
  - Un ancien fichier jamais importé est importé, même quand `AUDIT.md` existe déjà.
- `MG-03` : statuts `FAIT`, `EN_COURS` et `TRANCHEE (journal <date>)` préservés. La numérotation se poursuit par préfixe, au-delà du plus grand id importé (AU-08). Les specs existantes restent inchangées (`cmp`).
- `MG-04` : les anciens livrables ne sont **jamais modifiés ni supprimés**, et restent identiques octet pour octet.
- `MG-05` : idempotence. Deux exécutions successives, à date fixée et avec les mêmes sorties d'agents rejouées, produisent un `AUDIT.md` identique octet pour octet, sans nouvel id ni nouvel import.

### 13. Anciens audits gardés comme alias — `AX` (audit)

- `AX-04` : `legacy-audit`, `vibecode-audit` et `ai-lab-audit` deviennent des alias légers, **sans** `context: fork`, avec les mêmes lignes `name:`.
  - Chacun affiche d'abord, mot pour mot : « `/<nom>` est un alias de `/audit`, conservé pendant la version <CORE_VERSION de la Phase 2> et retiré à la version suivante. »
  - Puis il invoque l'outil Skill `audit`, avec les arguments traduits par `harness.py audit alias-args --skill <nom> --arguments-file F` (fichier écrit par Write, jamais par le shell).
- `AX-05` : traduction.
  - `legacy-audit [R] --categories X --max-specs N` → `audit [R] --profile software --lenses <X ou le jeu legacy> --max-specs N --via legacy-audit`.
  - `vibecode-audit [R] --axes X --max-findings N` → `audit [R] --profile software --lenses <axes développés, ou le jeu vibecode> --max-findings N --via vibecode-audit`.
  - `ai-lab-audit [R] --lenses X --max-questions N --models M` → `audit [R] --profile research --lenses <X ou le jeu research> --max-questions N --models M --via ai-lab-audit`. Les alias courts de MD-06 sont conservés.
- `AX-06` : `--profile` force le profil, même si le tampon en porte d'autres. Le comportement de chaque alias reste ainsi limité à ses lentilles d'origine.

### 14. Non-régression sur fixtures — `NR`

- `NR-01` : chaque fixture a ses sorties d'auditeurs et de validateurs figées, par lentille, sous `tests/fixtures/audit-replay/<projet>/`. On rejoue :
  - les rejeux de la Phase 1 des trois audits, depuis `BASE2` (CA-27 de la Phase 1) ;
  - le rejeu de `/audit` avec les mêmes sorties.
- `NR-02` : comparaison structurelle (D10) sur l'ensemble normalisé `{préfixe, clé RG-02, sévérité, statut, taille|difficulté, count}` :
  - `/audit --profile software` doit retrouver l'union de `legacy-audit` et `vibecode-audit` ;
  - `/audit --profile research` doit retrouver `ai-lab-audit`.
- `NR-03` : la différence constatée doit être **exactement** la liste attendue `tests/fixtures/audit-nonreg/expected-gaps.json`. Chaque entrée porte un id `E-A*` ou `E-I*`, le finding concerné et la justification ci-dessous.
- `NR-04` : écarts attendus, un par un.
  - `E-A1` : un seul `AUDIT.md` au lieu de trois fichiers (ROADMAP §2.3).
  - `E-A2` : avec `legacy` et `vibecode` actifs ensemble, les motifs VIB sont proposés aux jalons et peuvent produire `SPEC-vib-*` (§2.3 : specs et roadmap pour `software`). Seul, `vibecode` ne produit ni roadmap ni spec, comme avant.
  - `E-A3` : la ligne « Lancer » des `Q-*` vise `/factory-run --profile research` au lieu de `/lab-run` (§2.3, D9).
  - `E-A4` : un finding trouvé à la fois par une lentille `legacy` et une lentille `vibecode` (même clé) n'apparaît qu'une fois (AD-07). Avant, il apparaissait dans deux livrables.
  - `E-A5` : ids de gate `audit.*` à la place de `legacy-audit.*`, `vibecode-audit.*` et `ai-lab-audit.*`. Une seule gate finale. Les questions de framing de `legacy` et `vibecode` sont regroupées dans un appel (4 questions au plus).
  - `E-A6` : la condition « factory présente » des specs `SPEC-lab-*` devient « profil `software` actif, ou factory inférée » (SO-03). Elle est équivalente sur un projet antérieur à la Phase 2.
  - `E-A7` : l'en-tête « Généré par /audit » liste les profils et les lentilles.
  - `E-A8` : avertissement d'alias en tête de session, journalisé (AX-04).
  - `E-A9` : en headless, un audit `software` complet s'arrête avant l'écriture (gate `stop` de `legacy`), alors que `/vibecode-audit` seul écrivait. L'alias `vibecode-audit` garde son comportement (AX-06).
  - `E-A10` : au-delà de 5 lentilles, les auditeurs partent en vagues (AD-04). Aucun alias n'est concerné : 4, 5 et 5 lentilles.
  - `E-I1` : `.claude/harness.json` est écrit à l'installation (HJ-01).
  - `E-I2` : l'orchestrateur porte des blocs par profil (EP-06).
  - `E-I3` : `ai-lab.code-index` est fusionnée dans `software-factory.code-index`, posée une seule fois (EP-04).
  - `E-I4` : `/lab-run` est généré depuis le gabarit commun, avec un texte différent de celui de `BASE2`. L'équivalence est structurelle : rejeux LR-*.
  - `E-I5` : lignes `harness-scout` et événement de gate `software-factory.profiles` dans le journal.
  - `E-I6` : `/software-factory` sur un projet de recherche non équipé propose `research` (en plus de `software` si un vrai paquet logiciel est détecté), au lieu d'installer seulement la factory (§2.2).
- `NR-05` : recette réelle par l'utilisateur, R9 ci-dessous. Les écarts observés en LLM réel, hors `E-*`, sont listés un par un et justifiés dans le rapport de fin de phase.

### Découpage en lots (ordre de livraison, chacun testable seul par `T`)

| Lot | Contenu | CA | Dépend de |
| --- | --- | --- | --- |
| L0 | Merge de la Phase 1, `BASE2` relevé dans cette spec ; recette R8 (outil Skill depuis un skill en ligne) | — | Phase 1 |
| L1 | PF-01 à PF-04 : `hcore/profiles.py`, `SCHEMA.md`, `harness.py profile validate/list`, fixtures `profile-toy` et `profile-invalid` | 04 | L0 |
| L2 | PX-01 à PX-05 et PF-05 : profils `software` et `research` ; jeux fermés pilotés par les profils (fusion, gates, journal, modèles, FD-11, verdicts) ; outillage d'extraction | 05, 06, 07, 13 | L1 |
| L3 | LP-01 à LP-07 : `loop.py`, façades, routage d'entrée, gabarit d'orchestrateur à blocs | 14, 15 | L2 |
| L4 | HJ-01 à HJ-06, SC-01 à SC-08 : `stamp.py`, `scout.py`, `scout/prompt.md`, rôle `harness.scout` ; fixtures `profile-software`, `profile-research`, `profile-mixed` | 08, 09, 11, 25 | L2 |
| L5 | AR-01 à AR-04, EP-01 à EP-07, AX-01 à AX-03 : `software-factory` et alias `ai-lab` | 10, 12, 16, 26 (partiel) | L3, L4 |
| L6 | AD-01 à AD-12, LN-01, LN-02 : `skills/audit/SKILL.md`, extension de `audit.py` | 18, 19, 24 | L2, L4 |
| L7 | SO-01 à SO-05, MG-01 à MG-05 : gabarits `AUDIT.md`, migration | 20, 21 | L6 |
| L8 | AX-04 à AX-06 : trois alias d'audit, `audit alias-args`, catalogue des gates | 17, 23 | L7 |
| L9 | NR-01 à NR-04 : rejeux comparés, `expected-gaps.json` | 22 | L8 |
| L10 | README (sections « Profils », `/audit`, alias), `tests/fixtures/README.md`, BACKLOG (Q3, Q10, gel levé), rafraîchissement de `.claude/harness/` de ce dépôt, passage complet des CA | 01 à 31 | tous |

Un commit par lot au minimum, un commit par skill rebranché (L5 : software-factory, ai-lab ; L6 : audit ; L8 : un par alias).

### Fichiers créés ou modifiés

**Créés**
- `skills/_core/profiles/SCHEMA.md`
- `skills/_core/profiles/software/profile.json`, `orchestrator.md`, `install.md`, `scout.md`
- `skills/_core/profiles/software/roles/factory-planner.md`, `factory-builder.md`, `factory-verifier.md`
- `skills/_core/profiles/software/lenses/` : `hygiene.md`, `portabilite.md`, `qualite.md`, `filet.md`, `acces.md`, `injection.md`, `metier.md`, `maintenabilite.md`, `evolutivite.md`
- `skills/_core/profiles/research/profile.json`, `orchestrator.md`, `install.md` (corpus 1b et 1c, Phase 2b), `scout.md`
- `skills/_core/profiles/research/roles/lab-director.md`, `lab-neuro.md`, `lab-math.md`, `lab-builder.md`, `lab-verifier.md`
- `skills/_core/profiles/research/lenses/fidelite.md`, `validite.md`, `fuites.md`, `bio.md`, `route.md`
- `skills/_core/scout/prompt.md`
- `skills/_core/hcore/profiles.py`, `stamp.py`, `scout.py`, `loop.py`, `aliases.py`
- `skills/_core/templates/audit/` : un gabarit par section de SO-01
- `skills/audit/SKILL.md`
- `skills/_core/tests/` : `test_profiles.py`, `test_extraction.py`, `test_stamp.py`, `test_scout.py`, `test_loop.py`, `test_entry.py`, `test_audit_unified.py`, `test_audit_migration.py`, `test_audit_nonreg.py`, `test_aliases.py`
- Fixtures listées ci-dessous

**Modifiés**
- `skills/_core/hcore/__init__.py` (`CORE_VERSION` 2.0.0), `fusion.py`, `factory.py`, `labrun.py`, `gates.py`, `models.py`, `journal.py`, `findings.py`, `verdicts.py`, `audit.py`, `tshirt.py`, `harness.py`
- `skills/software-factory/SKILL.md`, `skills/ai-lab/SKILL.md`, `skills/legacy-audit/SKILL.md`, `skills/vibecode-audit/SKILL.md`, `skills/ai-lab-audit/SKILL.md`
- `README.md`, `tests/fixtures/README.md`, `specs/harness-v2/BACKLOG.md`
- `.claude/harness/` de ce dépôt (copie identique de `skills/_core/`, Q-C de la Phase 1)

**Inchangés** (vérifié par CA-28) : `install_skills.sh`, `install_skills.ps1`, `skills/ship-pr/`, `skills/brainstorm/`, `skills/code-index/`.

### Fixtures (`tests/fixtures/`)

Convention existante : aucun fichier à nom pointé, aucun fichier nommé `CLAUDE.md`. Les tests les copient sous leur vrai nom dans un dossier temporaire, avec `git init` (D4). La raison est donnée en [DOC] I6.

- `profile-software/` : petite application Node.
  - `package.json` avec dépendances, `src/`, `test/`, `github/workflows/ci.yml` (renommé `.github/`).
  - Défauts semés, un ou plusieurs par lentille :
    - hygiene : chaîne `FAKE_API_KEY=fake-...` volontairement factice, `gitignore.txt` incomplet ;
    - portabilite : chemin absolu `C:/Users/...` ;
    - qualite : `catch {}` vide ;
    - filet : aucun test sur un module ;
    - acces : route sans vérification d'appartenance ;
    - injection : requête construite par concaténation ;
    - metier : quantité fournie par le client et acceptée telle quelle ;
    - maintenabilite : `src/util/format.js` et `src/utils/format.js` divergents ;
    - evolutivite : URL en dur.
  - Aucun corpus scientifique.
- `profile-research/` : PoC Python sans paquet.
  - `requirements.txt` (numpy, torch), `claude-md.txt` (renommé `CLAUDE.md`) avec « Vocabulaire », « État du projet », contraintes non négociables et mention GPU.
  - `docs/JOURNAL.md` : 3 entrées datées `## AAAA-MM-JJ — …`, dont une qui tranche une question.
  - `docs/ARCHITECTURE.md` : une équation et une décision numérotée.
  - `docs/EXTENSIONS.md` : tableau des résultats, inspiration hippocampe.
  - `eval/recall.py` : `argparse`, baseline à budget de tokens différent (fuite semée).
  - `model/config.py` : valeur par défaut différente de l'état annoncé.
- `profile-mixed/` : le corpus de `profile-research/` plus un vrai paquet : `pyproject.toml` avec `[project]`, `src/<pkg>/`, `tests/`, CI.
- `profile-toy/` : profil minimal valide (un rôle, une lentille, une gate, un critère `glob`) pour CA-06.
- `profile-invalid/<cas>/` : un dossier par erreur de PF-03.
- `profile-extraction/` : `base2/<skill>.md` (copies à `BASE2`), `sections.json`, `retired.json`.
- `profile-expected/{software,research,mixed}/` : fichiers déterministes attendus de l'installation (`settings.json`, `tasks.json`, `gitignore.txt`, `harness.json`, blocs d'orchestrateur) et verdict `scout-expected.json`.
- `audit-replay/{profile-software,profile-research,profile-mixed}/<lentille>.json` et `validators/<id>.json`.
- `audit-expected/{profile-software,profile-research,profile-mixed}/AUDIT.md` et `specs/`, à date fixée.
- `audit-legacy-deliverables/` : `ROADMAP-legacy.md` (`LEG-03 FAIT`), `AUDIT-vibecode.md` (`VIB-02 EN_COURS`), `AUDIT-lab.md` (`Q-01 TRANCHEE (journal 2026-09-12)`), `specs/SPEC-leg-03-gitignore.md`.
- `audit-nonreg/expected-gaps.json`.

Les projets vide et ambigu sont fabriqués par les tests dans un dossier temporaire, sans fixture.

## Critères d'acceptation

`<PY>` = l'interpréteur détecté. `T` = `cd skills/_core/tests && <PY> -B -m unittest discover -s . -t .`. `S` = `specs/SPEC-phase2-profils-audit.md`. `K` = `<PY> skills/_core/harness.py`. Les recherches utilisent `grep`, parce que `rg` est absent du PATH de Git Bash. Les dossiers temporaires sont créés par les tests.

- [ ] **CA-01 — Tests verts.** `T` → exit 0.
- [ ] **CA-02 — Stdlib seule, Python 3.9.** `cd skills/_core/tests && <PY> -B -I -S -m unittest discover -s . -t .` → exit 0, avec `<PY> --version` en 3.9.x.
- [ ] **CA-03 — Chaque règle est testée.** `for id in $(grep -oE '\b(PF|PX|HJ|SC|AR|EP|LP|AX|AD|LN|SO|MG|NR)-[0-9]{2}\b' S | sort -u); do grep -rlq "$id" skills/_core/tests || echo "$id"; done` → aucune sortie.
- [ ] **CA-04 — Validation des profils.** `K profile validate skills/_core/profiles/software` et `K profile validate skills/_core/profiles/research` → exit 0. Pour chaque `tests/fixtures/profile-invalid/<cas>` → exit 2, et le message nomme l'erreur.
- [ ] **CA-05 — Aucun nom de profil dans le noyau.** `grep -rnE 'factory-(planner|builder|verifier)|lab-(director|neuro|math|builder|verifier)|PRE-ENREGISTRE|APPROUVEE|hygiene|portabilite|fidelite|validite|STACK_DENY|FACTORY_TASKS' skills/_core/hcore skills/_core/harness.py` → aucune sortie.
- [ ] **CA-06 — Ajouter un profil = ajouter un dossier.** `test_profiles.AddProfileTest` :
  - copie `skills/_core` et `profile-toy` sous `profiles/toy/` dans un dossier temporaire ;
  - `profile list`, `scout signals`, `audit plan --profile toy` et `factory-run start --profile toy` y voient le profil `toy` ;
  - aucun fichier hors de `profiles/toy/` ne diffère de `skills/_core` (`diff -r`).
- [ ] **CA-07 — Extraction sans perte.**
  - Pour chaque fichier `tests/fixtures/profile-extraction/base2/<skill>.md` : `git show <BASE2>:skills/<skill>/SKILL.md | cmp - <fichier>` → exit 0.
  - `test_extraction` → chaque phrase des sections de `sections.json` est trouvée dans `skills/_core/profiles/**` ou dans `skills/*/SKILL.md`, sauf celles de `retired.json`.
  - Chaque entrée de `retired.json` porte un champ `roadmap` non vide.
- [ ] **CA-08 — Verdict du scout sur fixtures.** Avec des sorties d'agent figées, `K scout verdict` rend :
  - `profile-software` : `software` retenu, `research` rejeté, `clear: true` ;
  - `profile-research` : `research` retenu, `software` non retenu ;
  - `profile-mixed` : les deux retenus, `clear: true` ;
  - dossier vide : `proposal: ["software"]`, `by: fallback` ;
  - projet temporaire calibré dans la zone `uncertain` : `clear: false`.

  Chaque sortie est égale à `scout-expected.json` (JSON parsé).
- [ ] **CA-09 — Preuve du scout vérifiée.** Un signal `judgement` qui cite un fichier absent, une ligne hors du fichier, ou un extrait absent de ces lignes, est listé dans `rejected_signals` et ne compte pas dans le score. Un scout mort deux fois → `clear: false`, avec l'incertitude « scout non recueilli ».
- [ ] **CA-10 — Arbitrage.** Tests de `software-factory.profiles` :
  - `autonomy` absente → `ask` ;
  - `auto` avec proposition nette → `default`, plus deux événements `gate`, dont un `source: default` ;
  - `auto` avec proposition ambiguë → exit 1, et stderr contient le chemin `scout-*.json` et `--profile` ;
  - repli headless identique ;
  - une gate de priorisation d'audit en `auto` → `ask` avec avertissement (GT-03).
- [ ] **CA-11 — Tampon.**
  - `stamp add` sur un `harness.json` `{"autonomy": "gate", "x": 1}` conserve `autonomy` et `x` ;
  - un second `add` du même profil donne un fichier identique (`cmp`) ;
  - un JSON illisible → exit 2, fichier inchangé (`cmp`) ;
  - aucune sous-commande `stamp remove` (`K stamp remove` → exit 2) ;
  - `stamp resolve` rend `inferred/software` sur `toy-project` équipé d'un `factory-run` antérieur.
- [ ] **CA-12 — `--rescan`.** Rejeu dans un projet temporaire équipé `software` (fixture `profile-software` + installation rejouée), puis ajout du corpus de `profile-research` :
  - `added: ["research"]` ;
  - les agents `lab-*` sont créés, et les agents `factory-*` restent `identique` ;
  - `settings.json` contient les règles `research` et les règles `software` d'avant ;
  - l'orchestrateur reçoit le bloc `harness.profile.research`, et son texte hors bloc reste égal octet pour octet ;
  - retirer ensuite le corpus et relancer donne `vanished: ["research"]`, et le tampon le contient toujours.
- [ ] **CA-13 — Génération inchangée en profil unique.**
  - `sf apply` sur `tests/fixtures/merge-input` (stack `node`) → égal à `tests/fixtures/merge-expected` (test de la Phase 1, inchangé).
  - Les fichiers déterministes d'une installation `software` et d'une installation `research` sont égaux à `profile-expected/*`. Seuls ajouts admis : `harness.json` et les blocs EP-06.
  - `git diff --exit-code <BASE2> -- tests/fixtures/merge-expected`.
- [ ] **CA-14 — Boucle unique.**
  - Les tests FR-01 à FR-04 et LR-01 à LR-09 passent.
  - `git diff --exit-code <BASE2> -- skills/_core/tests/test_factory.py` et le fichier de test LR-* de `BASE2` : aucune assertion modifiée.
  - Un profil déclarant une phase `deploy` → exit 2.
- [ ] **CA-15 — Routage d'entrée.** `K factory-run start` rend :
  - spec `APPROUVEE` → `software/build` ;
  - `experiments/EXP-*.md` `PRE-ENREGISTRE` → `research/build` ;
  - `suivant` → `research/plan` ;
  - texte libre avec un profil actif → ce profil ;
  - deux profils actifs → gate `factory-run.profile` ;
  - `--profile research` inactif → exit 1 ;
  - `--profile zzz` → exit 2.

  Le journal créé s'appelle `lab-run-*` quand l'instance `lab-run` est utilisée.
- [ ] **CA-16 — Alias `/ai-lab`.**
  - `sed -n 2p skills/ai-lab/SKILL.md` = `name: ai-lab`.
  - `grep -F -- "--profile research" skills/ai-lab/SKILL.md` ≥ 1, `grep -F "software-factory" skills/ai-lab/SKILL.md` ≥ 1, `grep -c "context: fork" skills/ai-lab/SKILL.md` = 0, `wc -l < skills/ai-lab/SKILL.md` ≤ 40.
- [ ] **CA-17 — Alias d'audit.** Pour `n` ∈ {legacy-audit, vibecode-audit, ai-lab-audit} :
  - `sed -n 2p skills/$n/SKILL.md` = `name: $n` ;
  - `grep -F "est un alias de \`/audit\`" skills/$n/SKILL.md` ≥ 1, `grep -F "retiré à la version suivante"` ≥ 1, `grep -c "context: fork"` = 0, `wc -l` ≤ 40.

  `test_aliases` vérifie la traduction AX-05 sur le tableau d'entrées suivant : `--categories "hygiene;qualite"`, `--axes "maintenabilite"`, `--axes "securite;evolutivite"`, `--max-specs 99` (borné à 25), `--lenses "validite"`, `--models "math=fable"`, chemin avec espaces.
- [ ] **CA-18 — Sélection des lentilles.** `K audit plan` rend :
  - tampon `{software}` → 9 lentilles ;
  - `--profile research` → 5 lentilles, quel que soit le tampon ;
  - `--lenses "securite;fuites"` avec les deux profils → `acces, injection, metier, fuites` ;
  - `--profile research --lenses hygiene` → exit 2 ;
  - `--max-questions 3` sans `research` → exit 2 ;
  - 14 lentilles → vagues `[5, 5, 4]`, une lentille par auditeur.
- [ ] **CA-19 — Propriétés de lentille.** Un test par ligne de LN-01, en rejeu :
  1. section groupée par `debt`, et texte de distinction présent ;
  2. 12 occurrences → 5 conservées, `count: 12`, `sampled: true`, et `SPLIT` refusé sur une lentille `occurrence` ;
  3. un critical `evolutivite` est classé avant un major `acces`, et `regression_risk` est sans effet ;
  4. une lentille `vibecode` morte deux fois → finding « surface non auditable » major ; une lentille `legacy` ou `research` morte deux fois → « non auditée » avec `échec` ;
  5. une fiche `Q-*` avec une clé `predictions` → exit 2, et le fragment `fidelite` est le seul à porter `test-cpu` ;
  6. le prompt de validateur rendu pour `validite`, `route` et `bio` contient la consigne de grep, et une entrée de journal postérieure à l'audit pose `TRANCHEE (journal <date>)`.
- [ ] **CA-20 — `AUDIT.md` unique.** Rejeu sur chaque fixture :
  - `AUDIT.md` et les specs sont égaux à `audit-expected/<p>/` (date fixée) ;
  - FD-11 ne trouve rien ;
  - `git status --porcelain` du projet temporaire ne liste ni `ROADMAP-legacy.md`, ni `AUDIT-vibecode.md`, ni `AUDIT-lab.md`, ni aucun chemin hors de `AUDIT.md`, `specs/` et `.harness/runs/` (`.claude/` est exclu par RG-05) ;
  - sur `profile-research`, la ligne `Lancer : \`/factory-run --profile research "` est présente.
- [ ] **CA-21 — Migration.** Projet temporaire = `profile-software` + `audit-legacy-deliverables` :
  - `AUDIT.md` contient `LEG-03` à `FAIT`, `VIB-02` à `EN_COURS`, `Q-01` à `TRANCHEE (journal 2026-09-12)` (avec `research` forcé), et de nouveaux ids à partir de `LEG-04` et `VIB-03` ;
  - les trois anciens fichiers et `SPEC-leg-03-gitignore.md` sont identiques (`cmp`) ;
  - une seconde exécution donne un `AUDIT.md` identique (`cmp`), avec 3 lignes `harness:import` ;
  - un ancien fichier modifié ensuite → avertissement, sans réimport.
- [ ] **CA-22 — Non-régression.** `test_audit_nonreg` → la différence NR-02 est égale à `expected-gaps.json`. Contrôle croisé : `for id in $(grep -oE '\bE-[AI][0-9]+\b' S | sort -u); do grep -q "\"$id\"" tests/fixtures/audit-nonreg/expected-gaps.json || echo "$id"; done` → aucune sortie, et réciproquement.
- [ ] **CA-23 — Catalogue des gates.** Chaque id parmi `software-factory.profiles`, `factory-run.profile`, `audit.profiles`, `audit.drop-security`, `audit.software.framing`, `audit.software.assignment`, `audit.research.framing`, `audit.research.selection`, `audit.final` :
  - est trouvé par `grep -rF` dans `skills/software-factory/SKILL.md`, `skills/audit/SKILL.md` ou `skills/_core/profiles/` ;
  - a un défaut justifié et un repli headless dans le catalogue (`K gate list`) ;
  - seules `software-factory.profiles` et `audit.profiles` portent `phase2_auto: true`.
- [ ] **CA-24 — Journal.** `K journal validate` → exit 0 sur les journaux des rejeux. Les noms vérifient `^(software-factory|factory-run|lab-run|audit|…)-[0-9]{8}-[0-9]{6}\.jsonl$`, avec les noms de JR-01 plus `audit`. Le journal d'installation contient une ligne `agent: harness-scout`, et celui d'un alias, un événement `alias`.
- [ ] **CA-25 — Modèle du scout.** `models.json` absent → `harness.scout` résolu en `haiku`, `pass_param: true`. `--models "harness.scout=inherit"` → `pass_param: false`. Les autres rôles absents restent `inherit` (MD-02).
- [ ] **CA-26 — Frontmatter.**
  - Pour les 8 skills de `BASE2` : `diff <(git show <BASE2>:$f | sed -n 2p) <(sed -n 2p $f)` est vide.
  - `skills/audit/SKILL.md` : première ligne `---`, `name: audit`, `description:` non vide.
  - `grep -c "disable-model-invocation" skills/audit/SKILL.md skills/software-factory/SKILL.md` = 0 pour chacun.
- [ ] **CA-27 — README.**
  - `grep -F "## Profils" README.md` ≥ 1, `grep -F "### \`audit\`" README.md` ≥ 1, `grep -F -- "--rescan" README.md` ≥ 1, `grep -F ".claude/harness.json" README.md` ≥ 1.
  - Chaque section d'alias mentionne « alias ».
- [ ] **CA-28 — Fichiers hors périmètre intacts.** `git diff --exit-code <BASE2> -- install_skills.sh install_skills.ps1 skills/ship-pr skills/brainstorm skills/code-index` → exit 0.
- [ ] **CA-29 — Aucun artefact parasite.** `git status --porcelain` ne liste ni `__pycache__`, ni `.pyc`, ni journal, ni `findings.jsonl`, ni `scout-*.json`, ni fichier de transit.
- [ ] **CA-30 — Fixtures inertes.** `find tests/fixtures -name CLAUDE.md -o -name '.*' -not -name '.' | grep -v '^tests/fixtures$'` → aucune sortie.
- [ ] **CA-31 — Profils copiés dans les projets.** Après `K sf copy-core --root <tmp>` : `diff -r -x __pycache__ skills/_core/profiles <tmp>/.claude/harness/profiles` est vide, et `diff -r -x __pycache__ skills/_core .claude/harness` est vide dans ce dépôt (L10).

**Recettes par l'utilisateur, hors portes du Verifier :**
- **R8** (L0) : depuis un skill sonde sans `context: fork`, l'outil Skill invoque `software-factory` et `audit` avec des arguments, en interactif puis en headless. En cas d'échec, appliquer le repli AX-01 (lecture de `${CLAUDE_SKILL_DIR}/../<skill>/SKILL.md`).
- **R9** : `/legacy-audit` et `/vibecode-audit` à `BASE2` puis `/audit --profile software` sur `profile-software` ; `/ai-lab-audit` à `BASE2` puis `/audit --profile research` sur `profile-research`. Écarts hors `E-*` listés un par un.
- **R10** : `/software-factory` sur `profile-mixed`, puis `/software-factory --rescan` sans changement : aucune gate, aucune écriture.
- **R11** : `/audit` dans `/skills` : pas de conflit avec une commande intégrée ou un plugin du même nom.

## Hors-périmètre

- Le tampon complet de la Phase 3 (version, date, skills et options), `--upgrade`, `/harness-doctor` et sa proposition de `--rescan`, la migration des orchestrateurs sans blocs.
- La politique `auto` effective pour toute gate autre que `software-factory.profiles` et `audit.profiles`. Les fichiers `STOP-*.md`, l'état `BLOQUEE`, les enchaînements audit → factory-run → ship-pr (Phase 4).
- Le retrait d'un profil, la suppression des anciens livrables, et le retrait des alias d'audit (version suivante).
- Tout nouveau profil (infra/ansible, data pipeline, firmware) : seul le mécanisme est livré et testé par `profile-toy`.
- Les hooks Claude Code, la file et les worktrees, le packaging.
- La modification de `ship-pr`, `brainstorm`, `code-index` et des installeurs.
- La règle « code en anglais » dans les gabarits d'agents générés (BACKLOG §7).
- Tout commit, push, `/ship-pr` ou exécution de `install_skills.*` par le Builder.

## Risques

- **[IMPOSSIBLE] I1 — Blocs délimités dans `settings.json`.** La ROADMAP §2.2 veut régénérer « les blocs délimités des fichiers partagés (`settings.json`, …) ». Un JSON strict n'a pas de commentaires, donc pas de marqueurs.
  - Remplacement : l'union additive FU-01, idempotente.
  - Conséquence : on ne sait pas quelle entrée appartient à quel profil. Le retrait d'un profil n'est donc pas faisable proprement, ce qui conforte HJ-03 jusqu'à la Phase 3.
- **[IMPOSSIBLE] I2 — Agent fichier `harness-scout` global.** Les installeurs ne lient que des skills, et un skill ne peut pas installer un agent global. Le scout est donc un sous-agent dynamique (Explore + prompt + paramètre `model`). Son nom n'existe que dans le journal.
- **[IMPOSSIBLE] I3 — `/lab-run` comme alias par invocation.** `factory-run` porte `disable-model-invocation: true` (`software-factory:49`), et l'outil Skill ne peut pas l'invoquer. D'où LP-06 : une seconde instance du gabarit. Pour la même raison, `skills/audit` et `software-factory` ne doivent jamais recevoir ce champ, sinon les alias cassent (CA-26).
- **[DOC] I4 — Imbrication.** Un sous-agent peut lancer des sous-agents jusqu'à 3 niveaux (BACKLOG §5). Un alias en `context: fork` donnerait : alias → audit → auditeur → validateur, soit 4 niveaux. Les alias sont donc en ligne (AX-01, AX-04). R8 vérifie l'invocation par l'outil Skill.
- **[DOC] I5 — `${CLAUDE_SKILL_DIR}/../<autre skill>`** : la lecture du dossier d'un autre skill n'est pas documentée (BACKLOG §5). R1 l'a validée pour `_core` seulement. Le repli AX-01 repose sur la même hypothèse, vérifiée par R8.
- **[DOC] I6 — `CLAUDE.md` imbriqués.** Claude Code charge les `CLAUDE.md` des sous-dossiers quand il lit des fichiers dans ces sous-dossiers. Un `tests/fixtures/profile-research/CLAUDE.md` contaminerait les sessions de ce dépôt, d'où la convention de renommage (CA-30).
- **Noyau bloqué sur les projets de la Phase 1.** `copy-core` refuse un `.claude/harness/` différent (EP-07). `--rescan` et la réinstallation s'arrêtent donc sur ces projets jusqu'à `--upgrade` (Phase 3). Ils continuent de fonctionner avec leur copie (règle de rétrocompatibilité).
- **Seuils du scout.** Les poids et seuils `accept`/`reject` sont calibrés sur trois fixtures. Un vrai projet de recherche peut tomber en `uncertain`, ce qui bloque en `auto` (AR-02) et pose une question en `gate`. Le journal du scout permet de recalibrer, en ne changeant que le profil.
- **Moteur de boucle fermé.** Un futur profil qui a besoin d'un type de phase inconnu (LP-02) imposera une modification du noyau. « Ajouter un profil = ajouter un dossier » ne vaut qu'à types de phase constants.
- **Extraction par phrases.** PX-03 détecte une phrase perdue, pas une phrase déplacée hors de son contexte. Les fragments sont relus par le Verifier contre `base2/`.
- **Contrats de format.** Les fragments de lentille et les adaptateurs FD-05 sont liés : modifier une taxonomie sans son schéma casse le parseur. CA-19 et CA-20 couvrent le lien.
- **Volume en profil mixte.** 14 lentilles en 3 vagues, plus autant de validateurs : coût et durée accrus, sollicitations de permission Bash plus nombreuses. À mesurer par le journal.
- **`code-index` câble `lab-run`** (`code-index:154`). L'instance LP-06 conserve le fichier, donc le câblage reste valide. Un bloc `rgkb` posé avant la Phase 2 sur un `lab-run` sans blocs de profil reste `personnalisé-conservé`.

## Questions ouvertes

Chaque question est déjà tranchée par défaut ; la justification tient en une ligne.

- **Q1 — Forme des profils.** Défaut : `profile.json`, plus des fragments Markdown référencés. Justification : la stdlib n'a pas de YAML, et la prose des rôles et des lentilles reste lisible en Markdown, sans échappement JSON.
- **Q2 — `auto` en Phase 2.** Défaut : appliqué à `software-factory.profiles` et `audit.profiles` seulement (AR-02), GT-03 partout ailleurs. Justification : §2.2 définit cet arbitrage dans la Phase 2, et §4.2 renvoie le reste à la Phase 4.
- **Q3 — Règle de « domination nette ».** Défaut : classement absolu par profil, avec `accept`/`reject`, et `clear` = aucun profil `uncertain`. Justification : avec le cumul, une domination relative entre profils n'a pas de sens.
- **Q4 — Sort de `/lab-run`** (Q3 du BACKLOG). Défaut : instance du gabarit commun, profil `research` imposé (LP-06). Justification : une seule implémentation (§2.1), sans invocation impossible (I3), et `ci/lab.*` reste compatible.
- **Q5 — `/ai-lab` sans échéance.** Défaut : pas d'avertissement (AX-02). Justification : §2.2 « pour ne rien casser » est plus précis que la règle commune.
- **Q6 — Regroupement des lentilles.** Défaut : vagues de 5 au plus, une lentille par auditeur (AD-04). Justification : préserve « sa lentille et rien d'autre » des trois audits.
- **Q7 — Motifs VIB en specs.** Défaut : seulement si `legacy` est actif dans le même run (SO-02). Justification : c'est la chaîne « vibecode → legacy en aval » d'aujourd'hui, faite en un passage.
- **Q8 — Scout sur `/audit` d'un projet non équipé.** Défaut : verdict utilisé et non écrit dans le tampon. Justification : `/audit` est en lecture seule sur le projet audité.
- **Q9 — Défaut du modèle `harness.scout`.** Défaut : `haiku`. Justification : la ROADMAP exige « modèle économique », ce qui prime sur MD-02 pour ce rôle seulement.
- **Q10 — Retrait d'un profil.** Défaut : aucun mécanisme en Phase 2 ; `vanished` est seulement rapporté. Justification : I1 rend le retrait non sûr, et la ROADMAP ne demande que l'ajout.
- **Q11 — Plafond des alias.** Défaut : ≤ 40 lignes par alias (CA-16, CA-17). Justification : un alias qui porte des règles redeviendrait une seconde implémentation.

---

Fichiers lus pour cette spec :
- `C:\Users\fuzzz\claude-skills\specs\harness-v2\ROADMAP.md`
- `C:\Users\fuzzz\claude-skills\specs\harness-v2\BACKLOG.md`
- `C:\Users\fuzzz\claude-skills\specs\SPEC-noyau-core-journal.md`
- `C:\Users\fuzzz\claude-skills\specs\SPEC-phase1-rebranchement.md`
- `C:\Users\fuzzz\claude-skills\skills\*\SKILL.md` (les 8)
- `C:\Users\fuzzz\claude-skills\skills\_core\harness.py`
- `C:\Users\fuzzz\claude-skills\skills\_core\hcore\fusion.py`, `factory.py`, `models.py`, `journal.py`, `blocks.py`, `registry.py`
- `C:\Users\fuzzz\claude-skills\tests\fixtures\README.md`
- `C:\Users\fuzzz\claude-skills\README.md`
- `C:\Users\fuzzz\claude-skills\.claude\skills\factory-run\SKILL.md`

Écart à signaler avant d'utiliser cette spec : sur `v2/phase-1-core`, la Phase 1 n'est pas livrée. Les modules `gates.py`, `findings.py`, `audit.py`, `stack.py`, `tshirt.py` et `labrun.py` n'existent pas encore, et les SKILL.md des audits et d'ai-lab sont dans leur état d'avant rebranchement. La spec suppose donc la Phase 1 mergée (lot L0, `BASE2`).