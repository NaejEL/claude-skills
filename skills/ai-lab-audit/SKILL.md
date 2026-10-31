---
name: ai-lab-audit
description: Audite un projet de recherche IA en lecture seule — cartographie du corpus scientifique (journal, architecture, feuille de route, évals), cinq auditeurs parallèles par lentilles (fidélité code↔maths, validité statistique des résultats acquis, fuites et confondants dans les évals, analogies biologiques de façade, cohérence de la feuille de route), validation adversariale des findings, arbitrage humain — puis écrit AUDIT-lab.md avec les corrections à faire et les questions de recherche candidates, chacune prête pour /lab-run. À utiliser quand l'utilisateur veut une revue externe de son PoC de recherche avant de choisir la prochaine expérience.
context: fork
user-invocable: true
argument-hint: "[chemin du projet] [--lenses \"l1;l2\"] [--max-questions N] [--models \"role=modele;...\"]"
---

# AI Lab audit — revue externe d'un projet de recherche IA

Auditer un projet de recherche sans le modifier : cartographier son corpus scientifique, lancer cinq auditeurs parallèles par lentilles, valider chaque finding par contestation adversariale, faire arbitrer l'utilisateur, puis écrire `AUDIT-lab.md` — d'un côté les **corrections** (bugs, incohérences code↔doc, fuites dans les évals), de l'autre les **questions de recherche candidates** classées, chacune avec la commande `/lab-run` qui la transforme en protocole pré-enregistré. Auditer n'est pas expérimenter : ce skill ne lance aucun run et ne rédige aucun protocole — il alimente la boucle `/lab-run`, il ne la détourne pas.

## Noyau déterministe

Les règles déterministes sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : ne jamais les réimplémenter, appeler la CLI `harness.py` et suivre sa sortie JSON. Règles propres : **AA-01** à **AA-14** (`hcore/audit.py` et son profil, `findings.py`, `tshirt.py`) ; partagées : **AU-01** à **AU-16**, **FD-01** à **FD-11**, **RG-01** à **RG-07**, **TS-01** à **TS-05**, **ST-01** à **ST-05**, **GT-01** à **GT-08**, **MD-01** à **MD-08**, **JR-01**, **JR-02** (journal sous `.harness/runs/` du projet audité).

**Interpréteur** : `<PY>` = le premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9 : `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`. Toute sortie d'agent et tout JSON se transmettent au noyau par un fichier écrit avec l'outil Write sous `.harness/runs/` (jamais par le shell) ; le noyau le supprime après lecture.

## Règles impératives (toutes les phases)

- **Lecture seule absolue sur le projet audité.** Seules écritures autorisées (le noyau refuse toute autre, AA-04) : `AUDIT-lab.md`, `specs/SPEC-lab-*.md`, le journal `.harness/runs/` et le registre projet. Ne jamais « corriger en passant », ne jamais lancer un run d'éval, ne jamais toucher au journal, à l'architecture, à la feuille de route ni aux documents figés.
- **« Zéro finding » est une réponse normale et acceptable.** Cette phrase figure telle quelle dans le prompt de chaque auditeur et de chaque validateur — jamais de finding inventé pour remplir un quota.
- **Une lentille muette n'est pas une lentille satisfaite.** Un auditeur mort ou à la sortie inexploitable rend le même silence qu'un vrai « zéro finding », et ce silence se lit comme un satisfecit — particulièrement grave ici, où l'absence de finding sur `validite` ou `fuites` peut être invoquée pour publier un résultat. Le noyau relance **une fois**, puis rend `not-audited` : la lentille figure comme **non auditée** dans `AUDIT-lab.md`, marquée `échec` au rapport ; ne jamais présenter un audit amputé comme une couverture complète. Un validateur mort deux fois laisse son finding **non validé**, jamais `CONFIRMED`.
- **Chaînes interdites** : ne jamais écrire `Statut :` suivi de `PRE-ENREGISTRE` ni de `APPROUVEE`, où que ce soit (le noyau le vérifie, FD-11). Toute spec commence par `Statut : PROPOSEE` ; ailleurs, périphraser (« une fois le protocole pré-enregistré par /lab-run »).
- **Pas de protocole dans le livrable** : une question candidate tient en une phrase falsifiable, avec ce qui la motive (finding source, chiffre du journal) et ce qu'elle trancherait — jamais de prédictions chiffrées, de seeds ni de critères d'abandon : c'est le travail du Director sous gate humaine, dans `/lab-run`.
- **Frugalité** : auditeurs en lecture seule recevant la carte et leur lentille ; preuve = extrait ≤ 3 lignes avec fichier et ligne, ou citation datée du journal, ou constat structurel ; validateurs = mini-agents à prompt court.
- **L'arbitrage appartient à l'utilisateur** (Phase 5). Sans interaction possible, s'arrêter en erreur explicite **avant la Phase 5** (`stop`, AA-13).

