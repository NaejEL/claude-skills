---
name: legacy-audit
description: Audite un repo legacy en lecture seule — cartographie, quatre agents d'audit parallèles par familles de smells, validation adversariale des findings, estimation T-shirt, priorisation interactive par jalons — puis écrit une roadmap de remise à niveau et une spec factory (specs/SPEC-leg-*.md, statut proposé) par finding retenu. À utiliser quand l'utilisateur veut auditer un projet existant et en tirer un plan d'assainissement exécutable par /factory-run.
context: fork
user-invocable: true
argument-hint: "[chemin du repo à auditer] [--categories \"c1;c2\"] [--max-specs N]"
---

# Legacy audit — diagnostic d'un repo legacy et plan d'assainissement

Auditer un repo existant sans le modifier : cartographier, lancer quatre auditeurs parallèles par familles de smells, valider chaque finding par contestation adversariale, estimer en tailles T-shirt, faire arbitrer les priorités et les jalons par l'utilisateur, puis écrire une roadmap `ROADMAP-legacy.md` et une spec factory par finding retenu — prêtes pour `/factory-run`.

## Noyau déterministe

Les règles déterministes sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : ne jamais les réimplémenter, appeler la CLI `harness.py` et suivre sa sortie JSON. Règles propres : **LA-01** à **LA-13** (`hcore/audit.py` et son profil, `findings.py`, `tshirt.py`) ; partagées : **AU-01** à **AU-16** (arguments, relances, dédup, reprise, renumérotation, compteurs), **FD-01** à **FD-11** (schéma de finding, validateur unique, spec, chaînes interdites), **RG-01** à **RG-07** (registre projet `.claude/findings.jsonl`), **TS-01** à **TS-05**, **ST-01** à **ST-04**, **GT-01** à **GT-08**, **MD-01** à **MD-08** (`--models` : rôles `audit.auditor`, `audit.validator`), **JR-01**, **JR-02** (journal sous `.harness/runs/` du repo audité).

**Interpréteur** : `<PY>` = le premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9 : `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`. Toute sortie d'agent et tout JSON se transmettent au noyau par un fichier écrit avec l'outil Write sous `.harness/runs/` (jamais par le shell : backticks, `$`, apostrophes) ; le noyau le supprime après lecture.

## Règles impératives (toutes les phases)

- **Lecture seule absolue sur le repo audité.** Seules écritures autorisées (le noyau refuse toute autre) : `ROADMAP-legacy.md`, `specs/SPEC-leg-*.md`, le journal `.harness/runs/` et le registre projet. Ne jamais « corriger en passant » — même un `.gitignore` manquant est un finding, pas une action. Jamais de `git init`.
- **« Zéro finding » est une réponse normale et acceptable.** Cette phrase figure telle quelle dans le prompt de chaque auditeur et de chaque validateur — jamais de finding inventé pour remplir un quota.
- **Une famille muette n'est pas une famille saine.** Un auditeur mort ou à la sortie inexploitable rend le même silence qu'un vrai « zéro finding », et ce silence se lit comme un satisfecit. Le noyau relance **une fois** (`relaunch`), puis rend `not-audited` : la famille figure alors comme **non auditée** dans la roadmap, marquée `échec` au rapport. Un audit amputé reste utile ; un audit qui tait son amputation est trompeur. Un validateur mort deux fois laisse son finding **non validé**, jamais `CONFIRMED`.
- **Chaîne interdite** : ne jamais écrire `Statut :` suivi de `APPROUVEE` où que ce soit (le noyau le vérifie, FD-11) ; toute spec commence par `Statut : PROPOSEE`. Pour parler d'approbation ailleurs, périphraser.
- **Frugalité** : auditeurs en lecture seule (type Explore) recevant la carte et leur famille ; preuve = extrait ≤ 3 lignes ou constat structurel ; validateurs = mini-agents à prompt court.
- **La priorisation appartient à l'utilisateur** (AskUserQuestion, Phase 5). Sans interaction possible, s'arrêter en erreur explicite avant la Phase 5 : un audit sans arbitrage ne produit ni roadmap ni specs (`stop`, LA-12).

## Phase 1 — Reconnaissance et cartographie

