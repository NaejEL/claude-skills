# Feuille de route — claude-skills v2 (texte d'origine, conservé tel quel)

> Ce document est la **feuille de route** fournie par l'utilisateur le 2026-10-16. Ce n'est pas un besoin constructible en un cycle : chaque incrément en est extrait sous forme de spec (`specs/SPEC-*.md`). Les corrections de cap décidées depuis sont dans `BACKLOG.md`, qui prime sur ce texte en cas de conflit.

---

Tu travailles dans le dépôt claude-skills (skills globaux Claude Code, liés depuis `skills/<nom>/SKILL.md` par `install_skills.sh` / `install_skills.ps1`). Ce dépôt est mon harnais : il installe dans mes projets une usine logicielle multi-agents (`software-factory`), un cycle de PR (`ship-pr`), des audits (`legacy-audit`, `vibecode-audit`, `ai-lab-audit`), un labo scientifique (`ai-lab`), un index de code (`code-index`) et un `brainstorm`.

Objectif de cette évolution, en une phrase : **passer d'une collection de skills à gates humaines à un harnais versionné, à noyau commun, capable de tourner en boucle avec le minimum d'interventions de ma part, et de se mettre à jour dans les projets déjà équipés.**

Travail phasé. Chaque phase = une branche, un diff que tu me montres, mon accord, merge. Pas de `/ship-pr` ni de push de ta propre initiative pendant ce chantier — c'est le dépôt du harnais lui-même, il ne s'auto-modifie pas en autonomie.

---

## Phase 0 — Lecture et inventaire (aucune écriture)

Lis intégralement tous les `skills/*/SKILL.md`, les templates d'agents qu'ils génèrent, `install_skills.*`, `README.md`, et le code de `code-index` (blocs délimités `<!-- rgkb:debut -->`, fusion de `settings.json`, hooks git).

Rends-moi en conversation, sans écrire de fichier :

1. **Tableau des duplications** : pour chaque brique ci-dessous, quels skills en portent une copie et en quoi les copies divergent — gate humaine (AskUserQuestion), validateur adversarial de finding, registre cumulatif de findings, détection de stack, fusion de `.claude/settings.json`, génération de fichiers sous blocs délimités, lecture d'un modèle par rôle (`lab-models.json`, `--models`), estimation T-shirt, mode headless.
2. **Carte des gates humaines** : chaque point où un skill attend une réponse de moi, avec ce qui se passe si elle n'arrive pas (headless). Classe-les : (a) décision irréversible ou coûteuse, (b) décision de goût/priorité, (c) simple confirmation.
3. **Carte des interdits inter-skills** : chaque endroit où un skill s'interdit d'en lancer un autre (« suggère `/factory-run` sans jamais lancer la commande », etc.).
4. **Inventaire rôles et lentilles** : pour `software-factory` vs `ai-lab`, rôle par rôle, ce qui est commun et ce qui est propre au type de projet ; idem pour les lentilles des trois audits. C'est la matière première des profils (Phase 2).
5. **Fichiers générés dans les projets** : liste exhaustive par skill, avec pour chacun : régénérable sans perte / contient de la personnalisation utilisateur probable / mixte.
6. Tes questions. N'avance pas avant mes réponses.

---

## Phase 1 — Noyau commun (`skills/_core`)

Extraire les briques dupliquées dans un endroit unique que les autres skills référencent au lieu de les copier. Choisis la forme (skill `harness-core` chargé par les autres, fichiers Markdown inclus par référence, scripts Python stdlib sous `skills/_core/`) en fonction de ce que Claude Code permet réellement aujourd'hui pour partager du contenu entre skills — vérifie dans la doc, propose, justifie, attends mon accord.

Contenu minimal du noyau :

