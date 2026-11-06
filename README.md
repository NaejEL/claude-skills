# claude-skills

Personal global [Claude Code](https://code.claude.com/docs) skills, versioned so they can be reused across several machines (Windows / Linux / macOS).

## Install

The `harness` plugin is the only install route. The repository is its own marketplace (`.claude-plugin/marketplace.json`, source `./`):

```bash
claude plugin marketplace add <repository-path-or-url>
claude plugin install harness@harness
```

The skills are exposed as `/harness:<skill>`; the short form (`/ship-pr`) works too. For development: `claude --plugin-dir <repository>`.

The plugin cache is keyed by `version` (`.claude-plugin/plugin.json`): any change under `skills/` requires a `version` bump, otherwise `claude plugin update` answers "already at the latest version". A guard checks this (`harness.py plugin version-guard`, the `plugin-guard` scenario of `ci/test-harness.*`).

`ripgrep`, required by `code-index`, is installed by `/code-index` on first use (it asks first).

### Migrating from the link install

Earlier versions linked each skill into `~/.claude/skills` with `install_skills.*` (removed in 3.0.0). Remove those links before installing the plugin, otherwise each skill appears twice. The commands below remove **only** the links that point into this clone and never follow them; a foreign link or a real folder is left alone. Replace `<clone>` with the path of this repository.

```powershell
# Windows (PowerShell)
$skills = '<clone>\skills\'   # keep the trailing backslash: a sibling folder such as skills-x must not match
Get-ChildItem "$HOME\.claude\skills" -Force | Where-Object { $_.LinkType } | ForEach-Object {
  $target = @($_.Target)[0]
  if ($target -and $target.StartsWith($skills, [StringComparison]::OrdinalIgnoreCase)) {
    [System.IO.Directory]::Delete($_.FullName, $false)
  }
}
```

```bash
# Linux / macOS
clone=<clone>
find ~/.claude/skills -maxdepth 1 -type l | while read -r l; do
  case "$(readlink "$l")" in "$clone"/skills/*) rm "$l" ;; esac
done
```

## Skills

### `software-factory`

**Single** entry point for installing a multi-agent factory in any project. It detects the applicable **profiles** (see "Profiles"), installs the factory of each one and records the selected profiles in `.claude/harness.json`:

```text
/software-factory
/software-factory --profile "software;research"
/software-factory --rescan
/software-factory --upgrade
```

`--profile` forces the profiles and skips the scout; `--rescan` reruns the scout and only proposes **additions** (a profile that has disappeared is reported, never removed). Without options, an already equipped project is read back from `.claude/harness.json` (or deduced from its generated files) with no new scout.

The skill detects the project's stack (C, C#, Python, Node, Docker, Ansible…) and generates:

| Generated file | Role |
| --- | --- |
| `.claude/agents/factory-planner.md` | Analyses the need + the code, writes the spec, lists its questions (read-only) |
| `.claude/agents/factory-builder.md` | Strictly implements the approved spec, code + tests, green build required |
| `.claude/agents/factory-verifier.md` | Adversarial verification, runs the tests, JSON verdict (never edits) |
| `.claude/skills/factory-run/SKILL.md` | Orchestrator: Planner → human gate on the spec → Builder → Verifier |
| `ci/factory.sh` + `ci/factory.ps1` | Thin CI entry: `claude -p "/factory-run 'specs/SPEC-x.md'"` |
| `.claude/settings.json` | `permissions.deny` rules to save tokens (merged) |
| `.vscode/tasks.json` | Factory VS Code tasks (merged) |

Lifecycle of a request:

```text
/factory-run "add CSV export of the reports"
```

1. **Planner** (separate context) analyses and asks its questions — **you are the Product Owner**;
2. the spec `specs/SPEC-*.md` is only built after **your explicit approval**;
3. **Builder** (fresh context) implements code + tests and must deliver a green build;
4. **Verifier** (blank context, adversarial) runs the tests and returns a JSON verdict; on `CHANGES_REQUESTED`, its issues are fed back to the Builder — **3 iterations maximum**, then an explicit failure.

The spec format uses English keywords (`Status:` with `PROPOSED`/`APPROVED`/`BLOCKED`/`DELIVERED`, `Blocking questions:`, `Files scope:`, `Priority:`, `Depends on:`, `Answer:`, `Default:`, `none`, `## Open questions`); the core writes English. The former French forms (`Statut :`, `PROPOSEE`/`APPROUVEE`/`BLOQUEE`/`LIVREE`, `Questions bloquantes :`, `Périmètre fichiers :`, `Priorité :`, `Dépend de :`, `Réponse :`, `Défaut :`, `aucune`, `## Questions ouvertes`) are still accepted when reading (read-only compatibility).

In CI: `ci/factory.sh specs/SPEC-x.md` (safe mode `--permission-mode acceptEdits` + tool allowlist) or `--yolo` for `--dangerously-skip-permissions`.

### `harness-doctor`

Diagnoses the harness installation of a project, or of a tree of projects. In a project, it compares the installed version with that of the claude-skills repository (commits behind), reports divergent blocks (`edited`, `outdated`), missing files, rgkb hooks that are declared but absent, a missing `models.json`, an unauthenticated `gh` and new profiles (it **proposes** `--rescan`, without running it), then proposes `--upgrade`: it runs it (through the Skill tool, `software-factory` then `code-index`) when the diff only touches blocks and the autonomy policy allows it.

```text
/harness-doctor
/harness-doctor --scan ~/projects --depth 3
```

With `--scan <root>`, one line per equipped project: installed version, lag, last cycle, upgrade command. The scan is read-only and never runs an upgrade.

### `ship-pr`

Drives the **complete lifecycle of a GitHub pull request** from the current branch to the merge:

```text
/ship-pr main
/ship-pr develop --rounds 2 --themes "logic;regressions"
```

1. **Preflight**: gh authenticated, GitHub remote, branch ≠ target, clean working tree, push if needed;
2. **PR** created automatically (title + body generated from the commits) or resumed if it exists;
3. **Review rounds** (3 max, early stop when exhausted): 3 parallel read-only reviewers (logic/edge cases, regressions/call sites, diff consistency) → adversarial validation of each finding by a mini-agent → inline comment on the PR → fixes committed and pushed → reply to each thread with the fix hash, then resolution;
4. **Human gate**: explicit approval before `gh pr merge --merge --delete-branch` (merge commit, remote and local branches deleted).

Anti-drift safeguards: scope strictly limited to the diff (no refactoring, no speculative security hardening, no nitpicks), "zero findings" is an acceptable answer, cumulative registry preventing a rejected finding from resurfacing from one round to the next.

### `factory-queue`

Lists the specs in `specs/` with their derived status (proposed, blocked, in progress, delivered, merged), their dependencies (`Depends on:`) and their `Priority:`, then, with `run`, runs them one after the other: each eligible spec is handed to a headless child process (`claude -p "/factory-run <spec> --ship <target>"`, fresh context), whose PR is merged before moving on to the next. `run` requires the `auto` policy; a stopped child stops the queue. No other state is needed: everything is deduced from `Status:`, git and `.harness/runs/`.

```text
/factory-queue
/factory-queue run [--only "SPEC-a.md;SPEC-b.md"] [--target main] [--autonomy auto]
```

### `factory-batch`

Builds several specs **in parallel** (`--parallel N`, default 2, cap 4), each in a git worktree created and tracked by the harness, then delivers them **one at a time**: rebase of the local branch onto the target, `ship-pr`, merge, collection of the worktree's logs, removal. A non-trivial conflict stops the batch (type `conflict`) and keeps the worktree. Cannot be invoked by another skill.

```text
/factory-batch specs/SPEC-leg-*.md --parallel 3 --autonomy auto
/factory-batch --resume <id>
```

#### Coexistence with your worktrees

The harness never touches the main worktree or the ones you create yourself (i3, Orca, `git worktree add`). It only creates `factory/<slug>` worktrees under `<repository>.harness-wt/`, records them in a registry shared by all worktrees (`<git-common-dir>/harness/worktrees.json`, not versioned), and only operates on a path that is **both** in the registry **and** listed by `git worktree list --porcelain` with the recorded branch. Never `git worktree prune`, `remove --force`, `move`, `lock` or `unlock`. `git worktree list` is the only way to see its own; `/factory-run --worktree` builds a spec in a dedicated worktree, removed after the merge. Prerequisite: `.claude/harness/` and `.claude/settings.json` must be committed on the target branch.

### `audit`

**Unified, read-only** audit of a project: mapping, one auditor per lens, adversarial validation of each finding, interactive prioritisation, then **a single `AUDIT.md` deliverable** and `specs/SPEC-*.md` specs in the factory format.

```text
/audit
/audit C:/path/project --profile software --lenses "security;scalability" --max-findings 10
/audit --profile research --max-questions 4
```

Lenses come from the active profiles: `software` (`legacy` set: hygiene, portability, quality, safety net; `vibecode` set: access, injection, business logic, maintainability, scalability) and `research` (fidelity, validity, leaks, biological analogies, roadmap). `--lenses` accepts lens or axis names (`security` = access, injection, business logic); at most 5 auditors in parallel, in waves. `AUDIT.md` groups the header (profiles, lenses, complete or sampled), the sections of each set and a "Next steps" section; the old deliverables (`ROADMAP-legacy.md`, `AUDIT-vibecode.md`, `AUDIT-lab.md`) are **imported once** (`<!-- harness:import … -->` line, statuses `FAIT`, `EN_COURS`, `TRANCHEE` preserved), never modified or deleted. Idempotent: same inputs, same `AUDIT.md`.

### `legacy-audit`

**Alias** skill of `/audit --profile software` limited to the `hygiene`, `portabilite`, `qualite`, `filet` lenses (`--categories` becomes `--lenses`), kept during version 2.0.0 then removed. Writes `AUDIT.md` and the `SPEC-leg-*` specs.

### `vibecode-audit`

**Alias** skill of `/audit --profile software` limited to the vibecode lenses (`--axes` expanded into lenses), kept during version 2.0.0 then removed.

### `ai-lab`

**Alias** skill of `/software-factory --profile research`, kept with no deadline "so as not to break anything". Installs the **AI research lab** (`research` profile): Research Director, neuroscience and maths experts, Builder, Verifier, the `/lab-run` skill (second instance of the orchestrator template, `research` profile enforced), `ci/lab.*`, the core copy and the per-role model assignment (`.claude/models.json`, `lab.*` keys). On a project already equipped with the `software` profile, `research` is **added** to the `.claude/harness.json` stamp, nothing is removed.

```text
/ai-lab
/lab-run "does iterated CA3 reading improve paraphrase recall?"
/lab-run next
```

### `ai-lab-audit`

**Alias** skill of `/audit --profile research` (lenses `fidelite`, `validite`, `fuites`, `bio`, `route`), kept during version 2.0.0 then removed. The `Q-*` questions are launched with `/factory-run --profile research "<question>"`.

### `brainstorm`

Thinks an idea through with you by **challenging** it instead of validating it, and **stops**:

```text
/brainstorm "set up a technical audit offer for SMEs"
/brainstorm "replace our message queue with polling" --rounds 2
```

1. **Anchoring** of the topic on the current directory, hard budget of 12 files read — reconnaissance cut short and flagged if the topic has nothing to do with the directory; resumption of an earlier `BRAINSTORM-<slug>.md` so that an already discarded lead is not proposed again;
2. **5 parallel lenses in a blank context** each round (implicit assumptions, radical alternatives, counter-examples and edge cases, cost and feasibility, second-order effects) — each lead marked `[énoncé]` or `[hors énoncé]`, at least one out-of-statement lead required per round;
3. **Human gate each round** (AskUserQuestion): dig into / discard / amend each angle, the next round starts from your answers;
4. **Convergence**: synthesis in the conversation (idea after confrontation, retained angles, discarded angles with their reason), then a final gate offering to write it to `BRAINSTORM-<slug>.md` — if you decline, nothing is written.

**Termination condition**: hard cap of **3 rounds** (`--rounds N` bounded to `min(N, 3)`), forced move to convergence at the cap, observable early exit as soon as a round produces no new out-of-statement angle, and **5 retained leads at most** in the synthesis. The final report suggests `/factory-run` or `/lab-run` when a retained angle is implementable, without ever launching the command. Explicit error stop in headless execution: the skill is inherently interactive.

Rewired onto the `_core` core (`hcore/bs.py`): arguments and round cap, validation of the lenses' JSON, single retry of a silent lens (which disables the round's early exit), early exit, cap of 5 retained leads, slug, resumption and rendering of the synthesis are tested code. **No write before the final gate**: the core is stateless and the session passes it its own state on standard input; the journal is written with the synthesis.

