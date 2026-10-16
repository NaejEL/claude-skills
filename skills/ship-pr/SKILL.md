---
name: ship-pr
description: Pilote le cycle complet d'une pull request GitHub depuis la branche courante — création ou reprise de la PR, rondes de revue par 3 agents relecteurs parallèles avec validation adversariale des findings, commentaires inline, correctifs commités et threads résolus, puis merge (commit de merge) après validation utilisateur. À utiliser quand l'utilisateur veut faire relire, corriger et merger sa branche courante vers une branche cible.
context: fork
user-invocable: true
argument-hint: "<branche-cible> [--rounds N] [--themes \"t1;t2;t3\"]"
---

# Ship PR — revue itérative et merge d'une pull request

Piloter le cycle complet de la branche courante vers une branche cible : créer ou reprendre la PR GitHub, boucler revue → validation adversariale → commentaires inline → correctifs commités → threads résolus, jusqu'à épuisement des findings ou plafond de rondes, puis merger (commit de merge) après validation explicite de l'utilisateur et supprimer la branche de travail.

## Noyau déterministe

Bornes, compteurs, registre, journal et séquences `gh`/`git` de ce skill sont du code Python (bibliothèque standard, ≥ 3.9) dans `${CLAUDE_SKILL_DIR}/../_core/` : CLI `harness.py`, paquet `hcore/`, tests `tests/`. Ne jamais les rejouer à la main : appeler la CLI et suivre son JSON. Exit 1 = arrêt explicite : afficher le message de stderr tel quel et s'arrêter. Exit 2 = erreur d'usage ou borne invalide : l'afficher et s'arrêter. Règles portées : SP-01, SP-02 (`hcore/counters.py`) ; SP-03, SP-04 (`hcore/verdicts.py`) ; SP-05 à SP-10 (`hcore/shippr.py`, `registry.py`, `relaunch.py`) ; SP-11 à SP-19 (`hcore/ghflow.py`).

**Interpréteur** (règle unique, reproduite et testée par `hcore/interp.py`) : `<PY>` = le premier de `python`, `python3`, `py -3`, cherché dans le PATH, qui répond en moins de 5 s avec une version ≥ 3.9 ; aucun → s'arrêter en le disant. Le retenir par cette boucle Bash, portable (le délai n'est posé que si `timeout` existe ; absent, comme sur macOS, lancer la boucle avec le délai de l'outil Bash) :

```bash
t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done
```

Ci-dessous, `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" ship-pr` et `<run>` = le chemin du journal rendu par `start`.

**Journal** : chaque sous-agent est consigné dans `.claude/runs/ship-pr-<horodatage>.jsonl` par sa commande `reviewer` ou `validator`, avec `--model <modèle ou inherit> --duration-ms <ms> --tokens <n>` tirés du bloc d'usage de l'outil Agent (sans durée : `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" begin --run <run> --slot reviewer:<thème>` ou `validator:<id>` juste avant l'agent ; sans tokens : omettre l'option), `--output <fichier>` où la sortie de l'agent est écrite telle quelle avec l'outil Write sous `.claude/runs/` (jamais par stdin ni par une commande shell : backticks, `$` et apostrophes y seraient interprétés ou tronqués), `--dead` s'il est mort. Une mesure manquante ou invalide est journalisée `null` et signalée (`journal_warnings`) sans rien bloquer. Le champ `action` rendu dicte la suite ; ne jamais sauter un appel.

Parser `$ARGUMENTS` :

- **1er token** = branche cible (`main`, `develop`…). S'il est absent, demander la branche cible via AskUserQuestion avant toute chose.
- **`--rounds N`** (SP-01) et **`--themes "a;b;c"`** (SP-02) : transmis tels quels à `start`, qui borne les rondes à `min(N, 3)` (défaut 3) et accepte de 1 à 4 thèmes séparés par `;` (un thème = un agent relecteur ; défaut : les trois thèmes de 3.2). Une valeur hors bornes est une erreur explicite.

## Règles impératives (toutes les phases)

