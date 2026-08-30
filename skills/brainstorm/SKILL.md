---
name: brainstorm
description: Brainstorm et idéation en co-réflexion challengeante et convergente sur un sujet libre — cinq lentilles parallèles en contexte vierge (hypothèses implicites, alternatives radicales, contre-exemples, coût et faisabilité, effets de second ordre) qui contestent l'idée soumise et produisent des angles absents de l'énoncé, gate humaine à chaque tour, plafond dur de 3 tours puis convergence forcée vers une synthèse de 5 pistes maximum. À utiliser quand l'utilisateur veut être challengé sur une idée et faire émerger ce à quoi il n'a pas pensé, avec une fin explicite plutôt qu'un flot d'idées sans terme.
context: fork
user-invocable: true
argument-hint: "[sujet ou idée à challenger] [--rounds N]"
---

# Brainstorm — co-réflexion challengeante et convergente

Prendre une idée soumise par l'utilisateur et la mettre sous tension plutôt que la valider : lancer à chaque tour cinq lentilles parallèles en contexte vierge, faire remonter les angles que l'énoncé n'anticipait pas, confronter l'utilisateur à ces angles par une gate humaine, et **clore** — trois tours au maximum, puis une convergence forcée vers une synthèse de cinq pistes au plus. Ce skill n'est pas un générateur d'idées à volume : sa réussite se mesure à la qualité de la fin qu'il produit, pas au nombre de propositions.

Parser `$ARGUMENTS` :

- **1er token et suivants** (tout ce qui ne commence pas par `--`) = **sujet** ou idée à challenger, en texte libre, éventuellement long et vague. Mémoriser `SUJET` tel quel, mot pour mot, comme énoncé de référence de toute la session.
- **Sujet absent** (aucun token hors options) : avant toute autre chose, avant toute reconnaissance et avant tout sous-agent, demander le sujet à l'utilisateur par `AskUserQuestion` (« Sur quoi veux-tu qu'on co-réfléchisse ? »), avec une option de saisie libre. Ne rien lancer tant que `SUJET` est vide ; si aucune réponse n'est possible, appliquer l'arrêt headless des règles impératives.
- **`--rounds N`** : nombre de tours de challenge, borné dur à `min(N, 3)`. Défaut : 3. Une valeur non entière ou `< 1` est refusée avec un message explicite plutôt que corrigée silencieusement. Mémoriser `ROUNDS`. Le plafond de 3 n'est jamais dépassé, quelle que soit la demande.

## Règles impératives (toutes les phases)

- **Contester l'idée soumise, systématiquement.** Chaque tour doit produire au moins une objection nommée à l'énoncé de l'utilisateur : une hypothèse qu'il tient pour acquise, un cas où son idée ne tient pas, un coût qu'il n'a pas chiffré. Poser la contradiction en toutes lettres, avec ce qui la fonde ; ne jamais l'enrober au point qu'elle devienne invisible.
- **Interdiction de l'approbation complaisante ou par défaut.** Ne jamais ouvrir une réponse par un compliment sur l'idée, ne jamais conclure « bonne idée » ou « c'est solide » sans un test qui l'établit, ne jamais retenir une piste au seul motif qu'elle vient de l'utilisateur. Un accord n'est légitime qu'accompagné de la raison observable qui a fait tomber l'objection. Si un tour n'a rien trouvé à contester, le dire tel quel — c'est un résultat, pas un échec à masquer par des idées de remplissage.
- **Marquer chaque piste `[énoncé]` ou `[hors énoncé]`.** `[énoncé]` = présente, même en germe, dans le texte de `SUJET` ou dans une réponse antérieure de l'utilisateur ; `[hors énoncé]` = absente de tout ce que l'utilisateur a écrit jusqu'ici. Le marquage figure sur chaque piste, dans la synthèse de tour comme dans le rapport final. **Au moins une piste `[hors énoncé]` doit être produite à chaque tour** ; si les cinq lentilles n'en rendent aucune, le dire explicitement — c'est le déclencheur de la sortie anticipée, jamais un prétexte à inventer une piste pour remplir la case.
- **Registre cumulatif des pistes écartées.** Tenir en mémoire, d'un tour à l'autre et pour toute la session, `{id, titre, marquage, tour, raison de l'écartement, qui l'a écartée (utilisateur / lentille)}`. Une piste au registre ne peut **jamais** être reproposée, ni telle quelle, ni reformulée, ni redécoupée. Avant de présenter la synthèse d'un tour, confronter chaque piste au registre et supprimer les résurgences en le signalant en une ligne.
- **Le tri appartient à l'utilisateur** (`AskUserQuestion` à la fin de chaque tour, Phase 3). Si aucune interaction n'est possible (exécution headless, `claude -p`, absence de terminal interactif), **s'arrêter en erreur explicite** avant le premier tour, avec le message : « /brainstorm est intrinsèquement dialogué : il co-réfléchit avec l'utilisateur tour par tour et ne peut pas produire de synthèse sans ses arbitrages. Relancer en session interactive. » Ne produire ni synthèse ni fichier dans ce cas.
- **Frugalité.** Les lentilles sont des sous-agents en contexte vierge recevant le briefing du tour et leur seule lentille, jamais une mission « explore tout ». Aucune écriture sur disque avant la gate finale de la Phase 4.

