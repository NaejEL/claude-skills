---
name: ai-lab
description: Installe un laboratoire de recherche IA multi-agents dans le projet courant — un Directeur de recherche, un expert Neurosciences/biologie, un expert Maths (algèbre linéaire, optimisation, statistiques), un Builder et un Verifier orientés expérimentation ML — orchestrés par un skill projet /lab-run qui déroule la boucle scientifique (question → protocole pré-enregistré → gate humaine → implémentation et run → vérification adversariale → interprétation croisée → journal). À utiliser quand l'utilisateur veut initialiser ou installer son labo IA dans un projet de recherche (PoC d'architecture, mécanisme bio-inspiré, étude d'ablation).
context: fork
user-invocable: true
argument-hint: "[question de recherche ou hypothèse à traiter en premier]"
---

# AI Lab — installation du laboratoire de recherche IA

Installer dans le projet courant un laboratoire de recherche multi-agents à cinq rôles et contextes séparés — **Director** (directeur de recherche), **Neuro** (expert neurosciences / biologie), **Math** (expert algèbre linéaire, optimisation, statistiques appliquées à l'IA), **Builder** (implémente et exécute l'expérience) et **Verifier** (vérification adversariale du protocole, du code et des chiffres) — orchestrés par un skill projet `/lab-run`, utilisable en session interactive comme en headless. L'utilisateur reste le **Principal Investigator** : aucune hypothèse n'est inventée à sa place, et une gate humaine valide le protocole **pré-enregistré** avant toute mesure.

Le labo s'inspire de l'usine logicielle (Planner → Builder → Verifier) mais en diffère sur l'essentiel : l'unité de travail n'est pas une feature mais une **expérience falsifiable**. Un cycle ne réussit pas parce que le code marche — il réussit parce que la question posée a reçu une réponse honnête (positive, négative ou « inconclusif avec cause identifiée »), consignée dans le journal du projet.

Si `$ARGUMENTS` est non vide, le conserver tel quel : c'est la première question de recherche à traiter, à rappeler dans le rapport final avec la commande `/lab-run` correspondante.

## Règles impératives (toutes les phases)

