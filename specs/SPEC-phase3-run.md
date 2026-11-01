# SPEC — Phase 3 : versioning, upgrade, doctor

Statut : APPROUVEE

## Contexte

Les Phases 1 et 2 sont livrées : noyau `skills/_core/` (494 tests verts), profils, scout, `/audit` unifié (commit 982e189). Cette spec livre la Phase 3 **telle que la décrit `specs/SPEC-phase3-upgrade-doctor.md`**, déjà APPROUVEE. Le détail des règles, des fixtures et des lots s'y trouve. Ses décisions, et celles des specs des Phases 1 et 2, priment.

## Périmètre

Tous les lots de la spec Phase 3, dans l'ordre de son découpage :
- tampon `.claude/harness.json` complété (version du dépôt, date, skills et options, politique, profils) ;
- `--upgrade` sur `/software-factory` (tous profils) et `/code-index` : blocs délimités seuls, hors-bloc préservé, migrations, diff montré, idempotent, projet sans tampon détecté ;
- `/harness-doctor` et `--scan <racine>` ;
- en-tête de version sur les fichiers régénérés.

## Critères d'acceptation

- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passe.
- Chaque règle déterministe nouvelle a un **test de comportement**.
- Un `--upgrade` relancé sans changement produit zéro diff (test).
- Une personnalisation hors bloc survit à `--upgrade` (test).
- `bash -n install_skills.sh` passe ; `install_skills.*` est inchangé.
- `.claude/harness/` est rafraîchi par `sf copy-core --refresh`.

## Règles de frugalité (impératives)

- Aucun test qui lit la prose d'un SKILL.md (grep de phrases, comptage de lignes, largeur).
- Pas de campagne de mutation.
- Le Verifier lit **chaque** fichier de code nouveau ou modifié avant d'approuver, et ne remonte que les défauts **majeurs**. Les mineurs vont au §8 du BACKLOG.
- Code, commentaires et chaînes en anglais ; prose Markdown en français.

## Hors-périmètre

Phases 4 à 7, et tout commit ou push.