## Phase 1 — Reconnaissance et ancrage

Dans la session principale, sans sous-agent, **budget dur de 12 fichiers lus au total** :

1. **Reprise** : chercher dans le répertoire courant un fichier de synthèse antérieur portant sur le même sujet — `BRAINSTORM-<slug>.md`, où `<slug>` est le slug de `SUJET` (voir Phase 4), puis à défaut tout `BRAINSTORM-*.md` dont le titre recouvre le sujet. S'il existe, le lire et **charger sa section « Angles écartés » dans le registre cumulatif dès le tour 1** : ces pistes sont déjà tranchées et ne seront pas reproposées. Charger aussi ses angles retenus comme acquis de départ. Signaler « session reprise depuis `<fichier>` » à l'utilisateur.
2. **Pertinence** : déterminer si `SUJET` a un rapport avec le répertoire courant (le sujet nomme-t-il du code, un produit, une architecture, un fichier présents ici ?). **Si le sujet n'a aucun rapport avec le répertoire courant** (sujet personnel, stratégique, hors logiciel, ou projet différent) : **écourter la reconnaissance immédiatement**, ne lire aucun fichier au-delà de la reprise du point 1, l'annoncer en une ligne (« reconnaissance écourtée : le sujet est sans rapport avec le répertoire courant ») et enchaîner sur la Phase 2. La session n'est jamais bloquée par ce cas.
3. **Ancrage** (uniquement si le sujet est lié au répertoire courant) : lire `README.md` et `CLAUDE.md` s'ils existent, l'arborescence sur 2 niveaux, et au plus les fichiers directement nommés par le sujet — **dans la limite des 12 fichiers du budget, sans jamais explorer au-delà**. Ne pas ouvrir de dépendances, ne pas parcourir l'historique git, ne pas lire un fichier « pour voir ».

Produire l'**ancrage** en quelques lignes : sujet retenu mot pour mot, reprise (oui/non, fichier), pertinence au répertoire courant (ancrée / écourtée), fichiers effectivement lus, contraintes déjà connues, `ROUNDS`.

## Phase 2 — Tour de challenge : cinq lentilles en parallèle

Rejouée à chaque tour, du tour 1 au tour `ROUNDS`. Lancer **en un seul message** les cinq agents de lentille, donc **en parallèle et en contexte vierge** : aucun ne voit le prompt, le raisonnement ni les conclusions des quatre autres — la confrontation n'a lieu qu'à la synthèse du tour, en Phase 3. Les cinq lentilles sont fixes et toujours toutes lancées :

- **(a) `hypotheses`** — hypothèses implicites : ce que l'énoncé tient pour acquis sans le dire et qui, faux, fait tomber l'idée.
- **(b) `alternatives`** — alternatives radicales : d'autres façons d'atteindre le même but, y compris ne rien faire ou résoudre le problème en amont.
- **(c) `contre-exemples`** — contre-exemples et cas limites : situations concrètes, précédents ou volumétries où l'idée casse ou produit l'inverse de l'effet visé.
- **(d) `cout`** — coût et faisabilité : ce que l'idée coûte réellement (temps, argent, complexité, maintenance, compétences) et ce qui la rend infaisable dans le contexte donné.
- **(e) `second-ordre`** — effets de second ordre : ce que l'idée déclenche une fois qu'elle marche — incitations perverses, dépendances créées, effets sur les autres acteurs, coût de sortie.

