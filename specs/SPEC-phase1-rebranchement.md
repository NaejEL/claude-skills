# SPEC — Fin de la Phase 1 : briques manquantes du noyau `_core` et rebranchement des six skills restants

Statut : APPROUVEE (2026-10-17, décisions ci-dessous)

Phase 1 de `specs/harness-v2/ROADMAP.md`. L'utilisateur a levé le gel « 10 cycles » du BACKLOG et demande que toutes les phases soient livrées. Cette spec ne couvre que la fin de la Phase 1. Elle fait suite à `specs/SPEC-noyau-core-journal.md` (spec 0), dont elle reprend les conventions : identifiants de règle, `<PY>`, rejeux scriptés, cible −⅓.

## Décisions (2026-10-17)

Règle de l'utilisateur : la ROADMAP fait foi ; une règle héritée qui la contredit est modifiée ou retirée.

- **X1** : on applique la ROADMAP. `model:` est écrit dans le frontmatter des agents fichiers générés, dans un bloc délimité régénérable, **et** l'outil Agent reçoit le paramètre `model`. La règle contraire `ai-lab:135` est retirée. Remplace le défaut proposé pour Q2.
- **X2** : les clés `lab.*` sont les clés réelles d'ai-lab (`ai-lab:147-155`).
- **X3** : `rgkb.py` garde une implémentation autonome des blocs, parce qu'il est copié seul. Un test d'équivalence le lie à `hcore/blocks.py`, et la divergence sur le marqueur de fin absent est corrigée dans le sens du noyau.
- **X4** : registre projet `.claude/findings.jsonl`, local, ajouté à `.git/info/exclude`, une ligne par finding (compacté) ; registres de run en événements (X11). La dédup inter-skills est un comportement nouveau voulu par la ROADMAP.
- **X5** : journal partout. Les audits déclarent `.claude/runs/` dans leurs écritures autorisées. brainstorm n'écrit rien avant sa gate finale ; son journal est écrit à ce moment-là.
- **X6** : `--models "role=modele;…"` sur tous les orchestrateurs (factory-run, ship-pr, audits, ai-lab). Sans l'option, le comportement est inchangé.
- **X7** : conversion verdict du Verifier → schéma de finding partielle, et documentée comme telle.
- **X8** : valeur de modèle inconnue = erreur explicite, dans le fichier comme dans `--models` (D8). `ai-lab:158` est aligné.
- **X9** : code-index exige Python ≥ 3.9, détecté par le noyau. Ce prérequis est documenté.
- **X10** : la ROADMAP demande des « profils prêts à l'installation » : on fournit les préréglages d'ai-lab et un préréglage `economy`/`quality` générique pour la factory et les audits, en données dans `models.py`.
- **X11** : voir X4.
- Les autres questions prennent les défauts proposés plus bas. Q-G1 : `auto` est appliqué comme `gate` tant que la Phase 4 n'est pas livrée.

## Contexte

**Le besoin.**
- Compléter le noyau avec les briques Phase 1 qui manquent : gate, schéma de finding unique, registre projet, modèles par rôle, détection de stack, estimation T-shirt, fusion générique.
- Rebrancher, un commit par skill : code-index (avec D8), ai-lab, ai-lab-audit, legacy-audit, vibecode-audit et brainstorm.
- Régénérer l'usine de ce dépôt (incrément 1 du BACKLOG).
- Règle : **comportement observable identique avant/après, sauf le journal**. Les écarts proposés sont listés plus bas, un par un.

**Référence.** `BASE1=031df12` (HEAD au début de cette phase).

**Avertissement : arbre de travail modifié pendant la lecture.** Le statut git était propre au départ. Pendant l'exploration, plusieurs fichiers de `skills/_core/` ont changé :
- `runs.py` : verrou `runs.locked`, `LockTimeout`, reprise de `os.replace` sous Windows.
- `harness.py` : `journal amend`, `ship-pr drop`, `--summary-file`, `--not-fixed-file`, `--trailer`, `--title-file`, retrait des fichiers de transit, `copy-core` bloqué = exit 1.
- `registry.py` : nouveau statut `DUPLICATE`.
- Nouveau test : `tests/test_runs_lock.py`.

Ce sont les corrections du BACKLOG §7, en cours, non commitées. `skills/ship-pr/SKILL.md:89` passe encore `--summary "<résumé>"` par le shell. Le lot L1 finalise ce travail, quel que soit son auteur.

### État du noyau, brique par brique (vérifié)

| Brique ROADMAP | État dans `_core` | Écart à combler |
| --- | --- | --- |
| Gate | **Absente.** Les 27 points `AskUserQuestion` sont en prose (tableau GT). | Primitive, catalogue, journalisation. |
| Finding + validateur | **Partiel.** `verdicts.py` parse 3 formats : Verifier (`:57`), relecteur ship-pr (`:85`), validateur ship-pr (`:115`). Les 3 formats d'auditeur et les 3 de validateur des audits sont en prose (`legacy-audit:52-68`, `ai-lab-audit:57-75`, `vibecode-audit:64-93`). Aucun schéma unique, aucune conversion. `ghflow.comment_body` (`:162`) est la seule conversion existante. | Schéma, validateur, adaptateurs, 3 conversions. |
| Registre cumulatif | **Run seulement.** `registry.py` : registre de run, clé `file::titre normalisé` (`:29`), statuts D2 plus `DUPLICATE`. Rien au niveau du projet. | Registre projet (RG). |
| Modèles par rôle | **Module non branché.** `models.py` : jeu de rôles ouvert, valeur inconnue dans le fichier = erreur (`:50`), aucune migration de `lab-models.json`. | Rôles fermés, migration, câblage. |
| Détection de stack | **Absente.** Six copies en prose : `software-factory:31`, `ai-lab:29`, `code-index:49`, `legacy-audit:34`, `vibecode-audit:40`, `ai-lab-audit:35`. Seule la table `STACK_DENY` est dans `fusion.py:37`. | Une copie (ST). |
| T-shirt | **Absente.** Barèmes en prose : `legacy-audit:50`, `ai-lab-audit:66` (barème GPU en plus), `vibecode-audit:61`. | Une copie (TS). |
| Fusion settings et blocs | **Unique mais spécifique à la factory.** `fusion.py` code en dur les règles `deny` (`:37-45`), les tâches Factory (`:53-74`) et les lignes `.gitignore` (`:45`). code-index ne peut pas s'en servir tel quel : il a besoin de `allow`, `enabledMcpjsonServers`, `.mcp.json`, ses propres tâches, `exclude` de `config.json`. `blocks.py` est générique mais n'est utilisé par aucun skill. `rgkb.py:766-838` a **sa propre** implémentation des blocs `# >>> rgkb >>>`, qui diverge : un marqueur de fin absent tronque le fichier (`rgkb.py:825-826`), là où `blocks.py:39-40` lève `BlockError`. | Moteur générique (FU), blocs (BK), voir X3. |
| Journal | `journal.py:22-23` limite les noms à `factory-run` et `ship-pr`. Les lignes sont toutes de type agent. | Noms étendus, événements `gate`. |

**Autres faits établis par lecture.**
- D8 est confirmé : `rgkb.py:568` réécrit `config.json` avec `DEFAULT_CONFIG`.
- `rgkb.py:845-852` (`set_config_hooks`) écrase aussi `config.json` avec `DEFAULT_CONFIG` quand le JSON est illisible. C'est la même famille de perte de données.
- `rgkb.py` est copié seul dans les projets, sous `.claude/rgkb/`. Il n'a pas accès à `_core`.
- C1 est confirmé : `.claude/agents/factory-planner.md:13` ne liste que 5 skills sur 8, et `.claude/skills/factory-run/SKILL.md` n'a pas la règle « Verifier muet ».
- C1 encore : les portes de l'usine du dépôt ne connaissent que `bash -n` et `bats` (`factory-builder.md:28-32`), pas `unittest`.
- `ci/factory.sh:61` n'autorise aucun interpréteur Python.
- Les installeurs lient tout sous-dossier (`install_skills.sh:176`, `install_skills.ps1:168`).

**Tailles à `BASE1`** (comptées par Read ; le Builder les confirme par `git show 031df12:<f> | wc -l`) :

| Fichier | Lignes | Cible ⌊2/3⌋ |
| --- | --- | --- |
| `skills/code-index/SKILL.md` | 189 | ≤ 126 |
| `skills/ai-lab/SKILL.md` | 231 | ≤ 154 |
| `skills/ai-lab-audit/SKILL.md` | 145 | ≤ 96 |
| `skills/legacy-audit/SKILL.md` | 163 | ≤ 108 |
| `skills/vibecode-audit/SKILL.md` | 191 | ≤ 127 |
| `skills/brainstorm/SKILL.md` | 103 | ≤ 68 (conditionnelle, voir X5) |
| `skills/software-factory/SKILL.md` | 96 | reste ≤ 96 |
| `skills/ship-pr/SKILL.md` | 112 | reste ≤ 118 |

## Périmètre

### 1. Briques du noyau (règles déplacées ou créées)