1. **Arguments, git, reprise** : écrire `$ARGUMENTS` tel quel dans `.harness/runs/legacy-audit-arguments.txt`, puis `K audit start --skill legacy-audit --arguments-file …` (AU-01 à AU-03 : `REPO` absolu, `--categories` familles parmi `hygiene`, `portabilite`, `qualite`, `filet` séparées par `;`, `--max-specs` borné à `min(N, 25)` défaut 15 ; chemin inexistant → arrêt, option ou valeur invalide → exit 2). Il ouvre le run dans le repo, sonde git (`git_absent` → LA-03 : pré-finding de la famille hygiène et **aucune commande git ensuite**), lit la factory (LA-04 `factory`) et reprend `ROADMAP-legacy.md` s'il existe (AU-09 : statuts `FAIT`/`EN_COURS` préservés, numérotation poursuivie, `resumed`). Il rend `run`, `auditors` (modèle et `pass_param` du rôle `audit.auditor`), `validator`, `cap`, `allowed_writes`. Passer à chaque sous-agent le paramètre `model` quand `pass_param` est vrai, jamais pour `inherit`.
2. **Stack et bornes** : `K stack detect --root "<REPO>"` (marqueurs, manifestes, dossiers d'artefacts, `sampled` au-delà de 2000 fichiers : arborescence de 3 niveaux, 40 fichiers lus par auditeur, échantillonnage par plus gros / plus récents / points d'entrée). Lire les manifestes trouvés.
3. **Carte** : arborescence 2-3 niveaux, stack et commandes de build, nombre de fichiers, 15 plus gros fichiers, README, LICENSE, `.gitignore`, CI, tests, `git_absent`, factory (absente : recommander `/software-factory`, non bloquant), reprise, échantillonnage.

## Phase 2 — Audit parallèle par familles de smells

Lancer **en un seul message** les auditeurs, un par famille retenue (LA-01) :

- **(a) `hygiene`** (ids `HYG-`) — versioning absent, `.gitignore` absent ou insuffisant, binaires et artefacts trackés, fichiers géants versionnés, **secrets/credentials commités** (clés, mots de passe, `.env` tracké), licence absente, fins de ligne incohérentes sans `.gitattributes` ;
- **(b) `portabilite`** (`PORT-`) — chemins absolus « marche sur ma machine », config d'environnement en dur, dépendances non épinglées / obsolètes / vulnérables, scripts non portables Windows/Unix, CI absente, build non reproductible ;
- **(c) `qualite`** (`QUAL-`) — bugs manifestes, gestion d'erreurs absente (catch vides, codes retour ignorés), code mort, duplication massive, fonctions ou fichiers démesurés, TODO/FIXME anciens ;
- **(d) `filet`** (`FIL-`) — tests absents ou vides, documentation absente (README, installation, usage), logs de debug résiduels, points d'entrée non documentés.

Chaque prompt contient : la carte, sa famille **et rien d'autre à chercher**, le budget de lecture, la phrase « **zéro finding est une réponse normale et acceptable** », l'interdiction d'écrire, la preuve vérifiable (fichier + ligne + extrait ≤ 3 lignes, ou constat structurel), le barème T-shirt (XS < 30 min, S < 2 h, M demi-journée, L 1-2 jours, XL à découper) et un unique bloc JSON final (LA-05) :

```json
{"findings": [{"id": "HYG-01", "category": "gitignore-absent", "severity": "critical|major|minor",
  "title": "résumé court", "location": {"file": "chemin/relatif ou null", "line": 12},
  "evidence": "extrait ≤ 3 lignes ou constat structurel", "impact": "conséquence concrète",
  "remediation": "correction proposée en une phrase", "size": "XS|S|M|L|XL", "depends_on": []}]}
```

`critical` est réservé aux secrets commités, aux bugs avérés et aux pertes de données potentielles. Chaque retour : `K audit auditor --run <run> --unit <famille> --output <fichier> [--dead] --duration-ms <ms> --tokens <n>` ; `action` : `relaunch` (relancer cette famille **une fois**), `not-audited`, `validate` (`to_validate` ; `duplicates` écartés **sans validateur**, y compris REJECTED du registre projet, `previous=<statut>@<source>`), `none`.

## Phase 3 — Validation adversariale

Pour chaque finding de `to_validate`, un **mini-agent validateur** (effort faible, prompt court : le finding + relire la preuve à la source) le conteste : la preuve existe-t-elle à cet endroit ? vrai smell, choix délibéré ou faux positif (chemin absolu d'un fichier d'exemple, gros fichier qui est une fixture) ? sévérité et taille plausibles ? Il termine par (LA-07) :

```json
{"verdict": "CONFIRMED|REJECTED", "reason": "justification en une phrase", "size_correction": "XS|S|M|L|XL|null"}
```

`K audit validator --run <run> --finding <id> --output <fichier> [--dead]` (relance unique, puis `unvalidated`). `K audit next --run <run>` rend `step` : `audit`, `validate`, `consolidate`, ou `report` (**zéro CONFIRMED → Phase 7** : « repo sain sur les familles auditées », réponse normale) et le tableau `counters` par famille (LA-13 : bruts, confirmés, rejetés ou dédupliqués ; `échec` pour une famille non auditée).