- **Gate** : une seule primitive, paramétrée par la *politique d'autonomie* (Phase 4). Un appelant déclare `gate(kind=a|b|c, question, default)` ; c'est la politique qui décide si on demande, si on prend le défaut, ou si on s'arrête.
- **Finding** : un schéma JSON unique (id, source skill, sévérité, axe, preuve = fichier:lignes + extrait, motif à N occurrences, statut : proposé / validé / rejeté / corrigé / tranché, hash du fix éventuel) et le **validateur adversarial** qui le consomme. `ship-pr`, les trois audits et le verifier de la factory produisent et lisent ce schéma. Un finding d'audit se convertit en spec factory, en note rgkb ou en commentaire de PR par une fonction, pas par réécriture.
- **Registre cumulatif** : un fichier par projet, format texte une ligne par finding (même philosophie que `.knowledge/`), partagé entre skills — un finding rejeté dans `ship-pr` ne ressuscite ni au tour suivant ni dans un audit ultérieur.
- **Modèles par rôle** : `.claude/models.json` unique (remplace `lab-models.json`, migration lue une fois et jamais destructive), clés par rôle (`factory.planner|builder|verifier`, `shippr.reviewer|validator`, `audit.auditor|validator`, rôles `lab.*` existants), valeur = modèle ou `inherit`, override `--models "role=modele;…"` partout. Application : `model:` du frontmatter pour les agents fichiers, paramètre `model` du tool Agent pour les agents dynamiques. Profils prêts à l'installation.
- **Fusion de `settings.json`** et **blocs délimités** : une seule implémentation, réentrante, jamais d'écrasement hors bloc.
- **Journal de cycle** : `.claude/runs/<skill>-<horodatage>.jsonl` — par étape : agent, modèle, durée, itération, verdict, findings produits/validés/rejetés, tokens si l'outillage les expose. Pas d'interprétation, des faits.
- **Détection de stack** et **estimation T-shirt** : une copie.

Les skills existants sont rebranchés sur le noyau **sans changement de comportement observable** dans cette phase — c'est un refacto, il doit être vérifiable par un cycle identique avant/après sur un projet fixture. Chaque skill rebranché est un commit.

---

## Phase 2 — Profils : un seul point d'entrée, un seul audit

Aujourd'hui les mêmes idées existent en plusieurs exemplaires selon le type de projet : `software-factory` / `ai-lab` sont la même boucle (planifier → gate → construire → vérifier adversarialement → consigner) avec des rôles différents ; `legacy-audit` / `vibecode-audit` / `ai-lab-audit` sont le même audit (cartographier → auditeurs parallèles par lentilles → validation adversariale → priorisation → livrables) avec des lentilles différentes. Je veux une seule implémentation de chaque, et un **profil** qui porte les différences.

### 2.1 Profils

Un profil = un fichier de données (YAML/JSON/Markdown à frontmatter, à toi de choisir), **pas du code**, sous `skills/_core/profiles/<nom>/` :

- rôles de la boucle (nom, mission, lecture seule ou non, modèle par défaut, fichier d'agent généré) ;
- format des artefacts (spec factory vs protocole pré-enregistré, journal d'expériences, tableau de résultats) ;
- lentilles d'audit (nom, taxonomie de smells, ce qui compte comme preuve) ;
- vérifications déterministes spécifiques (vulnérabilités/secrets vs fuites/confondants/seeds) ;
- `permissions.deny` propres au profil (venv, poids, données pour le labo) ;
- critères de détection (§2.2).

Profils initiaux, obtenus en **extrayant** l'existant sans perte de comportement : `software` (depuis `software-factory` + `legacy-audit` + `vibecode-audit`, les deux derniers devenant des jeux de lentilles d'un même profil) et `research` (depuis `ai-lab` + `ai-lab-audit`). Prévoir que d'autres arrivent (infra/ansible, data pipeline, firmware…) sans toucher au noyau : ajouter un profil = ajouter un dossier.

Un projet peut cumuler plusieurs profils (un labo avec un vrai paquet logiciel autour). Le tampon `harness.json` (Phase 3) enregistre les profils actifs.

### 2.2 Détection et arbitrage

Un agent **`harness-scout`** (lecture seule, modèle économique) cartographie le projet et rend un verdict structuré : signaux trouvés par profil (fichiers, dépendances, structure, corpus scientifique, GPU, CI…), profils proposés avec score et preuves, incertitudes. Pas de magie : les critères sont dans les profils et le scout les applique.

- `/software-factory` devient le point d'entrée unique : il lance le scout, **arbitre** (en `auto` : prend la proposition si un profil domine nettement, s'arrête avec le verdict si c'est ambigu ; en `gate` : demande), puis génère la factory du ou des profils retenus. `/ai-lab` reste disponible comme alias forçant le profil `research`, pour ne rien casser.
- `/factory-run` et `/audit` lisent les profils actifs dans `harness.json` ; ils ne redétectent pas à chaque cycle.
- **Réévaluation** : `/software-factory --rescan` (et `/harness-doctor`, Phase 3, le propose quand il voit des signaux nouveaux) relance le scout, compare au tampon, et propose d'**ajouter** un profil, jamais d'en retirer sans accord explicite — un projet qui grandit gagne des rôles et des lentilles, il n'en perd pas silencieusement. Ajouter un profil régénère uniquement les blocs des nouveaux fichiers et les blocs délimités des fichiers partagés (`settings.json`, orchestrateur).

### 2.3 Audit unique

`/audit` remplace les trois skills d'audit (qui restent comme alias le temps d'une version, avec avertissement) :

