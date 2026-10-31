---
name: vibecode-audit
description: Audite en lecture seule un projet vibecodé (généré par IA) et écrit un unique rapport AUDIT-vibecode.md — cartographie, cinq auditeurs parallèles guidés par une taxonomie des signatures propres au code généré (contrôle d'accès absent, injection, rendu non échappé, logique métier exploitable, réimplémentation entre sessions, adhérence au fournisseur), validation adversariale, findings agrégés en motifs à N occurrences, difficulté en ordre de grandeur et ordre d'attaque par gravité d'abord, puis pondération sécurité, maintenabilité, évolutivité. À utiliser quand l'utilisateur reprend un PoC généré par IA et veut savoir par où attaquer avant une mise en production ; prémâche le travail de /legacy-audit, qui vise au contraire la dette d'accumulation d'un code écrit par des humains.
context: fork
user-invocable: true
argument-hint: "[chemin du projet] [--axes \"securite;maintenabilite;evolutivite\"] [--max-findings N]"
---

# Vibecode audit — par où attaquer un projet généré par IA

Diagnostiquer un projet vibecodé sans le modifier, et répondre à une seule question : **par où attaquer**. Cartographier, lancer cinq auditeurs parallèles guidés par une taxonomie de signatures propres au code généré, contester chaque finding, agréger en motifs, estimer la difficulté, faire arbitrer l'ordre, puis écrire **un seul fichier** : `AUDIT-vibecode.md`.

Ce skill diagnostique, il ne remédie pas : il ne génère aucune spec, ne pose aucun garde-fou, ne modifie rien. Le passage à l'exécution appartient à `/legacy-audit` en aval, qui reprend le rapport pour en tirer une roadmap et des specs.

**Ce qui le distingue de `/legacy-audit`** : deux distributions de défauts. `/legacy-audit` vise la dette d'**accumulation** — code humain, dérive sur des années, turnover, patches successifs. Ce skill vise la dette de **génération** — chaque session régénère sans connaître la précédente, et le modèle produit le chemin nominal. Lancer les deux à la suite est le mode d'emploi normal, pas une redondance.

## Noyau déterministe

Les règles déterministes sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : ne jamais les réimplémenter, appeler la CLI `harness.py` et suivre sa sortie JSON. Règles propres : **VA-01** à **VA-13** (`hcore/audit.py` et son profil, `findings.py`, `tshirt.py`) ; partagées : **AU-01** à **AU-16**, **FD-01** à **FD-11**, **RG-01** à **RG-07**, **TS-01** à **TS-05**, **ST-01** à **ST-04**, **GT-01** à **GT-08**, **MD-01** à **MD-08** (`--models` : rôles `audit.auditor`, `audit.validator`), **JR-01**, **JR-02** (journal sous `.harness/runs/` du projet audité).

**Interpréteur** : `<PY>` = le premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9 : `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`. Toute sortie d'agent et tout JSON se transmettent au noyau par un fichier écrit avec l'outil Write sous `.harness/runs/` (jamais par le shell) ; le noyau le supprime après lecture.

## Règles impératives (toutes les phases)

- **Lecture seule absolue sur le projet audité.** Seule écriture autorisée (VA-03, le noyau refuse toute autre) : `AUDIT-vibecode.md` — avec le journal `.harness/runs/` et le registre projet. Ni spec, ni hook, ni fichier de configuration, ni correctif « en passant ». Jamais de `git init`, de commit ni d'installation de dépendance. Un défaut trouvé est un finding, pas une action.
- **Aucune adhérence à une pile technique.** La taxonomie décrit des **classes de défaut**. Ne jamais inscrire dans un prompt, dans le rapport ou dans une recommandation le nom d'un framework, d'une bibliothèque, d'un fournisseur ou d'un écosystème : la pile sert seulement à savoir *où regarder*. Un motif qui ne s'énonce qu'en nommant une techno est mal formulé — le reformuler en classe de défaut.
- **Le finding est un motif, pas une occurrence.** Les auditeurs émettent directement `{pattern, occurrences[], count}` ; le clustering n'est jamais une étape séparée. Un motif à 15 occurrences est **un** finding, chiffré.
- **« Zéro finding » est une réponse normale et acceptable.** Cette phrase figure telle quelle dans le prompt de chaque auditeur et de chaque validateur — jamais de finding inventé pour remplir un quota.
- **Ce qui ne peut pas être audité est un finding, jamais un silence.** Artefact de distribution absent, environnement d'exécution inaccessible, outil de détection indisponible, service tiers configuré hors du dépôt : une **surface non auditable** de sévérité au moins `major` (VA-06, refusée en dessous), dans le fichier de données du rapport. Une absence de donnée ne doit jamais se lire comme une absence de problème.
- **Chaînes interdites** : ne jamais écrire `Statut :` suivi de `APPROUVEE` ni de `PRE-ENREGISTRE` où que ce soit (le noyau le vérifie, FD-11).
- **Frugalité** : auditeurs `Explore` en lecture seule recevant la carte et leur famille **et rien d'autre à chercher** ; preuve = extrait ≤ 3 lignes avec fichier et ligne, ou constat structurel ; validateurs = mini-agents à prompt court.
- **L'ordre d'attaque appartient à l'utilisateur** (Phase 5). Sans interaction possible, écrire le rapport avec l'ordre par défaut et le signaler en tête (VA-11) — le diagnostic reste utile sans arbitrage.

## Phase 1 — Reconnaissance et cartographie

Dans la session principale, sans sous-agent. Objectif : savoir *où regarder*, pas auditer.

1. **Arguments, git, reprise** : écrire `$ARGUMENTS` tel quel dans `.harness/runs/vibecode-audit-arguments.txt`, puis `K audit start --skill vibecode-audit --arguments-file …` (AU-01 à AU-03, VA-01, VA-02 : `REPO` absolu ; `--axes` parmi `securite`, `maintenabilite`, `evolutivite` séparés par `;` ; `--max-findings` borné à `min(N, 30)` défaut 15 ; chemin inexistant → arrêt, valeur invalide → exit 2). **Retirer `securite` exige une confirmation** : gate `vibecode-audit.drop-security` (*confirmer le retrait* / *garder*), avant `start`. Le noyau sonde git (`git_absent` : pré-finding à reporter, **aucune commande git ensuite**), reprend un `AUDIT-vibecode.md` existant (AU-09 : statuts `FAIT`/`EN_COURS` préservés, numérotation `VIB-` poursuivie, sans jamais comparer les deux états) et rend `run`, `auditors` (modèle et `pass_param` : passer `model` à l'outil Agent quand `pass_param` est vrai, jamais pour `inherit`), `validator`, `cap`.
2. **Forme du projet** : `K stack detect --root "<REPO>"` ; arborescence 2-3 niveaux ; manifestes de dépendances et verrous, découpage client / serveur / asynchrone, schéma de données et migrations, tests, CI, configuration par environnement.
3. **Frontières de confiance** : localiser les points d'entrée exposés (routes, contrôleurs, fonctions déclenchées par requête, gestionnaires d'événements) et la couche d'accès aux données — la carte que reçoivent `acces`, `injection` et `metier`.
4. **Signaux de génération** (relevé, jamais reproché) : commits volumineux et peu nombreux, styles hétérogènes entre fichiers voisins, commentaires paraphrasant le code, fichiers d'instructions pour un assistant, trous dans une séquence numérotée. **Recherche systématique des candidats à la réimplémentation** : répertoires de même niveau aux noms proches (même racine, singulier/pluriel, suffixe ajouté) et fichiers de même nom dans des répertoires différents ; chaque paire entre dans la carte de `maintenabilite` avec consigne de la comparer. C'est le motif le plus caractéristique du vibecodé et le seul qu'aucun auditeur ne trouve fichier par fichier.
5. **Vérifications déterministes** : audit de vulnérabilités du gestionnaire de paquets et détecteur de secrets, s'ils existent, en lecture seule et sans installation ni mise à jour ; **outil absent → surface non auditable**. Trier les vulnérabilités **par atteignabilité en production** avant toute agrégation.
6. **Artefact de distribution** : si le projet produit un livrable client (paquet, bundle, image), vérifier ce qu'il contient ; indisponible sans construire le projet (ce que ce skill ne fait pas) → surface non auditable (les secrets exposés côté client ne se voient pas dans les sources).
7. **Bornes** : `sampled` rendu par `stack detect` au-delà de 2000 fichiers : arborescence de 3 niveaux, 40 fichiers lus par auditeur, échantillonnage sur les points d'entrée exposés, la couche d'accès aux données et les plus gros fichiers.

Produire la **carte** : forme, frontières de confiance, tests / CI / migrations / configuration, signaux de génération, vérifications déterministes, surfaces non auditables, `git_absent`, reprise, échantillonnage.

## Phase 2 — Audit parallèle par familles de signatures

Lancer **en un seul message** les auditeurs des familles retenues : trois couvrent l'axe `securite`, une par axe restant (VA-01).

- **(a) `acces`** (`ACC-`, sécurité) — **contrôle d'accès absent ou déporté chez le client** : accès à la ressource d'autrui en substituant un identifiant, sans vérification d'appartenance côté serveur ; pas de notion de rôle, ou rôle déclaré par le client et cru sur parole ; points d'administration non protégés ; affectation en masse laissant le client écrire des champs privilégiés ; contrôle présent dans l'interface seule. Cause commune : *la génération écrit le chemin nominal, et l'autorisation n'est jamais dans la demande*.
- **(b) `injection`** (`INJ-`, sécurité) — **entrée non fiable traitée comme du code, sorties non échappées** : requêtes ou commandes par concaténation ; traversée de chemin ; injection de gabarit ; désérialisation d'entrée non fiable ; contenu utilisateur inséré sans échappement, y compris différé via un champ persisté ; requêtes forgées quand la session est portée par le navigateur ; validation jamais rejouée côté serveur ; points de débogage ou d'amorçage restés actifs ; erreurs révélant l'implémentation. Motif typique : *l'abstraction sûre est utilisée partout sauf sur la requête compliquée*.
- **(c) `metier`** (`MET-`, sécurité) — **invariants du domaine jamais imposés** : ressource finie attribuable deux fois (unicité, transaction, verrou absents) ou dépassée par requêtes concurrentes ; montants, quantités, remises, propriétaire fournis par le client et acceptés tels quels ; transitions d'état sans vérification de l'état de départ ; aucun frein à l'authentification ni aux opérations coûteuses, énumération possible ; données personnelles collectées au-delà du nécessaire, secrets d'authentification sans dérivation robuste, données personnelles dans les journaux, ni durée de conservation ni suppression ; aucune trace exploitable après incident. **Famille la plus rentable et la moins couverte par l'outillage** : elle exige de reconstituer des règles écrites nulle part.
- **(d) `maintenabilite`** (`MNT-`) — **incohérences entre sessions de génération**, d'abord le travail **transversal, invisible fichier par fichier** : la même fonction écrite plusieurs fois sous des noms différents ; les mêmes règles métier dans l'interface et côté serveur avec des divergences silencieuses ; la même entité décrite différemment de part et d'autre du réseau. Puis : contrats si larges qu'ils ne contraignent rien ; pistes abandonnées ; tests absents ou dont les assertions portent sur les doublures ; erreurs capturées sans traitement ; style discontinu ; commentaires qui paraphrasent le code.
- **(e) `evolutivite`** (`EVO-`) — **choix qui bloquent la suite** : structure de données modifiée sans migration rejouable ni annulable ; service tiers appelé partout sans frontière d'abstraction ; interrogation en boucle, lecture non paginée, index absents ; adresses, identifiants, seuils en dur au lieu d'être externalisés ; traitements longs ou faillibles dans le cycle de requête ; code supposant un utilisateur à la fois là où le domaine garantit le contraire.

Chaque prompt contient : la carte (frontières de confiance comprises), **sa famille et rien d'autre**, le budget de lecture, la phrase « **zéro finding est une réponse normale et acceptable** », l'interdiction d'écrire ou d'exécuter, l'interdiction de nommer une pile, la preuve vérifiable, le barème de difficulté — **un ordre de grandeur, pas une estimation** : XS < 30 min, S < 2 h, M demi-journée, L 1-2 jours, XL à découper ; en cas d'hésitation, la plus grande — et un unique bloc JSON final (VA-04) :

```json
{"findings": [{"id": "ACC-01", "axis": "securite|maintenabilite|evolutivite",
  "pattern": "énoncé du motif en une phrase, sans nom de techno", "severity": "critical|major|minor",
  "occurrences": [{"file": "chemin/relatif", "line": 42, "evidence": "extrait ≤ 3 lignes"}],
  "count": 12, "sampled": true, "impact": "ce qu'un attaquant ou un mainteneur peut en faire, concrètement",
  "remediation": "correction du motif en une phrase — la classe, pas une occurrence",
  "difficulty": "XS|S|M|L|XL", "regression_risk": "faible|moyen|eleve",
  "risk_rationale": "ce qui fonde ce niveau : couverture de tests, nombre d'appelants, portée", "depends_on": []}]}
```

`occurrences` : jusqu'à 5 exemples représentatifs, `count` le total réel, `sampled: true` au-delà (le noyau normalise). `critical` est réservé à ce qui est exploitable à distance sans authentification, expose ou détruit des données d'autrui, ou viole un invariant du domaine avec conséquence métier directe. `difficulty` estime le motif entier. `regression_risk` est **informatif** : il n'entre dans aucun tri, et `risk_rationale` le fonde sur des faits observés dans ce projet — sur un projet sans tests, répondre `eleve` partout n'apprend rien : graduer relativement aux autres motifs.

Chaque retour : `K audit auditor --run <run> --unit <famille> --output <fichier> [--dead] --duration-ms <ms> --tokens <n>`. **Une famille muette n'est jamais une famille saine** : `relaunch` (une fois), puis `surface` (VA-05 : surface non auditable `major`, `bruts = échec`, annoncée en tête du rapport). `validate` rend `to_validate`, `duplicates` (écartés sans validateur) et `merge` (VA-07 : doublon entre deux auditeurs, **jamais écarté au hasard** — fusionner en un motif à la formulation la plus précise, l'union des occurrences et la sévérité la plus haute ; comptage et difficulté ne sont pas arbitrés ici : transmettre au validateur les deux estimations, exiger qu'il tranche avec des chiffres vérifiés à la source — `corrected_count` — et l'inviter à scinder si l'écart signale un motif trop grossier).

## Phase 3 — Validation adversariale

Un **mini-agent validateur** (effort faible, prompt court) conteste chaque motif de `to_validate` : les occurrences existent-elles à ces endroits ? le contrôle manquant est-il assuré ailleurs (couche intermédiaire, contrainte en base, configuration du service, intergiciel global) — **piège principal**, un contrôle centralisé invisible dans le fichier lu produit un faux positif massif ? vrai défaut ou **choix délibéré et documenté** (chercher la documentation) ? bon axe ? sévérité et difficulté plausibles ? Deux consignes impératives : **la charge de la preuve est sur le motif** (impossibilité de trancher → `REJECTED`) et **contester, pas confirmer par politesse**. Ne jamais suggérer la conclusion attendue : une hypothèse de lien entre deux motifs se pose en question ouverte. Il peut **scinder** un motif trop grossier (VA-08) :

```json
{"verdict": "CONFIRMED|REJECTED|SPLIT", "reason": "justification en une phrase",
 "severity_correction": "critical|major|minor|null", "axis_correction": "securite|maintenabilite|evolutivite|null",
 "difficulty_correction": "XS|S|M|L|XL|null", "corrected_count": 0, "false_occurrences": ["chemin:ligne"],
 "split_into": [{"pattern": "énoncé", "occurrences": ["chemin:ligne"], "severity": "…", "difficulty": "…"}]}
```

`axis_correction` n'est pas cosmétique : un motif sur le mauvais axe est trié après tout l'axe prioritaire (le classement initial suit la lentille, pas la nature). `K audit validator --run <run> --finding <id> --output <fichier> [--dead]` applique reclassements et scissions, retire les `false_occurrences` et recalcule `count`. **Validation partielle assumée** (VA-09) : si la validation intégrale est disproportionnée, `K audit next` ordonne les motifs en attente (`critical` d'abord, puis par nombre d'occurrences) ; valider dans cet ordre ; les autres partent **marqués `non validé`** (ils n'ont pas été réfutés, ils n'ont pas été vérifiés) et le nombre validé sur le total figure dans l'encadré de limites. Un validateur mort deux fois laisse son motif `non validé`, jamais `CONFIRMED`. **Zéro CONFIRMED** : `next` rend `deliverable` → Phase 6, rapport « aucun motif confirmé sur les axes audités » qui conserve les surfaces non auditables.

## Phase 4 — Consolidation

`K audit consolidate --run <run>` renumérote en `VIB-nn` (VA-10) : **la sévérité prime sur l'axe**, puis l'axe (sécurité, maintenabilité, évolutivité), puis la difficulté croissante ; le risque de régression n'intervient dans aucun tri. **Un `critical` n'est jamais relégué derrière un axe** : tous les `critical` en tête, tous axes confondus, avant le premier `major` (un nom de ressource erroné qui empêche un composant de démarrer, une valeur de configuration qui est aussi un secret, une absence de transaction qui est aussi un contournement d'autorisation). Le noyau rend `raised_criticals` (remontée délibérée, à signaler) et `quick_wins` (XS ou S de sévérité `major` ou `critical`, signalés sans remonter dans l'ordre : un gain rapide reste second par rapport à un motif critique difficile). Compléter les **dépendances** évidentes (une correction qui traverse une couche absente dépend de sa création ; un motif de configuration dépend de l'externalisation de la configuration).

## Phase 5 — Ordre d'attaque (gate humaine)

Volontairement légère. **Un seul appel**, deux questions (`vibecode-audit.order`, via `K gate decide` / `answer`) : « Ordre d'attaque ? » — *Gravité d'abord* (défaut) / *Gains rapides* / *Tout ce qui bloque* / *Garder l'ordre* ; « Motifs mineurs ? » — *Les détailler* / *Les lister en une ligne* / *Les omettre*. Jamais de question sur le risque de régression, jamais les motifs un par un. Écrire les choix dans `.harness/runs/vibecode-audit-data.json` (`name`, `date`, `axes`, `path`, `headless`, `order` et `order_label` si l'ordre diffère du défaut, `surfaces` `[{surface, why, needs}]`, `findings` `{VIB-nn: {detail, reason: "minor"|"cap", omit}}`), puis `K audit plan --run <run> --data-file …` rend les motifs détaillés sous le plafond `--max-findings` (l'excédent : `short_cap`), `quick_wins`, `raised_criticals` et la charge. Récapitulatif en texte, puis `vibecode-audit.final` : **Écrire AUDIT-vibecode.md** / **Réajuster** (une fois, `K audit readjust --run <run>`) / **Abandonner**. Headless (VA-11) : `--headless` applique les défauts (*Gravité d'abord*, *Les détailler*) et `headless: true` les signale en tête du rapport.

## Phase 6 — Génération du rapport (seule phase qui écrit)

`K audit render --run <run> --data-file …` écrit `AUDIT-vibecode.md` (VA-12) depuis le gabarit du noyau, **et rien d'autre** : encadré de limites (validés sur total), surfaces non auditables, « Par où attaquer » (tableau ordonné, gains rapides, critiques remontés), motifs détaillés, non détaillés, rejetés, suite vers `/legacy-audit`. Statuts `A_FAIRE` / `EN_COURS` / `FAIT` / `REPORTE`. Reprise : lignes et statuts existants conservés, « rapport repris » au rapport, sans comparaison ni évolution — ce skill n'a pas de mémoire entre exécutions. Puis `K audit publish --run <run> --deliverable`.

## Phase 7 — Rapport final

- **Carte** : projet, forme, taille, git présent/absent, complet ou échantillonné, rapport créé ou repris, signaux de génération ;
- **Motifs** (VA-13) : `| Famille | Bruts | Confirmés | Scindés | Rejetés/dédupliqués | Occurrences confirmées |` depuis `counters` ;
- **Surfaces non auditables** avec ce qu'il faudrait pour les couvrir ; **Par où attaquer** : les trois premiers motifs et leur difficulté ;
- **Fichier écrit** : `AUDIT-vibecode.md` — et le rappel qu'aucun autre fichier n'a été touché ;
- **Prochaine action** : `/legacy-audit "<chemin>"` pour en tirer roadmap et specs ;
- **Limites** : les familles sans finding ne sont pas des familles sans défaut, et la logique métier reste la surface la moins couverte par tout outillage automatique.