**Gate — `hcore/gates.py`**
- `GT-01` : la politique est lue dans `.claude/harness.json`, clé `autonomy` ∈ {`gate`, `auto`}. Fichier ou clé absents → `gate`. Valeur invalide ou JSON illisible → exit 2.
- `GT-02` : table de décision. En `gate` : `ask` pour a, b et c. En `auto` : `default` pour b et c, `ask` pour a.
- `GT-03` : garde Phase 1. Une valeur `auto` est appliquée comme `gate`, avec un avertissement journalisé (Q-G1).
- `GT-04` : une gate de dialogue (`brainstorm.*`) rend toujours `ask` (ROADMAP 4.2 : « brainstorm reste intrinsèquement dialogué »).
- `GT-05` : une gate sans défaut dont la décision serait `default` → `stop` (exit 1, message).
- `GT-06` : chaque gate déclare un repli headless (`stop` | `default` | `skip`), rendu avec la décision. Le skill l'applique quand AskUserQuestion est indisponible, et le déclare comme tel.
- `GT-07` : deux événements `gate` sont journalisés, la décision puis la réponse : id, kind, policy, decision, default, answer, source ∈ `user|default|headless`.
- `GT-08` : un catalogue unique des 27 gates (tableau ci-dessous). Chaque entrée porte id, kind, options, défaut avec justification d'une ligne, et repli headless. Un id inconnu → exit 2.

**Catalogue des gates** (classement : proposition du BACKLOG §4). Les options sont citées telles qu'à `BASE1`. Le repli headless reproduit le comportement actuel ; `C3` signale un comportement aujourd'hui non spécifié.