### `code-index`

Installs a **local knowledge server backed by ripgrep** in the current project, and wires the factory or lab already present to it:

```text
/code-index
/code-index --reindex
/code-index --no-wire
```

The server (`.claude/rgkb/rgkb.py`) is a standard-library Python program with **no dependency to install**; only `rg` must be available. It is exposed in two equivalent ways: a **stdio MCP server** declared in `.mcp.json` (tools `mcp__rgkb__search`, `definition`, `symbols`, `neighbors`, `file_card`, `notes`, `note_add`, `status`, `reindex`) and a **CLI** usable from Bash as well as headless.

Everything lives under `.knowledge/`, **versioned in the repository** — that is the point: a `git clone` passes the knowledge base from one user to another, with nothing to rebuild.

| File | Role | Truth |
|---|---|---|
| `config.json` | index scope (globs, exclusions, caps) | source |
| `config.local.json` | machine-specific settings, **the only unversioned file** | source |
| `notes.jsonl` | notes written by humans and agents | source |
| `files.jsonl` / `symbols.jsonl` | indexed files, definitions found by ripgrep | derived |
| `graph.json` | file → mentioned symbol edges | derived |
| `index.sqlite` | query cache, rebuilt from the text | derived |

The sources are **text, one line per item**: a git conflict can be read and merged. `index.sqlite` is declared binary in `.knowledge/.gitattributes` — on a conflict take either side and rerun `index --force`, which regenerates it from the sources. A reindex with no code change produces **no diff**.

