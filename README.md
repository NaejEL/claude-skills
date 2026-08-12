# claude-skills

Skills globaux [Claude Code](https://code.claude.com/docs) personnels, versionnés pour être réutilisés sur plusieurs machines (Windows / Linux / macOS).

## Installation

Cloner le dépôt puis lier les skills dans `~/.claude/skills` :

```powershell
# Windows (jonctions, sans droits admin)
.\install_skills.ps1
```

```bash
# Linux / macOS (liens symboliques)
./install_skills.sh
```

Les scripts sont idempotents : relancer après un `git pull` ou l'ajout d'un skill ne casse rien. Les skills sont disponibles dans toute nouvelle session Claude Code.

## Skills

### `software-factory`

Initialise une **usine logicielle multi-agents** dans n'importe quel projet :

```text
/software-factory
```

Le skill détecte la stack du projet (C, C#, Python, Node, Docker, Ansible…) et génère :

| Fichier généré | Rôle |
|---|---|
| `.claude/agents/factory-planner.md` | Analyse le besoin + le code, rédige la spec, liste ses questions (lecture seule) |
| `.claude/agents/factory-builder.md` | Implémente strictement la spec approuvée, code + tests, build vert exigé |
| `.claude/agents/factory-verifier.md` | Vérification adversariale, exécute les tests, verdict JSON (jamais d'édition) |
| `.claude/skills/factory-run/SKILL.md` | Orchestrateur : Planner → gate humaine sur la spec → Builder → Verifier |
| `ci/factory.sh` + `ci/factory.ps1` | Entrée CI mince : `claude -p "/factory-run 'specs/SPEC-x.md'"` |
| `.claude/settings.json` | Règles `permissions.deny` pour économiser les tokens (fusionné) |
| `.vscode/tasks.json` | Tâches VS Code Factory (fusionné) |

Cycle d'un besoin :

```text
/factory-run "ajouter l'export CSV des rapports"
```

1. **Planner** (contexte séparé) analyse et pose ses questions — **vous êtes le Product Owner** ;
2. la spec `specs/SPEC-*.md` n'est construite qu'après **votre approbation explicite** ;
3. **Builder** (contexte frais) implémente code + tests et doit rendre un build vert ;
4. **Verifier** (contexte vierge, adversarial) exécute les tests et rend un verdict JSON ; en cas de `CHANGES_REQUESTED`, ses issues sont réinjectées au Builder — **3 itérations maximum**, puis échec explicite.

En CI : `ci/factory.sh specs/SPEC-x.md` (mode sûr `--permission-mode acceptEdits` + liste blanche d'outils) ou `--yolo` pour `--dangerously-skip-permissions`.

### `ship-pr`

Pilote le **cycle complet d'une pull request GitHub** depuis la branche courante jusqu'au merge :

```text
/ship-pr main
/ship-pr develop --rounds 2 --themes "logique;régressions"
```

1. **Préflight** : gh authentifié, remote GitHub, branche ≠ cible, working tree propre, push si nécessaire ;
2. **PR** créée automatiquement (titre + corps générés depuis les commits) ou reprise si elle existe ;
3. **Rondes de revue** (3 max, arrêt anticipé à épuisement) : 3 relecteurs parallèles en lecture seule (logique/cas limites, régressions/sites d'appel, cohérence du diff) → validation adversariale de chaque finding par un mini-agent → commentaire inline sur la PR → correctifs commités et poussés → réponse à chaque thread avec le hash du fix puis résolution ;
4. **Gate humaine** : validation explicite avant `gh pr merge --merge --delete-branch` (commit de merge, branche distante et locale supprimées).

Garde-fous anti-dérive : périmètre strictement limité au diff (pas de refacto, pas de durcissement sécurité spéculatif, pas de nitpick), « zéro finding » est une réponse acceptable, registre cumulatif empêchant un finding rejeté de ressusciter d'une ronde à l'autre.

### `legacy-audit`

Audite un **repo legacy en lecture seule** et en tire un plan d'assainissement exécutable par la factory :

```text
/legacy-audit
/legacy-audit C:/chemin/vieux-projet --categories "hygiene;qualite" --max-specs 10
```

1. **Cartographie** du repo (stack, taille, git présent ou non — l'absence de versioning est un finding) ;
2. **4 auditeurs parallèles** par familles de smells (hygiène du dépôt, portabilité/config, qualité du code, filet de sécurité : tests/doc) → **validation adversariale** de chaque finding par un mini-agent qui relit la preuve à la source ;
3. **Priorisation interactive** : nombre de jalons, critère dominant et affectation par thème décidés par l'utilisateur (AskUserQuestion) ;
4. **Livrables** : `ROADMAP-legacy.md` (jalons, estimations, dépendances) + une spec `specs/SPEC-leg-*.md` au format factory (statut proposé) par finding retenu — prêtes pour `/factory-run`.

Garde-fous : lecture seule stricte hors livrables (même un `.gitignore` manquant est un finding, pas une action), « zéro finding » est une réponse acceptable, estimation T-shirt (XS→XL, les XL sont découpés en specs chaînées), idempotent (reprise d'une roadmap existante, statuts FAIT préservés, specs jamais écrasées).

## Ajouter un skill

Créer `skills/<nom>/SKILL.md` (frontmatter `name` + `description` minimum), relancer le script d'installation, commiter.
