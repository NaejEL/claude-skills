# Fixtures des scénarios de bout en bout

Consommateur : `ci/test-harness.sh` et `ci/test-harness.ps1` (runner `ci/scenarios/run.py`). Les fixtures de la
suite unitaire restent dans `tests/fixtures/` (Q13) ; celles-ci sont des projets de scénario et des sorties
d'agents simulés. Rien n'y est dupliqué : `legacy-node` référence `tests/fixtures/toy-project` (`fixture.json`).

Convention (comme `tests/fixtures/README.md`) : aucun nom pointé, aucun `CLAUDE.md`. Le runner les renomme dans le
dossier temporaire du scénario : `claude-md.txt` devient `CLAUDE.md` ; pour `legacy-node`, `claude/` devient `.claude/`,
`vscode/` devient `.vscode/` et `gitignore.txt` devient `.gitignore` (table `renames` de `fixture.json`). Les fichiers
texte sont normalisés en LF à la copie. Le dépôt nu servant de remote n'est pas versionné : il est créé à l'exécution
sous `<tmp>/<scénario>/github.com/acme/toy.git` (`ghflow.py` exige `github.com` dans l'URL d'origine). Le dossier
`specs/` de `toy-py` est vide et créé par le scénario.

## Projets

- `toy-py/` : projet jouet Python (`toy/core.py`, un module ; `tests/test_core.py`, un test vert ; `unittest`, aucune
  dépendance). Écrit pour cette phase. Le scout attendu retient `software` seul.
- `legacy-node/` : projet « installé à l'ancienne », avant le noyau v2 (ni bloc délimité ni tampon).
  - Sources du projet : `tests/fixtures/toy-project`, par référence (`fixture.json`, `sources`).
  - Fichiers générés : octet pour octet ceux de ce dépôt au commit `7be1afb` (sortie réelle de software-factory,
    stack Bash), listés avec leur origine dans `fixture.json` (`"from": "7be1afb:<chemin>"`) : `claude/agents/factory-*.md`,
    `claude/skills/factory-run/SKILL.md`, `ci/factory.sh`, `ci/factory.ps1`, `claude/settings.json`, `vscode/tasks.json`,
    `gitignore.txt`.
  - `claude/lab-models.json` : écrit pour cette phase, au format d'ai-lab (clés sans préfixe `lab.`).
  - `customizations.json` : chaque personnalisation hors bloc semée (fichier, extrait exact, raison). Le seul écart
    entre un fichier de la fixture et son origine est l'ajout de ces extraits ; `suffix`, quand il existe, est le texte
    ajouté en fin de fichier : le runner commite d'abord le fichier sans lui, puis avec, pour reproduire l'historique
    git dont la conversion a besoin (CV-01).

## Sorties d'agents simulés (`agents/<scénario>/`, FX-05)

Écrites par le runner là où les SKILL.md prescrivent l'outil Write (`.harness/runs/`), puis passées au noyau par
`--output`. Origine : rédigées pour cette phase.

- `common/verifier.md` : gabarit du rapport du Verifier ; le runner y insère le verdict de la vraie commande de test.
- `install-fresh/scout.json` : sortie du scout au format SC-03 (aucun signal : seuls les signaux déterministes comptent).
- `factory-auto/` : besoin, spec du Planner (`SPEC-mean.md`, sans question bloquante), spec bloquée (`SPEC-blocked.md`),
  correctifs du Builder (`builder.patch`, `builder-2.patch`, appliqués par `git apply`).
- `stop-iteration3/` : spec et verdicts `CHANGES_REQUESTED` du Verifier (`verifier-1..3.md`), puis la contre-épreuve
  (`verifier-b1..b3.md` : deux refus, un Verifier mort, un accord).
- `shippr-automerge/` : correctif de la branche `feature` (`feature.patch`), sortie des relecteurs (zéro finding), titre et
  corps de la PR.
- `models-absent/SPEC-models.md` : spec approuvée rejouée sans fichier de modèles.

## Attendus (`expected/<scénario>/`, FX-06)

- `install-fresh/` : `files.txt` (fichiers créés, hors `.claude/harness/`), `settings.json` (le jeton `{RUN <hook>}` remplace la
  chaîne d'interpréteurs de chaque commande de hook : interpréteur détecté, puis `python3`, `python`, `py -3`), `tasks.json`, `gitignore.txt` ; comparaison sur le JSON parsé, ordre des clés compris.
- `stop-iteration3/stop-lines.txt` : lignes qui doivent figurer dans le `STOP-*.md`.