**Index freshness.** During a `/factory-run` or `/lab-run` cycle, it is automatic: check before the first phase that spends, reindex by the Builder after its changes. Outside a cycle, **git hooks** take care of it:

```text
python .claude/rgkb/rgkb.py hooks install --with-commit
python .claude/rgkb/rgkb.py hooks status
python .claude/rgkb/rgkb.py hooks remove
```

`post-merge` (hence `git pull`) and `post-rewrite` (rebase) reindex after the fact; `--with-commit` adds `pre-commit`, which reindexes and stages `.knowledge/`, so that **every commit carries an index consistent with its code**. The hooks only write if the content has changed and never make a git operation fail; `RGKB_NO_HOOK=1 git pull` neutralises them once. An existing hook is completed with a delimited block, never overwritten. `.git/hooks/` is not versioned, but the **intent** is: `hooks install` writes `"hooks": "commit"` in `.knowledge/config.json`, and any `status` or `index` reconciles the local hooks with it. A user who clones therefore gets them on the first cycle, without running anything. `rgkb.py init` never rewrites an existing `config.json`, and `hooks install` never replaces an unreadable `config.json`.

`post-checkout` is **deliberately absent**: reindexing after a branch switch dirties the tree every time and git refuses the next checkout. With `pre-commit`, it has nothing to do anyway.

