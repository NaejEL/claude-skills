# SPEC — Phase 7 : distribution en plugin `harness` (étapes M1 à M3)

Statut : LIVREE
Questions bloquantes : aucune
Périmètre fichiers : .claude-plugin/**, skills/**, ci/**, install_skills.sh, install_skills.ps1, README.md, specs/harness-v2/BACKLOG.md, specs/harness-v2/ETUDE-packaging-plugin.md, .claude/harness/**, tests/fixtures/**

## Contexte

L'étude `specs/harness-v2/ETUDE-packaging-plugin.md` et ses recettes (section « Résultats des recettes ») sont la référence. Ces recettes ont établi les points suivants :
- le nom `claude-skills` est réservé, et l'utilisateur a choisi **`harness`** ;
- le noyau répond depuis le plugin ;
- la forme courte `/ship-pr` fonctionne aussi en headless ;
- le cache est indexé par version.

Décision de l'utilisateur : migrer selon les étapes M1 à M3 de l'étude. M4, le retrait d'`install_skills.*`, est hors périmètre.

## Périmètre

- **M1 — Manifestes et garde de version :**
  - créer `.claude-plugin/plugin.json` (`name: "harness"`, `version: "2.0.0"`, `description`, `author`) et `.claude-plugin/marketplace.json` (source `./`) ;
  - ajouter une garde de version déterministe : tout changement sous `skills/` après le dernier commit qui a modifié `version` fait échouer la garde, tant que `version` n'est pas relevée. Elle est branchée dans `ci/test-harness.sh|.ps1` ;
  - ajouter un scénario `ci/` qui lance `claude plugin validate .` quand `claude` est disponible, et qui est SKIP sinon.
- **M2 — Indépendance au mode d'installation :**
  - le tampon et `/harness-doctor` lisent la version dans `.claude-plugin/plugin.json` quand il existe, avec repli sur git ;
  - le noyau fournit le nom effectif d'un skill pour l'outil Skill (`harness:<skill>` quand le skill tourne depuis un plugin, `<skill>` sinon). Les alias (AX-01, AX-04) et les enchaînements de la Phase 4 l'utilisent ;
  - les textes destinés à l'utilisateur gardent la forme courte (P3).
- **M3 — Double voie :**
  - `install_skills.sh` et `install_skills.ps1` affichent un avertissement de retrait et la commande d'installation du plugin ;
  - ils gagnent une option `--unlink` (`-Unlink`) qui retire **seulement** les liens qu'ils ont créés vers ce dépôt ;
  - le README reçoit une section « Installer » qui décrit les deux voies.

## Critères d'acceptation

- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passe.
- `bash ci/test-harness.sh` et `pwsh -NoProfile -File ci/test-harness.ps1` passent, garde de version comprise.
- La garde a un test de comportement : un changement sous `skills/` sans hausse de version la fait échouer, et avec une hausse elle passe.
- Le nom effectif a un test de comportement, dans les deux modes.
- `--unlink` a un test de comportement dans un `HOME` temporaire : il retire les liens vers ce dépôt et ne touche à aucun autre lien ni dossier réel.
- `bash -n install_skills.sh` passe.
- `.claude/harness/` est rafraîchi par `sf copy-core --refresh`.

## Règles de frugalité (impératives)

- Ne jamais **exécuter** `install_skills.*` sur le vrai `HOME`. On les teste uniquement dans un `HOME` ou un `USERPROFILE` temporaire, comme le scénario `install-skills` de la Phase 6.
- Aucun test qui lit la prose d'un SKILL.md, et pas de campagne de mutation.
- Le Verifier lit **chaque** fichier de code nouveau ou modifié et ne remonte que les défauts **majeurs**. Les mineurs vont au §8 du BACKLOG.
- Code, commentaires et chaînes en anglais ; prose Markdown en français.

## Hors-périmètre

M4 (retrait d'`install_skills.*`), toute publication de marketplace distante, tout commit ou push.