- **Périmètre = le diff de la PR, rien d'autre.** Aucun finding hors des hunks du diff ; aucune proposition de refactoring, de renommage cosmétique ou de durcissement sécurité spéculatif ; plancher de sévérité : un nitpick de style ou une préférence personnelle n'est pas un finding.
- **« Zéro finding » est une réponse normale et acceptable.** Cette phrase figure telle quelle dans le prompt de chaque relecteur et de chaque validateur — jamais de finding inventé pour remplir un quota.
- **Frugalité** : relecteurs = agents lecture seule recevant uniquement les hunks du diff et un contexte minimal (jamais une mission « explore le repo ») ; validateurs = mini-agents à prompt court et effort faible ; 3 rondes maximum ; sortie anticipée dès qu'une ronde ne produit aucun finding confirmé ; à partir de la ronde 2, seuls les commits de correctif et les zones déjà signalées sont revus — jamais de re-revue des fichiers inchangés.
- **Un thème muet n'est pas un thème relu — et bloque le merge** (SP-05). Un relecteur mort (erreur d'API, connexion coupée) ou dont la sortie est inexploitable (SP-03) rend le même silence qu'un vrai « zéro finding », et la sortie anticipée le transformerait en feu vert. `reviewer` rend `relaunch` : relancer **une fois** ; au second échec il rend `uncovered` : le thème est **non couvert**, à signaler dans le commentaire de synthèse de la PR et au rapport. Le noyau ne compte jamais ce silence comme une ronde sans finding et **refuse le merge** : la gate humaine n'est même pas proposée, le skill s'arrête en expliquant quel angle n'a pas été relu et invite à relancer. Ce skill agit sur le dépôt distant : contrairement à un audit, il ne peut pas se contenter de déclarer son amputation. Même règle pour les validateurs (SP-06) : un validateur mort deux fois laisse son finding **non validé** (`unvalidated`) — ni posté en commentaire inline, ni corrigé d'office, il figure au rapport comme restant à trancher.
- **Un commit par ronde** (SP-17), message `fix(review): corrections round N — <résumé>`. Jamais d'amend, jamais de force-push.
- **Jamais de merge sans validation explicite de l'utilisateur** (AskUserQuestion en Phase 4).
- **Registre cumulatif des findings** (SP-07) : `.claude/runs/ship-pr-<horodatage>.registry.jsonl`, tenu par le noyau pour tous les findings, **y compris les REJETÉS**. `reviewer` dédoublonne chaque nouveau finding contre lui (même fichier, titre normalisé) avant validation : un finding rejeté ne ressuscite pas d'une ronde à l'autre. Écarter aussi, au jugement, un doublon du même sujet sous un autre titre.

## Phase 1 — Préflight

`K start --target <cible> [--rounds N] [--themes "…"]` (SP-11) vérifie dans l'ordre l'authentification `gh`, le remote GitHub, la branche courante ≠ cible et l'existence de `origin/<cible>`, et s'arrête au premier échec avec son message : ne jamais continuer sur un préflight rouge. Il ajoute `.claude/runs/` à `.git/info/exclude` s'il n'y figure pas, ouvre le journal et le registre, et rend `run`, `themes`, `dirty` et `owner_repo`.

1. Si `dirty` est vrai → AskUserQuestion : **commiter maintenant** (proposer un message) / **stash** (le noter pour le rappeler au rapport final) / **abandonner**.
2. `K sync --run <run>` (SP-12) : pousse la branche (`git push -u origin HEAD`) si l'upstream manque ou si des commits ne sont pas poussés.

## Phase 2 — Pull request