The wiring (unless `--no-wire`) adds to the existing agents a delimited, re-entrant `<!-- rgkb:debut -->` / `<!-- rgkb:fin -->` block, without ever rewriting their prompt: file card before reading a whole file, reading the notes before forming an opinion, reindex after modification for the Builder, and at the final logging of a cycle a note proposal (1 to 3 per cycle, never what the index finds on its own). `/software-factory` and `/ai-lab` offer to install it at the end of their run (Phase 6b), always with explicit agreement.

The skill relies on the `_core` core (`hcore/cx.py`) for everything deterministic: arguments, the `rg` install command, repository state, versioned copy of the server, merging of `.mcp.json`, `settings.json`, `tasks.json` and the `config.json` exclusion, re-entrant blocks, `tools` and `--allowedTools` completed without removing anything. It requires Python ≥ 3.9.

## Autonomy policy

The `autonomy` key of `.claude/harness.json` is `gate` (every human decision is asked) or `auto` (default installed by `/software-factory`). The skills' `--autonomy gate|auto` option overrides it for one run, without ever writing the stamp; the effective policy is passed on to chained skills. In `auto`, a type (b) or (c) gate takes its justified default, logged (the justification is in the skill that raises the gate and in `harness.py gate list`); a type (a) gate is evaluated on its stop condition. An `auto` loop asks nothing beyond its stop conditions: `BLOCKED` spec (blocking question with no default), three iterations without approval, agent dead twice, repeated scope drift, destructive operation, secret, failed child, gate with no default.

