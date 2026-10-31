# SPEC — Fin de la Phase 1 : lots L8 à L14

Statut : APPROUVEE

## Contexte

Les lots L1 à L7 de `specs/SPEC-phase1-rebranchement.md` sont livrés : noyau `skills/_core/`, 314 tests verts, software-factory et ship-pr rebranchés. Cette spec livre le reste, **tel que décrit dans la grande spec**, sections « 2. Rebranchement, skill par skill » et « Découpage en lots ». Ses Décisions (X1 à X11) priment.

## Périmètre

- **L8** : code-index. Le correctif D8 (`rgkb init` écrase `config.json`), puis le rebranchement sur le noyau (CX-01 à CX-16, BK-02).
- **L9** : ai-lab et le lab-run qu'il génère (AL, LR, C2), avec les modèles par le noyau.
- **L10, L11, L12** : ai-lab-audit, legacy-audit et vibecode-audit, rebranchés sur le moteur `hcore/audit.py` (AA, LA, VA). Le journal est écrit dans `.harness/runs/` (X5).
- **L13** : brainstorm (BS). Aucune écriture avant sa gate finale.
- **L14** : README (paragraphe par skill rebranché), mise à jour du §8 du BACKLOG, `sf copy-core --refresh` de `.claude/harness/`.

## Critères d'acceptation

- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passe.
- Chaque skill rebranché appelle le noyau pour ses règles déterministes, et chacune de ces règles a un **test de comportement** dans `skills/_core/tests/`.
- Le comportement observable de chaque skill est inchangé, sauf le journal et les décisions X1 à X11.
- `bash -n install_skills.sh` passe. `install_skills.*` ne change pas.

## Règles de frugalité (impératives)

- Aucun test qui lit de la prose de SKILL.md : pas de grep de phrases, pas de comptage ni de largeur de lignes.
- Pas de campagne de mutation.
- Le Verifier ne remonte que les défauts **majeurs**, c'est-à-dire ceux qui provoquent une erreur ou un comportement faux. Les mineurs vont dans le §8 du BACKLOG, jamais dans une itération.
- Code, commentaires et chaînes en anglais. Prose Markdown en français.

## Hors-périmètre

Phases 2 à 7, et tout commit ou push.
