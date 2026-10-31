---
name: brainstorm
description: Brainstorm et idéation en co-réflexion challengeante et convergente sur un sujet libre — cinq lentilles parallèles en contexte vierge (hypothèses implicites, alternatives radicales, contre-exemples, coût et faisabilité, effets de second ordre) qui contestent l'idée soumise et produisent des angles absents de l'énoncé, gate humaine à chaque tour, plafond dur de 3 tours puis convergence forcée vers une synthèse de 5 pistes maximum. À utiliser quand l'utilisateur veut être challengé sur une idée et faire émerger ce à quoi il n'a pas pensé, avec une fin explicite plutôt qu'un flot d'idées sans terme.
context: fork
user-invocable: true
argument-hint: "[sujet ou idée à challenger] [--rounds N]"
---

# Brainstorm — co-réflexion challengeante et convergente

Prendre une idée soumise par l'utilisateur et la mettre sous tension plutôt que la valider : lancer à chaque tour cinq lentilles parallèles en contexte vierge, faire remonter les angles que l'énoncé n'anticipait pas, confronter l'utilisateur par une gate humaine, et **clore** — trois tours au maximum, puis une convergence forcée vers cinq pistes au plus. Ce n'est pas un générateur d'idées à volume : sa réussite se mesure à la qualité de la fin qu'il produit.

## Noyau déterministe

Les règles déterministes sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : ne jamais les réimplémenter, appeler la CLI `harness.py` (`bs`) et suivre sa sortie JSON. Règles : **BS-01** à **BS-12** (`hcore/bs.py`), **GT-01** à **GT-08** (gates de dialogue : toujours `ask`, GT-04), **JR-01**, **JR-02**. **Interpréteur** : `<PY>` = le premier de `python`, `python3`, `py -3` qui répond en moins de 5 s avec une version ≥ 3.9 : `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done` ; `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

**Aucune écriture sur disque avant la gate finale** (X5) : le noyau est sans état, la session tient le sien (registre, tour, réponses aux gates) et le transmet **sur l'entrée standard**, en heredoc à délimiteur quoté (`K bs round <<'BS' … BS`), jamais en argument ni en fichier. Le journal est écrit avec la synthèse, à la gate finale.

## Règles impératives (toutes les phases)

- **Contester l'idée soumise, systématiquement.** Chaque tour produit au moins une objection nommée à l'énoncé : une hypothèse tenue pour acquise, un cas où l'idée ne tient pas, un coût non chiffré. La poser en toutes lettres, avec ce qui la fonde.
- **Interdiction de l'approbation complaisante ou par défaut.** Jamais de compliment en ouverture, jamais « bonne idée » sans un test qui l'établit, jamais de piste retenue au seul motif qu'elle vient de l'utilisateur. Un accord n'est légitime qu'avec la raison observable qui a fait tomber l'objection. Un tour qui n'a rien trouvé à contester le dit tel quel — c'est un résultat, pas un échec à masquer par des idées de remplissage.
- **Marquer chaque piste `[énoncé]` ou `[hors énoncé]`** (`enonce` / `hors-enonce`) : présente, même en germe, dans `SUJET` ou une réponse de l'utilisateur, ou absente de tout ce qu'il a écrit. **Au moins une piste `[hors énoncé]` par tour** ; si les lentilles n'en rendent aucune, le dire — c'est le déclencheur de la sortie anticipée, jamais un prétexte à inventer.
- **Registre cumulatif des pistes écartées** `{titre, marquage, tour, raison, par qui}` pour toute la session. Une piste au registre n'est **jamais** reproposée, ni telle quelle, ni reformulée, ni redécoupée : le noyau retire les titres identiques (BS-03) ; **la reformulation reste à ton jugement** — la signaler en une ligne et la supprimer.
- **Le tri appartient à l'utilisateur** (gates, AskUserQuestion). Sans interaction possible (headless, `claude -p`, pas de terminal interactif), **s'arrêter en erreur explicite** avant le premier tour : « /brainstorm est intrinsèquement dialogué : il co-réfléchit avec l'utilisateur tour par tour et ne peut pas produire de synthèse sans ses arbitrages. Relancer en session interactive. » Ni synthèse ni fichier.
- **Frugalité** : lentilles = sous-agents en contexte vierge recevant le briefing du tour et leur seule lentille, jamais « explore tout ».

## Phase 1 — Arguments, reprise et ancrage

1. `K bs args <<'BS'` + `$ARGUMENTS` + `BS` rend `subject` (BS-01 : tous les jetons hors options, mot pour mot), `rounds` (BS-02 : `--rounds` borné à `min(N, 3)`, défaut 3 ; non entier ou `< 1` → erreur explicite), `slug` et `path` `BRAINSTORM-<slug>.md` (BS-09). **Sujet vide** : avant toute reconnaissance et tout sous-agent, gate `brainstorm.subject` (« Sur quoi veux-tu qu'on co-réfléchir ? », saisie libre).
2. **Reprise** (BS-10) : `K bs resume --path <path>` charge la section « Angles écartés » du fichier du même sujet dans le registre dès le tour 1 (à défaut, juger si un autre `BRAINSTORM-*.md` recouvre le sujet) ; signaler « session reprise depuis `<fichier>` ».
3. **Ancrage, budget dur de 12 fichiers lus** : si `SUJET` n'a aucun rapport avec le répertoire courant, écourter (« reconnaissance écourtée : le sujet est sans rapport avec le répertoire courant ») ; sinon `README.md`, `CLAUDE.md`, l'arborescence sur 2 niveaux et les fichiers nommés par le sujet, sans jamais explorer au-delà. Produire l'**ancrage** en quelques lignes (sujet, reprise, pertinence, fichiers lus, contraintes, `rounds`).

## Phase 2 — Tour de challenge : cinq lentilles en parallèle

À chaque tour, **en un seul message**, les cinq lentilles fixes en contexte vierge : aucune ne voit les autres. **`hypotheses`** (ce que l'énoncé tient pour acquis et qui, faux, fait tomber l'idée), **`alternatives`** (autres façons d'atteindre le but, y compris ne rien faire ou agir en amont), **`contre-exemples`** (cas, précédents ou volumétries où l'idée casse ou produit l'inverse), **`cout`** (temps, argent, complexité, maintenance, compétences ; ce qui la rend infaisable ici), **`second-ordre`** (incitations perverses, dépendances, effets sur les autres acteurs, coût de sortie une fois qu'elle marche). Chaque prompt contient : `SUJET` mot pour mot, l'ancrage, l'état du tour (numéro, arbitrages), la liste du registre interdite de reproposition, sa lentille **et rien d'autre**, le marquage obligatoire, « ne jamais valider l'idée par défaut : ta sortie contient au moins une objection nommée », la phrase « **rendre moins de pistes qu'un maximum est une réponse normale et acceptable** », l'interdiction d'écrire sur disque, et un unique bloc JSON final de 4 pistes au plus (BS-04) :

```json
{"pistes": [{"id": "HYP-01", "lens": "hypotheses", "origine": "enonce|hors-enonce",
  "titre": "formulation courte", "these": "l'affirmation en une phrase",
  "appui": "fait, précédent, extrait ≤ 3 lignes, ou raisonnement explicite",
  "consequence": "ce que ça change pour l'idée si c'est vrai", "question_a_trancher": "la question à poser, en une phrase"}],
 "objection_principale": "l'objection la plus forte à l'énoncé, en une phrase"}