Each stop writes a `.harness/runs/STOP-<timestamp>.md` file (in English, 40 lines at most: where, why, how to resume, the exact command), a `stop` event in the journal, and exits with code 1; the harness never deletes them. The chains: `/audit` → `/factory-queue run` (the specs written, in the computed priority order), `/factory-run` → `/ship-pr` (delivery commit then PR), and `/ship-pr` merges **without asking** if five conditions are true (no validated finding left, all threads resolved, CI green, target not protected, no conflict), posting the decision as a PR comment; otherwise the PR stays open. `/brainstorm` launches nothing. This repository stays in `gate`: the harness does not modify itself in autonomy.

## Hooks

`/software-factory` installs in `.claude/settings.json` (additive merge, your hooks and comments are kept) three stdlib Python hooks, copied with the core under `.claude/harness/hooks/`: a **permanent** Bash/PowerShell safety net that blocks `git push --force`, branch deletion, history rewriting, destruction of uncommitted work and file deletions outside generated artifacts (it is a best-effort net, not a proof: run the intended operation yourself in a terminal); during `/factory-run`, the check of the spec's `Files scope:` (the second drift stops the cycle); during `/ship-pr`, the restriction to the PR's diff; and, if the project configures a linter (`hooks.lint` in `.claude/harness.json`), a verification `PostToolUse`, never blocking. An internal error in a hook lets the action through and says so. The hooks only take effect in the next session (or after review in `/hooks`).

## Profiles

A **profile** is a data folder under `skills/_core/profiles/<name>/` (`profile.json` manifest plus Markdown fragments: roles, lenses, orchestrator, detection); it contains no code. Two profiles are shipped: `software` (software factory, fallback profile) and `research` (AI research lab). Adding a profile = adding a folder; `harness.py profile validate <folder>` checks it (schema: `skills/_core/profiles/SCHEMA.md`).

A `harness-scout` agent (read-only Explore sub-agent, economical model) detects the applicable profiles: the core collects the deterministic signals and verifies the agent's evidence. The selected profiles are recorded in `.claude/harness.json` (`profiles` key); the core only adds. A clear proposal is taken by default in `auto` autonomy, an ambiguous proposal stops with the `--profile` resume command.

## Upgrading an equipped project

Each equipped project carries a **versioned** `.claude/harness.json` stamp: version of the claude-skills repository that produced it (git tag or hash), date, installed skills and their options, autonomy policy, active profiles, generated files with the hash of their blocks (`skills/_core/STAMP.md`). Each generated file starts with a `harness: claude-skills <version>` header, followed by **delimited blocks** (`harness.frontmatter`, `harness.body`, `harness.profile.<name>`, `harness.ci`, `rgkb`); everything outside a block belongs to the user.

```text
/software-factory --upgrade [--convert]
/code-index --upgrade
/harness-doctor
```

`--upgrade` only regenerates the blocks, preserves everything outside blocks (invariant checked before writing), migrates the formats (`lab-models.json` to `models.json`, old run registries to `.claude/findings.jsonl`), updates the `.claude/harness/` core copy in the same plan as the blocks of all profiles, **shows the full diff** then applies it, all or nothing, with a backup under `.harness/runs/upgrade-<timestamp>/backup/`. It is idempotent: rerun with no change, it produces no diff. A file generated before the core (without blocks) is converted losslessly if it has stayed as generated or has only received an addition at the end of the file; otherwise the `upgrade.convert` gate offers to keep it (default) or to convert it with a backup (`--convert` for all). A project without a stamp is detected by its generated files, and the stamp is created at the first upgrade. No rollback: a project installed by a harness newer than the repository is refused.

## The `skills/_core/` core