## Phase 1 — Reconnaissance et cartographie du corpus

1. **Arguments, labo, reprise** : écrire `$ARGUMENTS` tel quel dans `.harness/runs/ai-lab-audit-arguments.txt`, puis `K audit start --skill ai-lab-audit --arguments-file …` (AU-01 à AU-03, AA-01 à AA-03 : `REPO` absolu ; `--lenses` parmi `fidelite`, `validite`, `fuites`, `bio`, `route` séparées par `;` ; `--max-questions` borné à `min(N, 12)` défaut 6 ; `--models` pour cet audit seulement, rôles `neuro`, `math`, `director.cadrage`, `validator`, valeur ou rôle inconnus → exit 2). Il rend `run`, `lab` (AA-05 : agents et `lab-run` présents), `factory`, pour chaque auditeur `subagent_type` (`lab-math`, `lab-neuro`, `lab-director`, ou `Explore` sans labo : recommander alors `/ai-lab`, non bloquant), `model` et `pass_param` (AA-06 : `math` pour fidelite/validite/fuites, `neuro` pour bio, `director.cadrage` pour route, `validator` pour les validateurs), et la reprise d'un `AUDIT-lab.md` existant. Si le projet n'a **aucune inspiration biologique** (jugement, après la lecture du corpus de l'étape 2, qui peut précéder `audit start` : `REPO` = premier token sans `--`, sinon le répertoire courant), lancer `audit start` avec `--lenses` sans `bio` et le dire au rapport. Passer le paramètre `model` à chaque sous-agent quand `pass_param` est vrai, jamais pour `inherit` ; annoncer l'affectation en une ligne avant la première dépense. Un rôle coûteux reçoit la carte et sa lentille, jamais le journal entier.
2. **Stack et corpus** : `K stack detect --root "<REPO>"`, puis lire `CLAUDE.md`, `README.md` et `docs/` pour les chemins exacts du **journal d'expériences** (et le format de ses entrées), du **document d'architecture**, de la **feuille de route**, des **documents figés**, de la **vision**, de la **classe de config**, des **scripts d'éval** (question, métrique, contrôle, options `argparse`), du **vocabulaire**, de l'**état courant**, des **contraintes non négociables** et des **références**. Commande de test documentée relevée, exécutée seulement si elle est CPU et sans téléchargement (un échec est un finding `FID-`).
3. **Bornes** : `K stack journal --file <journal>` (ST-05) : au-delà de 1500 lignes (`sampled`), `validite` et `route` reçoivent les 15 dernières entrées plus le tableau des résultats ; marquer l'audit « échantillonné ».
4. **Reprise** : pour chaque question déjà retenue, chercher dans le journal une entrée **postérieure** à la date de l'audit qui l'a tranchée : `K audit settle --audit-date <AAAA-MM-JJ> --entry-date <AAAA-MM-JJ>` rend `TRANCHEE (journal <date>)` (AA-10) ou `null`.

Produire la **carte** : stack, matériel déclaré, chemins du corpus avec nombre d'entrées du journal et date de la dernière, évals et métriques, mécanismes de la feuille de route et leur statut, contraintes, références, `lab`, `factory`, reprise, échantillonnage.

## Phase 2 — Audit parallèle par lentilles

Lancer **en un seul message** les auditeurs (lecture seule, AA-05), un par lentille retenue :

- **(a) `fidelite`** (`FID-`) — fidélité code ↔ maths : pour chaque équation de l'architecture, l'implémentation fait-elle exactement ce qui est écrit (ordre des opérations, normalisations, signes, dimensions, précision, valeurs par défaut égales à celles de l'état du projet) ? décisions documentées non reflétées dans le code, ou l'inverse ; hyperparamètres en dur hors de la classe de config ; tests absents sur un composant mathématique central ; contraintes non négociables violées (gradient dans un projet « sans backprop », mémoire fp16 quand fp32 est exigé).
- **(b) `validite`** (`VAL-`) — validité statistique des résultats acquis : conclusions plus fortes que leurs données (un seul seed, écart-type du même ordre que l'effet, pas d'intervalle, comparaison non appariée) ; effets reposant sur une seule taille de modèle ou un seul corpus ; prédictions pré-enregistrées non atteintes mais résultat classé positif ; comparaisons multiples sans correction ; chiffres incohérents entre journal, tableau et `CLAUDE.md` ; « négatif » devenu « inconclusif » sans cause.
- **(c) `fuites`** (`LEAK-`) — fuites et confondants dans les évals : information traversant le reset par un autre canal que celui mesuré ; état global non réinitialisé entre conditions ; seed ou budget (pas, tokens, précision) différents selon la condition ; métrique sur un sous-ensemble différent ; mode train/eval ; troncature ou `try/except` silencieux ; écriture mémoire pendant le rappel là où le protocole l'interdit ; contrôle documenté mais absent du script.
- **(d) `bio`** (`BIO-`) — analogies biologiques de façade (le nom promet une propriété que l'implémentation n'a pas) ; mécanismes « repli » dont le déclencheur est déjà observé sans essai, ou implémentés sans déclencheur (contre « un symptôme avant un remède ») ; propriété biologique prédisant un comportement testable non mesuré ; référence citée inexactement.
- **(e) `route`** (`ROAD-`) — cohérence de la feuille de route : désaccords entre état courant, dernière entrée du journal et tableau des résultats ; expériences « à faire » dont le prérequis est satisfait ou invalidé ; ordre contredit par un résultat postérieur ; questions ouvertes jamais reprises ; décisions « quasi closes » sans la mesure qui les clôturerait ; décisions numérotées en conflit non arbitrées.

Chaque prompt contient : la carte, sa lentille **et rien d'autre**, le budget de lecture, la phrase « **zéro finding est une réponse normale et acceptable** », l'interdiction d'écrire et d'exécuter, la preuve vérifiable, la distinction des deux natures, et un unique bloc JSON final (AA-07) :

```json
{"findings": [{"id": "VAL-01", "lens": "validite", "nature": "correction|question",
  "severity": "critical|major|minor", "title": "résumé court",
  "location": {"file": "chemin/relatif ou null", "line": 12, "journal_date": "AAAA-MM-JJ ou null"},
  "evidence": "extrait ≤ 3 lignes ou citation", "impact": "ce que ça change pour les conclusions du projet",
  "proposal": "correction en une phrase, OU question de recherche falsifiable en une phrase",
  "size": "XS|S|M|L|XL", "depends_on": []}]}
```

`correction` = quelque chose de faux ou d'incohérent à réparer ; `question` = quelque chose d'inconnu que seule une expérience tranche. `critical` est réservé aux fuites qui invalident un résultat publié dans le tableau, aux violations d'une contrainte non négociable et aux conclusions-titre reposant sur une preuve insuffisante. `size` : barème XS < 30 min, S < 2 h, M demi-journée, L 1-2 jours, XL à découper ; pour une question, coût de l'expérience sur le matériel déclaré (XS quelques minutes GPU, S < 1 h, M demi-journée de runs, L plusieurs jours, XL hors de portée). Chaque retour : `K audit auditor --run <run> --unit <lentille> --output <fichier> [--dead] --duration-ms <ms> --tokens <n>` (`relaunch` : une fois ; `not-audited` ; `validate` avec `to_validate` ; doublons — AA-08 : même fichier et ligne, ou même document et date, et même lentille, y compris REJECTED, `TRANCHEE` et audit préexistant — écartés **sans validateur**).

## Phase 3 — Validation adversariale

Pour chaque finding de `to_validate`, un **mini-agent validateur** (effort faible, rôle `validator`) le conteste : la preuve existe-t-elle à cet endroit ? le journal ou l'architecture contiennent-ils déjà la réponse (un validateur de `validite`/`route`/`bio` **grep le journal** pour la question posée avant de confirmer) ? vrai problème ou choix délibéré documenté ? nature, sévérité et taille plausibles ? Sortie :

```json
{"verdict": "CONFIRMED|REJECTED", "reason": "justification en une phrase", "nature_correction": "correction|question|null", "size_correction": "XS|S|M|L|XL|null"}
```

`K audit validator --run <run> --finding <id> --output <fichier> [--dead]`, puis `K audit next --run <run>` (`step` : `audit`, `validate`, `consolidate`, ou `report` : **zéro CONFIRMED → Phase 7**, « projet cohérent sur les lentilles auditées »).

## Phase 4 — Consolidation

`K audit consolidate --run <run>` applique les corrections de nature et de taille et renumérote (AA-09) : **corrections** `COR-01…` (sévérité décroissante puis taille croissante) et **questions** `Q-01…` (sévérité décroissante puis coût croissant). Reste au jugement : une question dont la mesure repose sur une éval touchée par une correction `LEAK-`/`FID-` en dépend ; une correction de doc (`ROAD-`) qui ne fait que refléter un résultat acquis est XS sans dépendance. Rédiger la **fiche** de chaque question en quatre lignes — *Question*, *Motivation* (findings et chiffres cités avec leur date de journal), *Ce qu'elle trancherait*, *Coût estimé* — et regrouper les questions en **2 à 4 thèmes**.

## Phase 5 — Arbitrage interactif (gate humaine)

Corrections par sévérité, questions par thème, jamais une à une. `K audit themes --skill ai-lab-audit --count <n>` : appels de 4 thèmes au plus, 2 appels maximum. Gates (`K gate decide` / `answer`) : `ai-lab-audit.framing` (un appel, deux questions : corrections en *specs* / *lister* / *ignorer les mineures* ; priorité *fiabiliser* / *moins cher* / *feuille de route* / *ordre proposé*), `ai-lab-audit.selection` (un thème par question : *Toutes* / *Seulement la mieux classée* / *Aucune*). Écrire les choix dans `.harness/runs/ai-lab-audit-data.json` (`name`, `date`, `lab`, `factory`, `lenses`, `journal_date`, `order` selon le critère choisi, `findings` : `{COR-nn: {spec}}`, `{Q-nn: {question, motivation, decides}}` ou `{not_retained: "excluded"|"cap"}`), puis `K audit plan --run <run> --data-file …` (AA-02) rend les questions retenues sous le plafond `--max-questions` (l'excédent : `not_retained_cap`), les specs de correction (XS de même lentille regroupés par 4 ; XL découpés en specs chaînées) et la charge cumulée. Présenter le récapitulatif, puis `ai-lab-audit.final` : **Écrire AUDIT-lab.md** / **Réajuster** (une seule fois, `K audit readjust --run <run>`) / **Abandonner**.

## Phase 6 — Génération (seule phase qui écrit)

1. `K audit render --run <run> --data-file …` écrit `AUDIT-lab.md` (AA-11) depuis le gabarit : corrections, questions retenues avec leur ligne **Lancer** `/lab-run "<question>"`, non retenues, rejetées, lentilles non auditées ; statuts `A_FAIRE` / `EN_COURS` / `FAIT` / `TRANCHEE (journal <date>)` / `REPORTE`. Reprise : statuts préservés, numérotation poursuivie, « audit repris » au rapport.
2. Specs de correction (factory présente et choix de l'utilisateur) : par spec du plan, JSON des sections de jugement `{context, scope, criteria[], out_of_scope, risks}`, puis `K audit spec --run <run> --finding <COR-nn> --sections … --number <n> --slug <slug>`. Le noyau écrit le contrat factory exact (`Statut : PROPOSEE`) et, pour `fuites`, **ajoute toujours les deux critères imposés** (AA-12) : baseline et condition testée exécutées par la même commande à la variable près ; résultats du tableau dépendant de cette éval marqués *à re-mesurer* — la re-mesure est une question `Q-`, jamais une spec. Aucune spec existante n'est écrasée.
3. `K audit publish --run <run> --deliverable`.

## Phase 7 — Rapport final

- **Carte** : projet, stack, corpus (chemins), dernière entrée du journal, `lab`/`factory`, complet ou échantillonné, audit créé ou repris, **affectation des modèles** (rôle → modèle, fichier ou `--models`) ;
- **Findings** (AA-14) : `| Lentille | Bruts | Confirmés | Rejetés/dédupliqués | dont corrections | dont questions |` depuis `counters` ;
- **Corrections** : nombre, sévérités, specs écrites ou liste seule ; **Questions retenues** : ordre, coût cumulé, dépendances envers des corrections ;
- **Prochaine action** : une correction `critical` dont dépend une question d'abord (`/factory-run "specs/SPEC-lab-01-<slug>.md"`), sinon `/lab-run "<Q-01>"` ; labo absent → `/ai-lab` ;
- **Reste à faire** : questions non retenues, XL découpés, résultats marqués *à re-mesurer*.