## Phase 4 — Consolidation et estimation

`K audit consolidate --run <run>` renumérote les CONFIRMED en `LEG-nn` (LA-08 : sévérité décroissante puis taille croissante, tailles corrigées appliquées, numérotation poursuivie en reprise) et rend l'ordre. Compléter les **dépendances** structurelles évidentes (jugement) : versioning et `.gitignore` avant tout si `git_absent` ; purge des secrets avant une CI ; tests avant la CI qui les exécute. Regrouper les findings en **3 à 6 thèmes** (typiquement les familles, fusionnées si peu peuplées).

## Phase 5 — Priorisation interactive (gate humaine)

Jamais un finding à la fois : par thème. `K audit themes --skill legacy-audit --count <n>` découpe en appels de 4 thèmes au plus, 3 appels maximum. Deux rondes d'AskUserQuestion (`K gate decide` / `answer`) : **cadrage** `legacy-audit.framing` (un appel, deux questions : jalons 2 / 3 / 4 ; priorité *risque d'abord* / *quick wins* / *fondations* / *ordre proposé*), puis **affectation** `legacy-audit.assignment` (une question par thème : *Jalon 1* / *Jalon 2* / *Jalon dernier* / *Exclure de la roadmap* ; l'ordre intra-jalon découle du critère et des dépendances). Écrire les choix dans `.harness/runs/legacy-audit-data.json` (`name`, `date`, `factory`, `milestones` `[{number, title}]`, `findings` `{LEG-nn: {milestone, spec}}` ou `{not_retained: "excluded"|"cap"}`), puis `K audit plan --run <run> --data-file …` (LA-10, TS-05, LA-02) rend les specs (1 finding = 1 spec ; XS de même catégorie et même jalon regroupés par 4 ; chaque XL découpé en 2 specs ou plus ≤ L, chaînées), le plafond `--max-specs` appliqué **dans l'ordre des jalons** (`not_retained_cap` : l'excédent part en « non retenus ») et la charge cumulée par jalon. Présenter le récapitulatif, puis `legacy-audit.final` : **Générer roadmap + specs** / **Réajuster** (une seule fois : `K audit readjust --run <run>` rejoue la ronde d'affectation) / **Abandonner** (Phase 7 sans rien écrire). Sans interaction : `--headless` = `stop`.

## Phase 6 — Génération (seule phase qui écrit)

1. **Roadmap** (LA-09) : compléter le fichier de données (spec, `not_retained`) puis `K audit render --run <run> --data-file …` écrit `ROADMAP-legacy.md` depuis le gabarit du noyau : jalons et tableaux, liens relatifs en `/`, statuts `A_FAIRE` / `EN_COURS` / `FAIT` / `REPORTE`, sections « non retenus » et « rejetés », familles non auditées. Reprise : lignes existantes conservées, statuts préservés, « roadmap reprise » au rapport.
2. **Specs** (LA-11) : pour chaque spec de `plan`, écrire avec Write le JSON des sections de **jugement** `{context, scope, criteria[], out_of_scope, risks}` (critères objectivement testables, entrée → sortie ou exception attendue ; spec regroupée : un critère par finding et les ids dans `context` ; spec aval d'un XL : prérequis rappelé dans `context` et `risks`), puis `K audit spec --run <run> --finding <LEG-nn> --sections … --number <n> --slug <slug-court>`. Le noyau écrit le contrat factory exact (première ligne `Statut : PROPOSEE`, sections Contexte, Périmètre, Critères d'acceptation, Hors-périmètre, Risques, Questions ouvertes), **ajoute toujours la réécriture d'historique en Hors-périmètre pour un secret**, et **ne remplace jamais une spec existante** (`personnalisé-conservé`, signalé).
3. `K audit publish --run <run> --deliverable` publie les verdicts au registre projet (RG-03).

## Phase 7 — Rapport final

- **Carte** : repo, stack, taille, git présent/absent, complet ou échantillonné, roadmap créée ou reprise ;
- **Findings** : tableau `| Famille | Findings bruts | Confirmés | Rejetés/dédupliqués |` (LA-13, depuis `counters`) ;
- **Jalons** : intitulés, nombre de findings et charge cumulée (répartition des tailles) par jalon ;
- **Fichiers écrits** : roadmap + specs (créées / préservées / regroupées / découpées), avec l'état rendu par le noyau ;
- **Prochaine action** : factory présente → `/factory-run "specs/SPEC-leg-01-<slug>.md"` (il porte lui-même la gate d'approbation) ; absente → d'abord `/software-factory` ;
- **Reste à faire** : findings non retenus, XL découpés, et l'avertissement secrets — la purge d'historique n'est jamais faite par le skill ni par une spec générée.
