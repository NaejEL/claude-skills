---
name: vibecode-audit
description: Audite en lecture seule un projet vibecodé (généré par IA) et écrit un unique rapport AUDIT-vibecode.md — cartographie, cinq auditeurs parallèles guidés par une taxonomie des signatures propres au code généré (contrôle d'accès absent, injection, rendu non échappé, logique métier exploitable, réimplémentation entre sessions, adhérence au fournisseur), validation adversariale, findings agrégés en motifs à N occurrences, difficulté en ordre de grandeur et ordre d'attaque par gravité d'abord, puis pondération sécurité, maintenabilité, évolutivité. À utiliser quand l'utilisateur reprend un PoC généré par IA et veut savoir par où attaquer avant une mise en production ; prémâche le travail de /legacy-audit, qui vise au contraire la dette d'accumulation d'un code écrit par des humains.
context: fork
user-invocable: true
argument-hint: "[chemin du projet] [--axes \"securite;maintenabilite;evolutivite\"] [--max-findings N]"
---

# Vibecode audit — par où attaquer un projet généré par IA

Diagnostiquer un projet vibecodé sans le modifier, et répondre à une seule question : **par où attaquer**. Cartographier, lancer cinq auditeurs parallèles guidés par une taxonomie de signatures propres au code généré, contester chaque finding, agréger en motifs, estimer la difficulté, faire arbitrer l'ordre, puis écrire **un seul fichier** : `AUDIT-vibecode.md`.

Ce skill diagnostique, il ne remédie pas. Il ne génère aucune spec, ne pose aucun garde-fou, ne modifie rien. Le passage à l'exécution appartient à `/legacy-audit` en aval, qui reprend le rapport pour en tirer une roadmap et des specs.

**Ce qui le distingue de `/legacy-audit`** : deux distributions de défauts différentes. `/legacy-audit` vise la dette d'**accumulation** — code écrit par des humains, dérive sur des années, turnover, patches successifs, frameworks vieillis. Ce skill vise la dette de **génération** — chaque session régénère sans connaître ce que la précédente a écrit, et le modèle produit le chemin nominal. Lancer les deux à la suite est le mode d'emploi normal, pas une redondance.

Parser `$ARGUMENTS` :

- **1er token** (s'il ne commence pas par `--`) = chemin du projet ; défaut : répertoire courant. S'il n'existe pas → arrêt : « le chemin <chemin> n'existe pas ». Mémoriser `REPO` (chemin absolu, quoté si espaces).
- **`--axes "a;b"`** : restreint l'audit aux axes listés (`securite`, `maintenabilite`, `evolutivite`, séparateur `;`). Défaut : les trois. Retirer `securite` exige une confirmation explicite de l'utilisateur : c'est l'axe prioritaire du skill.
- **`--max-findings N`** : plafond de motifs détaillés dans le rapport, borné dur à `min(N, 30)`. Défaut : 15. On borne le livrable, jamais la détection : les motifs confirmés au-delà du plafond figurent dans le rapport en liste courte (section « non détaillés dans ce cycle »).

## Règles impératives (toutes les phases)

- **Lecture seule absolue sur le projet audité.** Seule écriture autorisée, en Phase 6 : `AUDIT-vibecode.md`. Rien d'autre — ni spec, ni hook, ni fichier de configuration, ni correctif « en passant ». Jamais de `git init`, jamais de commit, jamais d'installation de dépendance. Un défaut trouvé est un finding, pas une action.
- **Aucune adhérence à une pile technique.** La taxonomie ci-dessous décrit des **classes de défaut**. Ne jamais inscrire dans un prompt d'auditeur, dans le rapport ou dans une recommandation le nom d'un framework, d'une bibliothèque, d'un fournisseur ou d'un écosystème : la pile est découverte en Phase 1 et sert seulement à savoir *où regarder*. Un motif qui ne peut s'énoncer qu'en nommant une techno est mal formulé — le reformuler en classe de défaut.
- **Le finding est un motif, pas une occurrence.** Le code généré duplique le même défaut à travers le projet. Les auditeurs émettent directement `{pattern, occurrences[], count}` ; le clustering n'est jamais une étape séparée. Un motif à 15 occurrences est **un** finding, chiffré, pas quinze.
- **« Zéro finding » est une réponse normale et acceptable.** Cette phrase figure telle quelle dans le prompt de chaque auditeur et de chaque validateur — jamais de finding inventé pour remplir un quota.
- **Ce qui ne peut pas être audité est un finding, jamais un silence.** Artefact de distribution absent, environnement d'exécution inaccessible, outil de détection indisponible, service tiers dont la configuration vit hors du dépôt : émettre un finding `surface non auditable` de sévérité au moins `major`. Ne jamais laisser une absence de donnée se lire comme une absence de problème.
- **Chaînes interdites** : ne jamais écrire `Statut :` suivi de `APPROUVEE` ni de `PRE-ENREGISTRE` où que ce soit — les CI de la factory et du labo les greppent n'importe où dans un fichier.
- **Frugalité** : auditeurs = agents lecture seule recevant la carte et leur famille **et rien d'autre à chercher** ; preuve = extrait ≤ 3 lignes avec fichier et ligne, ou constat structurel ; validateurs = mini-agents à prompt court et effort faible.
- **Registre cumulatif des findings** : tenir `{id, motif, axe, occurrences, verdict}` pour tous les findings, **y compris les REJECTED**, alimenté aussi par un `AUDIT-vibecode.md` préexistant : un motif rejeté ou déjà traité ne ressuscite pas.
- **L'ordre d'attaque appartient à l'utilisateur** (AskUserQuestion en Phase 5). Si aucune interaction n'est possible (exécution headless), écrire le rapport avec l'ordre par défaut et le signaler explicitement en tête — le diagnostic reste utile sans arbitrage.

## Phase 1 — Reconnaissance et cartographie

Dans la session principale, sans sous-agent. Objectif : savoir *où regarder*, pas auditer.

1. **Git** : `git -C "<REPO>" rev-parse --git-dir`. Si échec → `GIT_ABSENT=true`, pré-finding, et aucune commande git ensuite.
2. **Forme du projet** : arborescence sur 2-3 niveaux ; manifestes de dépendances et fichiers de verrouillage présents à la racine et dans les sous-projets, quel que soit l'écosystème ; découpage client / serveur / traitement asynchrone ; présence d'un schéma de données et d'un dossier de migrations ; présence de tests, de CI, de configuration par environnement.
3. **Frontières de confiance** : localiser les points d'entrée exposés (routes, contrôleurs, fonctions déclenchées par requête, gestionnaires d'événements) et la couche d'accès aux données. C'est la carte que reçoivent les auditeurs `acces`, `injection` et `metier` — sans elle, ils lisent au hasard.
4. **Signaux de génération** : indices que le projet a été produit par sessions successives — commits volumineux et peu nombreux, styles hétérogènes entre fichiers voisins, commentaires paraphrasant le code, fichiers d'instructions destinés à un assistant, trous dans une séquence numérotée. Relevé pour le rapport, jamais reproché en tant que tel.
   **Recherche systématique des candidats à la réimplémentation** : lister les répertoires de même niveau dont les noms sont proches (même racine, singulier/pluriel, suffixe ajouté), et les fichiers portant le même nom dans des répertoires différents. Chaque paire trouvée entre telle quelle dans la carte remise à l'auditeur `maintenabilite`, avec consigne de la comparer. La réimplémentation entre sessions est le motif le plus caractéristique du vibecodé et le seul qu'aucun auditeur ne trouve en lisant les fichiers un par un : la Phase 1 doit lui fournir ses pistes, jamais le laisser les deviner.
5. **Vérifications déterministes** : si le gestionnaire de paquets détecté fournit un audit de vulnérabilités, l'exécuter en lecture seule et sans installation ni mise à jour ; de même pour un détecteur de secrets s'il est disponible. **Outil absent → finding `surface non auditable`**, jamais un silence. Trier les vulnérabilités remontées **par atteignabilité en production** avant toute agrégation : une vulnérabilité d'outillage de développement ne doit pas enterrer la seule joignable depuis une requête utilisateur.
6. **Artefact de distribution** : si le projet produit un livrable destiné au client (paquet, bundle, image), vérifier ce qu'il contient réellement. S'il n'est pas disponible et ne peut pas être obtenu sans construire le projet — ce que ce skill ne fait pas — c'est un finding `surface non auditable` : les secrets exposés côté client ne se voient pas dans les sources.
7. **Reprise** : si `<REPO>/AUDIT-vibecode.md` existe, charger ses motifs (détaillés, non détaillés, rejetés) dans le registre cumulatif.
8. **Bornes** : compter les fichiers hors dossiers d'artefacts et de dépendances installées. Si > 2000 : arborescence limitée à 3 niveaux, budget de 40 fichiers lus par auditeur, échantillonnage prioritaire sur les points d'entrée exposés, la couche d'accès aux données et les plus gros fichiers ; marquer l'audit « échantillonné » pour le rapport.

Produire la **carte** : forme du projet, frontières de confiance localisées, présence/absence de tests, CI, migrations, configuration par environnement, signaux de génération, résultats des vérifications déterministes, surfaces non auditables, `GIT_ABSENT`, reprise, échantillonnage.

## Phase 2 — Audit parallèle par familles de signatures

Lancer **en un seul message** les auditeurs (type `Explore`, lecture seule) des familles retenues par `--axes`. Trois familles couvrent l'axe `securite`, une par axe restant.

- **(a) `acces`** (ids `ACC-`, axe sécurité) — **contrôle d'accès absent ou déporté chez le client**. Accès à la ressource d'autrui en substituant un identifiant, sans vérification d'appartenance côté serveur. Absence de notion de rôle, ou rôle déclaré par le client et cru sur parole. Points d'entrée d'administration ou de gestion non protégés. Affectation en masse laissant le client écrire des champs privilégiés. Contrôle présent uniquement dans l'interface — la vue masque l'action, le point d'entrée reste nu. Cause commune à énoncer dans le prompt : *la génération écrit le chemin nominal, et l'autorisation n'est jamais dans la demande*.
- **(b) `injection`** (ids `INJ-`, axe sécurité) — **entrée non fiable traitée comme du code, et sorties non échappées**. Construction de requêtes ou de commandes par concaténation ; traversée de chemin sur les fichiers ; injection de gabarit ; désérialisation d'entrée non fiable. Insertion de contenu contrôlé par l'utilisateur dans le rendu sans échappement, y compris différée via un champ persisté. Absence de protection contre les requêtes forgées quand la session est portée automatiquement par le navigateur. Validation cantonnée à la saisie et jamais rejouée côté serveur. Points d'entrée de débogage ou d'amorçage restés actifs ; erreurs renvoyées au client révélant l'implémentation. Motif typique à chercher explicitement : *l'abstraction sûre est utilisée partout sauf sur la requête compliquée*.
- **(c) `metier`** (ids `MET-`, axe sécurité) — **invariants du domaine jamais imposés**. Ressource à capacité finie attribuable deux fois faute de contrainte d'unicité, de transaction ou de verrouillage. Capacité dépassée par requêtes concurrentes. Montants, quantités, remises ou identifiants de propriétaire fournis par le client et acceptés tels quels. Transitions d'état franchies sans vérification de l'état de départ. Absence de frein sur l'authentification et les opérations coûteuses ; énumération de comptes ou de ressources possible. Données personnelles collectées au-delà du nécessaire, secrets d'authentification stockés sans dérivation robuste, données personnelles présentes dans les journaux, aucune durée de conservation ni voie de suppression. Aucune trace exploitable après incident. **Famille la plus rentable et la moins couverte par l'outillage automatique** : elle exige de reconstituer les règles du domaine à partir du code, puisqu'elles ne sont écrites nulle part.
- **(d) `maintenabilite`** (ids `MNT-`) — **incohérences entre sessions de génération**. En priorité, et c'est un travail **transversal, invisible fichier par fichier** : la même fonction écrite plusieurs fois sous des noms différents ; les mêmes règles métier présentes à la fois dans l'interface et côté serveur, avec des divergences silencieuses ; la même entité décrite différemment de part et d'autre de la frontière réseau. Puis : contrats si larges qu'ils ne contraignent plus rien ; pistes abandonnées jamais retirées ; tests absents, ou dont les assertions portent sur les doublures et ne vérifient aucun comportement ; erreurs capturées sans traitement ni propagation ; style et structure discontinus d'un fichier à l'autre ; commentaires qui paraphrasent le code sans jamais dire pourquoi.
- **(e) `evolutivite`** (ids `EVO-`) — **choix qui bloquent la suite**. Structure de données modifiée sans historique de migration, impossible à rejouer ailleurs ni à annuler. Appels à un service tiers disséminés dans le code applicatif sans frontière d'abstraction. Interrogation des données dans une boucle ; lecture non paginée de collections destinées à croître ; absence d'index sur les critères de filtrage. Adresses, identifiants et seuils inscrits dans le code au lieu d'être externalisés par environnement. Traitements longs ou faillibles exécutés dans le cycle de requête, sans travail différé. Code supposant un utilisateur à la fois là où le domaine garantit le contraire.

Chaque prompt d'auditeur contient : la carte de la Phase 1 (frontières de confiance comprises), **sa famille et rien d'autre à chercher**, le budget de lecture, la phrase « **zéro finding est une réponse normale et acceptable** », l'interdiction absolue d'écrire ou d'exécuter quoi que ce soit, l'interdiction de nommer une pile technique dans ses findings, l'exigence de preuve vérifiable, le barème de difficulté — **un ordre de grandeur, pas une estimation** : XS < 30 min, S < 2 h, M demi-journée, L 1-2 jours, XL à découper ; en cas d'hésitation entre deux tailles, retenir la plus grande — et le format de sortie exigé — un unique bloc JSON final :

```json
{"findings": [{"id": "ACC-01", "axis": "securite|maintenabilite|evolutivite",
  "pattern": "énoncé du motif en une phrase, sans nom de techno",
  "severity": "critical|major|minor",
  "occurrences": [{"file": "chemin/relatif", "line": 42, "evidence": "extrait ≤ 3 lignes"}],
  "count": 12, "sampled": true,
  "impact": "ce qu'un attaquant ou un mainteneur peut en faire, concrètement",
  "remediation": "correction du motif en une phrase — la classe, pas une occurrence",
  "difficulty": "XS|S|M|L|XL", "regression_risk": "faible|moyen|eleve",
  "risk_rationale": "ce qui fonde ce niveau : couverture de tests, nombre d'appelants, portée",
  "depends_on": []}]}
```

Règles de remplissage à inscrire dans le prompt : `occurrences` contient jusqu'à 5 exemples représentatifs et `count` le total réel — au-delà, `sampled: true`. `severity: critical` est réservé à ce qui est exploitable à distance sans authentification, à ce qui expose ou détruit des données d'autrui, et à ce qui viole un invariant du domaine avec conséquence métier directe. `difficulty` estime l'effort pour corriger **le motif entier**, pas une occurrence. `regression_risk` est **informatif** : il ne participe à aucun tri, et `risk_rationale` doit le fonder sur des faits observés dans ce projet — sur un projet sans tests, répondre `eleve` partout n'apprend rien et doit être évité au profit d'une gradation relative aux autres motifs du même projet.

## Phase 3 — Validation adversariale

1. **Dédupliquer** chaque motif contre le registre cumulatif (même énoncé ou même ensemble d'occurrences), verdicts REJECTED et rapport préexistant compris.
   **Doublon entre deux auditeurs — ne jamais écarter au hasard.** Deux lentilles trouvent régulièrement le même motif avec des comptages, des difficultés et des risques divergents, chacune l'ayant vu depuis son angle. Fusionner en un seul motif dont l'énoncé retient la formulation la plus précise, l'union des occurrences, et **la sévérité la plus haute**. Le comptage et la difficulté ne sont pas arbitrés ici : le désaccord est transmis tel quel au validateur, dont le prompt cite les deux estimations et exige qu'il tranche avec des chiffres vérifiés à la source (champ `corrected_count`). Un désaccord d'ampleur entre deux auditeurs est le signal que le motif est peut-être trop grossier — le validateur doit être invité à le scinder.
2. Pour chaque motif survivant, lancer un **mini-agent validateur** (effort faible, prompt court) chargé de le contester : les occurrences citées existent-elles réellement à ces endroits ? le contrôle manquant n'est-il pas assuré ailleurs (couche intermédiaire, contrainte en base, configuration du service, intergiciel appliqué globalement) — piège principal de cette phase, car un contrôle centralisé invisible dans le fichier lu produit un faux positif massif ? est-ce un vrai défaut ou un **choix délibéré et documenté** (chercher la documentation avant de conclure) ? le motif est-il rangé sur le bon axe ? la sévérité et la difficulté sont-elles plausibles ?
   Le prompt du validateur porte deux consignes impératives : **la charge de la preuve est sur le motif** — en cas d'impossibilité de trancher, répondre `REJECTED` ; et **contester, pas confirmer par politesse**. Ne jamais suggérer au validateur la conclusion attendue : une hypothèse de lien entre deux motifs se pose en question ouverte, et sa réfutation est un résultat utile à consigner.
3. **Pouvoir de scission** : le validateur peut déclarer le motif trop grossier et le scinder, quand des occurrences réunies sous un même énoncé ne relèvent pas du même défaut ni de la même correction. Sortie exigée :

```json
{"verdict": "CONFIRMED|REJECTED|SPLIT", "reason": "justification en une phrase",
 "severity_correction": "critical|major|minor|null", "axis_correction": "securite|maintenabilite|evolutivite|null",
 "difficulty_correction": "XS|S|M|L|XL|null", "corrected_count": 0,
 "false_occurrences": ["chemin:ligne"],
 "split_into": [{"pattern": "énoncé", "occurrences": ["chemin:ligne"], "severity": "…", "difficulty": "…"}]}
```

`axis_correction` n'est pas cosmétique : un motif rangé sur le mauvais axe est trié après tout l'axe prioritaire. Une valeur de configuration qui est aussi un secret de signature, une dépendance vulnérable qui est aussi une porte d'entrée, une absence de transaction qui est aussi un contournement d'autorisation — le classement initial suit la lentille qui a trouvé le motif, pas sa nature. Le validateur reclasse ; la Phase 4 applique.

4. Ajouter chaque motif au registre avec son verdict ; appliquer les reclassements d'axe, retirer les `false_occurrences` et recalculer `count`. **Si zéro CONFIRMED → sauter en Phase 6** avec un rapport « aucun motif confirmé sur les axes audités » (réponse normale), qui conserve les surfaces non auditables.
5. **Validation partielle assumée.** Si le nombre de motifs rend la validation intégrale disproportionnée, valider en priorité les `critical`, puis les motifs dont l'énoncé est le plus falsifiable, puis ceux qui portent le plus d'occurrences. Les motifs non validés **partent au rapport marqués `non validé`**, jamais silencieusement mêlés aux autres : ils n'ont pas été réfutés, ils n'ont pas été vérifiés. Le nombre validé sur le total figure dans l'encadré de limites.

## Phase 4 — Consolidation

Dans la session principale, sans sous-agent :

- Appliquer les corrections et scissions des validateurs. Renuméroter en `VIB-01…` avec l'ordre par défaut : **la sévérité prime sur l'axe**, puis l'axe (sécurité, puis maintenabilité, puis évolutivité), puis la difficulté croissante. Le risque de régression n'intervient dans aucun tri.
  **Un `critical` n'est jamais relégué derrière un axe.** La pondération des axes ordonne ce qui est comparable ; elle ne doit pas enterrer un défaut grave parce que la lentille qui l'a trouvé n'était pas prioritaire. Un nom de ressource erroné qui empêche un composant de démarrer, une valeur de configuration qui est aussi un secret, une absence de transaction qui est aussi un contournement d'autorisation : ces motifs arrivent par les axes maintenabilité ou évolutivité et valent pourtant d'être traités en premier. Concrètement, **tous les `critical` sont ordonnés ensemble en tête, tous axes confondus**, avant le premier `major`. Signaler dans le rapport ceux dont l'axe n'est pas la sécurité — leur remontée est délibérée, pas une erreur de classement.
- Compléter les **dépendances** évidentes : un motif dont la correction traverse une couche absente dépend de la création de cette couche ; un motif de configuration dépend de l'externalisation de la configuration.
- Repérer les **gains rapides** : motifs `XS` ou `S` de sévérité `major` ou `critical`. Ils sont signalés comme tels dans le rapport, sans remonter dans le tri : un gain rapide reste second par rapport à un motif critique difficile, que l'ordre d'attaque ne doit jamais enterrer.
- Regrouper les motifs par axe pour la phase interactive.

## Phase 5 — Ordre d'attaque (gate humaine)

Volontairement légère — la rapidité du diagnostic est le critère premier du skill. **Un seul appel AskUserQuestion**, deux questions :

1. « Ordre d'attaque ? » — *Gravité d'abord, tous axes confondus, puis pondération sécurité > maintenabilité > évolutivité (défaut)* / *Gains rapides d'abord, à sévérité égale* / *Tout ce qui bloque la mise en production d'abord* / *Garder l'ordre proposé*.
2. « Que faire des motifs mineurs ? » — *Les détailler* / *Les lister en une ligne* / *Les omettre du rapport*.

Ne jamais poser de question sur le risque de régression : il informe, il ne trie pas. Ne jamais présenter les motifs un par un.

Présenter ensuite le récapitulatif en texte (axes, nombre de motifs, occurrences totales, répartition des difficultés, gains rapides), puis une dernière question : **Écrire AUDIT-vibecode.md** / **Réajuster** (une seule fois) / **Abandonner** (Phase 7 sans rien écrire).

## Phase 6 — Génération du rapport (seule phase qui écrit)

Écrire `<REPO>/AUDIT-vibecode.md`, et **rien d'autre**. Liens en chemins relatifs avec `/`. Statuts autorisés : `A_FAIRE` / `EN_COURS` / `FAIT` / `REPORTE`. Squelette :

```markdown
# Audit vibecode — <nom du projet>

Généré par /vibecode-audit le <date>. Axes : <liste>. Audit complet | échantillonné.

> **Portée et limites de cet audit.** Diagnostic statique en lecture seule, produit par un modèle de
> langage. Il ne remplace pas une revue de sécurité applicative : aucun accès à l'environnement
> d'exécution, aux identifiants, à la configuration réelle des services tiers ni au trafic ; aucun
> test d'intrusion. L'auditeur partage une partie des angles morts du modèle qui a produit le code —
> l'absence de finding sur une famille ne prouve rien. Les surfaces listées ci-dessous n'ont pas pu
> être auditées du tout.
>
> **Validation.** <n> motifs sur <total> ont passé la validation adversariale. Les autres sont
> marqués `non validé` : ils n'ont pas été réfutés, ils n'ont pas été vérifiés.
>
> **Les difficultés sont des ordres de grandeur, pas des estimations.** Elles varient d'un audit à
> l'autre sur le même code. La gravité, elle, est stable : c'est sur elle que repose l'ordre.

## Surfaces non auditables
| Surface | Pourquoi | Ce qu'il faudrait pour la couvrir |

## Par où attaquer
Ordre retenu : <critère choisi>. <n> motifs, <m> occurrences au total.

| # | ID | Motif | Axe | Sév. | Occ. | Diff. | Risque rég. | Validé | Dépend de | Statut |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | VIB-01 | Les points d'entrée de modification ne vérifient pas l'appartenance de la ressource | sécurité | critical | 14 | M | élevé | oui | — | A_FAIRE |

Gains rapides (XS/S de sévérité major ou critical) : VIB-07, VIB-11. Signalés, sans remonter dans l'ordre.

Critiques remontés depuis un autre axe que la sécurité : VIB-03 (évolutivité). Remontée délibérée — la gravité prime sur l'axe.

## Motifs détaillés
### VIB-01 — <énoncé du motif>
- **Axe / sévérité / difficulté** : sécurité / critical / M — **occurrences** : 14 (échantillon ci-dessous)
- **Risque de régression** : élevé — <ce qui le fonde> *(information, n'entre pas dans l'ordre)*
- **Impact** : <ce qu'un attaquant ou un mainteneur peut en faire>
- **Occurrences** : `chemin/fichier.ext:42`, `chemin/autre.ext:88`, … (+10)
- **Correction du motif** : <une phrase, la classe entière>
- **Statut** : A_FAIRE

## Motifs non détaillés dans ce cycle
| ID | Motif | Axe | Sévérité | Occ. | Raison (mineur / au-delà du plafond) |

## Motifs rejetés à la validation
| ID | Motif | Raison |

## Suite
Ce rapport diagnostique ; il ne remédie pas. Pour en tirer un plan exécutable :
`/legacy-audit "<chemin>"` — qui produit roadmap et specs, et couvre en complément la dette
d'accumulation que le présent audit ne cherche pas.
```

**Idempotence / reprise** : si un rapport existait en Phase 1, préserver les statuts `FAIT`/`EN_COURS`, poursuivre la numérotation `VIB-`, et signaler « rapport repris » — sans jamais comparer les deux états ni calculer d'évolution : ce skill n'a pas de mémoire entre exécutions.

## Phase 7 — Rapport final

Émettre un rapport structuré en session :

- **Carte** : projet, forme, taille, git présent/absent, audit complet ou échantillonné, rapport créé ou repris, signaux de génération relevés ;
- **Motifs** : tableau `| Famille | Motifs bruts | Confirmés | Scindés | Rejetés/dédupliqués | Occurrences confirmées |` ;
- **Surfaces non auditables** : liste, avec ce qu'il faudrait pour les couvrir ;
- **Par où attaquer** : les trois premiers motifs de l'ordre retenu, avec leur difficulté ;
- **Fichier écrit** : `AUDIT-vibecode.md` — et le rappel qu'aucun autre fichier n'a été touché ;
- **Prochaine action** : `/legacy-audit "<chemin>"` pour transformer le diagnostic en roadmap et en specs exécutables ;
- **Limites** : rappeler que les familles sans finding ne sont pas des familles sans défaut, et que la logique métier reste la surface la moins couverte par tout outillage automatique.