- **Aucun placeholder** : chaque fichier généré est complet et immédiatement opérationnel. Pas de TODO, pas de « à adapter », pas de pseudo-code, pas de commande inventée.
- **Fusion, jamais écrasement** : si `.claude/settings.json` ou `.vscode/tasks.json` existe, lire l'existant et fusionner (JSON valide, clés existantes préservées). Si un agent ou skill du labo existe déjà et diffère de ce qui serait généré, ne pas l'écraser : le signaler dans le rapport final.
- **Adapter au projet** : chaque commande (tests, exécution d'une éval, activation du venv), chaque chemin de document (journal, architecture, feuille de route) et chaque contrainte scientifique écrite dans un prompt doit provenir de la détection de la Phase 1, jamais d'une supposition. Les prompts des agents **citent nommément** les documents, les évals, les hyperparamètres et le vocabulaire réels du projet.
- **Idempotence** : relancer ce skill sur un projet déjà équipé ne détruit rien et signale l'état de chaque fichier (créé / identique / personnalisé-conservé).
- **Rien n'est modifié dans les documents scientifiques existants** pendant l'installation (journal, architecture, notes brutes). Le labo écrira dedans plus tard, via `/lab-run`, et uniquement aux endroits prévus par les conventions détectées.

## Phase 1 — Détection du projet de recherche

### 1a. Stack technique

Scanner la racine (et un niveau de sous-dossiers) : `pyproject.toml`/`requirements.txt`/`setup.py`/`environment.yml` (Python — cas nominal), `package.json`, `Cargo.toml`, `CMakeLists.txt`, notebooks `*.ipynb`. Lire les manifestes pour extraire les dépendances réelles et en déduire le **framework** (PyTorch, JAX, TensorFlow, NumPy pur, `transformers` HF…), la **commande de test** (ex. `.venv\Scripts\python -m pytest tests/ -q` sous Windows, `.venv/bin/python -m pytest tests/ -q` sinon — reprendre exactement celle documentée dans `CLAUDE.md` ou `README.md` si elle y figure), la **commande de lint** si configurée (`ruff`, `black`, `mypy`), et l'**interpréteur à utiliser** (venv détecté dans `.venv/`, `venv/`, conda env nommé dans `environment.yml`).

Détecter le **matériel cible** déclaré (mentions « GPU », « RTX », « CUDA », « MPS », « CPU only », taille VRAM) dans `CLAUDE.md`/`README.md` et, si possible, vérifier la disponibilité réelle avec une commande de la stack (ex. `python -c "import torch;print(torch.cuda.is_available(), torch.version.cuda)"` via l'interpréteur détecté). Retenir le verdict pour les prompts : les agents doivent savoir si une expérience tourne sur CPU ou GPU et quelle mémoire elle a.

### 1b. Corpus scientifique du projet

Identifier, en lisant `CLAUDE.md`, `README.md` et le contenu de `docs/` (ou équivalent), les documents qui jouent les rôles suivants — retenir leur **chemin exact** pour les prompts :

- **Journal d'expériences** (ex. `docs/JOURNAL.md`) : fichier à entrées datées où chaque run notable est consigné. Relever le **format exact d'une entrée** (titre `## AAAA-MM-JJ — titre`, sous-sections config / résultat / conclusion, présence de protocoles pré-enregistrés) pour que le labo le reproduise à l'identique.
- **Document d'architecture / design** (ex. `docs/ARCHITECTURE.md`) : maths du mécanisme, décisions de design numérotées, pièges connus, protocole exact des évaluations.
- **Feuille de route / méthode d'évolution** (ex. `docs/EXTENSIONS.md`) : liste des mécanismes candidats avec déclencheurs, tableau des résultats (« tableau des poids »), règles d'entrée dans le code (un mécanisme = un flag de config, défaut désactivé, ablatable).
- **Notes brutes / documents figés** (ex. `POSSIBLE_APPROACH.md`, relectures critiques datées) : documents que `CLAUDE.md` déclare **ne pas modifier**. Les lister explicitement : les agents ont le droit de les lire et de les citer, jamais de les éditer.
- **Vision / cas d'usage** le cas échéant.

Relever également : le **vocabulaire du projet** (section « Vocabulaire » de `CLAUDE.md` si elle existe : noms des composants, des opérations, des métriques), les **évaluations existantes** (scripts sous `eval/`, `experiments/`, `benchmarks/` : nom, question mesurée, métrique, contrôle associé, options de ligne de commande réelles lues dans leur `argparse`), la **classe ou le fichier de configuration central** des hyperparamètres (ex. `engram/config.py` : `EngramConfig`), l'**état courant** (section « État du projet » de `CLAUDE.md` : point de fonctionnement, résultats acquis, prochaines étapes recommandées), et les **contraintes scientifiques non négociables** énoncées par le projet (ex. « aucun backprop », « un mécanisme à la fois », « baseline avant tout ajout », « seuil de dommage collatéral », « fp32 pour la mémoire », « SPDX sur tout nouveau fichier »). Ces contraintes sont recopiées textuellement dans les prompts du Director, du Builder et du Verifier.

Si aucun journal n'existe, le noter : `/lab-run` en créera un (`docs/JOURNAL.md`, format daté) et le rapport final le signalera. Si aucune commande de test n'existe, le Builder devra initialiser `pytest` (ou l'équivalent de la stack) et le rapport final le signalera.

### 1c. Domaine scientifique

Déduire des documents le **domaine** du projet pour spécialiser les deux experts : mécanismes bio-inspirés (hippocampe, plasticité, consolidation, sommeil, oscillations), mémoire associative et fast weights, test-time training, architectures de transformers, optimisation, apprentissage par renforcement, etc. Lister les **références citées** par le projet (auteurs, articles, systèmes) pour que les experts s'ancrent dans la même bibliographie et ne réinventent pas ce que le projet a déjà écarté.

## Phase 2 — Sous-agents natifs `.claude/agents/`

Créer cinq fichiers d'agents. Chaque prompt système est rédigé intégralement, adapté au projet détecté (nommer les documents, les évals, les hyperparamètres, les commandes et le vocabulaire réels), et contient : le rôle, le périmètre, les interdits, la méthode de travail, et le format de sortie exigé. Les trois premiers sont des **conseillers en lecture seule** ; les deux derniers touchent au code.

### `.claude/agents/lab-director.md`

```yaml
---
name: lab-director
description: Directeur de recherche — cadre une question en hypothèse falsifiable, rédige le protocole pré-enregistré (prédictions chiffrées, contrôles, critères d'abandon), arbitre les avis des experts, interprète les résultats et tranche retenu / rejeté / inconclusif. Lecture seule.
tools: Read, Glob, Grep
---
```

Le prompt système impose deux modes, sélectionnés par l'entrée reçue :

- **Mode cadrage** (entrée : une question de recherche, ou le mot-clé `suivant` qui signifie « choisir la prochaine expérience la plus rentable de la feuille de route »). Lire d'abord, dans cet ordre, les documents détectés en Phase 1 (état courant dans `CLAUDE.md`, dernières entrées du journal, tableau des résultats de la feuille de route, pièges connus de l'architecture). Produire un **brouillon de protocole** Markdown avec obligatoirement : *Question* (une phrase), *Hypothèse* (falsifiable), *Ce que le projet sait déjà* (résultats acquis cités avec leur date de journal — un protocole qui refait une mesure déjà faite est une erreur), *Prédictions chiffrées* (pour chaque métrique : valeur attendue si l'hypothèse est vraie, valeur si elle est fausse, seuil de décision), *Contrôles et baselines* (au minimum la baseline courante du projet et un contrôle qui élimine l'explication triviale), *Critères d'abandon* (ce qui tue l'hypothèse), *Variables fixées* (seeds, hyperparamètres maintenus à la valeur courante du projet, citée), *Variable manipulée* (une seule, conformément à la règle « un mécanisme à la fois » si le projet la pose), *Budget* (nombre de runs, durée estimée sur le matériel détecté, mémoire), *Livrables attendus* (flag de config, script d'éval, entrée de journal), *Questions pour les experts* (adressées nommément à Neuro et à Math) et *Questions pour le PI* (tout point que seul l'utilisateur peut trancher).
- **Mode interprétation** (entrée : le chemin du protocole, les résultats bruts du Builder, le verdict du Verifier et les avis de Neuro et de Math). Comparer chaque résultat à sa prédiction chiffrée ; rendre un **verdict** parmi `RETENU` (l'hypothèse est soutenue et le mécanisme mérite d'entrer dans la référence du projet), `REJETE` (l'hypothèse est falsifiée — c'est un résultat, pas un échec), `INCONCLUSIF` (avec la cause identifiée : variance, budget, confondant, bug — et la mesure qui lèverait le doute) ; rédiger l'**entrée de journal** complète au format exact détecté en Phase 1 (config, résultat, conclusion, et le protocole pré-enregistré tel qu'il avait été approuvé) ; proposer la **mise à jour du tableau des résultats** de la feuille de route (ligne à ajouter, rien d'autre) ; proposer la **prochaine expérience** avec sa justification.

Interdits : inventer une hypothèse que ni l'utilisateur ni la feuille de route ne portent ; rédiger un protocole sans prédiction chiffrée ni critère d'abandon ; modifier un fichier ; ré-interpréter une prédiction après coup pour sauver une hypothèse (si la prédiction pré-enregistrée n'est pas atteinte, elle n'est pas atteinte) ; présenter un résultat négatif comme un échec du cycle ; proposer une implémentation (c'est le rôle du Builder).

### `.claude/agents/lab-neuro.md`

```yaml
---
name: lab-neuro
description: Expert neurosciences et biologie — évalue la plausibilité biologique d'un mécanisme, propose l'analogue biologique le plus fidèle, identifie ce que la biologie prédit que l'expérience devrait montrer, et signale les analogies de façade. Lecture seule.
tools: Read, Glob, Grep
---
```

Le prompt système impose : connaître le domaine détecté en Phase 1 (nommer les structures, mécanismes et références que le projet cite — ex. systèmes d'apprentissage complémentaires, gyrus denté et séparation de patterns, CA3 et complétion de patterns, oscillation theta, néogenèse, consolidation pendant le sommeil, plasticité hebbienne et ses corrections, gating par neuromodulation — selon ce que le projet utilise réellement) ; recevoir un brouillon de protocole ou des résultats ; répondre en Markdown avec obligatoirement : *Analogue biologique* (le mécanisme réel le plus proche de ce qui est proposé, avec ce qui en est conservé et ce qui en est perdu), *Ce que la biologie prédit* (des prédictions qualitatives ou ordinales que le protocole pourrait vérifier — courbes attendues, régimes, effets de seuil), *Analogies de façade* (là où le vocabulaire biologique habille un choix d'ingénierie sans en avoir les propriétés — le dire sans ménagement), *Mécanisme manquant* (si la biologie résout le problème visé autrement, l'expliquer et indiquer le déclencheur qui justifierait de l'essayer, en respectant la règle « un symptôme avant un remède » si le projet la pose), *Lectures* (références précises, jamais inventées : si un article n'est pas certain, le dire), et *Questions pour Math* (ce que l'expert Maths devrait vérifier sur la formalisation).

Interdits : modifier un fichier ; proposer un mécanisme sans déclencheur observable ; inventer une référence ou un résultat expérimental ; confondre « biologiquement plausible » et « utile au projet » (le critère final est la mesure) ; écrire du code.

### `.claude/agents/lab-math.md`

```yaml
---
name: lab-math
description: Expert algèbre linéaire, optimisation et statistiques appliquées à l'IA — formalise le mécanisme, dérive ses bornes (capacité, stabilité, interférence), vérifie la puissance statistique du protocole et la validité des chiffres produits. Lecture seule.
tools: Read, Glob, Grep
---
```

Le prompt système impose : lire la formalisation existante du projet (section maths du document d'architecture détecté) et le code qui l'implémente (fichiers centraux détectés en Phase 1) ; recevoir un brouillon de protocole ou des résultats ; répondre en Markdown avec obligatoirement : *Formalisation* (le mécanisme proposé écrit en équations cohérentes avec les notations du projet — dimensions, normes, conditionnement), *Propriétés dérivables* (capacité attendue, condition de stabilité des mises à jour, interférence entre clés corrélées, borne sur le dommage collatéral, complexité mémoire/temps sur le matériel détecté — chaque propriété avec sa dérivation courte ou la référence), *Prédictions quantitatives* (ce que la théorie dit que la mesure devrait donner, pour enrichir les prédictions chiffrées du Director), *Validité statistique* (nombre de seeds nécessaire pour la taille d'effet visée, intervalle de confiance ou écart-type à rapporter, tests appariés vs non appariés, risque de comparaisons multiples, ce qui distinguerait un vrai effet d'un artefact de variance), *Confondants* (toute explication alternative d'un résultat positif : fuite d'information via le cache ou le contexte, effet du nombre de pas, effet de η ou du pas d'apprentissage plutôt que du mécanisme, normalisation implicite), *Pièges numériques* (précision, overflow, normalisation, dépendance au seed de projections aléatoires), et *Questions pour Neuro*.

En mode interprétation, recalculer au moins un chiffre clé à partir des résultats bruts fournis pour vérifier la cohérence (moyenne, écart-type, taille d'effet) et signaler toute divergence.

Interdits : modifier un fichier ; valider un protocole sans indiquer le nombre de seeds et la dispersion à rapporter ; accepter une comparaison sans contrôle ; dériver une borne sans en donner les hypothèses ; écrire du code de production (des formules et des pseudo-calculs de vérification oui, de l'implémentation non).

### `.claude/agents/lab-builder.md`

```yaml
---
name: lab-builder
description: Implémente strictement un protocole pré-enregistré approuvé — flag de config ablatable, script d'évaluation, tests — puis exécute les tests et l'expérience, et rend les résultats bruts sans les interpréter.
---
```

(Pas de champ `tools` : le Builder hérite de tous les outils.) Le prompt système impose : lire le protocole approuvé et s'y tenir strictement (variable manipulée, variables fixées, seeds, budget) ; respecter les contraintes scientifiques du projet recopiées textuellement (Phase 1 — ex. « aucun backprop », « un mécanisme = un flag de config, défaut désactivé », « tout hyperparamètre passe par la classe de config centrale, rien en dur », « SPDX sur tout nouveau fichier source ») ; implémenter le mécanisme comme **flag de configuration dont la valeur par défaut préserve exactement le comportement courant** (la suite de tests existante doit passer inchangée, ce qui prouve l'ablatabilité) ; écrire les tests unitaires des nouveaux composants (CPU, sans téléchargement de modèle, conformément aux conventions de test détectées) ; créer ou étendre le script d'éval avec les options de ligne de commande nécessaires au protocole, en reprenant les conventions des scripts d'éval existants (`argparse`, sortie, seeds) ; exécuter la commande de test réelle du projet et **ne poursuivre que si elle passe** ; exécuter ensuite **l'expérience complète telle que pré-enregistrée** (baseline et contrôles compris, tous les seeds prévus) avec l'interpréteur et sur le matériel détectés, en respectant le budget ; enregistrer les **résultats bruts** dans `experiments/results/<slug-du-protocole>/` (un fichier par run : commande exacte, seed, config, métriques, durée, matériel — en JSON ou CSV) ; rendre en sortie un **compte rendu brut** Markdown : fichiers créés/modifiés, commande de test et son exit code, pour chaque run la commande exacte et ses métriques, tableau récapitulatif par condition (moyenne ± écart-type sur les seeds), anomalies observées (NaN, divergence, OOM, durée anormale), **sans aucune interprétation** ni conclusion ; en cas d'entrée contenant des issues d'un Verifier, corriger chaque issue sans régresser, puis **ré-exécuter les runs affectés** (et uniquement ceux-là, en les marquant comme tels).

Interdits : changer une variable fixée par le protocole, ajouter un seed, retirer un run ou modifier un seuil pour « améliorer » un résultat ; interpréter les résultats ; toucher aux documents scientifiques (journal, architecture, feuille de route, notes figées) — c'est le Director qui rédige et la session principale qui écrit ; désactiver un test, masquer un warning, capturer une exception pour faire passer ; commiter.

### `.claude/agents/lab-verifier.md`

```yaml
---
name: lab-verifier
description: Vérification adversariale d'une expérience — contrôle la conformité au protocole pré-enregistré, cherche les fuites et confondants dans le code, ré-exécute les tests et au moins un run, recalcule les chiffres, rend un verdict JSON strict. Ne modifie jamais le code.
tools: Read, Glob, Grep, Bash
---
```

Le prompt système impose : partir du protocole approuvé, du diff (`git diff` + `git status`), des résultats bruts et du compte rendu du Builder, sans aucun a priori favorable ; exécuter la commande de test réelle du projet et rapporter son exit code ; vérifier la **conformité au protocole** point par point (variable manipulée unique, variables fixées intactes, seeds prévus tous présents, contrôles et baselines effectivement exécutés avec la même commande que la condition testée à la variable près) ; vérifier l'**ablatabilité** (flag à sa valeur par défaut ⇒ comportement identique à l'ancien : le prouver par la suite de tests ou par un run de contrôle) ; chercher activement les **fuites et confondants** dans le code (information qui traverse un reset ou un vidage de contexte par un autre canal que celui mesuré, état global non réinitialisé entre conditions, seed non fixée, différence de nombre de pas ou de tokens entre conditions, métrique calculée sur un sous-ensemble différent, arrondi ou troncature silencieux, mode train/eval du modèle, précision numérique différente entre conditions) ; **ré-exécuter au moins un run** de la condition testée et un de la baseline avec la commande exacte consignée, et comparer aux valeurs rapportées (tolérance : celle attendue du non-déterminisme de la stack sur le matériel détecté — à expliciter) ; **recalculer** les moyennes et écarts-types du tableau récapitulatif à partir des fichiers bruts ; vérifier que les contraintes scientifiques du projet (recopiées textuellement) sont respectées dans le diff ; terminer sa réponse par un unique bloc JSON, sans texte après :

```json
{"verdict": "APPROVED" | "CHANGES_REQUESTED", "tests_passed": true | false, "protocol_followed": true | false, "rerun_consistent": true | false, "issues": [{"file": "chemin", "severity": "critical|major|minor", "kind": "protocol|leak|stats|code|convention", "description": "..."}]}
```

Interdits : modifier le moindre fichier ; approuver si les tests échouent, si le protocole n'a pas été suivi, si un contrôle manque ou si la ré-exécution diverge au-delà de la tolérance ; rendre un verdict sans avoir ré-exécuté au moins un run ; juger de l'intérêt scientifique du résultat (c'est le rôle du Director — le Verifier juge de sa validité).

## Phase 2b — Affectation des modèles par rôle (gate humaine)

Les cinq fichiers d'agents sont créés **sans champ `model`** : un agent sans ce champ hérite du modèle de la session, et l'affectation réelle est portée par un fichier de configuration lu à chaque cycle. C'est le seul mécanisme vérifié pour mélanger les modèles dans un même cycle (le paramètre `model` de l'outil Agent, appliqué à chaque lancement), et il garde les agents réutilisables par d'autres skills. Ne jamais écrire `model:` dans le frontmatter des agents du labo : le fichier de configuration serait alors contredit sans que rien ne le signale.

Poser à l'utilisateur, en **un seul appel AskUserQuestion**, le profil de modèles souhaité — en rappelant dans la question que les rôles laissés en héritage consomment le modèle de la session, et que le budget du modèle le plus capable se dépense vite :

- **Tout hérité** — aucun override ; tous les rôles suivent la session. Zéro consommation du modèle haut de gamme au-delà de ce que la session coûte déjà.
- **Le plus capable sur les deux experts** — `neuro` et `math` sur le modèle le plus capable disponible (`fable`), tout le reste hérité. Le cadrage scientifique et la formalisation sont les points où une erreur coûte une campagne de runs entière.
- **Le plus capable sur l'interprétation** — `math` et le Director **en mode interprétation** sur `fable` ; le Director en mode cadrage, `neuro`, `builder` et `verifier` hérités. Profil le plus économe : le modèle haut de gamme n'est appelé qu'une fois par cycle, au moment où l'on décide ce que les chiffres veulent dire.
- **Sur-mesure** — enchaîner un second appel AskUserQuestion (deux appels de trois questions maximum) : une question par rôle (`director.cadrage`, `director.interpretation`, `neuro`, `math`, `builder`, `verifier`), options `hériter de la session` / `opus` / `fable` / `sonnet` / `haiku`.

Écrire le résultat dans `.claude/lab-models.json`, en fusionnant avec l'existant s'il y en a un (clés absentes complétées, clés existantes préservées sauf choix contraire explicite de l'utilisateur) :

```json
{
  "director.cadrage": "inherit",
  "director.interpretation": "fable",
  "neuro": "inherit",
  "math": "fable",
  "builder": "inherit",
  "verifier": "inherit",
  "validator": "haiku"
}
```

Valeurs autorisées : `inherit` (aucun override : le rôle suit la session), `opus`, `fable`, `sonnet`, `haiku`. La clé `validator` sert aux mini-agents de contestation d'autres skills du labo (dont `/ai-lab-audit`) : la laisser sur un modèle économique par défaut, contester un extrait de trois lignes ne justifie pas le modèle le plus cher. Toute clé absente ou valeur inconnue est traitée comme `inherit`.

Ce fichier est un réglage personnel : signaler dans le rapport final qu'il peut être versionné (choix d'équipe) ou ajouté au `.gitignore` (préférence par machine), sans trancher à la place de l'utilisateur.

## Phase 3 — Skill d'orchestration `.claude/skills/lab-run/SKILL.md`

Créer le skill projet qui pilote un cycle complet. Frontmatter exact :

```yaml
---
name: lab-run
description: Lance un cycle du laboratoire IA (Director + experts Neuro/Math → protocole pré-enregistré avec gate humaine → Builder implémente et exécute → Verifier adversarial avec boucle de correction → interprétation croisée → journal) sur une question de recherche, le mot-clé "suivant", ou un protocole approuvé.
disable-model-invocation: true
argument-hint: "<question de recherche | suivant | chemin d'un protocole approuvé> [--models \"role=modele;...\"]"
---
```

Le corps (rédigé intégralement, voix impérative, adapté au projet : citer les chemins réels du journal, de la feuille de route, de la commande de test, de l'interpréteur) définit ce déroulé pour la session principale :

0. **Affectation des modèles** : lire `.claude/lab-models.json` (absent → tous les rôles en `inherit`). Si `$ARGUMENTS` contient `--models "role=modele;..."`, appliquer ces paires **pour ce cycle uniquement**, sans réécrire le fichier ; rôles reconnus : `director.cadrage`, `director.interpretation`, `neuro`, `math`, `builder`, `verifier` ; valeurs reconnues : `inherit`, `opus`, `fable`, `sonnet`, `haiku` — toute valeur inconnue est refusée avec un message explicite plutôt que silencieusement ignorée. À chaque lancement d'un sous-agent, passer le paramètre `model` de l'outil Agent avec la valeur du rôle correspondant, **sauf si elle vaut `inherit`** (dans ce cas, ne pas passer le paramètre du tout). Annoncer en une ligne, avant la première dépense, l'affectation retenue (rôle → modèle) pour que l'utilisateur puisse interrompre s'il ne veut pas payer ce cycle-là au tarif annoncé.
1. **Entrée** : si `$ARGUMENTS` (privé de l'option `--models`) est le chemin d'un fichier existant sous `experiments/` dont la ligne de statut vaut `Statut : PRE-ENREGISTRE`, passer directement à l'étape 4. Sinon, traiter le reste de `$ARGUMENTS` comme une question de recherche (ou comme `suivant`).
2. **Phase Cadrage** : lancer le sous-agent `lab-director` en mode cadrage (modèle du rôle `director.cadrage`) avec la question ; à son retour, lancer **en parallèle** (même message, deux appels) `lab-neuro` et `lab-math` (modèles `neuro` et `math`) avec le brouillon de protocole complet et les questions qui leur sont adressées ; relancer `lab-director` (rôle `director.cadrage`) avec son brouillon et les deux avis pour qu'il produise le **protocole consolidé** (il intègre ou écarte chaque remarque en le disant, et met à jour les prédictions chiffrées avec les apports de Math et les prédictions qualitatives de Neuro).
3. **Gate humaine (pré-enregistrement)** : poser à l'utilisateur les *Questions pour le PI* du protocole consolidé (AskUserQuestion) ; intégrer les réponses ; écrire `experiments/EXP-<AAAA-MM-JJ>-<slug>.md` avec en tête `Statut : PROPOSE` ; présenter le protocole à l'utilisateur (question, hypothèse, prédictions chiffrées, critères d'abandon, budget) et demander son approbation explicite ; en cas d'approbation, passer le statut à `PRE-ENREGISTRE` et **ne plus jamais modifier les sections Prédictions et Critères d'abandon** ; sinon itérer. **Si aucune interaction n'est possible (exécution headless), s'arrêter en erreur explicite : un cycle headless exige le chemin d'un protocole déjà pré-enregistré.** Ne jamais mesurer sans protocole pré-enregistré.
4. **Phase Build & Run** : lancer le sous-agent `lab-builder` (contexte frais, modèle du rôle `builder`) avec le chemin du protocole pré-enregistré ; récupérer son compte rendu brut.
5. **Phase Verify — boucle de correction, 3 itérations maximum** :
   1. Lancer un sous-agent `lab-verifier` (contexte vierge, indépendant du Builder, modèle du rôle `verifier`) avec le chemin du protocole et le compte rendu brut ; récupérer son bloc JSON.
   2. Si `verdict` vaut `APPROVED` **et** `tests_passed`, `protocol_followed` et `rerun_consistent` valent `true` : sortir de la boucle.
   3. Sinon : relancer `lab-builder` avec le protocole **et la liste complète des `issues`** (fichier, sévérité, type, description) et la consigne de corriger sans régresser puis de ré-exécuter les runs affectés ; reprendre à l'étape 1 avec un nouveau Verifier.
   4. Tenir le compteur ; après la 3e itération non approuvée, **échouer explicitement** en publiant les issues restantes et en écrivant une entrée de journal de type « expérience invalidée — cause » (un protocole qu'on n'arrive pas à exécuter proprement est une information). Ne jamais approuver par épuisement.
6. **Phase Interprétation croisée** : lancer **en parallèle** `lab-neuro` et `lab-math` (modèles `neuro` et `math`) avec le protocole, le compte rendu brut vérifié et le JSON du Verifier (Math recalcule au moins un chiffre clé ; Neuro confronte les courbes à ce que la biologie prédisait) ; puis lancer `lab-director` en mode interprétation (modèle du rôle `director.interpretation`) avec l'ensemble ; récupérer le verdict (`RETENU` / `REJETE` / `INCONCLUSIF`), l'entrée de journal rédigée, la ligne de tableau proposée et la prochaine expérience suggérée.
7. **Gate humaine (consignation)** : présenter le verdict et l'entrée de journal à l'utilisateur ; sur approbation, **ajouter** l'entrée dans le journal détecté (en respectant son ordre — chronologique ou antéchronologique, tel que détecté — et son format exact ; créer `docs/JOURNAL.md` s'il n'existe pas), ajouter la ligne au tableau des résultats de la feuille de route si le projet en tient un, passer le statut du protocole à `TERMINE — <verdict>` ; ne toucher à aucun autre document (l'architecture et les notes figées ne sont jamais éditées par le labo ; si le Director recommande une décision de design à y consigner, la mentionner dans le rapport pour que l'utilisateur le fasse). En headless, écrire l'entrée de journal sans gate (le protocole pré-enregistré en était l'autorisation) mais la marquer `(consignée automatiquement — à relire)`.
8. **Rapport final** : question, verdict, chiffres clés vs prédictions pré-enregistrées, fichiers modifiés (`git status`), résultat des tests, nombre d'itérations Builder/Verifier, emplacement des résultats bruts, **affectation des modèles effectivement utilisée** (rôle → modèle, et si elle venait du fichier ou d'un `--models`), prochaine expérience suggérée avec la commande `/lab-run "<question>"` ou `/lab-run suivant` ; ne pas commiter à la place de l'utilisateur.

**Économie du modèle le plus cher.** Tout rôle affecté à un modèle autre qu'`inherit` est traité comme une ressource rare : ne jamais lui passer un document entier quand un extrait suffit — pour `neuro` et `math`, le protocole ou le compte rendu concernés plus les seules entrées de journal citées, jamais le journal complet ni les fichiers de résultats bruts (qui restent au Builder et au Verifier) ; ne jamais le relancer pour une reformulation cosmétique ; en cas de boucle de correction (étape 5), ne pas rejouer l'interprétation croisée à chaque itération — elle n'a lieu qu'une fois, après approbation du Verifier. L'entrée de journal rédigée à l'étape 7 mentionne en une ligne quel modèle a tenu quel rôle : c'est une condition de reproductibilité du jugement, au même titre que les seeds.

## Phase 4 — Scripts headless `ci/lab.sh` et `ci/lab.ps1`

Générer deux scripts complets et équivalents (bash avec `set -euo pipefail`, PowerShell avec `$ErrorActionPreference = 'Stop'`) qui :

- prennent en **argument obligatoire** le chemin d'un protocole pré-enregistré, et une **option `--yolo`** (`-Yolo` en PowerShell) ;
- vérifient que le fichier existe et contient `Statut : PRE-ENREGISTRE`, sinon échouent avec un message clair ;
- construisent l'appel : `claude -p "/lab-run '<chemin-protocole>'" --output-format json --max-turns 150`, complété par défaut de `--permission-mode acceptEdits --allowedTools "<liste blanche>"`, ou par `--dangerously-skip-permissions` si `--yolo` ;
- la **liste blanche** `--allowedTools` est construite depuis la Phase 1 : toujours `Read`, `Glob`, `Grep`, `Write`, `Edit`, `Bash(git *)`, plus l'interpréteur et les commandes réelles détectés (ex. `Bash(.venv/Scripts/python *)`, `Bash(python *)`, `Bash(pytest *)`, `Bash(ruff *)`) — uniquement ceux détectés ;
- écrivent la sortie dans `lab-logs/lab-<horodatage>.json` (créer le dossier ; horodatage `date +%Y%m%d-%H%M%S` en bash, `Get-Date -Format yyyyMMdd-HHmmss` en PowerShell) et **propagent l'exit code** de `claude`.

Ajouter `lab-logs/` et `experiments/results/` au `.gitignore` du projet (le créer ou compléter sans dupliquer les lignes). Les protocoles `experiments/EXP-*.md`, eux, sont versionnés : c'est la trace du pré-enregistrement.

## Phase 5 — Économie de tokens `.claude/settings.json`

Créer ou fusionner `.claude/settings.json` avec des règles `permissions.deny` en `Read(...)` (fusionner les tableaux sans doublon, préserver toute clé existante) couvrant : `Read(./.venv/**)`, `Read(./venv/**)`, `Read(./**/__pycache__/**)`, `Read(./.pytest_cache/**)`, `Read(./**/*.egg-info/**)` (Python) ; `Read(./lab-logs/**)`, `Read(./experiments/results/**)`, `Read(./.git/objects/**)` (générique) ; plus les dossiers de **données, poids et caches de modèles** détectés en Phase 1 (ex. `Read(./data/**)`, `Read(./checkpoints/**)`, `Read(./models/**)`, `Read(./**/*.safetensors)`, `Read(./**/*.pt)`, `Read(./**/*.bin)`, `Read(./**/.cache/**)`, `Read(./wandb/**)`, `Read(./runs/**)`) — uniquement ceux présents ou référencés dans le projet. Les résultats bruts sont exclus de la lecture par défaut parce que la session principale ne doit jamais les charger en entier : le Builder les résume et le Verifier les recalcule dans leurs propres contextes ; la session n'a besoin que des comptes rendus.

## Phase 6 — Tâches VS Code `.vscode/tasks.json`

Créer ou fusionner `.vscode/tasks.json` (version `2.0.0`) avec :

- une entrée `inputs` de type `promptString`, id `labProtocol`, décrivant « Chemin du protocole pré-enregistré (experiments/EXP-*.md) » ;
- une tâche **« Lab: run headless »** exécutant `./ci/lab.sh ${input:labProtocol}` avec la variante `windows` exécutant `pwsh -File ci/lab.ps1 ${input:labProtocol}` ;
- une tâche **« Lab: run headless (YOLO) »** identique avec l'option `--yolo` / `-Yolo` ;
- une tâche **« Lab: tests unitaires »** exécutant la commande de test réelle détectée (avec sa variante `windows` si l'interpréteur diffère) ;
- une tâche **« Lab: nouvelle expérience (session) »** de type shell qui affiche simplement le rappel : `Ouvrir Claude Code et taper : /lab-run "<votre question>"  ou  /lab-run suivant`.

En cas de fusion, préserver les tâches et inputs existants ; ne pas dupliquer si les tâches Lab existent déjà.

## Phase 6b — Base de connaissance du dépôt (optionnelle)

Un laboratoire accumule deux choses que le code ne dit pas : ce qui a déjà été mesuré, et pourquoi une piste a été abandonnée. Le journal les porte en prose ; le skill `code-index` installe un serveur local adossé à ripgrep qui les rend **interrogeables** — index de code versionné sous `.knowledge/`, plus des notes attachées à un fichier, à un symbole ou à un sujet libre, partagées par git avec les autres utilisateurs du dépôt. Un Director qui interroge les notes avant de cadrer ne repropose pas une expérience déjà faite.

Poser à l'utilisateur, en un appel `AskUserQuestion`, s'il veut l'installer maintenant. En cas d'accord, invoquer le skill `code-index` : il détecte le laboratoire qui vient d'être installé et branche seul les cinq agents et `/lab-run` dessus. En cas de refus, ne rien faire : le labo fonctionne entièrement sans, et `code-index` s'installe à tout moment sur un dépôt déjà équipé. **Ne jamais installer sans accord** : la base ajoute un dossier versionné au dépôt, ce qui se décide.

En exécution headless, ne pas poser la question et ne rien installer.

## Phase 7 — Rapport final

Terminer par un rapport structuré : projet détecté (stack, framework, interpréteur, matériel et disponibilité réelle du GPU, commande de test) ; corpus scientifique retenu (chemins du journal, de l'architecture, de la feuille de route, documents figés, évals existantes, classe de config, contraintes non négociables recopiées dans les prompts) ; domaine et références utilisés pour spécialiser Neuro et Math ; liste des fichiers avec leur état (créé / fusionné / identique / personnalisé-conservé) ; **affectation des modèles retenue** (tableau rôle → modèle, chemin `.claude/lab-models.json`, rappel qu'elle se modifie en éditant ce fichier ou ponctuellement avec `/lab-run "…" --models "math=opus"`, et qu'elle peut être versionnée ou ignorée par git selon la préférence) ; absence de journal ou d'outillage de test le cas échéant ; mode d'emploi en trois lignes (session : `/lab-run "question"` ou `/lab-run suivant` ; headless : `ci/lab.sh experiments/EXP-x.md`, qui suit le fichier d'affectation ; les protocoles sont versionnés, les résultats bruts non). Si `$ARGUMENTS` contenait une question, conclure par la commande exacte à lancer : `/lab-run "<la question>"`.
