---
name: ship-pr
description: Pilote le cycle complet d'une pull request GitHub depuis la branche courante — création ou reprise de la PR, rondes de revue par 3 agents relecteurs parallèles avec validation adversariale des findings, commentaires inline, correctifs commités et threads résolus, puis merge (commit de merge) après validation utilisateur. À utiliser quand l'utilisateur veut faire relire, corriger et merger sa branche courante vers une branche cible.
context: fork
user-invocable: true
argument-hint: "<branche-cible> [--rounds N] [--themes \"t1;t2;t3\"]"
---

# Ship PR — revue itérative et merge d'une pull request

Piloter le cycle complet de la branche courante vers une branche cible : créer ou reprendre la PR GitHub, boucler revue → validation adversariale → commentaires inline → correctifs commités → threads résolus, jusqu'à épuisement des findings ou plafond de rondes, puis merger (commit de merge) après validation explicite de l'utilisateur et supprimer la branche de travail.

Parser `$ARGUMENTS` :

- **1er token** = branche cible (`main`, `develop`…). S'il est absent, demander la branche cible via AskUserQuestion avant toute chose.
- **`--rounds N`** : plafond de rondes, borné dur à `min(N, 3)`. Défaut : 3.
- **`--themes "a;b;c"`** : remplace les angles de revue par défaut (séparateur `;`, un thème = un agent relecteur ; moins de thèmes = moins de relecteurs, 4 maximum).

## Règles impératives (toutes les phases)

- **Périmètre = le diff de la PR, rien d'autre.** Aucun finding hors des hunks du diff ; aucune proposition de refactoring, de renommage cosmétique ou de durcissement sécurité spéculatif ; plancher de sévérité : un nitpick de style ou une préférence personnelle n'est pas un finding.
- **« Zéro finding » est une réponse normale et acceptable.** Cette phrase figure telle quelle dans le prompt de chaque relecteur et de chaque validateur — jamais de finding inventé pour remplir un quota.
- **Frugalité** : relecteurs = agents lecture seule recevant uniquement les hunks du diff et un contexte minimal (jamais une mission « explore le repo ») ; validateurs = mini-agents à prompt court et effort faible ; 3 rondes maximum ; sortie anticipée dès qu'une ronde ne produit aucun finding confirmé ; à partir de la ronde 2, seuls les commits de correctif et les zones déjà signalées sont revus — jamais de re-revue des fichiers inchangés.
- **Un thème muet n'est pas un thème relu — et bloque le merge.** Un relecteur mort (erreur d'API, connexion coupée) ou dont la sortie est inexploitable rend le même silence qu'un vrai « zéro finding », et la sortie anticipée le transformerait en feu vert. À la fin de chaque ronde, vérifier que **chaque thème lancé a rendu un bloc JSON exploitable** ; pour chaque thème manquant, relancer **une fois**. Si le second essai échoue, le thème est **non couvert** : le signaler dans le commentaire de synthèse de la PR et au rapport, et **refuser le merge en Phase 4** — la gate humaine n'est même pas proposée, le skill s'arrête en expliquant quel angle n'a pas été relu et invite à relancer. Ce skill agit sur le dépôt distant : contrairement à un audit, il ne peut pas se contenter de déclarer son amputation. Ne jamais compter un thème mort comme une ronde sans finding, ni déclencher la sortie anticipée sur son silence. Même règle pour les validateurs : un validateur mort laisse son finding **non validé** — il n'est ni posté en commentaire inline, ni corrigé d'office, et il figure au rapport comme restant à trancher.
- **Un commit par ronde**, message `fix(review): corrections round N — <résumé>`. Jamais d'amend, jamais de force-push.
- **Jamais de merge sans validation explicite de l'utilisateur** (AskUserQuestion en Phase 4).
- **Registre cumulatif des findings** : tenir en mémoire `{fichier, ligne, résumé, verdict}` pour tous les findings, **y compris les REJETÉS**. Tout nouveau finding est dédupliqué contre ce registre avant validation : un finding rejeté ne ressuscite pas d'une ronde à l'autre.

## Phase 1 — Préflight

Exécuter chaque check dans l'ordre ; en cas d'échec, s'arrêter avec le message indiqué (ne jamais continuer sur un préflight rouge) :

