---
name: ai-lab-audit
description: Audite un projet de recherche IA en lecture seule — cartographie du corpus scientifique (journal, architecture, feuille de route, évals), cinq auditeurs parallèles par lentilles (fidélité code↔maths, validité statistique des résultats acquis, fuites et confondants dans les évals, analogies biologiques de façade, cohérence de la feuille de route), validation adversariale des findings, arbitrage humain — puis écrit AUDIT-lab.md avec les corrections à faire et les questions de recherche candidates, chacune prête pour /lab-run. À utiliser quand l'utilisateur veut une revue externe de son PoC de recherche avant de choisir la prochaine expérience.
context: fork
user-invocable: true
argument-hint: "[chemin du projet] [--lenses \"l1;l2\"] [--max-questions N]"
---

# AI Lab audit — revue externe d'un projet de recherche IA

Auditer un projet de recherche sans le modifier : cartographier son corpus scientifique, lancer cinq auditeurs parallèles par lentilles, valider chaque finding par contestation adversariale, faire arbitrer l'utilisateur, puis écrire `AUDIT-lab.md` — d'un côté les **corrections** (bugs, incohérences code↔doc, fuites dans les évals), de l'autre les **questions de recherche candidates** classées, chacune avec la commande `/lab-run` qui la transforme en protocole pré-enregistré. Auditer n'est pas expérimenter : ce skill ne lance aucun run et ne rédige aucun protocole — il alimente la boucle `/lab-run`, il ne la détourne pas.

Parser `$ARGUMENTS` :

