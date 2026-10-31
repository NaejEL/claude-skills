# Fixtures

- `toy-project/` : projet jouet minimal (Node, sans dependance) pour la recette R2
  (`/software-factory` puis un cycle `/factory-run` sur `specs/SPEC-somme.md`) et pour les
  rejeux scriptes de `skills/_core/tests/`.
- `merge-input/` : fichiers existants d'un projet deja configure (`settings.json`,
  `tasks.json`, `gitignore.txt` copie en `.gitignore`), entree des tests SF-01 a SF-03.
- `merge-expected/` : resultat attendu de la fusion de software-factory sur `merge-input/`
  pour la stack `node` (comparaison sur le JSON parse, ordre des cles compris).
- `audit/` : rejeux scriptes du moteur d'audit (`skills/_core/tests/test_audit.py`) :
  `<skill>.json` (sorties figees des auditeurs et des validateurs, choix du skill),
  `<skill>.expected.md` (livrable attendu), `skeletons.json` (lignes de structure des
  squelettes de livrable a BASE1 `031df12`), `resume/` (roadmap et spec existantes pour
  la reprise). Les livrables n'y portent pas leur vrai nom (`ROADMAP-legacy.md`,
  `AUDIT-*.md`), que le `.gitignore` du depot ignore.

Les fichiers de configuration n'y portent pas leur nom pointe (`.gitignore`, `.claude/`)
pour ne pas agir sur ce depot ; les tests les copient sous leur vrai nom dans un dossier
temporaire.