```

**Une lentille muette n'est pas une lentille sans objection.** Passer au noyau les cinq blocs extraits (`null` pour un agent mort) : `K bs round <<'BS' {"round": n, "rounds": R, "lenses": {…}, "discarded": […], "relaunched": […]} BS`. `action: relaunch` → relancer **une fois** les lentilles nommées et rappeler avec `relaunched` ; ensuite `synthesize` : la lentille toujours muette est **nommée** (`missing_lenses`) dans la synthèse du tour, dans la gate et dans le fichier, et la **sortie anticipée est désactivée pour ce tour** (BS-05).

## Phase 3 — Synthèse du tour et gate humaine

Dans la session principale : `pistes` (dédupliquées par le noyau contre le registre, `removed` à signaler), regroupées par tension (les lentilles qui se contredisent sont un résultat, pas à lisser), classées par force de l'appui, avec leur marquage, leur thèse, leur appui et leur conséquence, **l'objection principale du tour en tête**. Si `early_exit` (BS-06 : aucune piste `[hors énoncé]` n'a survécu) : annoncer « sortie anticipée : aucun angle hors énoncé nouveau au tour <n> » et passer à la Phase 4. Sinon, gate `brainstorm.round` (obligatoire à la fin de chaque tour) : pour les principaux angles **Creuser** (le tour suivant part de là) / **Écarter** (au registre, avec sa raison, définitivement) / **Amender** (la version amendée remplace l'originale), plus **continuer** ou **converger**. Grouper les angles par question, toujours offrir la saisie libre. Si `converge` et `ceiling` (BS-07) : « plafond de <rounds> tours atteint, passage à la convergence », aucun tour supplémentaire même demandé ; sinon, si l'utilisateur continue, tour suivant.

## Phase 4 — Convergence et gate finale

Aucune nouvelle piste ici : le tri de ce qui a survécu. Classer les pistes (force de l'appui, effet sur l'idée initiale, coût) et **trancher** : le noyau retient les **5 premières** (BS-08, plafond dur non paramétrable) et range les autres en « non retenus dans ce cycle » avec leur rang ; ne jamais renvoyer la décision à l'utilisateur pour éviter de trancher. Rédiger `idea` (l'idée après confrontation : ce qui tient, a bougé, est tombé) et `objections` (celles qui ont tenu, et pourquoi), puis `K bs render --root . <<'BS' {"subject", "idea", "objections", "ranked": [{"title", "marking", "body"}], "discarded": [{"title", "marking", "round", "reason", "by"}], "played", "rounds", "end": "ceiling|early|requested", "missing_lenses"} BS` rend la synthèse (BS-11) : la restituer **en conversation**. **Suggestion de chaînage** si un angle est directement implémentable : `/factory-run "<l'angle formulé comme un besoin>"` ou `/lab-run "<l'angle formulé comme une question falsifiable>"` — l'afficher, **ne jamais la lancer**, sinon ne rien suggérer.

**Gate finale** `brainstorm.write` : **Écrire la synthèse** / **Ne rien écrire**. Puis `K bs finish --root . <<'BS' {…mêmes données, "gates": [{"id", "answer"}] pour chaque gate posée, "write_answer": "<option>"} BS` : il écrit le journal `.harness/runs/brainstorm-<horodatage>.jsonl` (les gates posées, puis la dernière) et, sur *Écrire*, `BRAINSTORM-<slug>.md` (FD-11 vérifié) en **conservant toutes les lignes de l'ancienne section « Angles écartés »** (BS-10) pour qu'une session ultérieure ne les ressuscite pas. Sur *Ne rien écrire*, aucun fichier de synthèse : le dire explicitement.
