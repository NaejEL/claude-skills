---
name: audit
description: Audit unifié en lecture seule d'un projet — cartographie, un auditeur par lentille (dette d'accumulation d'un repo legacy, dette de génération d'un projet généré par IA, revue d'un projet de recherche IA), validation adversariale, priorisation interactive, puis un seul AUDIT.md et des specs. À utiliser quand l'utilisateur veut auditer un projet, savoir par où l'attaquer ou obtenir une roadmap de remise à niveau.
context: fork
user-invocable: true
argument-hint: "[REPO] [--profile p[;p]] [--lenses \"l;…\"] [--max-specs N] [--max-findings N] [--max-questions N] [--models \"r=m;…\"]"
---

# Audit — diagnostic unifié, un seul `AUDIT.md`

Auditer le projet `REPO` (défaut : dossier courant) avec les lentilles des profils actifs et écrire **un seul livrable**, `AUDIT.md`, plus les specs retenues. Remplace `/legacy-audit`, `/vibecode-audit` et `/ai-lab-audit`, conservés comme alias. Ne jamais corriger le projet : le passage à l'exécution se fait par `/factory-run`.

## Noyau déterministe

Code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : **AD** et **LN** (`hcore/profiles.py`), moteur **AU-01** à **AU-16** (`audit.py`), **FD**, **RG**, **TS**, **SO** et **MG** (`unified.py`), **GT**. Appeler la CLI et suivre sa sortie JSON ; ne jamais réimplémenter. `<PY>` : premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9 (voir `/software-factory`). `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

## Règles impératives

- **Lecture seule absolue sur le projet audité.** Seules écritures : `AUDIT.md`, `specs/SPEC-leg-*` et `SPEC-lab-*`, `.harness/runs/` (le noyau refuse tout autre chemin). `ROADMAP-legacy.md`, `AUDIT-vibecode.md` et `AUDIT-lab.md` ne sont jamais écrits, jamais modifiés.
- **« Zéro finding » est une réponse normale et acceptable** ; cette phrase figure telle quelle dans chaque prompt d'auditeur. Une lentille muette n'est pas une lentille satisfaite.
- **Un auditeur par lentille**, sa lentille et rien d'autre, jamais deux lentilles dans un auditeur ; au plus 5 en parallèle, au-delà en vagues (`waves`, dans l'ordre profil → jeu → lentille).
- **Chaînes interdites** : ne jamais écrire `Statut :` suivi du statut d'un artefact prêt à construire (le noyau le refuse, FD-11). Les specs sont écrites par le noyau.
- Fichiers de transit : écrire avec Write sous `.harness/runs/`, jamais par stdin ni shell.

## Phase 1 — Arguments, profils, lentilles

1. Écrire `$ARGUMENTS` avec Write dans `.harness/runs/audit-arguments.txt`, en extraire `REPO`, `--via <alias>` (option interne) et les options. `K audit open --root "<REPO>" [--via <alias>]` ouvre le journal `audit-<horodatage>` et y consigne l'événement `alias`.
2. **Profils actifs** : `--profile` ; sinon `K stamp resolve --root "<REPO>"` (tampon, puis fichiers générés antérieurs) ; sinon scout **en lecture seule** (Explore, voir `/software-factory`, rôle `harness.scout`) dont le verdict sert à cet audit et **n'est pas écrit** dans le tampon, gate `audit.profiles` (même sémantique que `software-factory.profiles` : proposition nette en `auto` → défaut, ambiguë → exit 1, headless `default` si nette).
3. `K audit plan --root "<REPO>" --profile "<p;p>" [--lenses …] [--max-specs N] [--max-findings N] [--max-questions N] --via …` rend `lenses` (défaut : union des lentilles ; une lentille ou un axe hors profil actif ou inconnu → exit 2 ; `securite` → `acces;injection;metier`), `waves` et `caps` (`legacy` : `--max-specs` ≤ 25 défaut 15 ; `vibecode` : `--max-findings` ≤ 30 défaut 15 ; `research` : `--max-questions` ≤ 12 défaut 6 ; option d'un jeu inactif → exit 2).
4. Un moteur par jeu actif, dans l'ordre du tampon : `K audit start --unified --skill legacy-audit|vibecode-audit|ai-lab-audit --root "<REPO>" --only "<lentilles du jeu retenues>" --arguments-file …` (jeu `legacy` → `legacy-audit`, `vibecode` → `vibecode-audit`, `research` → `ai-lab-audit`). Il sonde git (`git_absent` : aucune commande git ensuite), lit la factory et **reprend** `AUDIT.md` et chaque ancien livrable non encore importé (statuts `FAIT`, `EN_COURS`, `TRANCHEE` préservés, numérotation poursuivie, `imports`, `import_warnings` à reporter). Le fichier d'arguments ne porte que `REPO`, le plafond du jeu et `--models`.

## Phase 2 — Cartographie commune

Union des étapes des jeux actifs : arborescence 2-3 niveaux, `K stack detect --root "<REPO>"` (bornes : au-delà de 2000 fichiers, `sampled`, 3 niveaux, 40 fichiers par auditeur), manifestes, README, LICENSE, CI, tests, `git_absent`, factory et labo présents ; selon le jeu, étapes de `map_text` (`K profile show <profil>`, `lens_sets[]`) : corpus scientifique et reprise du journal (`research`) ; frontières de confiance, signaux de génération, paires de réimplémentation, vérifications déterministes, artefact de distribution (`vibecode`).

## Phase 3 — Auditeurs par lentille

Par vague, **en un seul message**, un auditeur par lentille (`subagent_type` de la lentille quand le labo est présent, sinon Explore ; paramètre `model` du `model_role` quand `pass_param` est vrai, jamais pour `inherit`). Prompt = carte, `fragment_text` de la lentille (`K profile show <profil>`, `lenses[]`) et `critical_text`, budget de lecture, interdiction d'écrire (et d'exécuter, sauf `allowed_exec`), preuve vérifiable (fichier + ligne + extrait ≤ 3 lignes), barème T-shirt (`size_scale` : `dev`, ou coût GPU pour les questions) et bloc JSON final du jeu. Propriétés : `debt` (cadrage de la dette), `shape` (`pattern` : `{pattern, occurrences[≤5], count, sampled}` ; `occurrence` : ces champs sont refusés), `ordering`, `unauditable` (lentille morte deux fois : `finding` « surface non auditable » major, ou `mark` « non auditée »), `no_run` et `no_protocol` (aucun run, aucun protocole pour les lentilles de recherche). Chaque retour : `K audit auditor --run <run du jeu> --unit <unité> --output <fichier> [--dead] --duration-ms <ms> --tokens <n>`.

## Phase 4 — Validation adversariale

Pour chaque `to_validate` (doublons écartés sans validateur, tous jeux confondus), un mini-validateur (rôle `audit.validator`, ou `lab.validator` pour `research`) conteste la preuve, la sévérité et la taille ; champs de verdict admis = `validator_fields` de la lentille ; pour `journal_check`, grep du journal avant de confirmer. `K audit validator …`, puis `K audit next` et `K audit consolidate` par jeu (zéro CONFIRMED → Phase 6).

## Phase 5 — Priorisation interactive (gates, 4 questions au plus par appel)

`audit.software.framing` (jalons, critère dominant) et `audit.software.assignment` (3 appels au plus) si `legacy` ; `audit.software.order` (ordre d'attaque, sort des mineurs) si `vibecode`, et `audit.drop-security` seulement si `vibecode` est partiel et exclut `securite` ; `audit.research.framing` et `audit.research.selection` (2 appels au plus) si `research`. Chaque gate : `K gate decide --root "<REPO>" --run <audit> --id …`, AskUserQuestion, `K gate answer … --answer-file` (`reask` → reposer la question). Headless : `stop` pour `legacy` et `research` (tout l'audit s'arrête avant l'écriture), `default` signalé en tête pour `vibecode`. Données de rendu : fichier JSON du jeu, puis `K audit plan --run <run du jeu> --data-file …`. Gate finale `audit.final` : **Écrire AUDIT.md (+ specs)** / **Réajuster** (une fois) / **Abandonner**.

## Phase 6 — Génération (seule phase qui écrit)

1. Par jeu : `K audit render --run <run du jeu> --data-file …` prépare le bloc de section (rien n'est écrit sous l'ancien nom). Puis `K audit assemble --root "<REPO>" --set-run <run> [--set-run <run>] --profiles "<p;p>" --lenses "<l;l>" [--sampled]` écrit `AUDIT.md` : en-tête « Généré par /audit le … », profils, lentilles, complet ou échantillonné, lignes `<!-- harness:import … -->` + « Repris depuis », bloc de chaque jeu dans l'ordre du tampon, « Suite ». Idempotent : mêmes entrées, même date → fichier identique.
2. **Specs** : pour chaque spec du plan (jeu `legacy`, et jeu `research` si `software` est actif ou la factory présente et choisi), JSON des sections de jugement `{context, scope, criteria[], out_of_scope, risks}` puis `K audit spec --run … --finding … --sections … --number <n> --slug …` ; jamais écrasée. Les questions `Q-*` se lancent par `/factory-run --profile research "<question>"` ; les deux critères imposés à `fuites` sont conservés.
3. `K audit publish --run <run du jeu> --deliverable` pour chaque jeu (registre projet).

## Phase 7 — Rapport final

Carte (projet, stack, taille, git, complet ou échantillonné, imports et avertissements) ; tableau par lentille (bruts, confirmés, rejetés ou dédupliqués ; scindés et occurrences pour `pattern` ; corrections et questions pour `research`) ; surfaces non auditables ; fichiers écrits (`AUDIT.md` et specs, avec l'état rendu) ; prochaine action (`/factory-run "specs/SPEC-…"`, `/factory-run --profile research "<question>"`) ; reste à faire. Les familles sans finding ne sont pas des familles sans défaut.