```
/audit                              # lentilles = union des profils actifs
/audit --lenses "securite;fuites"   # sous-ensemble
/audit --profile research           # force un profil
```

- Cartographie commune, puis auditeurs parallèles **par lentille** (bornés en nombre, regroupés si trop de lentilles), validation adversariale via le noyau, priorisation (auto ou gate selon la politique), livrables dans le **schéma de finding unique** du noyau.
- Les différences que les trois skills actuels revendiquent sont **préservées comme propriétés de lentille**, pas perdues : dette d'accumulation vs dette de génération, motif à N occurrences, gravité prime sur l'axe, « ce qui ne peut pas être audité est un finding », aucun run ni protocole pour les lentilles de recherche, grep du journal pour les questions déjà tranchées.
- Sorties selon les profils : specs factory et roadmap (`software`), corrections `COR-*` et questions `Q-*` prêtes pour `/factory-run` en profil `research`, le tout dans un seul `AUDIT.md`.
- Reprise idempotente d'un audit antérieur, quel que soit le skill d'origine (lecture des anciens `ROADMAP-legacy.md`, `AUDIT-vibecode.md`, `AUDIT-lab.md` comme entrée de migration).

Vérification de non-régression : sur les fixtures (Phase 6), `/audit` en profil `software` doit retrouver les findings que `legacy-audit` + `vibecode-audit` trouvaient, et `/audit` en profil `research` ceux d'`ai-lab-audit`. Écarts listés et justifiés un par un.

---

## Phase 3 — Versioning, upgrade, doctor

- **Tampon** `.claude/harness.json` écrit dans chaque projet équipé : version du dépôt claude-skills (tag git ou hash), date, skills installés et leurs options, politique d'autonomie choisie, profils actifs.
- **`--upgrade`** sur `/software-factory` (donc tous les profils), `/code-index` : lit le tampon, régénère uniquement les blocs délimités, préserve tout le hors-bloc, migre les formats (lab-models → models, anciens registres), montre le diff complet, applique. Idempotent : relancer sans changement produit zéro diff. Un projet sans tampon (installé avant cette version) est détecté par la présence des fichiers générés, et le tampon est créé à la première mise à jour.
- **`/harness-doctor`** : dans un projet — version installée vs version du dépôt, blocs délimités divergents, fichiers attendus manquants, hooks git rgkb déclarés mais absents, `models.json` absent, `gh` non authentifié ; avec `--scan <racine>` — balaye les sous-dossiers, une ligne par projet équipé : version, retard, dernier cycle (depuis `.claude/runs/`). Propose `--upgrade` mais ne le lance que si la politique d'autonomie l'y autorise.
- Les fichiers régénérés portent en en-tête la version qui les a produits.

