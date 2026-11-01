# SPEC — Phases 4 et 5 : politique d'autonomie, boucle, hooks

Statut : APPROUVEE

## Contexte

Les Phases 1 à 3 sont livrées (583 tests verts, commit d438091). Cette spec livre les Phases 4 et 5 **telles que les décrit `specs/SPEC-phase4-5-autonomie-hooks.md`**, déjà APPROUVEE. Le détail des règles, des fixtures et des lots s'y trouve. Ses décisions, et celles des specs des Phases 1 à 3, priment.

## Périmètre

Tous les lots de la spec Phases 4-5, dans l'ordre de son découpage :
- politique `autonomy: gate | auto` dans `harness.json` et `--autonomy`, défaut installé `auto`, gates (b)/(c) au défaut journalisé ;
- spec `BLOQUEE`, merge auto de `ship-pr` sous conditions, enchaînements audit → factory-run → ship-pr ;
- priorisation calculée des audits en `auto` (« fiabiliser d'abord », jalons calculés), y compris en headless : `/audit` doit aller jusqu'à `AUDIT.md` sans réponse humaine ;
- conditions d'arrêt (a) et fichiers `STOP-<horodatage>.md` ;
- `/factory-queue`, `/factory-batch`, `/factory-run --worktree` ;
- hooks Phase 5 (PostToolUse lint, PreToolUse périmètre factory-run et ship-pr, filet Bash), activation contextuelle, deuxième dérive = arrêt (a).

## Critères d'acceptation

- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passe.
- Chaque règle déterministe nouvelle a un **test de comportement**.
- Un hook en erreur interne laisse passer et le signale (test).
- Le filet Bash bloque `git push --force` quelle que soit la politique (test).
- `bash -n install_skills.sh` passe ; `install_skills.*` est inchangé.
- `.claude/harness/` est rafraîchi par `sf copy-core --refresh`.

## Règles de frugalité (impératives)

- Aucun test qui lit la prose d'un SKILL.md (grep de phrases, comptage de lignes, largeur).
- Pas de campagne de mutation.
- Le Verifier lit **chaque** fichier de code nouveau ou modifié avant d'approuver, et ne remonte que les défauts **majeurs**. Les mineurs vont au §8 du BACKLOG.
- Code, commentaires et chaînes en anglais ; prose Markdown en français.

## Hors-périmètre

Phases 6 et 7, et tout commit ou push.