`K pr --run <run>` (SP-13) reprend la PR ouverte de la branche courante vers la cible. S'il n'y en a pas, il rend `log` et `stat` : en tirer le titre (l'intention du changement) et le corps (résumé + liste des changements notables), écrire le corps tel quel avec l'outil Write dans `.claude/runs/pr-body.md` (jamais par stdin ni par le shell), puis `K pr --run <run> --title "<titre>" --body-file .claude/runs/pr-body.md` crée la PR. La réponse porte `number`, `url`, `created`, `headRefOid` et l'état de merge (SP-14).

Si `conflicting` est vrai → AskUserQuestion : **résoudre maintenant** (merger `origin/<cible>` dans la branche, résoudre, commiter, pousser) / **continuer la revue quand même** / **abandonner**.

## Phase 3 — Boucle de revue (3 rondes maximum)

Répéter 3.1 → 3.6 jusqu'à ce que `end-round` rende une sortie (SP-08) : **`exhaustion`** (succès nominal : une ronde sans finding CONFIRMED, tous ses thèmes couverts) ou **`cap`** (avertissement : plafond de rondes atteint, à signaler distinctement dans le rapport). Une ronde sans CONFIRMED dont un thème n'est pas couvert ne sort pas : son silence ne vaut pas épuisement, la boucle continue (SP-05). Une ronde sans finding `post` passe directement de 3.3 à `end-round` (3.6).

### 3.1 Périmètre de la ronde

`K diff --run <run>` (SP-15) : ronde 1, le diff complet de la PR ; rondes suivantes, uniquement le diff depuis le HEAD d'avant le commit de correctif de la ronde précédente (ce commit est donc relu) plus les hunks des fichiers déjà signalés. Jamais de re-revue des fichiers inchangés.

### 3.2 Relecteurs parallèles

Lancer **en un seul message** les sous-agents relecteurs (type Explore, lecture seule), un par thème rendu par `start`. Thèmes par défaut :

- (a) **logique et cas limites** : erreurs de logique, conditions inversées, off-by-one, cas vides/null, erreurs non gérées ;
- (b) **régressions et contrats des sites d'appel** : signatures modifiées, comportements attendus par les appelants existants, compatibilité des données ;
- (c) **cohérence interne du diff** : code mort introduit, incohérences entre les morceaux du changement (une moitié modifiée, l'autre oubliée).

Chaque prompt de relecteur contient : les hunks du diff du périmètre 3.1 (rien de plus), les règles de périmètre (pas de refacto, pas de sécurité spéculative, pas de nitpick), la phrase « **zéro finding est une réponse acceptable et fréquente** », l'interdiction de poster quoi que ce soit sur la PR, et le format de sortie exigé — un unique bloc JSON final (SP-03) :

```json
{"findings": [{"file": "chemin/relatif", "line": 42, "side": "RIGHT", "severity": "critical|major|minor", "title": "résumé court", "description": "le bug et son scénario de déclenchement", "fix": "correction suggérée"}]}
```

Consigner chaque retour par `K reviewer --run <run> --theme "<thème>" …` : il rend `relaunch`, `uncovered`, ou les findings `to_validate` (avec leur `id`) et les `duplicates` écartés sans validateur.

### 3.3 Validation adversariale

Pour chaque finding de `to_validate`, lancer un **mini-agent validateur** (effort faible, prompt court : le finding + le hunk concerné + les règles de périmètre) chargé de le contester : est-ce dans le diff ? est-ce un vrai bug avec un scénario concret ? vaut-il un correctif ici, ou est-ce un refacto/nitpick déguisé ? Sortie exigée (SP-04) : `{"verdict": "CONFIRMED|REJECTED", "reason": "justification en une phrase"}`. Consigner par `K validator --run <run> --finding <id> …` : il rend `post` (CONFIRMED), `drop` (REJECTED), `relaunch` ou `unvalidated`, et inscrit le verdict au registre.

### 3.4 Commentaires inline

Pour chaque finding `post` : `K comment --run <run> --finding <id>` (SP-16) poste le commentaire inline avec le `headRefOid` relu au moment du post. Sur HTTP 422 seulement (ligne hors du diff), il se replie sur un commentaire niveau fichier, en dernier recours sur un commentaire de PR citant fichier et ligne ; toute autre erreur est un arrêt (exit 1).

### 3.5 Correctifs

Appliquer soi-même chaque correctif confirmé (édition directe, pas de sous-agent), au plus près de la correction suggérée — sans élargir le périmètre. Puis `K commit --run <run> --summary "<résumé>" --fixed <id>… [--not-fixed "<id>:<raison>"]…` (SP-17, SP-09) : un commit `fix(review)` poussé, et chaque finding confirmé consigné au registre, corrigé (avec le hash) ou volontairement **non** corrigé avec sa raison (faux positif découvert au moment du fix, correctif impossible sans élargir le périmètre).

### 3.6 Réponse et résolution des threads

`K threads --run <run>` (SP-18) répond « Corrigé dans <hash>. » puis résout le thread de chaque finding corrigé ; il répond avec la raison et laisse **ouvert** celui de chaque finding non corrigé. Puis `K end-round --run <run>` (SP-08, SP-10) : compteurs de la ronde, puis sortie de boucle ou ronde suivante (reboucler en 3.1).

## Phase 4 — Merge (gate humaine)

1. `K merge --run <run> --check` (SP-05, SP-19) refuse — et le skill s'arrête là, sans gate — si un thème n'a pas été couvert. Sinon il rend le résumé (SP-10 : findings bruts/confirmés/rejetés/dédoublonnés par ronde, commits de correctif avec leurs hashes, threads résolus et restés ouverts, findings non validés) et l'état de merge à jour : le présenter. Si `conflicting`, le signaler et proposer de résoudre avant la question de merge.
2. **AskUserQuestion** : « Merger la PR #<n> vers <cible> ? » — options : **Merger** / **Laisser la PR ouverte**.
3. Si l'utilisateur valide : `K merge --run <run>` (SP-19) — commit de merge explicite (`gh pr merge --merge --delete-branch`, jamais `--squash` ni `--rebase`) qui supprime la branche distante et la branche locale, puis `git checkout <cible> && git pull`. Si un stash a été fait en Phase 1, rappeler à l'utilisateur de faire `git stash pop` — sans le faire d'office.

## Phase 5 — Rapport final

Émettre un rapport structuré :

- **PR** : numéro, URL, branche → cible, créée ou reprise ;
- **Rondes** : tableau `| Ronde | Findings bruts | Confirmés | Rejetés/dédupliqués |` ;
- **Correctifs** : un hash de commit par ronde, avec résumé ;
- **Threads** : résolus (avec hash cité) / laissés ouverts (avec raison) ;
- **Sortie de boucle** : épuisement (succès) ou plafond de rondes atteint (avertissement — signaler qu'une relecture humaine complémentaire est prudente) ;
- **Décision** : mergée (commit de merge + branche supprimée, branche courante = <cible> à jour) ou laissée ouverte ;
- **Reste à faire** : stash à dépiler, conflits non résolus, threads ouverts, findings non validés, thèmes non couverts, le cas échéant ;
- **Journal** : chemins du journal et du registre sous `.claude/runs/`.
