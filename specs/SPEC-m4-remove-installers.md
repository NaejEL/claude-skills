# SPEC — M4: remove `install_skills.*`, the plugin is the only install route

Status: DELIVERED
Blocking questions: none
Files scope: install_skills.sh, install_skills.ps1, README.md, ci/**, skills/**, .claude/harness/**, .claude-plugin/**, specs/harness-v2/BACKLOG.md, specs/harness-v2/ETUDE-packaging-plugin.md, .harness/tmp/**

## Context

Step M4 of `specs/harness-v2/ETUDE-packaging-plugin.md`: after M1-M3 (plugin `harness`, version guard, deprecation notice and `--unlink`), the link installers are removed; `ripgrep` is left to `code-index`, which already offers to install it under the gate `code-index.rg-install`. User decision (2026-11-06): do M4 now. The house rules of `.claude/agents/*` and `.claude/skills/factory-run/SKILL.md` were already updated by hand (no `install_skills` gate any more; never write into the real `~/.claude/`).

## Scope

1. Delete `install_skills.sh` and `install_skills.ps1` (`git rm`; this spec is the accepted scope for that deletion).
2. `ci/`: remove the scenarios that only exist for the installers (`install-skills`, `install-unlink`, their modules and registrations in `ci/scenarios/run.py`, and their fixtures if unused elsewhere). Keep `install-fresh` if it tests `/software-factory` installation and not the link installer; adapt it otherwise. Legacy fixtures that merely *mention* `install_skills` in their text (`ci/fixtures/legacy-node/**`, `tests/fixtures/**`) stay untouched: they represent old projects.
3. `README.md`, section "Install": the plugin is the only route (`claude plugin marketplace add …`, `claude plugin install harness@harness`, `--plugin-dir` for development, the version-bump rule). Drop the links route and the external-tools section; say that `ripgrep` is installed by `/code-index` on first use. Add a short "Migrating from the link install" paragraph with copy-pasteable commands that remove **only** the links of `~/.claude/skills` that point into this clone, never following them (PowerShell: entries with a `LinkType` whose target is under `<clone>\skills\`, removed with a non-recursive `[System.IO.Directory]::Delete($path, $false)`; bash: `find ~/.claude/skills -maxdepth 1 -type l` filtered on `readlink` under `<clone>/skills/`, removed with `rm` without `-r`). Remove every other README mention of `install_skills`.
4. Every remaining reference outside legacy fixtures and historical `specs/`: skills (`SKILL.md` text, e.g. `code-index` or `harness-doctor` pointing to the installers), core code and templates, tests (`skills/_core/tests/test_repo_factory.py` follows the new house rules: no `bash -n install_skills.sh` gate; the "never run install_skills" assertion becomes "never write into the real `~/.claude/`").
5. `specs/harness-v2/ETUDE-packaging-plugin.md`: one line under the migration plan saying M4 was done (date, version).
6. Version: `.claude-plugin/plugin.json` → `3.0.0` (removing an install route is a breaking change). Refresh `.claude/harness/` (`sf copy-core --refresh`, `core history --rebuild`).

## Acceptance criteria

- `git ls-files | grep install_skills` lists nothing; `git grep -n install_skills -- . ':!specs' ':!tests/fixtures' ':!ci/fixtures'` lists nothing (or only the README migration paragraph if it names the old scripts).
- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passes (module by module if over 10 minutes).
- `bash ci/test-harness.sh` and `pwsh -NoProfile -File ci/test-harness.ps1` pass, `plugin-guard` included; `claude plugin validate .` passes.
- The README migration commands are tested once, by the Builder, in a temporary `HOME`/`USERPROFILE` with: a link into the clone (removed), a link elsewhere (kept), a real folder (kept, content intact), and the clone intact afterwards. Not a unit test; report the transcript.
- `diff -rq skills/_core .claude/harness`: only `MANIFEST.json`.

## Frugality rules (mandatory)

- Scratch files under `.harness/tmp/` only.
- Never write into the real `~/.claude/` or the real `HOME`.
- No tests reading SKILL.md or README prose; no mutation campaigns.
- Verifier: reads every changed code file in full; major defects only; minor ones to BACKLOG §8.

## Out of scope

The BACKLOG §8 minors (next spec), legacy fixtures, historical `specs/` other than the ETUDE line, any commit or push.
