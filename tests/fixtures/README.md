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
- `profile-toy/` : profil minimal valide (un role, une lentille, une gate, un critere `glob`) :
  la preuve qu'ajouter un profil est ajouter un dossier.
- `profile-invalid/<cas>/` : un dossier par erreur de validation d'un profil ; les cas a deux profils
  (`duplicate-lens`, `two-fallbacks`, `duplicate-model-role`) sont des dossiers qui en contiennent deux.
- `profile-software/`, `profile-research/`, `profile-mixed/` : petits projets pour le scout et l'installation
  (application Node, PoC Python de recherche, les deux). `github/` devient `.github/`, `claude-md.txt`
  devient `CLAUDE.md` dans le dossier temporaire du test.
- `profile-extraction/` : `base2/<skill>.md` (les SKILL.md a la fin de la Phase 1, octet pour octet),
  `sections.json` (les lignes extraites sans perte dans les profils), `retired.json` (phrases retirees
  parce que la ROADMAP les contredit).
- `audit-legacy-deliverables/` : anciens livrables a reprendre (`old-roadmap.md`, `old-vibecode.md`,
  `old-lab.md`, `specs/`), stockes sous un autre nom parce que le `.gitignore` du depot ignore les vrais.
- `audit-nonreg/expected-gaps.json` : la liste exacte des ecarts attendus entre `/audit` et les anciens audits.

Les fichiers de configuration n'y portent pas leur nom pointe (`.gitignore`, `.claude/`)
pour ne pas agir sur ce depot ; les tests les copient sous leur vrai nom dans un dossier
temporaire.
