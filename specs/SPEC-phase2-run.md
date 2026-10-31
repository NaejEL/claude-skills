# SPEC — Phase 2 : profils, scout, point d'entrée unique, `/audit` unifié

Statut : APPROUVEE

## Contexte

La Phase 1 est livrée : le noyau `skills/_core/` (426 tests verts) et les 8 skills rebranchés. Cette spec livre la Phase 2 **telle que la décrit `specs/SPEC-phase2-profils-audit.md`**, déjà APPROUVEE. Le détail des règles (PF, PX, HJ, SC, AR, EP, LP, AX, AD, LN, SO, MG, NR), les fixtures et les lots s'y trouvent. Ses décisions et celles de `specs/SPEC-phase1-rebranchement.md` priment.

## Périmètre

Tous les lots de la spec Phase 2, dans l'ordre de son tableau « Découpage en lots » :
- profils `software` et `research` en données, sous `skills/_core/profiles/` ;
- tampon `.claude/harness.json` ;
- scout en sous-agent dynamique ;
- arbitrage ;
- `/software-factory` comme point d'entrée unique, avec `--rescan` ;
- alias `/ai-lab` ;
- `/audit` unifié, dans un nouveau skill `skills/audit/` ;
- anciens audits gardés comme alias avec avertissement ;
- sorties dans un seul `AUDIT.md` ;
- reprise des anciens livrables ;
- non-régression sur fixtures.

## Critères d'acceptation

- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passe.
- Chaque règle déterministe nouvelle a un **test de comportement**.
- `/audit` en profil `software` retrouve sur les fixtures les findings de legacy-audit et de vibecode-audit, et `/audit` en profil `research` ceux d'ai-lab-audit. Chaque écart est listé et justifié.
- `bash -n install_skills.sh` passe ; `install_skills.*` est inchangé.
- `.claude/harness/` est rafraîchi par `sf copy-core --refresh`.

## Règles de frugalité (impératives)

- Aucun test qui lit la prose d'un SKILL.md (grep de phrases, comptage de lignes, largeur).
- Pas de campagne de mutation.
- Le Verifier lit le code nouveau ou modifié et ne remonte que les défauts **majeurs**. Les mineurs vont au §8 du BACKLOG.
- Code, commentaires et chaînes en anglais ; prose Markdown en français.

## Hors-périmètre

Phases 3 à 7, et tout commit ou push.