- **1er token** (s'il ne commence pas par `--`) = chemin du projet ; défaut : répertoire courant. S'il n'existe pas → arrêt : « le chemin <chemin> n'existe pas ». Mémoriser `REPO` (chemin absolu, quoté si espaces).
- **`--lenses "a;b"`** : restreint l'audit aux lentilles listées (`fidelite`, `validite`, `fuites`, `bio`, `route`, séparateur `;`). Défaut : les cinq. Si le projet n'a aucune inspiration biologique détectée en Phase 1, la lentille `bio` est retirée d'office et le rapport le dit.
- **`--max-questions N`** : plafond de questions de recherche retenues dans le livrable, borné dur à `min(N, 12)`. Défaut : 6. On borne le livrable, jamais la détection : les candidates au-delà du plafond figurent dans `AUDIT-lab.md` (section « non retenues dans ce cycle »).

## Règles impératives (toutes les phases)

- **Lecture seule absolue sur le projet audité.** Seules écritures autorisées, en Phase 6 : `AUDIT-lab.md` et, le cas échéant, des specs `specs/SPEC-lab-*.md`. Ne jamais « corriger en passant », ne jamais lancer un run d'éval, ne jamais toucher au journal, à l'architecture, à la feuille de route ni aux documents figés.
- **« Zéro finding » est une réponse normale et acceptable.** Cette phrase figure telle quelle dans le prompt de chaque auditeur et de chaque validateur — jamais de finding inventé pour remplir un quota. Un projet dont les conclusions sont proportionnées à ses données est un bon résultat d'audit.
- **Chaînes interdites** : ne jamais écrire `Statut :` suivi de `PRE-ENREGISTRE` (la CI du labo la greppe n'importe où dans un fichier) ni `Statut :` suivi de `APPROUVEE` (CI de la factory), où que ce soit. Toute spec générée commence par `Statut : PROPOSEE` ; pour parler de pré-enregistrement ailleurs, périphraser (« une fois le protocole pré-enregistré par /lab-run »).
- **Pas de protocole dans le livrable** : une question candidate est formulée en une phrase falsifiable, avec ce qui la motive (finding source, chiffre du journal) et ce qu'elle trancherait — jamais de prédictions chiffrées, de seeds ni de critères d'abandon : c'est le travail du Director sous gate humaine, dans `/lab-run`.
- **Frugalité** : auditeurs = agents lecture seule recevant la carte et leur lentille (jamais une mission « relis tout ») ; preuve = extrait ≤ 3 lignes avec fichier et ligne, ou citation datée du journal, ou constat structurel ; validateurs = mini-agents à prompt court et effort faible.
- **Registre cumulatif des findings** : tenir en mémoire `{id, fichier|document, ligne|date, lentille, résumé, verdict}` pour tous les findings, **y compris les REJECTED**, alimenté aussi par un `AUDIT-lab.md` préexistant : un finding rejeté, déjà corrigé, ou une question déjà tranchée par une entrée de journal postérieure ne ressuscite pas.
- **L'arbitrage appartient à l'utilisateur** (AskUserQuestion en Phase 5). Si aucune interaction n'est possible (exécution headless), s'arrêter en erreur explicite avant la Phase 5.

## Phase 1 — Reconnaissance et cartographie du corpus

Dans la session principale, sans sous-agent :

1. **Stack** : manifestes Python (`pyproject.toml`, `requirements.txt`, `environment.yml`) ou autres ; framework (PyTorch, JAX, NumPy…) ; interpréteur et commande de test documentés dans `CLAUDE.md`/`README.md` (relevés, jamais exécutés sauf la commande de test si elle est CPU et sans téléchargement — un échec de tests est un finding `FID-`).
2. **Corpus scientifique** (même méthode que `/ai-lab` Phase 1b) : identifier par lecture de `CLAUDE.md`, `README.md` et `docs/` les chemins exacts du **journal d'expériences** (et le format de ses entrées), du **document d'architecture** (sections maths, décisions numérotées, pièges connus, protocole des évals), de la **feuille de route** (mécanismes candidats, déclencheurs, tableau des résultats), des **documents figés** (déclarés « ne pas modifier »), de la **vision**, de la **classe de config** centrale, des **scripts d'éval** (nom, question mesurée, métrique, contrôle, options `argparse` réelles), du **vocabulaire**, de l'**état courant** (section « État du projet »), des **contraintes non négociables** et des **références bibliographiques** citées.
3. **Labo** : présence de `.claude/agents/lab-director.md`, `lab-neuro.md`, `lab-math.md` et de `.claude/skills/lab-run/SKILL.md`. Si présents, `LAB=true` : les auditeurs des lentilles `fidelite`/`validite`/`fuites` sont lancés avec `subagent_type: lab-math`, la lentille `bio` avec `lab-neuro`, la lentille `route` avec `lab-director` (chacun reçoit en plus le prompt de lentille ci-dessous). Sinon `LAB=false` : agents `Explore` avec le prompt de lentille seul, et recommandation `/ai-lab` au rapport — non bloquant.
4. **Factory** : présence de `.claude/skills/factory-run/SKILL.md` (détermine si les corrections peuvent devenir des specs en Phase 6).
5. **Reprise** : si `<REPO>/AUDIT-lab.md` existe, charger toutes ses lignes (corrections, questions retenues / non retenues / rejetées) dans le registre cumulatif. Pour chaque question déjà retenue, vérifier dans le journal si une entrée postérieure à la date de l'audit l'a tranchée : si oui, la marquer `TRANCHEE (journal <date>)`.
6. **Bornes** : si le journal dépasse 1 500 lignes, les auditeurs `validite` et `route` reçoivent les 15 dernières entrées plus le tableau des résultats, pas le journal entier ; marquer l'audit « échantillonné » pour le rapport.

Produire la **carte** : stack, matériel déclaré, chemins du corpus avec le nombre d'entrées du journal et la date de la dernière, liste des évals et de leurs métriques, liste des mécanismes de la feuille de route avec leur statut (retenu / repli / mesuré / à faire), contraintes non négociables, références, `LAB`, factory, reprise, échantillonnage.

## Phase 2 — Audit parallèle par lentilles

Lancer **en un seul message** les auditeurs (lecture seule), un par lentille retenue :

- **(a) `fidelite`** (ids `FID-`) — fidélité code ↔ maths : pour chaque équation du document d'architecture, l'implémentation correspondante fait-elle exactement ce qui est écrit (ordre des opérations, normalisations, signes, dimensions, précision numérique, valeurs par défaut de la config égales à celles annoncées dans l'état du projet) ? décisions de design documentées mais non reflétées dans le code, ou l'inverse (comportement du code sans décision écrite) ; hyperparamètres en dur hors de la classe de config ; tests unitaires absents sur un composant mathématique central ; contraintes non négociables violées (ex. un gradient calculé dans un projet « sans backprop », une mémoire en fp16 quand fp32 est exigé).
- **(b) `validite`** (ids `VAL-`) — validité statistique des résultats acquis : conclusions du journal, du tableau des résultats ou de l'état du projet plus fortes que leurs données (un seul seed, écart-type du même ordre que l'effet, pas d'intervalle rapporté, comparaison non appariée) ; effets présentés comme acquis qui reposent sur une seule taille de modèle ou un seul corpus ; prédictions pré-enregistrées non atteintes mais résultat classé positif ; comparaisons multiples sans correction ; chiffres incohérents entre deux documents (journal vs tableau vs `CLAUDE.md`) ; « résultat négatif » devenu « inconclusif » sans cause identifiée.
- **(c) `fuites`** (ids `LEAK-`) — fuites et confondants dans les évals : information qui traverse le reset ou le vidage de contexte par un autre canal que celui mesuré ; état global non réinitialisé entre conditions ; seed non fixée ou fixée différemment selon la condition ; baseline et condition testée exécutées avec un nombre de pas, de tokens ou une précision différents ; métrique calculée sur un sous-ensemble différent ; mode train/eval du modèle ; troncature, arrondi ou `try/except` silencieux ; écriture dans la mémoire pendant la phase de rappel là où le protocole l'interdit ; contrôle documenté dans l'architecture mais absent du script.
- **(d) `bio`** (ids `BIO-`) — analogies biologiques : mécanismes dont le nom biologique promet une propriété que l'implémentation n'a pas (analogie de façade) ; mécanismes « repli » de la feuille de route dont le déclencheur est déjà observé dans le journal sans que le mécanisme ait été essayé, ou l'inverse (mécanisme implémenté sans déclencheur observé, contraire à la règle « un symptôme avant un remède ») ; propriété biologique connue qui prédit un comportement testable non encore mesuré ; référence citée de façon inexacte.
- **(e) `route`** (ids `ROAD-`) — cohérence de la feuille de route : désaccords entre l'état courant de `CLAUDE.md`, la dernière entrée du journal et le tableau des résultats ; expériences annoncées « à faire » dont le prérequis est déjà satisfait (ou dont le prérequis a été invalidé) ; ordre recommandé contredit par un résultat postérieur ; questions ouvertes posées dans un document et jamais reprises ; décisions de design « quasi closes » sans la mesure qui les clôturerait ; conflits entre deux décisions numérotées non arbitrés.

Chaque prompt d'auditeur contient : la carte de la Phase 1, sa lentille **et rien d'autre à chercher**, le budget de lecture, la phrase « **zéro finding est une réponse normale et acceptable** », l'interdiction d'écrire et d'exécuter quoi que ce soit (hors commande de test CPU pour `fidelite`), l'exigence de preuve vérifiable (fichier + ligne + extrait ≤ 3 lignes, ou document + date d'entrée + citation, ou constat structurel), la distinction entre les deux natures de finding, et le format de sortie exigé — un unique bloc JSON final :

```json
{"findings": [{"id": "VAL-01", "lens": "validite", "nature": "correction|question",
  "severity": "critical|major|minor", "title": "résumé court",
  "location": {"file": "chemin/relatif ou null", "line": 12, "journal_date": "AAAA-MM-JJ ou null"},
  "evidence": "extrait ≤ 3 lignes ou citation", "impact": "ce que ça change pour les conclusions du projet",
  "proposal": "correction en une phrase, OU question de recherche en une phrase falsifiable",
  "size": "XS|S|M|L|XL", "depends_on": []}]}
```

`nature: correction` = quelque chose de faux ou d'incohérent à réparer (code, doc, éval). `nature: question` = quelque chose d'inconnu que seule une expérience tranche. `severity: critical` est réservé aux fuites qui invalident un résultat publié dans le tableau, aux violations d'une contrainte non négociable, et aux conclusions-titre du projet reposant sur une preuve insuffisante. `size` s'applique aux corrections (barème T-shirt : XS < 30 min, S < 2 h, M demi-journée, L 1-2 jours, XL à découper) ; pour une question, `size` estime le coût de l'expérience sur le matériel déclaré (XS = quelques minutes GPU, S < 1 h, M demi-journée de runs, L plusieurs jours, XL = hors de portée du matériel).

## Phase 3 — Validation adversariale

1. **Dédupliquer** chaque finding contre le registre cumulatif (même fichier/ligne ou même document/date et même lentille ; même question reformulée), verdicts REJECTED, entrées `TRANCHEE` et audit préexistant compris — les doublons sont écartés sans validateur.
2. Pour chaque finding survivant, lancer un **mini-agent validateur** (effort faible, prompt court : le finding + consigne de relire la preuve à la source) chargé de le contester : la preuve existe-t-elle réellement à cet endroit ? le journal ou l'architecture ne contiennent-ils pas déjà la réponse, la justification ou la décision (un validateur de `validite`/`route`/`bio` doit grepper le journal pour la question posée avant de confirmer) ? est-ce un vrai problème ou un choix délibéré documenté ? la nature (correction vs question), la sévérité et la taille sont-elles plausibles ? Sortie exigée :

```json
{"verdict": "CONFIRMED|REJECTED", "reason": "justification en une phrase", "nature_correction": "correction|question|null", "size_correction": "XS|S|M|L|XL|null"}
```

3. Ajouter chaque finding au registre avec son verdict. **Si zéro CONFIRMED → sauter en Phase 7** avec un rapport « projet cohérent sur les lentilles auditées » (réponse normale).

## Phase 4 — Consolidation

Dans la session principale, sans sous-agent :

- Appliquer les corrections de nature et de taille des validateurs. Séparer en deux listes : **corrections** renumérotées `COR-01…` (tri : sévérité décroissante puis taille croissante) et **questions** renumérotées `Q-01…` (tri : sévérité décroissante puis coût croissant).
- **Dépendances** : une question dont la mesure repose sur une éval touchée par une correction `LEAK-`/`FID-` dépend de cette correction (on ne relance pas une expérience sur un banc fuyant) ; une correction de doc (`ROAD-`) qui ne fait que refléter un résultat déjà acquis est taille XS et sans dépendance.
- Pour chaque question, rédiger la **fiche** en quatre lignes : *Question* (une phrase falsifiable), *Motivation* (findings sources et chiffres cités), *Ce qu'elle trancherait* (décision de design, ligne du tableau, conclusion-titre), *Coût estimé*. Rien d'autre — pas de protocole.
- Regrouper les questions en **2 à 4 thèmes** (typiquement : fiabilité des résultats acquis, mécanismes à essayer, passage à l'échelle, adressage/capacité — selon ce qui ressort) pour la phase interactive.

## Phase 5 — Arbitrage interactif (gate humaine)

Ne jamais présenter les findings un par un : corrections par sévérité, questions par thème. Deux rondes bornées d'AskUserQuestion :

1. **Cadrage** (un appel, deux questions) : « Que faire des corrections ? » (les transformer en specs factory si la factory est présente / les lister seulement dans l'audit / ignorer les mineures) et « Critère de priorité pour les questions ? » (fiabiliser d'abord — ce qui consolide les conclusions-titre / le moins cher d'abord / suivre l'ordre de la feuille de route / garder l'ordre proposé).
2. **Sélection** (un appel par groupe de ≤ 4 thèmes, 2 appels maximum) : une question par thème — « Thème <nom> (<n> questions, coûts <répartition>) : les retenir ? » avec options Toutes / Seulement la mieux classée / Aucune. Appliquer ensuite le plafond `--max-questions` dans l'ordre du critère choisi.

Présenter le récapitulatif (corrections → specs ou liste ; questions retenues dans l'ordre, avec coût cumulé) puis une dernière question : **Écrire AUDIT-lab.md (+ specs)** / **Réajuster** (une seule fois — rejoue la ronde 2) / **Abandonner** (Phase 7 sans rien écrire).

## Phase 6 — Génération (seule phase qui écrit)

### 6.1 `AUDIT-lab.md`

Écrire `<REPO>/AUDIT-lab.md`. Liens en chemins relatifs avec `/`. Squelette :

```markdown
# Audit du labo — <nom du projet>

Généré par /ai-lab-audit le <date>. Labo : présent | absent (lancer /ai-lab). Factory : présente | absente.
Lentilles : <liste>. Audit complet | échantillonné. Journal audité jusqu'à l'entrée du <date>.

## Corrections à faire
| ID | Finding | Lentille | Sévérité | Taille | Dépend de | Spec | Statut |
| --- | --- | --- | --- | --- | --- | --- | --- |
| COR-01 | E2 : la baseline n'est pas exécutée avec le même nombre de tokens que la condition testée | fuites | critical | S | — | [specs/SPEC-lab-01-e2-meme-budget.md](specs/SPEC-lab-01-e2-meme-budget.md) | A_FAIRE |

## Questions de recherche retenues (ordre recommandé)
### Q-01 — <titre court>
- **Question** : <une phrase falsifiable>
- **Motivation** : <findings sources, chiffres cités avec leur date de journal>
- **Ce qu'elle trancherait** : <décision / ligne du tableau / conclusion-titre>
- **Coût estimé** : <T-shirt> — **Dépend de** : COR-01
- **Lancer** : `/lab-run "<la question telle quelle>"`
- **Statut** : A_FAIRE

## Questions non retenues dans ce cycle
| ID | Question | Raison (exclue par l'utilisateur / au-delà du plafond) |

## Findings rejetés à la validation
| ID | Finding | Raison |
```

Statuts autorisés : `A_FAIRE` / `EN_COURS` / `FAIT` / `TRANCHEE (journal <date>)` / `REPORTE`. **Idempotence / reprise** : si un audit existait, préserver les statuts `FAIT`/`EN_COURS`/`TRANCHEE`, poursuivre la numérotation, ne pas régénérer les specs existantes, signaler « audit repris » au rapport.

### 6.2 Specs de correction (si factory présente et choix utilisateur)

Une spec `specs/SPEC-lab-<nn>-<slug>.md` par correction retenue, au **contrat factory exact** (première ligne `Statut : PROPOSEE`, sections *Contexte*, *Périmètre*, *Critères d'acceptation* testables, *Hors-périmètre*, *Risques*, *Questions ouvertes*). Regrouper les XS de même lentille (4 maximum) ; découper les XL en specs chaînées. Pour une correction de `fuites`, le critère d'acceptation inclut toujours « la baseline et la condition testée sont exécutées par la même commande à la variable manipulée près » et « les résultats du tableau dépendant de cette éval sont marqués *à re-mesurer* dans l'audit » — la re-mesure elle-même est une question `Q-`, jamais une spec. Ne jamais écraser une spec existante.

## Phase 7 — Rapport final

Émettre un rapport structuré :

- **Carte** : projet, stack, corpus détecté (chemins), dernière entrée de journal, `LAB`/factory, complet ou échantillonné, audit créé ou repris ;
- **Findings** : tableau `| Lentille | Bruts | Confirmés | Rejetés/dédupliqués | dont corrections | dont questions |` ;
- **Corrections** : nombre, sévérités, specs écrites ou liste seule ;
- **Questions retenues** : ordre, coût cumulé, dépendances envers des corrections ;
- **Prochaine action** : s'il existe une correction `critical` dont dépend une question, la traiter d'abord (`/factory-run "specs/SPEC-lab-01-<slug>.md"` ou à la main) ; sinon `/lab-run "<Q-01>"` — c'est `/lab-run` qui portera le protocole et sa gate ; labo absent → lancer d'abord `/ai-lab` ;
- **Reste à faire** : questions non retenues, XL découpés, résultats du tableau marqués *à re-mesurer*.