---

## Phase 4 — Politique d'autonomie et boucle

C'est le cœur du changement de philosophie. Aujourd'hui j'ai mis trop de validations humaines, et les skills s'interdisent de s'enchaîner. Je veux une boucle où j'interviens le moins possible, sans supprimer les protections qui comptent.

### 4.1 Politique déclarée, pas codée en dur

`harness.json` porte `autonomy: "gate" | "auto"` (+ override `--autonomy` sur chaque orchestrateur) :

- `gate` = comportement actuel, toutes les gates demandent.
- `auto` = les gates de type (b) et (c) prennent leur défaut et le **journalisent** ; seules les gates (a) s'arrêtent encore, et uniquement si leur condition d'arrêt est remplie (ci-dessous).

Le défaut installé pour moi est `auto`. Le défaut de chaque gate est écrit dans le skill et justifié en une ligne.

### 4.2 Ce qui ne demande plus

- **Spec de la factory** : le Planner écrit la spec et la factory enchaîne sur le Builder **sans approbation**, sauf si le Planner déclare des questions ouvertes bloquantes (champ explicite dans la spec, pas une impression). Dans ce cas la spec est marquée `BLOQUEE` et le cycle s'arrête proprement avec les questions dans le journal ; `/factory-run` reprend dès qu'elles ont une réponse dans la spec.
- **Merge de `ship-pr`** : auto si **toutes** ces conditions sont vraies — zéro finding validé restant, tous les threads résolus, CI verte si le repo en a une (`gh pr checks`), branche cible non protégée contre le merge automatique, pas de conflit. Une seule condition fausse → la PR reste ouverte, raison dans le journal et dans un commentaire de PR, pas de question posée.
- **Enchaînements** : les audits peuvent, en `auto`, lancer `/factory-run` sur les specs qu'ils produisent, par ordre de priorité calculée ; `/factory-run` peut lancer `/ship-pr` à build vert ; `brainstorm` reste intrinsèquement dialogué et ne lance rien — c'est le seul skill qui garde ce statut, par nature.
- **Priorisation des audits** : en `auto`, le critère par défaut est « fiabiliser d'abord » et le nombre de jalons est calculé, pas demandé.
- **Upgrade** : en `auto`, `/harness-doctor` lance `--upgrade` quand le diff ne touche que des blocs délimités.

### 4.3 Ce qui s'arrête encore (gates (a) et conditions d'arrêt)

- Opération destructive hors du périmètre déjà accepté : suppression de branche autre que celle de la PR mergée, `git push --force`, réécriture d'historique, suppression de fichiers non générés.
- Échec après le nombre maximal d'itérations Builder/Verifier (3) : arrêt explicite, pas de 4e tentative silencieuse, pas d'élargissement du périmètre pour « faire passer ».
- Spec `BLOQUEE` (4.2).
- Arbitrage de profil ambigu par le scout (2.2).
- Dérive de périmètre détectée par hook (Phase 5) deux fois dans le même cycle.
- Toute action qui coûterait de l'argent hors de l'abonnement ou toucherait un secret.

Chaque arrêt écrit un fichier `.claude/runs/STOP-<horodatage>.md` lisible en 30 secondes : où, pourquoi, quoi faire pour reprendre, commande exacte.

### 4.4 File et boucle

- **`/factory-queue`** : liste les specs par statut (proposée / bloquée / en cours / livrée / mergée), avec dépendances ; `/factory-queue run` dépile en `auto` jusqu'à vide ou arrêt (a).
- **`/factory-batch specs/SPEC-*.md`** : un worktree par spec, cycles en parallèle (nombre borné, option), puis `ship-pr` en file sur la cible — un seul merge à la fois, rebase de la PR suivante après chaque merge, arrêt sur conflit non trivial.
- **`/factory-run --worktree`** : crée son worktree et y travaille ; nettoie après merge. Documente comment ça coexiste avec un worktree déjà ouvert par moi (i3/Orca) : le skill ne touche jamais à un worktree qu'il n'a pas créé.