`skills/_core/` is not a skill (it has no `SKILL.md`): it is the shared deterministic core, in standard-library Python (≥ 3.9), exposed by a single `harness.py` CLI and tested by `py -3 -B -m unittest discover -s skills/_core/tests` (or `python3`). It carries what is not a matter of judgement — parsing of verdict JSON blocks, iteration and round counters, retry of a dead agent, file merges, `ship-pr`'s `gh`/`git` sequences, and for all skills: the **gate** primitive (autonomy policy, gate catalogue, headless fallback), the single **finding** schema (adapters, validator, conversions to spec, note or comment) with its local project registry **`.claude/findings.jsonl`** (excluded from git, one line per finding), **stack** detection and its bounds, **tshirt** sizes and sorts, per-role models (`.claude/models.json`, with migration from `lab-models.json`), the common audit engine — and writes the cycle journal `.harness/runs/<skill>-<timestamp>.jsonl`, excluded from git. The plugin ships it next to the skills, where `ship-pr` calls it through `${CLAUDE_SKILL_DIR}/../_core`; `software-factory` copies it into each equipped project under `.claude/harness/` (with a `MANIFEST.json`, and `history.json` which recognises its successive states: `harness.py core history --check`), which the generated `/factory-run` and the CI call.

## Testing the harness

Two levels of tests:

- **Unit tests** of the core: `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` (isolated rules, fixtures in `tests/fixtures/`).
- **End-to-end scenarios**: `bash ci/test-harness.sh` or `pwsh ci/test-harness.ps1`. A shared Python runner (`ci/scenarios/`, standard library only) replays, in temporary folders, the sequence of core calls prescribed by the SKILL.md files and the generated orchestrator, on the toy projects in `ci/fixtures/`. The agents are simulated (frozen outputs, the Verifier runs the project's real tests), `gh` is the fake `skills/_core/tests/fake_gh.py` on top of a local bare repository, and `claude` is never called: shims at the head of the PATH count any call to the real `gh` or `claude` (`real_gh_calls`, `real_claude_calls` in the report).

| Scenario | What it verifies |
| --- | --- |
| `install-fresh` | fresh install of `/software-factory` on a Python project |
| `plugin-guard` | plugin version guard (change under `skills/` without a `version` bump), effective name of a skill in both modes |
| `plugin-validate` | `claude plugin validate .` (SKIP without `claude`) |
| `upgrade-legacy` | `--upgrade` of a project installed the old way, out-of-block customisations kept |
| `factory-auto` | full `factory-run` cycle in `auto` up to the Verifier, and counter-test of a blocking question |
| `stop-iteration3` | clean stop at the 3rd iteration (`STOP-*.md`) |
| `shippr-automerge` | `ship-pr` with no finding: automatic merge, and the refusals (red CI, protected branch, silent theme) |
| `hook-diff` | `ship-pr`'s PreToolUse hook blocks outside the diff, executed through the `settings.json` line |
| `models-absent`, `models-legacy` | missing `models.json`, migration of `lab-models.json` |

Options: `--list [--verbose]`, `--scenario <id>` (repeatable), `--live`, `--keep`, `--fixtures <folder>`, `--report <file>` (PowerShell: `-List`, `-Details`, `-Scenario`, `-Live`, `-Keep`, `-Fixtures`, `-Report`). One `PASS|FAIL|SKIP <id> <duration>` line per scenario; exit code 0 (all `PASS` or justified `SKIP`), 1 (a `FAIL`, or `--live` without `claude`), 2 (unknown option or scenario). Under Git Bash without native symbolic links, `install-skills` is `SKIP` (Windows coverage goes through the PowerShell launcher).

`--live` adds `live-install`, `live-factory` and `live-hook`: the real `claude -p` (`--max-turns`, tool allowlist, never the permission bypass), with structural assertions only. It consumes the subscription and is never run by default. The real `ship-pr` remains a manual recipe on a disposable GitHub repository.

**`claude plugin eval` does not carry these scenarios** (BACKLOG §5): it can prepare a fixture, but no grader executes a shell command, whereas every expected result here is a state observable by command (exit code, bytes of a file, git state, state of the fake `gh`, journal). It also assumes a plugin, which Phase 7 had not decided. It remains worth revisiting for LLM-judged evaluations (spec quality).

## Adding a skill

Create `skills/<name>/SKILL.md` (frontmatter `name` + `description` minimum), bump `version` in `.claude-plugin/plugin.json`, commit.
