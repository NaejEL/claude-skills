# Schéma d'un profil

Un profil est un dossier `skills/_core/profiles/<nom>/` : un manifeste `profile.json` (JSON strict, UTF-8) et des fragments Markdown en français référencés par chemin relatif. Aucun fichier `.py` n'y figure. Ajouter un profil = ajouter un dossier ; `harness.py profile validate <dossier>` rend exit 0 si le profil est conforme, exit 2 avec la liste des erreurs sinon.

## Clés du manifeste

- `name` : identique au nom du dossier. `schema_version`. `fallback` : booléen, un seul profil à `true`.
- `fragments` : `{orchestrator, install, scout}`, chemins de fragments.
- `roles[]` : `{name, mission (fragment), read_only, tools, model_role, model_default, agent_file}`. Deux profils ne déclarent jamais le même `agent_file`.
- `model_roles[]`, `model_presets` : rôles de modèle et préréglages déclarés par le profil (extension de MD-01 et MD-08).
- `loop` : `{max_iterations, entry_role, phases[]}`. Types de phase connus du moteur : `plan`, `consult`, `consolidate`, `gate`, `build`, `verify`, `interpret`, `record`. Un autre type est refusé.
- `artefacts[]` : `{kind, dir, glob, status_proposed, status_ready, status_done}`. Les `status_ready` forment les chaînes interdites dans les livrables d'audit (FD-11).
- `verifier` : `{required_true[], issue_kinds[]}`. `deterministic_checks[]`.
- `settings` : `{deny_by_stack, deny_generic, deny_if_present}` ; `gitignore[]` ; `tasks` : `{inputs, tasks, test_task?}`.
- `ci` : `{script, command, max_turns, status_line, logs_dir}`. `orchestrator` : `{name, alias_of}` ; `entry_keywords[]` (mots d'entrée qui routent vers ce profil).
- `gates[]` : entrées au format du catalogue (`id`, `kind`, `options`, `default`, `rationale`, `headless`, …). Les ids restent dans l'espace de noms `<orchestrateur>.`, `gate_namespaces[]` ou `audit.<profil>.`.
- `journal_names[]` : noms de journal (JR-01).
- `lens_sets[]` : `{name, lenses[], plan, deliverable_section, spec_prefix, cap_option, cap, cap_default, statuses[], gates[], fragment, map_fragment?, intro_fragment?, validator_fragment?}`.
- `lenses[]` : `name`, `prefix`, `set`, `fragment`, et les propriétés LN : `debt`, `shape`, `ordering`, `axis`, `axis_rank`, `unauditable`, `no_run`, `no_protocol`, `allowed_exec`, `journal_check`, `nature`, `size_scale`, `critical_definition`, `subagent_type`, `model_role`, `stack_agnostic`, `dedup_key`, `evidence_kinds`, `receives`, `validator_fields`, `deliverable`.
- `detection` : `{accept, reject, criteria[]}` ; un critère porte `{id, kind, weight, …}`, `kind` ∈ `glob`, `dir`, `dependency`, `content`, `judgement`. Score = somme des poids trouvés ; `retained` si score ≥ `accept`, `rejected` si score < `reject`, sinon `uncertain`.
- `audit_sections[]` : sections de `AUDIT.md` du profil (gabarits sous `templates/`).

## Fragments

`roles/<rôle>.md`, `lenses/<lentille>.md` (les fragments commençant par `_` sont partagés par un jeu de lentilles), `orchestrator.md`, `install.md`, `scout.md`.
