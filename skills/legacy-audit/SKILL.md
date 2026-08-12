---
name: legacy-audit
description: Audite un repo legacy en lecture seule — cartographie, quatre agents d'audit parallèles par familles de smells, validation adversariale des findings, estimation T-shirt, priorisation interactive par jalons — puis écrit une roadmap de remise à niveau et une spec factory (specs/SPEC-leg-*.md, statut proposé) par finding retenu. À utiliser quand l'utilisateur veut auditer un projet existant et en tirer un plan d'assainissement exécutable par /factory-run.
context: fork
user-invocable: true
argument-hint: "[chemin du repo à auditer] [--categories \"c1;c2\"] [--max-specs N]"
---

# Legacy audit — diagnostic d'un repo legacy et plan d'assainissement

Auditer un repo existant sans le modifier : cartographier, lancer quatre auditeurs parallèles par familles de smells, valider chaque finding par contestation adversariale, estimer en tailles T-shirt, faire arbitrer les priorités et les jalons par l'utilisateur, puis écrire une roadmap `ROADMAP-legacy.md` et une spec factory par finding retenu — prêtes à être exécutées par `/factory-run`.

Parser `$ARGUMENTS` :

- **1er token** (s'il ne commence pas par `--`) = chemin du repo à auditer ; défaut : répertoire courant. S'il n'existe pas → arrêt : « le chemin <chemin> n'existe pas ». Mémoriser `REPO` (chemin absolu, quoté si espaces).
- **`--categories "a;b"`** : restreint l'audit aux familles listées (`hygiene`, `portabilite`, `qualite`, `filet`, séparateur `;`). Défaut : les quatre.
- **`--max-specs N`** : plafond de specs générées, borné dur à `min(N, 25)`. Défaut : 15. On borne le livrable, jamais la détection : les findings confirmés au-delà du plafond figurent dans la roadmap (section « non retenus dans ce cycle »).

## Règles impératives (toutes les phases)

- **Lecture seule absolue sur le repo audité.** Seules écritures autorisées, en Phase 6 : `ROADMAP-legacy.md` et les specs. Ne jamais « corriger en passant » — même un `.gitignore` manquant est un finding, pas une action. Jamais de `git init`.
- **« Zéro finding » est une réponse normale et acceptable.** Cette phrase figure telle quelle dans le prompt de chaque auditeur et de chaque validateur — jamais de finding inventé pour remplir un quota.
- **Chaîne interdite** : ne jamais écrire la chaîne `Statut :` suivie de `APPROUVEE` où que ce soit (roadmap, specs, rapport) — la CI de la factory la greppe n'importe où dans un fichier. Toute spec générée commence par `Statut : PROPOSEE` en première ligne ; pour parler d'approbation ailleurs, périphraser (« le statut approuvé »).
- **Frugalité** : auditeurs = agents lecture seule recevant la carte du repo et leur famille de smells (jamais une mission « explore tout ») ; preuve = extrait ≤ 3 lignes ou constat structurel ; validateurs = mini-agents à prompt court et effort faible ; budgets de lecture de la Phase 1 respectés.
- **Registre cumulatif des findings** : tenir en mémoire `{id, fichier, ligne, catégorie, résumé, verdict}` pour tous les findings, **y compris les REJECTED**, alimenté aussi par une roadmap préexistante : un finding rejeté ou déjà traité ne ressuscite pas.
- **La priorisation appartient à l'utilisateur** (AskUserQuestion en Phase 5). Si aucune interaction n'est possible (exécution headless), s'arrêter en erreur explicite avant la Phase 5 : un audit sans arbitrage humain ne produit ni roadmap ni specs.

## Phase 1 — Reconnaissance et cartographie

Dans la session principale, sans sous-agent :

1. **Git** : `git -C "<REPO>" rev-parse --git-dir`. Si échec → `GIT_ABSENT=true` : pré-finding (versioning absent, famille `hygiene`) et **aucune commande git sur ce repo ensuite**.
2. **Stack** : chercher les marqueurs (`*.csproj`/`*.sln`, `pyproject.toml`/`requirements.txt`, `package.json`, `go.mod`, `Cargo.toml`, `CMakeLists.txt`/`Makefile`, `Dockerfile`/`docker-compose*`, `*.yml` Ansible) et lire les manifestes trouvés.
3. **Factory** : présence de `.claude/skills/factory-run/SKILL.md` dans le repo. Si absente, le noter (recommandation `/software-factory` au rapport) — non bloquant.
4. **Reprise** : si `<REPO>/ROADMAP-legacy.md` existe, la lire et charger toutes ses lignes de findings (retenus, non retenus, rejetés) dans le registre cumulatif.
5. **Bornes gros repos** : compter les fichiers hors dossiers d'artefacts (`node_modules`, `.venv`, `venv`, `bin`, `obj`, `build`, `dist`, `target`, `__pycache__`, `.git`). Si > 2000 : arborescence limitée à 3 niveaux, budget de 40 fichiers lus par auditeur, échantillonnage par plus gros / plus récemment modifiés / points d'entrée ; marquer l'audit « échantillonné » pour le rapport.

Produire la **carte** : arborescence 2-3 niveaux, stack et commandes de build détectées, nombre de fichiers, top 15 des plus gros fichiers, présence/absence de README, LICENSE, `.gitignore`, CI, dossier de tests, `GIT_ABSENT`/factory/reprise.

## Phase 2 — Audit parallèle par familles de smells

Lancer **en un seul message** les auditeurs (type Explore, lecture seule), un par famille retenue par `--categories` :

- **(a) `hygiene`** (ids `HYG-`) — hygiène du dépôt : versioning absent, `.gitignore` absent ou insuffisant, binaires et artefacts de build trackés, fichiers géants versionnés, **secrets/credentials commités** (clés, mots de passe, `.env` tracké), licence absente, fins de ligne CRLF/LF incohérentes sans `.gitattributes` ;
- **(b) `portabilite`** (ids `PORT-`) — portabilité et configuration : chemins absolus « marche sur ma machine », config d'environnement en dur (URLs, ports, identifiants), dépendances non épinglées / obsolètes / vulnérables, scripts non portables Windows/Unix, absence de CI, build non reproductible ;
- **(c) `qualite`** (ids `QUAL-`) — qualité du code : bugs et problèmes de logique manifestes, gestion d'erreurs absente (catch vides, codes retour ignorés), code mort, duplication massive, fonctions ou fichiers démesurés, TODO/FIXME anciens ;
- **(d) `filet`** (ids `FIL-`) — filet de sécurité : tests absents ou vides, documentation absente (README, installation, usage), logs de debug résiduels, points d'entrée non documentés.

Chaque prompt d'auditeur contient : la carte de la Phase 1, sa famille de smells **et rien d'autre à chercher**, le budget de lecture, la phrase « **zéro finding est une réponse normale et acceptable** », l'interdiction d'écrire quoi que ce soit, l'exigence de preuve vérifiable (fichier + ligne + extrait ≤ 3 lignes, ou constat structurel du type « aucun fichier de test dans le repo »), le barème T-shirt (XS < 30 min, S < 2 h, M demi-journée, L 1-2 jours, XL à découper), et le format de sortie exigé — un unique bloc JSON final :

```json
{"findings": [{"id": "HYG-01", "category": "gitignore-absent", "severity": "critical|major|minor",
  "title": "résumé court", "location": {"file": "chemin/relatif ou null", "line": 12},
  "evidence": "extrait ≤ 3 lignes ou constat structurel", "impact": "conséquence concrète",
  "remediation": "correction proposée en une phrase", "size": "XS|S|M|L|XL", "depends_on": []}]}
```

`severity: critical` est réservé aux secrets commités, aux bugs avérés et aux pertes de données potentielles.

## Phase 3 — Validation adversariale

1. **Dédupliquer** chaque finding contre le registre cumulatif (mêmes fichier/ligne/catégorie), verdicts REJECTED et entrées de roadmap préexistante compris — les doublons sont écartés sans validateur.
2. Pour chaque finding survivant, lancer un **mini-agent validateur** (effort faible, prompt court : le finding + consigne de relire la preuve à la source) chargé de le contester : la preuve existe-t-elle réellement à cet endroit ? est-ce un vrai smell ou un choix délibéré / faux positif (chemin absolu dans un fichier d'exemple, gros fichier qui est une fixture) ? la sévérité et la taille sont-elles plausibles ? Sortie exigée :

```json
{"verdict": "CONFIRMED|REJECTED", "reason": "justification en une phrase", "size_correction": "XS|S|M|L|XL|null"}
```

3. Ajouter chaque finding au registre avec son verdict. **Si zéro CONFIRMED → sauter en Phase 7** avec un rapport « repo sain sur les familles auditées » (réponse normale).

## Phase 4 — Consolidation et estimation

Dans la session principale, sans sous-agent :

- Renuméroter les CONFIRMED en `LEG-01…LEG-NN` (tri : sévérité décroissante puis taille croissante) ; appliquer les `size_correction` des validateurs.
- Compléter les **dépendances** structurelles évidentes : mise sous versioning et `.gitignore` avant tout le reste si `GIT_ABSENT` ; purge des secrets avant mise en place d'une CI ; tests avant la CI qui les exécute.
- Regrouper les findings en **3 à 6 thèmes** (typiquement les familles, fusionnées si peu peuplées) pour la phase interactive.

## Phase 5 — Priorisation interactive (gate humaine)

Ne jamais présenter les findings un par un : toujours par thème agrégé. Deux rondes bornées d'AskUserQuestion :

1. **Cadrage** (un appel, deux questions) : « Combien de jalons ? » (2 / 3 / 4) et « Critère de priorité dominant ? » (risque d'abord — secrets, bugs / quick wins d'abord — XS et S / fondations d'abord — versioning, tests, CI / garder l'ordre proposé).
2. **Affectation** (un appel par groupe de ≤ 4 thèmes, 3 appels maximum) : une question par thème — « Thème <nom> (<n> findings, tailles <répartition>) : quel jalon ? » avec options Jalon 1 / Jalon 2 / Jalon dernier / Exclure de la roadmap. Les findings d'un thème héritent du jalon du thème ; l'ordre intra-jalon découle du critère de la ronde 1 et des dépendances.

Présenter ensuite le tableau récapitulatif (jalons, findings, tailles, charge cumulée) en texte, puis une dernière question : **Générer roadmap + specs** / **Réajuster** (une seule fois — boucle bornée à 1 réajustement, qui rejoue la ronde 2) / **Abandonner** (sortir en Phase 7 sans rien écrire).

## Phase 6 — Génération roadmap + specs (seule phase qui écrit)

### 6.1 Roadmap

Écrire `<REPO>/ROADMAP-legacy.md`. Liens en chemins relatifs avec `/` (jamais de backslash). Statuts autorisés : `A_FAIRE` / `EN_COURS` / `FAIT` / `REPORTE`. Squelette :

```markdown
# Roadmap de remise à niveau — <nom du repo>

Générée par /legacy-audit le <date>. Usine logicielle : présente | absente (lancer /software-factory).
L'ordre d'exécution des specs est porté par cette roadmap (jalons puis ordre du tableau).

## Jalon 1 — <intitulé choisi>
| ID | Finding | Sévérité | Taille | Dépend de | Spec | Statut |
|---|---|---|---|---|---|---|
| LEG-01 | Secrets commités dans config.py | critical | S | — | [specs/SPEC-leg-01-purge-secrets.md](specs/SPEC-leg-01-purge-secrets.md) | A_FAIRE |

## Jalon 2 — …

## Findings non retenus dans ce cycle
| ID | Finding | Raison (exclu par l'utilisateur / au-delà du plafond de specs) |

## Findings rejetés à la validation
| ID | Finding | Raison |
```

**Idempotence / reprise** : si une roadmap existait en Phase 1, préserver les statuts `FAIT`/`EN_COURS` existants, ne pas régénérer leurs specs, poursuivre la numérotation `LEG-` existante pour les nouveaux findings, et signaler « roadmap reprise » au rapport. Ne jamais écraser une spec existante : si `specs/SPEC-leg-<nn>-*.md` existe déjà, la conserver telle quelle et le signaler.

### 6.2 Mapping finding → spec

- Défaut : **1 finding retenu = 1 spec** `specs/SPEC-leg-<nn>-<slug>.md` (slug court en minuscules-avec-tirets).
- **Regroupement** : findings **XS de même catégorie et même jalon** → une spec commune (4 findings maximum), un critère d'acceptation numéroté par finding, ids cités dans `## Contexte`.
- **Découpage** : tout **XL** → 2 specs ou plus de taille ≤ L, chaînées par la colonne « Dépend de » de la roadmap ; la spec aval rappelle son prérequis dans `## Contexte` et `## Risques` (la factory n'a pas de notion de backlog : l'ordre reste porté par la roadmap).
- Plafond `--max-specs` appliqué dans l'ordre des jalons ; l'excédent part en « non retenus dans ce cycle ».

### 6.3 Format de spec (contrat factory exact)

Première ligne = le statut proposé, sections dans cet ordre, chaque critère d'acceptation objectivement testable (entrée → sortie ou exception attendue) — c'est la matière première du Builder et du Verifier. Pour les secrets, la réécriture d'historique est **toujours** en Hors-périmètre. Exemple complet :

```markdown
Statut : PROPOSEE

# SPEC-leg-03 — Ajouter un .gitignore adapté à la stack Python

## Contexte
Finding LEG-03 (major, XS) : aucun .gitignore ; __pycache__/ et .venv/ apparaissent dans git status.

## Périmètre
Créer un fichier .gitignore à la racine couvrant les artefacts Python et l'IDE.

## Critères d'acceptation
1. Un fichier `.gitignore` existe à la racine et contient au minimum `__pycache__/`, `*.pyc`, `.venv/`.
2. Après `git status --porcelain`, aucun chemin sous `__pycache__/` ni `.venv/` n'apparaît.
3. Les fichiers déjà trackés correspondant à ces motifs sont retirés de l'index (`git rm -r --cached`), sans suppression du disque.

## Hors-périmètre
Réécriture d'historique ; .gitignore par sous-dossier.

## Risques
Un motif trop large pourrait ignorer des fichiers légitimes ; vérifier `git status` après application.

## Questions ouvertes
Aucune
```

## Phase 7 — Rapport final

Émettre un rapport structuré :

- **Carte** : repo, stack, taille, git présent/absent, audit complet ou échantillonné, roadmap créée ou reprise ;
- **Findings** : tableau `| Famille | Findings bruts | Confirmés | Rejetés/dédupliqués |` ;
- **Jalons** : intitulés retenus, nombre de findings et charge cumulée (répartition des tailles T-shirt) par jalon ;
- **Fichiers écrits** : roadmap + liste des specs (créées / préservées / regroupées / découpées) ;
- **Prochaine action** : factory présente → `/factory-run "specs/SPEC-leg-01-<slug>.md"` (factory-run porte lui-même la gate d'approbation de la spec) ; factory absente → lancer d'abord `/software-factory` ;
- **Reste à faire** : findings non retenus, XL découpés, et le cas échéant l'avertissement secrets — la purge d'historique n'est jamais faite par le skill ni par une spec générée.
