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

## Ajouter un skill

Créer `skills/<nom>/SKILL.md` (frontmatter `name` + `description` minimum), relancer le script d'installation, commiter.
