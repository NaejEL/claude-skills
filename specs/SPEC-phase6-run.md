# SPEC — Phase 6 : tests du harnais

Statut : LIVREE

## Contexte

Les Phases 1 à 5 sont livrées (754 tests verts, commit 5070bb1). Cette spec livre la Phase 6 **telle que la décrit `specs/SPEC-phase6-tests-harnais.md`**, déjà APPROUVEE. Le détail des scénarios, des fixtures et des lots s'y trouve. Ses décisions, et celles des specs des Phases 1 à 5, priment.

## Périmètre

Tous les lots de la spec Phase 6 :
- `ci/fixtures/` : projets jouets minimaux, dépôt bare local comme remote ;
- scénarios exécutables vérifiés par script : installation à neuf, `--upgrade` d'un projet installé « à l'ancienne » avec personnalisations hors bloc qui survivent, cycle `factory-run` en `auto` jusqu'au Verifier, `ship-pr` à zéro finding → merge auto, hook qui bloque hors diff, `models.json` absent, `lab-models.json` legacy, arrêt propre à la 3e itération ;
- `ci/test-harness.sh` et `ci/test-harness.ps1` (ou l'outillage d'évaluation de Claude Code si la spec l'a retenu).

## Critères d'acceptation

- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passe.
- `bash ci/test-harness.sh` et `pwsh ci/test-harness.ps1` passent sur cette machine, sans réseau ni appel à un vrai modèle (agents, `gh` et `claude` simulés comme la spec le prévoit).
- `bash -n` passe sur chaque script Bash ajouté ; `install_skills.*` est inchangé.
- `.claude/harness/` est rafraîchi par `sf copy-core --refresh`.

## Règles de frugalité (impératives)

- Aucun test qui lit la prose d'un SKILL.md (grep de phrases, comptage de lignes, largeur).
- Pas de campagne de mutation.
- Le Verifier lit **chaque** fichier de code nouveau ou modifié avant d'approuver, et ne remonte que les défauts **majeurs**. Les mineurs vont au §8 du BACKLOG.
- Code, commentaires et chaînes en anglais ; prose Markdown en français.

## Hors-périmètre

Phase 7, et tout commit ou push.