---

## Phase 5 — Hooks Claude Code

Rendre déterministes des garde-fous qui ne sont que des consignes de prompt. Hooks générés par `/software-factory` dans le `settings.json` fusionné, scripts Python stdlib portables Windows/Linux/macOS, aucune dépendance nouvelle. Un hook qui rencontre une erreur interne **laisse passer et le signale**, il ne fait jamais échouer la session.

- `PostToolUse` sur `Edit|Write` : linter/formatteur de la stack détectée, non bloquant, sortie résumée.
- `PreToolUse` sur `Edit|Write` pendant `factory-run` : bloque (exit 2 + message) hors du périmètre déclaré par la spec en cours, si elle en déclare un.
- `PreToolUse` sur `Edit|Write` pendant `ship-pr` : bloque hors de `git diff --name-only <cible>...HEAD`, message rappelant « périmètre limité au diff ».
- `PreToolUse` sur `Bash` : bloque les commandes de la liste (a) de 4.3 (`push --force`, suppression de branches non prévues, `rm` hors fichiers générés) quelle que soit la politique d'autonomie — c'est le filet sous la boucle.
- Activation contextuelle : les hooks liés à `factory-run` / `ship-pr` ne sont actifs que pendant une exécution de ces skills. Propose le mécanisme (variable d'environnement posée par l'orchestrateur, fichier marqueur sous `.claude/`, autre), justifie, attends mon accord — un hook permanent bloquerait mes éditions manuelles.
- Après une dérive bloquée, l'agent reçoit le message et poursuit ; à la deuxième dans le même cycle, arrêt (a).

---

## Phase 6 — Tests du harnais

- `ci/fixtures/` : un ou deux projets jouets minimaux (une stack simple, un repo git avec remote factice ou dépôt bare local).
- Scénarios exécutables, chacun avec résultat attendu vérifiable par script : installation à neuf ; `--upgrade` sur un projet installé « à l'ancienne » (fixture figée avec des personnalisations hors bloc) et vérification qu'elles survivent ; cycle `factory-run` complet en `auto` jusqu'au Verifier ; `ship-pr` avec zéro finding → merge auto ; hook qui bloque hors diff ; `models.json` absent ; `lab-models.json` legacy ; arrêt propre à la 3e itération.
- Regarde si l'outillage d'évaluation de plugins/skills de Claude Code peut porter ces scénarios ; sinon, scripts `ci/test-harness.sh|.ps1`.

---

## Phase 7 — Packaging (étude, pas d'implémentation)

Un document court : faut-il remplacer `install_skills.*` par le mécanisme de plugins Claude Code (versions, mise à jour, distribution) ? Ce que ça apporte, ce que ça casse (installation de ripgrep, jonctions Windows, projets déjà équipés), un plan de migration si oui. Je déciderai après lecture.

---

## Règles communes

- **Périmètre** : rien d'autre que ces phases. Les skills remplacés en Phase 2 restent comme alias une version durant ; pas d'autre renommage, pas de refacto opportuniste hors Phase 1, pas de durcissement spéculatif.
- **Rétrocompatibilité** : un projet équipé avec la version actuelle continue de fonctionner sans `--upgrade` ; `--upgrade` ne détruit jamais, migre et explique.
- **Idempotence** partout : installation, upgrade, index, hooks.
- **Documentation** : README mis à jour par skill, même ton et même niveau de détail que l'existant, plus des sections « Profils », « Politique d'autonomie » et « Mettre à jour un projet équipé ».
- **Journal** : chaque décision prise automatiquement en `auto` est dans `.claude/runs/`, jamais silencieuse.
- **Désaccord** : si une consigne contredit ce que tu trouves dans le code réel ou dans la doc Claude Code actuelle, tu t'arrêtes et me le dis, tu ne tranches pas seul.
- **Fin de phase** : diff complet, procédure de vérification manuelle (commandes exactes, résultat attendu), liste de ce qui a été reporté à une phase suivante et pourquoi.