Chaque prompt de lentille contient : `SUJET` mot pour mot, l'ancrage de la Phase 1, l'état du tour (numéro, arbitrages de l'utilisateur aux tours précédents), la **liste des pistes du registre cumulatif interdites de reproposition**, sa lentille **et rien d'autre à chercher**, l'obligation de marquer chaque piste `[énoncé]` ou `[hors énoncé]`, la consigne « ne jamais valider l'idée par défaut : ta sortie doit contenir au moins une objection nommée », la phrase « **rendre moins de pistes qu'un maximum est une réponse normale et acceptable** », l'interdiction d'écrire quoi que ce soit sur disque, et le format de sortie exigé — au plus 4 pistes, un unique bloc JSON final :

```json
{"pistes": [{"id": "HYP-01", "lens": "hypotheses", "origine": "enonce|hors-enonce",
  "titre": "formulation courte", "these": "l'affirmation en une phrase",
  "appui": "ce qui la fonde : fait, précédent, extrait ≤ 3 lignes, ou raisonnement explicite",
  "consequence": "ce que ça change pour l'idée de l'utilisateur si c'est vrai",
  "question_a_trancher": "la question à poser à l'utilisateur en une phrase"}],
 "objection_principale": "l'objection la plus forte à l'énoncé, en une phrase"}
```

## Phase 3 — Synthèse du tour et gate humaine

Dans la session principale, sans sous-agent :

1. **Dédupliquer** les pistes des cinq lentilles entre elles, puis contre le **registre cumulatif** : toute piste équivalente à une piste déjà écartée est supprimée et la suppression signalée en une ligne.
2. **Consolider** : regrouper les pistes survivantes par tension (les lentilles qui se contredisent sont un résultat, l'exposer et non le lisser), classer par force de l'appui, et présenter en conversation, chaque piste avec son marquage `[énoncé]` / `[hors énoncé]`, sa thèse, son appui, sa conséquence. Présenter **l'objection principale du tour** en tête, avant les pistes.
3. **Test de sortie anticipée**, appliqué avant la gate : compter les pistes `[hors énoncé]` du tour qui ont survécu à la déduplication et au registre. **Si ce nombre vaut 0**, le tour n'a rien apporté que l'énoncé ne contenait déjà : l'annoncer (« sortie anticipée : aucun angle hors énoncé nouveau au tour <n> ») et passer immédiatement à la Phase 4, sans lancer de tour suivant.
4. **Gate humaine du tour** (`AskUserQuestion`, obligatoire à la fin de chaque tour) : présenter les angles du tour et demander à l'utilisateur, pour les principaux, ce qu'il en fait — **Creuser** (le tour suivant part de là), **Écarter** (l'inscrire au registre avec sa raison, définitivement), **Amender** (l'utilisateur reformule, la version amendée remplace l'originale). Ajouter une question de cadrage : **continuer au tour suivant** ou **converger maintenant**. Grouper les angles par question, ne jamais les égrener un par un, et toujours offrir la saisie libre.
5. **Boucle** : si l'utilisateur choisit de continuer **et** que le tour courant est `< ROUNDS`, incrémenter le tour et revenir en Phase 2 avec les arbitrages comme point de départ. **Au plafond** (tour courant `= ROUNDS`, donc au plus 3), le passage à la Phase 4 est **forcé** : l'annoncer (« plafond de <ROUNDS> tours atteint, passage à la convergence ») et ne proposer aucun tour supplémentaire, même si l'utilisateur en demande un.

## Phase 4 — Convergence et rapport final

Dernière phase : elle **clôt la session**. Aucune nouvelle piste n'est produite ici — seulement le tri de ce qui a survécu.

Appliquer un **plafond dur de 5 pistes retenues**, non paramétrable. Si plus de 5 ont survécu, hiérarchiser (force de l'appui, puis effet sur l'idée initiale, puis coût) et **trancher** : les surnuméraires basculent en « angles non retenus dans ce cycle » avec leur rang et la raison de l'arbitrage. Ne jamais rendre plus de 5 pistes retenues, ne jamais renvoyer la décision à l'utilisateur pour éviter de trancher.

Restituer la synthèse **en conversation**, dans cet ordre :

```markdown
# Brainstorm — <SUJET>

## L'idée après confrontation
<l'idée reformulée telle qu'elle sort des tours : ce qui tient, ce qui a bougé, ce qui est tombé>

## Objections qui ont tenu
- <objection, et pourquoi elle n'a pas été levée>

## Angles retenus (5 maximum)
1. **<titre>** `[énoncé|hors énoncé]` — thèse, appui, ce que ça change, prochaine action concrète.

## Angles écartés
| Angle | Marquage | Tour | Raison | Écarté par |
| --- | --- | --- | --- | --- |

## Angles non retenus dans ce cycle
| Angle | Rang | Raison (au-delà du plafond de 5) |

## Fin de session
Tours joués : <n>/<ROUNDS>. Fin : plafond atteint | sortie anticipée | convergence demandée.
```

**Suggestion de chaînage** : si un angle retenu est directement implémentable, l'indiquer avec la commande correspondante — `/factory-run "<l'angle formulé comme un besoin>"` pour un développement logiciel, `/lab-run "<l'angle formulé comme une question falsifiable>"` pour une question de recherche expérimentale. **Ne jamais lancer cette commande à la place de l'utilisateur** : la suggérer, l'afficher, et s'arrêter là. Si aucun angle n'est implémentable, ne rien suggérer.

**Gate finale d'écriture** (`AskUserQuestion`) : demander si la synthèse doit être écrite dans un fichier. Chemin **déterministe** : `<répertoire courant>/BRAINSTORM-<slug>.md`, où `<slug>` est dérivé de `SUJET` — minuscules, accents retirés, tout caractère non alphanumérique remplacé par un tiret, tirets consécutifs fusionnés, tronqué à 40 caractères, sans tiret final. Options : **Écrire la synthèse** / **Ne rien écrire**. En cas de refus, **rien n'est écrit sur disque** et le dire explicitement. En cas d'acceptation, écrire exactement la synthèse ci-dessus ; si le fichier existait déjà (reprise de la Phase 1), le remplacer par la version consolidée qui **conserve toutes les lignes de son ancienne section « Angles écartés »**, afin qu'une session ultérieure ne les ressuscite pas.