| ID | Source | Type | Options (BASE1) | Défaut déclaré — justification | Repli headless |
| --- | --- | --- | --- | --- | --- |
| `software-factory.code-index` | software-factory:92 | b | installer / refus | ne pas installer — la base ajoute un dossier versionné, « ce qui se décide » | skip |
| `factory-run.questions` | software-factory:54 | b | options du brouillon | aucun — rien à inventer (BLOQUEE arrive en Phase 4) | stop |
| `factory-run.approval` | software-factory:54 | c | approbation / itérer | approuver (ROADMAP 4.2), effectif seulement en `auto` | stop |
| `factory-run.need` (usine du dépôt) | `.claude/skills/factory-run/SKILL.md:16` | c | saisie libre | aucun | stop |
| `ship-pr.target` | ship-pr:29 | c | saisie | aucun — la cible ne se devine pas | stop (C3) |
| `ship-pr.dirty` | ship-pr:46 | a | commiter maintenant / stash / abandonner | abandonner — seule option qui n'écrit rien | default (C3) |
| `ship-pr.conflict` | ship-pr:53 | b | résoudre maintenant / continuer la revue quand même / abandonner | continuer la revue — non destructif, le merge garde sa gate | default (C3) |
| `ship-pr.merge` | ship-pr:98 | a | Merger / Laisser la PR ouverte | Laisser la PR ouverte — irréversible | default (C3) |
| `code-index.rg-install` | code-index:38 | c | commande retenue / repli local | ne pas installer, repli local signalé — dépendance système | skip |
| `code-index.hooks` | code-index:113 | b | `hooks install` / `--with-commit` / refus | `hooks install` (le « par défaut » de :113) | skip |
| `ai-lab.models` | ai-lab:137-142 | b | Tout hérité / experts / interprétation / Sur-mesure | Tout hérité — aucun surcoût | default (C3) |
| `ai-lab.code-index` | ai-lab:225 | b | installer / refus | ne pas installer | skip |
| `lab-run.pi-questions` | ai-lab:180 | b | questions pour le PI | aucun | stop |
| `lab-run.preregistration` | ai-lab:180 | a | approbation / itérer | aucun — pas de mesure sans protocole approuvé | stop |
| `lab-run.consignation` | ai-lab:188 | c | approbation | consigner, marqué « à relire » (ai-lab:188) | default |
| `legacy-audit.framing` | legacy-audit:84 | b | 2 / 3 / 4 ; risque d'abord / quick wins / fondations / ordre proposé | 3 jalons, risque d'abord (≈ « fiabiliser d'abord », ROADMAP 4.2) | stop |
| `legacy-audit.assignment` | legacy-audit:85 | b | Jalon 1 / Jalon 2 / Jalon dernier / Exclure de la roadmap | aucun (le calcul est en Phase 4) | stop |
| `legacy-audit.final` | legacy-audit:87 | c | Générer roadmap + specs / Réajuster / Abandonner | Générer | stop |
| `ai-lab-audit.framing` | ai-lab-audit:92 | b | specs / lister / ignorer les mineures ; fiabiliser / moins cher / feuille de route / ordre proposé | specs si factory présente, sinon liste ; fiabiliser d'abord | stop |
| `ai-lab-audit.selection` | ai-lab-audit:93 | b | Toutes / Seulement la mieux classée / Aucune | Toutes (le plafond s'applique après) | stop |
| `ai-lab-audit.final` | ai-lab-audit:95 | c | Écrire AUDIT-lab.md / Réajuster / Abandonner | Écrire | stop |
| `vibecode-audit.drop-security` | vibecode-audit:20 | b | confirmer le retrait / garder | garder `securite` — l'axe prioritaire | default (C3) |
| `vibecode-audit.order` | vibecode-audit:115-116 | b | Gravité d'abord… / Gains rapides… / Tout ce qui bloque… / Garder l'ordre ; Les détailler / Les lister en une ligne / Les omettre | Gravité d'abord (marqué défaut :115) ; Les détailler (rien n'est perdu) | default (:33) |
| `vibecode-audit.final` | vibecode-audit:120 | c | Écrire AUDIT-vibecode.md / Réajuster / Abandonner | Écrire | default (:33) |
| `brainstorm.subject` | brainstorm:16 | c, dialogue | saisie libre | aucun | stop |
| `brainstorm.round` | brainstorm:67 | b, dialogue | Creuser / Écarter / Amender ; continuer / converger | aucun | stop |
| `brainstorm.write` | brainstorm:103 | c, dialogue | Écrire la synthèse / Ne rien écrire | Ne rien écrire | stop |

**Finding — `hcore/findings.py`**
- `FD-01` : le schéma porte les champs suivants.
  - Obligatoires : `id`, `source` (skill), `severity` ∈ {critical, major, minor}, `axis` (lentille, famille, axe ou thème), `title`, `status`.
  - `evidence` : `{kind: code|journal|structural, file, lines: {start, end}, excerpt, journal_date}`.
  - `occurrences[]` : `{file, line, excerpt}`, avec `count` et `sampled`.
  - `fix_commit`.
  - Optionnels : `nature`, `size`, `depends_on`, `impact`, `remediation`, `regression_risk`, `risk_rationale`, `reason`, `raw` (sortie d'origine).
- `FD-02` : statuts, en sur-ensemble de D2 (tableau ci-dessous), avec les transitions autorisées.
- `FD-03` : validateur `finding validate <fichier>`. Exit 0 si conforme, sinon exit ≠ 0 avec la liste des erreurs.
- `FD-04` : un extrait de plus de 3 lignes (`legacy-audit:25`, `ai-lab-audit:27`, `vibecode-audit:31`) produit un avertissement, jamais un rejet : aujourd'hui, rien ne le vérifie.
- `FD-05` : adaptateurs sans perte vers le schéma, depuis 6 formats :
  - relecteur ship-pr (`ship-pr:74`) ;
  - auditeur legacy (`legacy-audit:52-56`) ;
  - auditeur ai-lab-audit (`ai-lab-audit:57-64`) ;
  - auditeur vibecode (`vibecode-audit:64-73`) ;
  - issue de Verifier factory (`software-factory:45`) ;
  - issue de Verifier labo (`ai-lab:128`).
- `FD-06` : un seul parseur de verdict de validateur, sur-ensemble des quatre formats (`ship-pr:81`, `legacy-audit:66-68`, `ai-lab-audit:74`, `vibecode-audit:89-93`). Les champs et la valeur `SPLIT` ne sont admis que pour la source qui les avait. Une sortie inexploitable = agent mort.
- `FD-07` : application d'un verdict : corrections de sévérité, d'axe, de taille, de nature, de difficulté ; retrait de `false_occurrences` et recalcul de `count` (`vibecode-audit:98`) ; scission (Q-F1).
- `FD-08` : finding → spec factory.
  - Première ligne `Statut : PROPOSEE`, titre `# SPEC-<préfixe>-<nn> — <titre>`.
  - Sections dans l'ordre de `legacy-audit:129-151` ; `Contexte` commence par « Finding <id> (<sévérité>, <taille>) : … ».
  - Le contenu des sections relevant du jugement est fourni par le skill dans un fichier.
  - Clauses imposées : réécriture d'historique en Hors-périmètre pour les secrets (`legacy-audit:126`) ; deux critères d'acceptation imposés pour `fuites` (`ai-lab-audit:134`).
- `FD-09` : finding → note rgkb : `{subject, text, tags, kind, source}`, accepté tel quel par `rgkb.py note-add` (`rgkb.py:1502-1508`).
- `FD-10` : finding → commentaire de PR. Le corps est identique octet pour octet à `ghflow.comment_body` (`ghflow.py:162-164`), qui l'appelle désormais.
- `FD-11` : contrôle des chaînes interdites dans tout livrable rendu : `Statut :` suivi de `APPROUVEE` ou de `PRE-ENREGISTRE` (`legacy-audit:24`, `ai-lab-audit:25`, `vibecode-audit:30`).

| Terme ROADMAP | Valeur du noyau | Origine |
| --- | --- | --- |
| proposé | `PROPOSED` | nouveau |
| validé | `CONFIRMED` | D2 |
| rejeté | `REJECTED`, `DUPLICATE` (écarté sans validateur) | D2, SP-07 |
| corrigé | `FIXED` + `fix_commit` | D2 |
| tranché | `SETTLED` + `settled_by` (`journal <date>` ou `user`) | `TRANCHEE` d'ai-lab-audit |
| — | `UNVALIDATED`, `NOT_FIXED` + `reason` | D2 (SP-06, SP-09) |

Les statuts de livrable (`A_FAIRE`, `EN_COURS`, `FAIT`, `REPORTE`, `TRANCHEE (journal <date>)`) restent un champ distinct, `deliverable_status`, en français : c'est un format partagé.

**Registre projet — `hcore/registry.py`**
- `RG-01` : fichier `.claude/findings.jsonl`, **une ligne par finding** (dernier état), triée par clé, réécrite atomiquement sous verrou.
- `RG-02` : la clé est la clé D2 (`finding_key`). Pour un motif à occurrences : `::<motif normalisé>`. Pour un finding sans fichier : `::<titre normalisé>`.
- `RG-03` : alimentation en fin de run depuis le registre de run.
  - Publiés : `REJECTED`, `FIXED`, `NOT_FIXED`, `SETTLED`.
  - `CONFIRMED` n'est publié que si le livrable qui le porte est écrit.
  - Ni `DUPLICATE` ni `UNVALIDATED` ne sont publiés.
  - Idempotent.
- `RG-04` : lecture au démarrage d'un run. Seuls `REJECTED` et `SETTLED` empêchent une résurrection : le finding est écarté avant tout validateur et noté `previous=<statut>@<source>`. `FIXED` et `NOT_FIXED` sont transmis comme historique sans écarter le finding : une régression de même titre doit pouvoir réapparaître.
- `RG-05` : exclusion git par `.git/info/exclude`, idempotente. Dépôt sans git : rien (Q-E).
- `RG-06` : verrou inter-processus, celui de `runs.locked`.
- `RG-07` : les registres de run D2 existants restent lisibles sans migration.

**Verrou et journal**
- `LK-01` : verrou exclusif par run pour tout cycle lecture → modification → écriture. Au-delà du délai, arrêt explicite (exit 1). Un verrou orphelin ne bloque jamais (présent dans l'arbre de travail, à finaliser en L1).
- `LK-02` : `os.replace` est retenté sous Windows en cas de `PermissionError`.
- `JR-01` : noms admis : `software-factory`, `factory-run`, `ship-pr`, `code-index`, `ai-lab`, `lab-run`, `ai-lab-audit`, `legacy-audit`, `vibecode-audit`, `brainstorm`.
- `JR-02` : événements typés. Une ligne sans `event` est une ligne d'agent (rétrocompatible avec les journaux existants) ; `event: "gate"` suit le schéma de GT-07.
- `JR-03` : `journal amend` complète une durée ou des tokens connus après l'appel (BACKLOG §7, présent dans l'arbre).

**Modèles — `hcore/models.py`**
- `MD-01` : jeu de rôles fermé :
  - `factory.planner`, `factory.builder`, `factory.verifier` ;
  - `shippr.reviewer`, `shippr.validator` ;
  - `audit.auditor`, `audit.validator` ;
  - `lab.director.cadrage`, `lab.director.interpretation`, `lab.neuro`, `lab.math`, `lab.builder`, `lab.verifier`, `lab.validator` (X2).
- `MD-02` : fichier absent → `inherit` partout.
- `MD-03` : valeur inconnue **dans le fichier** → `inherit` avec avertissement (`ai-lab:158`), voir X8.
- `MD-04` : `--models "r=m;…"` vaut pour le cycle seulement et ne réécrit jamais le fichier. Rôle ou valeur inconnus → exit 2 (`ai-lab:177`, `ai-lab-audit:18`).
- `MD-05` : migration lue une fois, jamais destructive. Si `models.json` est absent et `lab-models.json` présent, `models.json` est écrit avec les clés préfixées `lab.`, et `lab-models.json` reste intact octet pour octet. Si les deux fichiers existent, `lab-models.json` est ignoré avec un avertissement.
- `MD-06` : alias courts (`math`, `neuro`, `director.cadrage`, …, `validator` → `lab.validator`) acceptés dans `--models` de lab-run et d'ai-lab-audit.
- `MD-07` : la résolution rend `{model, pass_param}`. `inherit` → `pass_param: false`, le paramètre n'est pas passé (`ai-lab:177`).
- `MD-08` : les quatre préréglages d'ai-lab (`ai-lab:139-142`) deviennent des données. L'écriture fusionne : clés absentes complétées, clés existantes préservées (`ai-lab:144`).
- `MD-09` : pas de `model:` dans le frontmatter en Phase 1 (Q2, X1).

**Stack — `hcore/stack.py`**
- `ST-01` : union des marqueurs des six copies : `*.sln`, `*.csproj`, `pyproject.toml`, `requirements.txt`, `setup.py`, `environment.yml`, `*.ipynb`, `package.json`, `CMakeLists.txt`, `Makefile`, `go.mod`, `Cargo.toml`, `Dockerfile`, `docker-compose*.yml`, `compose*.yml`, `ansible.cfg`, `playbooks/`, `roles/`, `*.tf`. Racine et un niveau de sous-dossiers (`software-factory:31`).
- `ST-02` : sortie : marqueurs et chemins des manifestes trouvés, plus les stacks du noyau (`node`, `dotnet`, `python`, `cpp`, `rust`) qui alimentent SF-01. La lecture des manifestes reste au jugement.
- `ST-03` : liste des dossiers d'artefacts et volumineux, union de `legacy-audit:37` et `code-index:49`.
- `ST-04` : comptage des fichiers hors artefacts. Au-delà de 2000 : `sampled`, arborescence sur 3 niveaux, 40 fichiers par auditeur (`legacy-audit:37`, `vibecode-audit:47`).
- `ST-05` : un journal de plus de 1500 lignes → `sampled`, 15 dernières entrées (`ai-lab-audit:41`).

**T-shirt — `hcore/tshirt.py`**
- `TS-01` : énumération ordonnée XS…XL. Barème de développement : XS < 30 min, S < 2 h, M ½ j, L 1-2 j, XL à découper. Barème GPU d'`ai-lab-audit:66`.
- `TS-02` : un XL se découpe en au moins 2 specs ≤ L, chaînées (`legacy-audit:121`, `ai-lab-audit:134`). Les XS se regroupent par 4 au plus : même catégorie et même jalon (`legacy-audit:120`), ou même lentille (`ai-lab-audit:134`).
- `TS-03` : tris.
  - LEG et COR : sévérité décroissante, puis taille croissante (`legacy-audit:76`, `ai-lab-audit:83`).
  - Q : sévérité décroissante, puis coût croissant.
  - VIB : tous les critical en tête, tous axes confondus ; puis sécurité > maintenabilité > évolutivité ; puis difficulté croissante. `regression_risk` n'entre jamais dans un tri (`vibecode-audit:105-106`).
- `TS-04` : gains rapides = XS ou S de sévérité major ou critical, signalés sans remonter dans l'ordre (`vibecode-audit:108`).
- `TS-05` : charge cumulée et répartition des tailles par jalon ou par sélection (`legacy-audit:87`, `:160` ; `ai-lab-audit:95`).

**Fusion générique et blocs — `hcore/fusion.py`, `hcore/blocks.py`**
- `FU-01` : opérations JSON génériques :
  - union de tableau à un chemin ;
  - ajout de clé si absente, jamais d'écrasement ;
  - tâches dédoublonnées par `label`, inputs par `id`.

  JSONC, BOM et CRLF conservés ; tout ou rien ; états `créé`, `fusionné`, `identique`, `personnalisé-conservé`.
- `FU-02` : SF-01 à SF-03 réexprimés sur FU-01, sortie inchangée (fixtures `tests/fixtures/merge-*`).
- `FU-03` : lignes `.gitignore` génériques.
- `FU-04` : `install_file` (SF-04) pour tous les générateurs.
- `FU-05` : union dans la liste `tools:` du frontmatter, sans retrait (`code-index:129`, D7).
- `FU-06` : union dans la valeur `--allowedTools "…"` d'un script `ci/*`, sans retrait (`code-index:162`).
- `BK-01` : `blocks.py` porte le câblage `<!-- rgkb:debut -->` / `<!-- rgkb:fin -->` (`code-index:123`).
- `BK-02` : équivalence testée entre les blocs de hooks de `rgkb.py` et `blocks.py` sur entrées bien formées (X3).

**Moteur d'audit partagé — `hcore/audit.py`** (sans profil ni `/audit` : ce sont les fonctions communes aux trois audits)
- `AU-01` : le premier jeton qui ne commence pas par `--` est `REPO`, résolu en chemin absolu ; défaut : répertoire courant. Chemin inexistant → arrêt (`legacy-audit:15`, `ai-lab-audit:15`, `vibecode-audit:19`).
- `AU-02` : listes séparées par `;` (`--categories`, `--lenses`, `--axes`), défaut = toutes. Valeur inconnue → exit 2 (Q-J).
- `AU-03` : plafonds `min(N, cap)`, avec défaut. N non entier ou < 1 → exit 2 (Q-J).
- `AU-04` : lentille ou famille morte → une relance, puis l'issue propre au skill : « non auditée » avec `échec`, ou « surface non auditable » de sévérité major.
- `AU-05` : validateur mort deux fois → `UNVALIDATED`, jamais `CONFIRMED`.
- `AU-06` : dédup avant validateur contre le registre de run, la reprise et le registre projet, avec la clé propre à chaque skill.
- `AU-07` : zéro `CONFIRMED` → saut à la phase de rapport.
- `AU-08` : renumérotation par préfixe ; en reprise, la numérotation se poursuit.
- `AU-09` : reprise : les tableaux de `ROADMAP-legacy.md`, `AUDIT-lab.md` et `AUDIT-vibecode.md` sont relus vers le registre de run, statuts `FAIT`, `EN_COURS` et `TRANCHEE` préservés.
- `AU-10` : jeux de statuts de livrable propres à chaque skill.
- `AU-11` : FD-11 appliqué à tout fichier écrit.
- `AU-12` : `GIT_ABSENT` → plus aucune commande git ensuite, pas d'exclusion (`legacy-audit:33`, `vibecode-audit:39`).
- `AU-13` : compteurs du rapport par lentille : bruts, confirmés, rejetés ou dédupliqués, et selon le skill scindés et occurrences.
- `AU-14` : une spec existante n'est jamais écrasée (SF-04).
- `AU-15` : « Réajuster » une seule fois.
- `AU-16` : bornes des appels de gate : 4 thèmes au plus par appel, nombre maximal d'appels propre à chaque skill.

**Ce qui reste en prose dans le noyau : rien.** Les gabarits des livrables, en français, sont des **fichiers de données** sous `skills/_core/templates/` (format partagé), pas des chaînes dans le code.

### 2. Rebranchement, skill par skill (un commit chacun)

**code-index (lot L8)** — cible ≤ 126 lignes, ferme.

| ID | Règle | Source | Module |
| --- | --- | --- | --- |
| CX-01 | `--reindex`, `--no-wire` ; tout autre contenu est rappelé sans être interprété | :19-21 | `cx.py` |
| CX-02 | choix de la commande d'installation de rg par gestionnaire de paquets, repli local `rg_path` | :38-39 | `cx.py` |
| CX-03 | interpréteur par le PATH, jamais un venv (avec la contrainte de X9) | :41 | `interp.py` |
| CX-04 | relevé de l'état : git, usine, labo, installation antérieure, marqueurs, dossiers volumineux | :43-49 | `stack.py`, `cx.py` |
| CX-05 | copie de `rgkb.py` : absent → créé ; identique → rien ; `TOOL_VERSION` de l'asset ≥ → écrasé et annoncé ; projet > → conservé | :53-59 | `cx.py` |
| CX-06 | `.mcp.json` : `mcpServers.rgkb` ajouté si absent ; `py` → `-3` en tête de `args` ; jamais de chemin absolu | :63-76 | FU-01 |
| CX-07 | `settings.json` : `enabledMcpjsonServers` += rgkb ; `allow` += 7 outils de lecture + `Bash(<py> .claude/rgkb/rgkb.py *)`, jamais `note_add` ni `reindex` ; `deny` += `index.sqlite`, `graph.json` | :78-82 | FU-01 |
| CX-08 | `config.json` : `exclude` += `!<dossier>/**` pour chaque dossier volumineux détecté ; aucune suppression ; `rg_path` reste null | :88-92 | FU-01 |
| CX-09 | `init` ne réécrit jamais un `config.json` existant (D8) ; `set_config_hooks` ne remplace pas un JSON illisible (Q-K) ; `TOOL_VERSION` incrémenté | rgkb.py:568, :851 | `rgkb.py` |
| CX-10 | `.knowledge/` exclu par une règle → contre-règle `!.knowledge/**` en fin de fichier, précédée d'un commentaire d'une ligne, et rien d'autre | :107-108 | `cx.py` |
| CX-11 | hooks : gate `code-index.hooks` | :113 | GT |
| CX-12 | blocs `rgkb` réentrants dans les agents et skills détectés ; listes des cibles 6a, 6b, 6c | :123, :127, :143, :154 | BK-01 |
| CX-13 | `tools` += 7 outils de lecture dans les agents à `tools` limitatif | :129 | FU-05 |
| CX-14 | `--allowedTools` de `ci/factory.*` et `ci/lab.*` complété | :162 | FU-06 |
| CX-15 | `tasks.json` : input `rgkbQuery` et 5 tâches « Index: … », variante `windows` | :166-175 | FU-01 |
| CX-16 | état de chaque fichier au rapport | :31, :182 | FU |

Restent en prose :
- la raison d'être (« l'index se régénère, les notes ne se régénèrent pas ») ;
- les règles de versionnement et la liste à commiter ;
- l'explication des hooks, et pourquoi `post-checkout` est absent ;
- le **contenu rédigé** des blocs 6a, 6b et 6c (jugement : « rédigé pour l'agent concerné ») ;
- les contrôles de vraisemblance de l'index ;
- le rapport final.

**ai-lab et gabarit lab-run (lot L9)** — cible ≤ 154 lignes, ferme. Le gain vient des Phases 2b et 3 à 6 ; les blocs de frontmatter des agents sont condensés en ligne, comme dans software-factory.

| ID | Règle | Source | Module |
| --- | --- | --- | --- |
| AL-01 | `deny` : Python, générique, et données, poids, caches **présents** seulement | :207 | FU-01 |
| AL-02 | tâches : input `labProtocol`, 4 tâches « Lab: … », variantes `windows` | :211-219 | FU-01 |
| AL-03 | `.gitignore` += `lab-logs/`, `experiments/results/` et `.claude/runs/` (écart E2) | :203 | FU-03 |
| AL-04 | fichiers générés jamais écrasés ; états | :20, :22 | FU-04 |
| AL-05 | `models.json` remplace `lab-models.json` (migration MD-05) | :144-158 | MD |
| AL-06 | préréglages de modèles comme données ; gate `ai-lab.models` | :137-142 | MD-08, GT |
| AL-07 | `ci/lab.*` : argument obligatoire, vérification de la ligne de statut pré-enregistrée, `--max-turns 150`, liste blanche avec l'interpréteur du noyau, `lab-logs/`, exit code propagé | :195-201 | gabarit |
| AL-08 | noyau copié sous `.claude/harness/` (écart E1) | — | `copy_core` |
| AL-09 | gate `ai-lab.code-index` | :225 | GT |
| LR-01 | résolution des modèles, `--models` pour le cycle seulement, `inherit` → paramètre non passé | :177 | MD |
| LR-02 | entrée : chemin sous `experiments/` dont la ligne de statut vaut la valeur pré-enregistrée → Build ; `--models` retiré au préalable | :178 | `labrun.py` |
| LR-03 | expert mort → une relance → « expertise <neuro\|math> non recueillie » | :179 | `relaunch.py` |
| LR-04 | gates `lab-run.pi-questions` et `lab-run.preregistration` ; statuts PROPOSE → pré-enregistré | :180 | GT |
| LR-05 | succès si et seulement si `APPROVED` et `tests_passed`, `protocol_followed`, `rerun_consistent` à vrai ; 3 itérations, puis échec et entrée « expérience invalidée » | :184-186 | `labrun.py` |
| LR-06 | Builder ou Verifier mort → une relance sans consommer d'itération, puis échec (C2, écart E3) | — | `relaunch.py` |
| LR-07 | interprétation croisée une seule fois, après approbation | :191 | `labrun.py` |
| LR-08 | gate `lab-run.consignation` ; statut `TERMINE — <verdict>` | :188 | GT |
| LR-09 | schéma du Verifier labo (`kind` ∈ protocol\|leak\|stats\|code\|convention) | :128 | `verdicts.py` |

Restent en prose :
- les cinq prompts d'agents : rôles, modes, interdits, sections ;
- la détection du corpus scientifique (1b, 1c) ;
- l'« économie du modèle le plus cher » ;
- le rapport final.

**ai-lab-audit (lot L10)** — cible ≤ 96 lignes, ferme. Règles partagées : AU-01 à AU-16, TS-01 à TS-05, FD, RG, ST-05.

| ID | Règle | Source |
| --- | --- | --- |
| AA-01 | lentilles `fidelite`, `validite`, `fuites`, `bio`, `route` ; `bio` retirée si le skill déclare l'absence d'inspiration biologique (le jugement reste au skill) | :16 |
| AA-02 | `--max-questions` : `min(N, 12)`, défaut 6 ; l'excédent va en « non retenues » | :17 |
| AA-03 | rôles et alias de `--models` | :18 |
| AA-04 | écritures limitées à `AUDIT-lab.md` et `specs/SPEC-lab-*.md` | :22 |
| AA-05 | `LAB` : présence des fichiers ; lentille → `subagent_type` (fid, val, fuites → lab-math ; bio → lab-neuro ; route → lab-director), sinon Explore | :37 |
| AA-06 | lentille → rôle de modèle | :38 |
| AA-07 | préfixes `FID`, `VAL`, `LEAK`, `BIO`, `ROAD` ; schéma d'auditeur avec `nature` et `journal_date` | :49-64 |
| AA-08 | dédup : même fichier et ligne, ou même document et date, et même lentille | :70 |
| AA-09 | `COR-nn` et `Q-nn`, avec leurs tris | :83 |
| AA-10 | `TRANCHEE (journal <date>)` posé quand le skill désigne une entrée postérieure à la date de l'audit (comparaison de dates déterministe) | :40 |
| AA-11 | rendu d'`AUDIT-lab.md` (gabarit), y compris la ligne « Lancer : /lab-run "<question>" » | :103-128 |
| AA-12 | specs `fuites` : deux critères d'acceptation imposés | :134 |
| AA-13 | gates `framing`, `selection` et `final` ; repli headless : stop avant la Phase 5 | :29, :92-95 |
| AA-14 | tableau du rapport par lentille | :141 |

Restent en prose :
- les cinq taxonomies de lentilles ;
- les questions du validateur, dont le grep du journal ;
- « pas de protocole dans le livrable » ;
- la distinction correction / question ;
- les règles de dépendance (jugement) ;
- le regroupement en thèmes ;
- la prochaine action.

**legacy-audit (lot L11)** — cible ≤ 108 lignes, ferme : le gabarit de roadmap et l'exemple de spec représentent à eux seuls environ 43 lignes.

| ID | Règle | Source |
| --- | --- | --- |
| LA-01 | familles `hygiene`, `portabilite`, `qualite`, `filet` ; préfixes `HYG`, `PORT`, `QUAL`, `FIL` | :16, :45-48 |
| LA-02 | `--max-specs` : `min(N, 25)`, défaut 15 ; l'excédent va en « non retenus » | :17, :122 |
| LA-03 | `GIT_ABSENT` → pré-finding hygiène | :33 |
| LA-04 | présence de la factory | :35 |
| LA-05 | schéma d'auditeur ; `critical` réservé aux secrets, bugs et pertes de données (consigne restée en prose, l'énumération est validée) | :52-59 |
| LA-06 | dédup : même fichier, ligne et catégorie | :63 |
| LA-07 | schéma du validateur avec `size_correction` | :66-68 |
| LA-08 | `LEG-nn`, avec son tri | :76 |
| LA-09 | rendu de `ROADMAP-legacy.md` ; statuts ; liens relatifs en `/` | :93-113 |
| LA-10 | correspondance finding → spec (1:1, regroupement XS, découpage XL, plafond dans l'ordre des jalons) | :119-122 |
| LA-11 | spec rendue par FD-08 au contrat factory | :126-152 |
| LA-12 | gates `framing`, `assignment` (3 appels au plus) et `final` ; repli headless : stop | :27, :84-87 |
| LA-13 | tableau du rapport par famille | :159 |

Restent en prose :
- les quatre taxonomies de familles ;
- les questions du validateur ;
- les dépendances structurelles évidentes ;
- le regroupement en 3 à 6 thèmes ;
- le contenu des sections de spec relevant du jugement ;
- l'avertissement sur les secrets.

**vibecode-audit (lot L12)** — cible ≤ 127 lignes, ferme : le gabarit du rapport fait à lui seul 52 lignes.

| ID | Règle | Source |
| --- | --- | --- |
| VA-01 | axes ; familles → axe (acces, injection, metier → securite) ; préfixes `ACC`, `INJ`, `MET`, `MNT`, `EVO` | :20, :53-59 |
| VA-02 | `--max-findings` : `min(N, 30)`, défaut 15 ; l'excédent va en liste courte | :21 |
| VA-03 | écriture unique : `AUDIT-vibecode.md` | :25 |
| VA-04 | schéma d'auditeur ; 5 occurrences au plus, `count` réel, `sampled` au-delà | :64-73, :78 |
| VA-05 | famille morte → « surface non auditable » major, `bruts = échec`, annoncée en tête | :76 |
| VA-06 | « surface non auditable » toujours de sévérité ≥ major | :29 |
| VA-07 | fusion de doublons entre auditeurs (déclarés par le skill) : union des occurrences, sévérité maximale, deux estimations transmises au validateur | :83 |
| VA-08 | verdict à scission ; `false_occurrences` retirées, `count` recalculé ; reclassement d'axe appliqué | :89-98 |
| VA-09 | validation partielle : critical d'abord, puis par nombre d'occurrences ; `non validé` marqué ; ratio dans l'encadré | :99 |
| VA-10 | tri VIB ; critical venant d'un autre axe que la sécurité signalés ; gains rapides | :105-108 |
| VA-11 | gates `drop-security`, `order` et `final` ; repli headless : défaut écrit et signalé en tête | :20, :33, :113-120 |
| VA-12 | rendu du rapport (gabarit), reprise sans comparaison des états | :126-179 |
| VA-13 | tableau du rapport par famille | :186 |

Restent en prose :
- « aucune adhérence à une pile technique » ;
- les cinq taxonomies et leurs causes ;
- les signaux de génération et la recherche des paires à réimplémentation ;
- les vérifications déterministes externes (choix de l'outil) ;
- les consignes du validateur (charge de la preuve, contester) ;
- le décompte de `risk_rationale`.

**brainstorm (lot L13, bloqué par X5)** — cible ≤ 68 lignes si X5 autorise un emplacement d'écriture ; sinon ≤ 95, et seule BS-02 est branchée (justification : sans fichier de transit, `SUJET` ne peut être passé au noyau sans passer par le shell).

| ID | Règle | Source |
| --- | --- | --- |
| BS-01 | `SUJET` = tous les jetons qui ne commencent pas par `--`, mot pour mot | :15 |
| BS-02 | `--rounds` : `min(N, 3)`, défaut 3 ; non entier ou < 1 → erreur explicite | :17 |
| BS-03 | registre des pistes écartées, clé exacte ; la reformulation reste au jugement | :24 |
| BS-04 | schéma de lentille, 4 pistes au plus, `origine` ∈ enonce\|hors-enonce | :52-57 |
| BS-05 | lentille morte → une relance → nommée, et sortie anticipée **désactivée** pour ce tour | :27 |
| BS-06 | sortie anticipée si 0 piste « hors énoncé » survivante | :66 |
| BS-07 | plafond de tours → convergence forcée | :68 |
| BS-08 | plafond dur de 5 pistes retenues ; le surplus part en « non retenus », avec son rang | :74 |
| BS-09 | slug : minuscules, accents retirés, non-alphanumérique → `-`, tirets fusionnés, ≤ 40 caractères, pas de tiret final ; chemin `BRAINSTORM-<slug>.md` | :103 |
| BS-10 | reprise : section « Angles écartés » chargée ; réécriture qui conserve toutes ses lignes | :33, :103 |
| BS-11 | rendu de la synthèse (gabarit) | :78-99 |
| BS-12 | gates de dialogue `subject`, `round` et `write` | :16, :67, :103 |

Restent en prose :
- contester systématiquement ; pas d'approbation complaisante ;
- les cinq lentilles ;
- le budget de 12 fichiers ;
- la pertinence au répertoire courant ;
- le message d'arrêt headless, en français ;
- la suggestion de chaînage sans lancer la commande.

**Usine de ce dépôt (lot L4)** — pas de cible de lignes : c'est une régénération.
- `UF-01` : régénérer `.claude/skills/factory-run/SKILL.md`, `.claude/agents/factory-*.md` et `ci/factory.sh|.ps1` depuis le gabarit de software-factory **après** L2 et L3.
- `UF-02` : le Planner liste les 8 skills et précise que `_core` n'est pas un skill (C1).
- `UF-03` : les portes du Builder et du Verifier comprennent `bash -n`, le contrôle du frontmatter, `cd skills/_core/tests && <PY> -B -m unittest discover -s . -t .` et l'absence de `__pycache__`.
- `UF-04` : factory-run rebranché : FR-01 à FR-04, journal, « Un Verifier muet n'est pas un Verifier satisfait », gate `factory-run.need`.
- `UF-05` : `.claude/harness/` est une copie identique de `skills/_core/` (Q-C).
- `UF-06` : liste blanche CI : interpréteur plus `git`, `bash`, `bats`, `shellcheck`, `pwsh`.
- `UF-07` : les règles propres au dépôt sont conservées : ne jamais exécuter `install_skills.*`, cohérence `.sh`/`.ps1`, accents absents des messages d'installation.

### 3. Comportement observable identique : définition opérationnelle

- **(a) Artefacts.** Pour chaque générateur (software-factory, ai-lab, code-index), les fichiers produits sur fixture sont égaux à des fichiers attendus versionnés. Une seconde application ne change rien, octet pour octet.
- **(b) Boucles et bornes.** Un rejeu scripté par skill vérifie : relances, échecs, plafonds, sortie anticipée, dédup, tris.
- **(c) Messages.** Les messages d'arrêt déplacés dans le noyau sont en anglais (décision du 2026-10-17). Ceux qui restent en prose ne changent pas.
- **(d) Fichiers écrits.** La liste de chemins est inchangée, aux écarts E1 à E5 près.
- **(e) Gates.** Mêmes points, mêmes moments, mêmes options (catalogue GT-08).

**Écarts proposés**, chacun à confirmer :
- **E1** : le noyau est copié sous `.claude/harness/` par ai-lab, comme D1 l'a fait pour software-factory.
- **E2** : journaux sous `.claude/runs/` pour les dix skills, et exclusion git.
- **E3** : C2 corrigé dans lab-run (agent mort en Verify et en interprétation).
- **E4** : C3 : les replis headless de ship-pr deviennent définis.
- **E5** : `.claude/models.json` est créé par la migration (MD-05).
- **E6** et **E7**, conditionnels : registre projet (X4) et `--models` partout (X6).

## Critères d'acceptation

`<PY>` = l'interpréteur détecté (`py -3` sur la machine de l'utilisateur). `T` = `cd skills/_core/tests && <PY> -B -m unittest discover -s . -t .`. `S` = `specs/SPEC-phase1-rebranchement.md`. Les recherches utilisent `grep` (`rg` est absent du PATH de Git Bash).

- [ ] **CA-01 — Tests verts.** `T` → exit 0.
- [ ] **CA-02 — Stdlib seule, Python 3.9.** `cd skills/_core/tests && <PY> -B -I -S -m unittest discover -s . -t .` → exit 0, avec `<PY> --version` en 3.9.x.
- [ ] **CA-03 — Chaque règle est testée.** `for id in $(grep -oE '\b(GT|FD|RG|LK|JR|MD|ST|TS|FU|BK|AU|CX|AL|LR|AA|LA|VA|BS)-[0-9]{2}\b' S | sort -u); do grep -rlq "$id" skills/_core/tests || echo "$id"; done` → aucune sortie.
- [ ] **CA-04 — Chaque règle est pointée.** Pour chaque skill et chacun de ses préfixes (CX, AL et LR, AA, LA, VA, BS), `grep -oE '<PFX>-[0-9]{2}' skills/<skill>/SKILL.md | sort -u | wc -l` est égal au nombre d'identifiants de ce préfixe dans S. En plus, `grep -c "_core" skills/<skill>/SKILL.md` ≥ 1 pour les six skills.
- [ ] **CA-05 — Un tiers de lignes en moins.** Pour f ∈ {code-index, ai-lab, ai-lab-audit, legacy-audit, vibecode-audit} : `[ "$(wc -l < skills/$f/SKILL.md)" -le $(( $(git show 031df12:skills/$f/SKILL.md | wc -l) * 2 / 3 )) ]`. Pour brainstorm, même commande si X5 est tranché favorablement, sinon ≤ 95. En plus, software-factory ≤ 96 et ship-pr ≤ 118.
- [ ] **CA-06 — Le jugement reste dans les prompts.** `grep -F` trouve chaque phrase dans son fichier :
  - legacy-audit : « zéro finding est une réponse normale et acceptable », « Une famille muette n'est pas une famille saine », « git init » ;
  - vibecode-audit : « zéro finding est une réponse normale et acceptable », « Ce qui ne peut pas être audité est un finding », « la sévérité prime sur l'axe », « Aucune adhérence à une pile technique » ;
  - ai-lab-audit : « zéro finding est une réponse normale et acceptable », « Une lentille muette n'est pas une lentille satisfaite », « Pas de protocole dans le livrable » ;
  - ai-lab : « Un expert muet n'est pas un expert d'accord », « Ne jamais approuver par épuisement », « Ne jamais mesurer sans protocole pré-enregistré » ;
  - code-index : « l'index se régénère, les notes ne se régénèrent pas », « post-checkout », « Une à trois notes par cycle » ;
  - brainstorm : « Interdiction de l'approbation complaisante », « rendre moins de pistes qu'un maximum est une réponse normale et acceptable », « intrinsèquement dialogué ».
- [ ] **CA-07 — Messages d'arrêt conservés.**
  - Le message de chemin inexistant (AU-01) est trouvé en anglais (`does not exist`) par `grep -rF` dans `skills/_core/hcore`.
  - Le message headless de brainstorm reste en prose : `grep -F "/brainstorm est intrinsèquement dialogué" skills/brainstorm/SKILL.md`.
- [ ] **CA-08 — Frontmatter.** Pour chacun des 8 skills, les lignes `name:` et `description:` sont identiques à BASE1 : `diff <(git show 031df12:$f | sed -n '2,3p') <(sed -n '2,3p' $f)` est vide. La première ligne est `---`.
- [ ] **CA-09 — Journal.** `harness.py journal validate` :
  - rend exit 0 sur un journal mêlant lignes d'agent et événements `gate` ;
  - rend exit ≠ 0 sur un événement `gate` sans `decision` (test unitaire) ;
  - les journaux produits par les rejeux vérifient `^(software-factory|factory-run|ship-pr|code-index|ai-lab|lab-run|ai-lab-audit|legacy-audit|vibecode-audit|brainstorm)-[0-9]{8}-[0-9]{6}\.jsonl$`.
- [ ] **CA-10 — Politique de gate.** Des tests unitaires couvrent :
  - fichier absent → `ask` pour a, b et c ;
  - `autonomy: "auto"` → `ask` avec avertissement (GT-03) ;
  - fonction GT-02 en `auto` → `default` pour b et c, `ask` pour a ;
  - gate de dialogue → `ask` ;
  - gate sans défaut avec décision `default` → exit 1 ;
  - id inconnu ou valeur invalide → exit 2 ;
  - journal : décision et réponse enregistrées.
- [ ] **CA-11 — Inventaire des gates.** Pour chaque ligne du catalogue GT-08 :
  - l'id est trouvé par `grep -F` dans le `SKILL.md` du skill source (`skills/software-factory/SKILL.md` pour `factory-run.*`, `.claude/skills/factory-run/SKILL.md` pour `factory-run.need`) ;
  - chaque option de la colonne « Options » y est trouvée par `grep -F`.
- [ ] **CA-12 — Schéma de finding.** `harness.py finding validate` :
  - rend exit 0 sur des fixtures conformes ;
  - rend un exit ≠ 0 sur `severity` invalide, `status` hors FD-02, `occurrences` non liste, `evidence.kind=code` sans `file`, et transition interdite ;
  - un extrait de 4 lignes donne exit 0 et un avertissement (FD-04).
- [ ] **CA-13 — Adaptateurs sans perte.** Pour chacun des 6 formats de FD-05, la fixture convertie passe CA-12, et `raw` est égal à l'entrée.
- [ ] **CA-14 — Validateur unique.** `SPLIT` est accepté pour vibecode et refusé (sortie inexploitable) pour ship-pr ; `nature_correction` est accepté pour ai-lab-audit seulement ; une sortie sans bloc final = agent mort.
- [ ] **CA-15 — Conversions.**
  - `to_pr_comment` est égal à la sortie de `git show 031df12:skills/_core/hcore/ghflow.py` `comment_body` sur 3 fixtures (test unitaire figé).
  - La spec rendue commence par `Statut : PROPOSEE`, ses sections sont dans l'ordre de LA-11, et FD-11 ne trouve aucune chaîne interdite.
  - La note rendue est acceptée par `rgkb.py note-add` dans un projet jetable (exit 0, `added: true`).
- [ ] **CA-16 — Registre projet** (si X4 est accepté). Un rejeu dans un dépôt jetable :
  - finding REJETÉ dans un run ship-pr n°1 ;
  - même fichier et même titre dans un run n°2, puis dans un rejeu legacy-audit : écarté avant le validateur, avec `previous=REJECTED@ship-pr`.
  - Un finding FIXED de même clé n'est **pas** écarté.
  - `.claude/findings.jsonl` a une ligne par clé ; une seconde publication donne un fichier identique octet pour octet.
  - `git status --porcelain` ne liste pas `.claude/`.
- [ ] **CA-17 — Concurrence.** Sur 8 essais, 8 processus `ship-pr reviewer` parallèles (thèmes distincts), plus 4 publications concurrentes vers `findings.jsonl` : aucun thème perdu, aucune collision d'id, aucune `PermissionError`, aucune ligne perdue (test `LK-01`, `RG-06`).
- [ ] **CA-18 — Modèles.**
  - Absence de fichier → `inherit` et `pass_param: false`.
  - `lab-models.json` seul → `models.json` créé avec les clés `lab.*`, `lab-models.json` identique octet pour octet (`cmp`), seconde résolution sans écriture.
  - Valeur inconnue dans le fichier → `inherit` et avertissement.
  - Valeur ou rôle inconnus dans `--models` → exit 2.
  - Alias `math=fable` accepté pour lab-run et ai-lab-audit.
- [ ] **CA-19 — Câblage des modèles.** Rejeu factory-run avec `models.json = {"factory.verifier": "haiku"}` : la ligne du Verifier porte `"model": "haiku"`, et la résolution rend `pass_param: true` pour lui seul.
- [ ] **CA-20 — Stack.** Pour chaque marqueur de ST-01, une fixture minimale est détectée, à la racine et à un niveau de profondeur. Un projet de 2001 fichiers hors artefacts → `sampled: true` ; de 2000 → `false`.
- [ ] **CA-21 — T-shirt et tris.** Sur fixture :
  - l'ordre LEG est sévérité décroissante puis taille croissante ;
  - l'ordre VIB place un critical d'axe `evolutivite` avant tout major `securite` ;
  - `regression_risk` est sans effet ;
  - un XL est découpé en au moins 2 specs ≤ L ;
  - 5 XS d'une même catégorie et d'un même jalon donnent 2 specs (4 + 1).
- [ ] **CA-22 — Fusions.**
  - `git diff --exit-code 031df12 -- tests/fixtures/merge-expected` et les tests SF-01 à SF-03 sont verts.
  - Nouvelles fixtures code-index (`settings.json`, `.mcp.json`, `tasks.json`, `config.json`) et ai-lab (`settings.json`, `tasks.json`, `.gitignore`) : sortie égale à l'attendu ; seconde application identique octet pour octet ; commentaires JSONC conservés ; entrée `rgkb` existante différente → `personnalisé-conservé`.
- [ ] **CA-23 — D8.** Dans un projet jetable :
  - `rgkb.py init`, puis ajout d'une exclusion et de `"hooks": "commit"` dans `config.json`, puis `init` relancé : `config.json` reste identique octet pour octet ;
  - `TOOL_VERSION` est supérieur à `1.0.0` ;
  - un `config.json` illisible n'est pas réécrit par `hooks install` (si Q-K est accepté).
- [ ] **CA-24 — Blocs.** Sur 4 textes de hook bien formés, l'insertion et le retrait par `rgkb.py` et par `blocks.py` (style `hash`) donnent des sorties identiques.
- [ ] **CA-25 — Rejeu code-index.** Sur une fixture équipée d'une usine :
  - deux applications donnent un seul bloc `rgkb` par agent ;
  - `tools` est un sur-ensemble de la valeur à BASE1 ;
  - `--allowedTools` de `ci/factory.sh` contient les entrées d'avant ;
  - `bash -n ci/factory.sh` passe.
- [ ] **CA-26 — Rejeu lab-run.**
  - `APPROVED` avec `protocol_followed=false` → `fix`.
  - 3 itérations non approuvées → `fail`.
  - Verifier mort puis vivant → itération non consommée.
  - Expert mort deux fois → `expertise not collected` dans la décision.
  - Le journal passe CA-09.
- [ ] **CA-27 — Rejeux des audits.** Pour legacy, ai-lab-audit et vibecode, sur fixture :
  - famille morte deux fois → « non auditée » (vibecode : finding « surface non auditable » major) ;
  - doublon REJETÉ écarté sans validateur ;
  - zéro CONFIRMED → saut au rapport ;
  - livrable rendu égal à un attendu versionné ;
  - repli headless de la gate `framing` (ou `order`) : stop pour legacy et ai-lab-audit, défaut signalé pour vibecode.
- [ ] **CA-28 — Rejeu brainstorm** (selon X5).
  - Lentille morte deux fois avec 0 piste « hors énoncé » → **pas** de sortie anticipée.
  - 7 pistes survivantes → 5 retenues.
  - Slug : « Réécrire l'API — v2 ! » → `reecrire-l-api-v2`, et une chaîne de 60 caractères → ≤ 40 sans tiret final.
- [ ] **CA-29 — Chaînes interdites.** FD-11 ne trouve rien dans aucun livrable produit par CA-27 ni par CA-28.
- [ ] **CA-30 — Reprise.** Avec une fixture `ROADMAP-legacy.md` contenant `LEG-03 FAIT` et une spec existante : `LEG-03` reste `FAIT`, la numérotation reprend à `LEG-04`, et la spec existante est inchangée (`cmp`).
- [ ] **CA-31 — Usine du dépôt.**
  - `grep -c` trouve les 8 noms de skill dans `.claude/agents/factory-planner.md`.
  - `grep -F "Un Verifier muet n'est pas un Verifier satisfait" .claude/skills/factory-run/SKILL.md`.
  - `grep -F ".claude/harness/harness.py" .claude/skills/factory-run/SKILL.md`.
  - `grep -F "unittest discover" .claude/agents/factory-builder.md .claude/agents/factory-verifier.md`.
  - `diff -r -x __pycache__ skills/_core .claude/harness` est vide.
  - `bash -n ci/factory.sh` passe.
  - `pwsh -NoProfile -Command "[scriptblock]::Create((Get-Content ci/factory.ps1 -Raw))"` → exit 0.
  - `grep -E 'Bash\((py|python3?) ' ci/factory.sh` ≥ 1.
  - `grep -F "install_skills" .claude/agents/factory-builder.md` ≥ 1.
- [ ] **CA-32 — Un commit par skill.**
  - Pour chacun des 6 skills, `git log --oneline 031df12..HEAD -- skills/<nom>/SKILL.md | wc -l` = 1.
  - Le commit D8 ne touche que `skills/code-index/assets/rgkb.py` et des tests.
- [ ] **CA-33 — Installeurs intacts.** `git diff --exit-code 031df12 -- install_skills.sh install_skills.ps1`.
- [ ] **CA-34 — README.**
  - `grep -F ".claude/models.json" README.md` ≥ 1.
  - `grep -F "lab-models.json" README.md` ≥ 1, avec la mention de migration.
  - Le paragraphe `_core` cite `gate`, `finding`, `findings.jsonl`, `stack` et `tshirt`.
- [ ] **CA-35 — Aucun artefact parasite.** `git status --porcelain` ne liste ni `__pycache__`, ni `.pyc`, ni journal, ni `findings.jsonl`, ni fichier de transit.

**Recettes par l'utilisateur, hors portes du Verifier :**
- **R1** (préalable, encore ouverte) : `${CLAUDE_SKILL_DIR}/../_core` est-il atteint ?
- **R4** : `/code-index` deux fois sur une fixture personnalisée ; `config.json` conservé.
- **R5** : `/ai-lab` sur une fixture portant un `lab-models.json`.
- **R6** : chaque audit sur fixture.
- **R7** : `/brainstorm` interactif.

## Hors-périmètre

- Phases 2 à 7 : profils, scout, `/audit`, `harness.json` écrit par un skill, `--upgrade`, doctor, `--autonomy`, fichiers `STOP-*.md`, état `BLOQUEE`, hooks Claude Code, file et worktrees, packaging.
- Unifier les formats JSON **demandés aux agents** : ils restent identiques en Phase 1 et sont normalisés par adaptateurs (Q9).
- Appeler la conversion finding → note rgkb depuis un skill : la fonction et ses tests seulement.
- Dédup sémantique : elle reste au jugement. Le noyau porte la clé et les fusions déclarées.
- La règle « code en anglais » dans les gabarits d'agents générés (BACKLOG §7).
- Modifier `install_skills.*`, et tout commit, push ou `/ship-pr` par le Builder.

## Risques

- **R1 non faite.** Les six rebranchements reposent sur `${CLAUDE_SKILL_DIR}/../_core`, non documenté (BACKLOG §5). Un échec invalide les lots L8 à L13 tels que spécifiés.
- **Arbre de travail mouvant.** Les corrections §7 sont en cours, sans commit. L1 doit partir d'un état stabilisé, sinon CA-32 et les mesures de lignes sont faussées.
- **Lignes jointes.** Les `SKILL.md` ont déjà des lignes-paragraphes : la cible −⅓ peut être atteinte en fusionnant des lignes sans rien sortir (Q-G).
- **Mise en page des livrables.** Les gabarits passés en données changent la mise en page si un détail diffère. CA-27 compare à des attendus versionnés, qu'il faut tirer de livrables réels.
- **Contrats de format.** Les adaptateurs FD-05 figent les formats actuels : tout changement de prompt casse le parseur. Le lien prompt ↔ adaptateur doit être testé.
- **Noyau mélangé.** ai-lab et software-factory copient le même `.claude/harness/`. Une version différente bloque la seconde installation (`copy_core`, exit 1), et la mise à jour n'existe qu'en Phase 3.
- **Pas de rejeu exact.** Les cycles LLM ne se rejouent pas au mot près (D10). L'identité est structurelle (CA-25 à CA-28), plus les recettes R4 à R7.
- **Permissions.** Le nombre d'appels Bash au noyau augmente dans les audits : sollicitations de permission en session (à mesurer par le journal).
- **Détection Python dans ce dépôt.** Ce dépôt n'a aucun marqueur Python (ST-01). La régénération de l'usine n'y détecte pas `unittest` sans traitement explicite. CA-31 l'impose.

## Contradictions (signalées, non tranchées)

- **X1 — `model:` dans le frontmatter.**
  - La ROADMAP Phase 1 l'impose pour les agents fichiers.
  - `ai-lab:135` l'interdit : un fichier de configuration serait contredit sans signal.
  - La doc dit que le paramètre `model` de l'outil Agent prime. `inherit` n'est documenté que pour le frontmatter, pas pour le paramètre.
  - Les fichiers générés sans bloc (D5) deviennent `personnalisé-conservé` et ne seraient jamais mis à jour.
- **X2 — Rôles `lab.*`.** La ROADMAP parle de « rôles `lab.*` existants » ; il n'en existe aucun. Les clés réelles sont celles d'`ai-lab:147-155` (D2 du BACKLOG).
- **X3 — Une seule implémentation des blocs.** C'est impossible tant que `rgkb.py` est copié seul dans les projets (`code-index:53`) : il a sa propre implémentation, divergente sur un marqueur de fin absent (`rgkb.py:825-826`).
- **X4 — Registre partagé.**
  - La ROADMAP le veut « même philosophie que `.knowledge/` » (versionné, une ligne par finding).
  - Q-registre / D2 le place dans `.claude/runs/`, non versionné, en journal d'événements de plusieurs lignes par finding.
  - Une dédup inter-runs et inter-skills est un **nouveau** comportement, contraire à « identique ».
  - Un fichier versionné serait commité par `git add -A` dans `fix(review)` (`ghflow.py`, `commit_round`) et rendrait l'arbre sale au préflight suivant.
- **X5 — Journal et interdits d'écriture.**
  - Audits : « Seules écritures autorisées » (`legacy-audit:21`, `ai-lab-audit:22`) ; « rien d'autre » (`vibecode-audit:25`).
  - brainstorm : « Aucune écriture sur disque avant la gate finale », « rien n'est écrit sur disque » (`brainstorm:26`, `:103`), alors qu'il peut tourner dans un répertoire sans rapport avec le sujet.
  - Le journal, les fichiers d'état et les fichiers de transit écrits par Write contredisent ces textes.
- **X6 — `--models` « partout ».** C'est une option nouvelle sur factory-run, ship-pr, legacy-audit et vibecode-audit, contraire à « identique ». La spec 0 avait exclu l'ajout de `--models` à `argument-hint`.
- **X7 — Verifier de la factory.** La ROADMAP veut qu'il « produise et lise le schéma de finding ». Le BACKLOG §4 rappelle qu'il valide une implémentation, et son format (`software-factory:45`) n'a ni ligne ni preuve : la conversion est forcément partielle.
- **X8 — Valeur de modèle inconnue.** Dans le fichier, `inherit` (`ai-lab:158`). En `--models`, erreur (`ai-lab:177`). `models.py:50` lève une erreur dans les deux cas.
- **X9 — Plancher de l'interpréteur.** `code-index:41` accepte tout `python` qui répond à `--version`. Le noyau exige ≥ 3.9 avec délai d'attente. Rebrancher ajoute ce prérequis.
- **X10 — Profils de modèles prêts à l'installation.** Seul ai-lab en possède (`ai-lab:139-142`). En créer pour la factory ou les audits serait un comportement nouveau.
- **X11 — « Une ligne par finding ».** La ROADMAP le demande ; le registre D2 est un journal d'événements. RG-01 les concilie (projet compacté, run en événements), sous réserve de X4.

## Questions ouvertes (avec décision par défaut)

- **Q2 — Modèle par rôle.** Défaut : le paramètre `model` seul, passé quand la valeur ≠ `inherit` ; aucun `model:` en frontmatter en Phase 1. Justification : `ai-lab:135` et la doc (le paramètre prime) ; le frontmatter attend des blocs régénérables (Phase 3). Dépend de X1.
- **Q3 — Sort de `/lab-run`.** Défaut : orchestrateur distinct, rebranché sur le noyau (`labrun.py`, paramétrage de la machine de factory-run). Justification : les alias relèvent de la Phase 2.
- **Q4 — `disable-model-invocation`.** Défaut : inchangé. Justification : les enchaînements relèvent de la Phase 4 (D3).
- **Q5 — Pré-enregistrement du labo.** Défaut : il reste de type (a). Justification : c'est le seul verrou avant une dépense de runs (`ai-lab:180`).
- **Q9 — Schéma de finding avec `occurrences[]`.** Défaut : schéma FD-01 interne, avec adaptateurs depuis les formats inchangés des agents. Justification : comportement identique ; l'unification des prompts relève de `/audit` (Phase 2).
- **Q10 — Format des profils.** Hors phase. Les préréglages de modèles sont des données Python dans `models.py`. Justification : pas de YAML dans la stdlib.
- **Q11 — Correctifs séparés.** Défaut :
  - D8 dans un commit à part, avant le rebranchement de code-index (il ne touche que `rgkb.py`, réversible seul) ;
  - C1 par la régénération (L4) ;
  - C2 dans le commit d'ai-lab (le lab-run généré passe par `relaunch.py` ; le séparer obligerait à écrire de la prose puis à la retirer) ;
  - C3 dans le lot gate (L2).
- **Q14 — ship-pr et brainstorm consomment le noyau sans devenir des profils.** Défaut : oui. ship-pr et brainstorm restent des skills propres ; brainstorm utilise des gates de dialogue (GT-04) et ne produit pas de findings (pistes ≠ findings, registre BS-03 séparé).
- **Q-G1 — `auto` lu en Phase 1.** Défaut : appliqué comme `gate`, avec avertissement journalisé. Justification : un `auto` partiel sans `BLOQUEE` ni `STOP` enlèverait des gates sans filet.
- **Q-C — Usine du dépôt.** Défaut : copie sous `.claude/harness/`, comme le gabarit. Justification : un Builder qui modifie `skills/_core` ne doit pas casser l'orchestrateur qui l'appelle en cours de cycle. Rafraîchissement explicite en L14.
- **Q-E — `.claude/findings.jsonl`.** Défaut : local, dans `.git/info/exclude`. Justification : évite le `git add -A` de ship-pr et l'arbre sale ; le versionnement se décide en Phase 3. Dépend de X4.
- **Q-F1 — Scission (`SPLIT`).** Les parts sont-elles `CONFIRMED` ou à revalider ? Défaut : `CONFIRMED`. Justification : le validateur les a construites à la source ; la colonne « Scindés » de `vibecode-audit:186` les compte à part.
- **Q-G — Garde contre les lignes jointes.** Défaut : ajouter à CA-05 « longueur de ligne maximale ≤ celle de BASE1 ».
- **Q-J — Valeurs invalides des audits** (`--categories`, `--max-*` non entiers ou inconnus). Défaut : exit 2. Justification : D8 de la spec 0 et `brainstorm:17`.
- **Q-K — `set_config_hooks`** (`rgkb.py:851`). Défaut : corrigé dans le commit D8. Justification : même perte de données que D8.
- **Q-H — Commandes d'installation de rg.** Défaut : déplacées dans le noyau (CX-02). Justification : elles sont déterministes, et les installeurs Bash/PowerShell gardent leur propre copie, faute de Python garanti à l'installation.

## Découpage en lots (ordre de livraison)

| Lot | Contenu | Commits | CA | Dépend de |
| --- | --- | --- | --- | --- |
| L0 | Recette R1 (utilisateur) et arbitrage de X1 à X11 | — | — | — |
| L1 | Finaliser les corrections §7 : LK-01, LK-02, JR-03, `drop`, `--summary-file`, `--not-fixed-file`, `--title-file`, `--trailer` ; ship-pr branché dessus | core, ship-pr | 01, 02, 17, 33, 35 | — |
| L2 | JR-01, JR-02 ; gate GT-01 à GT-08 ; gates câblées dans software-factory (gabarit) et ship-pr (C3) | core, sf, ship-pr | 09, 10, 11 (partiel), 05 (sf/sp) | L1 |
| L3 | Modèles MD-01 à MD-08 ; câblage factory-run (gabarit) et ship-pr ; option `--models` si X6 est accepté | core, sf, ship-pr | 18, 19 | L2 |
| L4 | Régénération de l'usine du dépôt UF-01 à UF-07 | usine | 31 | L2, L3 |
| L5 | FD-01 à FD-11, RG-01 à RG-07 ; `comment_body` par FD-10 ; publication et lecture dans ship-pr si X4 est accepté | core, ship-pr | 12 à 16 | L1 |
| L6 | ST-01 à ST-05, TS-01 à TS-05, FU-01 à FU-06, BK-01 ; SF réexprimé ; Phase 1 de software-factory sur ST | core, sf | 20 à 22 | L1 |
| L7 | Moteur d'audit AU-01 à AU-16 et gabarits de livrables (données) | core | 21, 29, 30 | L5, L6 |
| L8 | code-index : commit D8 (CX-09), puis rebranchement (CX-01 à CX-16, BK-02) | 2 | 23 à 25, 05, 32 | L2, L6 |
| L9 | ai-lab et lab-run (AL, LR, C2) | 1 | 26, 22, 18 | L3, L6 |
| L10 | ai-lab-audit (AA + partagées) | 1 | 27, 05 | L7, L3 |
| L11 | legacy-audit (LA + partagées) | 1 | 27, 30 | L7 |
| L12 | vibecode-audit (VA + partagées) | 1 | 27 | L7 |
| L13 | brainstorm (BS) | 1 | 28 | L2, X5 |
| L14 | README, mise à jour du BACKLOG, rafraîchissement de `.claude/harness` du dépôt, passage complet des CA | doc, usine | 01 à 35 | tous |

Chaque lot passe `T` seul. L8 à L13 sont indépendants entre eux une fois L7 livré, sauf L13, qui dépend de X5.

---

Fichiers lus pour cette spec :
- `C:\Users\fuzzz\claude-skills\specs\harness-v2\ROADMAP.md`
- `C:\Users\fuzzz\claude-skills\specs\harness-v2\BACKLOG.md`
- `C:\Users\fuzzz\claude-skills\specs\SPEC-noyau-core-journal.md`
- `C:\Users\fuzzz\claude-skills\skills\_core\` (CLI, `hcore/*`, liste des tests)
- `C:\Users\fuzzz\claude-skills\skills\*\SKILL.md` (les 8)
- `C:\Users\fuzzz\claude-skills\skills\code-index\assets\rgkb.py`
- `C:\Users\fuzzz\claude-skills\README.md`
- `C:\Users\fuzzz\claude-skills\.claude\` (usine du dépôt)
- `C:\Users\fuzzz\claude-skills\ci\factory.sh`

Le noyau a été modifié pendant la lecture (corrections §7 non commitées : `runs.py`, `harness.py`, `registry.py`, `tests/test_runs_lock.py`). La spec en tient compte au lot L1.