1. `gh auth status` → sinon arrêt : « gh non authentifié — lancer `gh auth login` ».
2. `git remote get-url origin` doit contenir `github.com` → sinon arrêt : « pas de remote GitHub ».
3. `git rev-parse --abbrev-ref HEAD` : si la branche courante **est** la branche cible → arrêt : « vous êtes déjà sur <cible>, placez-vous sur la branche à merger ».
4. `git fetch origin <cible>` puis `git rev-parse --verify origin/<cible>` → sinon arrêt : « la branche cible <cible> n'existe pas sur origin ».
5. `git status --porcelain` non vide → AskUserQuestion : **commiter maintenant** (proposer un message) / **stash** (le noter pour le rappeler au rapport final) / **abandonner**.
6. Upstream : `git rev-parse --abbrev-ref --symbolic-full-name @{u}` ; si absent, ou si `git rev-list @{u}..HEAD --count` > 0 → `git push -u origin HEAD`.
7. Mémoriser owner et repo : `gh repo view --json owner,name -q '.owner.login + "/" + .name'`.

## Phase 2 — Pull request

Chercher une PR ouverte pour la branche courante :

```bash
gh pr list --head <branche> --base <cible> --state open --json number,url,title
```

- **Si vide** : générer le titre et le corps depuis `git log origin/<cible>..HEAD --oneline` et `git diff origin/<cible>...HEAD --stat` (titre = l'intention du changement, corps = résumé + liste des changements notables), puis :

```bash
gh pr create --base <cible> --title "<titre>" --body "<corps>"
```

- **Sinon** : reprendre la PR existante.

Mémoriser `PR_NUMBER` puis `HEAD_SHA` :

```bash
gh pr view <n> --json headRefOid -q .headRefOid
```

Détecter les conflits tôt : `gh pr view <n> --json mergeable,mergeStateStatus`. Si `CONFLICTING` → AskUserQuestion : **résoudre maintenant** (merger `origin/<cible>` dans la branche, résoudre, commiter, pousser) / **continuer la revue quand même** / **abandonner**.

## Phase 3 — Boucle de revue (3 rondes maximum)

Répéter les étapes 3.1 → 3.6 jusqu'à l'une des deux sorties :

- **Épuisement** (succès nominal) : une ronde ne produit aucun finding CONFIRMED → sortir de la boucle.
- **Plafond atteint** (avertissement) : le compteur de rondes atteint le cap → sortir en le signalant distinctement dans le rapport.

### 3.1 Périmètre de la ronde

- **Ronde 1** : le diff complet de la PR — `gh pr diff <n>`.
- **Rondes suivantes** : uniquement `git diff <sha-fin-de-ronde-précédente>..HEAD` plus les hunks des fichiers déjà signalés. Jamais de re-revue des fichiers inchangés.

### 3.2 Relecteurs parallèles

Lancer **en un seul message** les sous-agents relecteurs (type Explore, lecture seule), un par thème. Thèmes par défaut (remplacés par `--themes` si fourni) :

- (a) **logique et cas limites** : erreurs de logique, conditions inversées, off-by-one, cas vides/null, erreurs non gérées ;
- (b) **régressions et contrats des sites d'appel** : signatures modifiées, comportements attendus par les appelants existants, compatibilité des données ;
- (c) **cohérence interne du diff** : code mort introduit, incohérences entre les morceaux du changement (une moitié modifiée, l'autre oubliée).

Chaque prompt de relecteur contient : les hunks du diff du périmètre 3.1 (rien de plus), les règles de périmètre (pas de refacto, pas de sécurité spéculative, pas de nitpick), la phrase « **zéro finding est une réponse acceptable et fréquente** », l'interdiction de poster quoi que ce soit sur la PR, et le format de sortie exigé — un unique bloc JSON final :

```json
{"findings": [{"file": "chemin/relatif", "line": 42, "side": "RIGHT", "severity": "critical|major|minor", "title": "résumé court", "description": "le bug et son scénario de déclenchement", "fix": "correction suggérée"}]}
```

### 3.3 Validation adversariale

1. **Dédupliquer** d'abord chaque finding contre le registre cumulatif (mêmes fichier/ligne/sujet), verdicts REJECTED compris — les doublons sont écartés sans validateur.
2. Pour chaque finding survivant, lancer un **mini-agent validateur** (effort faible, prompt court : le finding + le hunk concerné + les règles de périmètre) chargé de le contester : est-ce dans le diff ? est-ce un vrai bug avec un scénario concret ? vaut-il un correctif ici, ou est-ce un refacto/nitpick déguisé ? Sortie exigée :

```json
{"verdict": "CONFIRMED|REJECTED", "reason": "justification en une phrase"}
```

3. Ajouter chaque finding au registre avec son verdict. **Si zéro CONFIRMED → épuisement, sortir de la boucle.**

### 3.4 Commentaires inline

Pour chaque finding CONFIRMED, poster un commentaire inline avec le `HEAD_SHA` **courant au moment du post** (le push de fin de ronde changera le SHA — toujours relire `headRefOid` avant de poster) :

```bash
gh api repos/{owner}/{repo}/pulls/<n>/comments \
  -f body="**[<severity>] <title>**

<description>

Correction suggérée : <fix>" \
  -f commit_id=<HEAD_SHA> -f path=<file> -F line=<line> -f side=RIGHT
```

Mémoriser l'`id` (databaseId) retourné pour chaque commentaire. **Fallback en cas de HTTP 422** (ligne hors du diff) : commentaire niveau fichier — mêmes paramètres sans `line`/`side`, avec `-f subject_type=file` ; en dernier recours `gh pr comment <n> --body "..."` en citant fichier et ligne dans le corps.

### 3.5 Correctifs

Appliquer soi-même chaque correctif confirmé (édition directe, pas de sous-agent), au plus près de la correction suggérée — sans élargir le périmètre. Puis :

```bash
git add -A && git commit -m "fix(review): corrections round <N> — <résumé>" && git push
```

Mémoriser le hash du commit de correctif et relire `headRefOid`.

### 3.6 Réponse et résolution des threads

Récupérer le mapping commentaire → thread (GraphQL est le seul moyen d'obtenir les thread ids) :

```bash
gh api graphql -f query='query($owner:String!,$repo:String!,$number:Int!){
  repository(owner:$owner,name:$repo){ pullRequest(number:$number){
    reviewThreads(first:100){ nodes{ id isResolved
      comments(first:10){ nodes{ databaseId } } } } } } }' \
  -f owner=<owner> -f repo=<repo> -F number=<n>
```

Pour chaque commentaire posté en 3.4 dont le correctif est appliqué, répondre puis résoudre le thread :

```bash
gh api repos/{owner}/{repo}/pulls/<n>/comments/<comment_id>/replies \
  -f body="Corrigé dans <hash-du-commit-de-fix>."
gh api graphql -f query='mutation($t:ID!){
  resolveReviewThread(input:{threadId:$t}){ thread{ id isResolved } } }' -f t=<thread_id>
```

Si un finding confirmé n'a volontairement **pas** été corrigé (faux positif découvert au moment du fix, correctif impossible sans élargir le périmètre), répondre au thread en l'expliquant, le laisser **ouvert**, et le consigner au registre comme non corrigé.

Fin de ronde : incrémenter le compteur et reboucler en 3.1.

## Phase 4 — Merge (gate humaine)

1. Présenter le résumé : nombre de rondes, findings bruts/confirmés/rejetés par ronde, commits de correctif avec leurs hashes, threads résolus et restés ouverts.
2. Re-vérifier `gh pr view <n> --json mergeable,mergeStateStatus` (les pushes ont pu changer l'état). Si `CONFLICTING`, le signaler et proposer de résoudre avant la question de merge.
3. **AskUserQuestion** : « Merger la PR #<n> vers <cible> ? » — options : **Merger** / **Laisser la PR ouverte**.
4. Si l'utilisateur valide :

```bash
gh pr merge <n> --merge --delete-branch
git checkout <cible> && git pull
```

Commit de merge explicite (jamais `--squash` ni `--rebase`) ; `--delete-branch` supprime la branche distante et la branche locale. Si un stash a été fait en Phase 1, rappeler à l'utilisateur de faire `git stash pop` — sans le faire d'office.

## Phase 5 — Rapport final

Émettre un rapport structuré :

- **PR** : numéro, URL, branche → cible, créée ou reprise ;
- **Rondes** : tableau `| Ronde | Findings bruts | Confirmés | Rejetés/dédupliqués |` ;
- **Correctifs** : un hash de commit par ronde, avec résumé ;
- **Threads** : résolus (avec hash cité) / laissés ouverts (avec raison) ;
- **Sortie de boucle** : épuisement (succès) ou plafond de rondes atteint (avertissement — signaler qu'une relecture humaine complémentaire est prudente) ;
- **Décision** : mergée (commit de merge + branche supprimée, branche courante = <cible> à jour) ou laissée ouverte ;
- **Reste à faire** : stash à dépiler, conflits non résolus, threads ouverts, le cas échéant.
