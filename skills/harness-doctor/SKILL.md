---
name: harness-doctor
description: Diagnoses a project's harness installation (software factory, lab, knowledge base) — installed version against that of the claude-skills repository, diverging blocks, missing files, missing rgkb hooks, missing models.json, unauthenticated gh, new profiles — and proposes `--upgrade`; with `--scan <root>`, one line per equipped project (version, lag, last cycle). Use when the user asks about the state of their harness, an update, or an inventory of their equipped projects.
user-invocable: true
argument-hint: "[--scan <root>] [--depth N] [--autonomy gate|auto]"
---

# Harness doctor — state and update of equipped projects

Diagnose the harness installation of the current project, or of a tree of projects with `--scan`. This skill **modifies nothing** itself: it reads, reports, proposes, and only launches an update through the `software-factory` and `code-index` skills (`--upgrade`).

## Deterministic core

All the rules are Python code (standard library, ≥ 3.9) in `${CLAUDE_SKILL_DIR}/../_core/`: never reimplement them, call the CLI and follow its JSON output. Rules: **VS** (`version.py`), **DR** (`doctor.py`), **SN** (`scan.py`), **UP** (`upgrade.py`), **PR** (proposals), **GT-09**, **JR-04**.

**Interpreter** (rule D5, `hcore/interp.py`): `<PY>` = the first of `python`, `python3`, `py -3` that answers in under 5 s with a version ≥ 3.9; in practice `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" interp` under each of these three simple commands, the first that returns `command`. No candidate → stop. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`. The core used is **the repository's** (global), never the project's copy: it is the one that knows the current version.

## Project mode (no argument)

1. `K doctor --root .` returns a JSON: `equipped` (`stamp`, `inferred` or `none`), `version` (installed, repository, lag: `up_to_date`, `behind`, `ahead`, `diverged`, `unknown`), `core` (copy `.claude/harness/`, `mixed`, `customized`), `blocks` (each block `ok`, `edited`, `outdated`, `edited+outdated` or `missing_block`), `legacy_files`, `missing`, `hooks`, `models`, `gh`, `signals`, `upgrade` (`changes`, `blocks_only`, `by_skill`), a `status` `ok`/`warn`/`error` per check, and `proposal`. `none` project: say so (`/software-factory` installs) and write nothing.
2. Present the report per check, with the status and, for each anomaly, the cause and the remedy in one line:
   - `edited`: block modified by hand, it will be replaced by the upgrade (backup); customization is done **outside the block**;
   - `hooks.missing`: `post-merge`, `post-rewrite` (and `pre-commit`) declared in `.knowledge/config.json` but missing — the `code-index` upgrade reinstalls them;
   - `models.migration_available`: `lab-models.json` to migrate, which `--upgrade` does;
   - `gh`: `gh auth login`;
   - `signals.propose_rescan`: **propose** `/software-factory --rescan`; never launch it.
3. **Upgrade proposal** (PR-01): if `upgrade.changes` is not null, `proposal.gate` is `harness-doctor.upgrade-blocks` (the diff only touches blocks, union merges, the core copy and the stamp) or `harness-doctor.upgrade-other` (conversions, recreated files, migrations). `proposal.decision` says whether to `ask` or `default`.
   - Gate `harness-doctor.upgrade-blocks` (options "Run the upgrade" / "Do nothing", default **Run**); gate `harness-doctor.upgrade-other` (same options, default **Do nothing**: report the command and the classes of `proposal.blockers`). `K gate decide --root . --id <gate>` then, after AskUserQuestion, `K gate answer --run <run> --id <gate> --answer-file …` (answer written by Write); without interaction (headless) `--headless`, `default` fallback.
   - **`auto` policy** (UA-01, UA-02): `K upgrade plan --root . --skill software-factory --interpreter "<PY>"` (then `code-index`) writes the plan without touching the project, and `K doctor auto-upgrade --plan <plan.json> --autonomy auto` returns `action`: `apply` (non-empty plan where every change is a block, a union merge, the core copy or the stamp, with no diverging block) → launch the upgrade without asking; `propose` → launch nothing, show the command and the changes at issue (`causes`); `none` → nothing to do (a second pass after upgrade gives an empty plan, UA-04). In `gate`, `action` = `ask`: raise the gate `harness-doctor.upgrade`. The change of `autonomy` (absent key) is never a block: visible in the diff, never applied by this path.
4. If the upgrade is launched: obtain the effective name of each skill with `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" plugin skill-name --skill <skill> --skill-dir "${CLAUDE_SKILL_DIR}"` (field `name`: `harness:<skill>` from the plugin, `<skill>` otherwise), then invoke with the Skill tool `software-factory` with the argument `--upgrade` then, in this order, `code-index` with `--upgrade`, each **only if its plan is not empty** (`proposal.commands`). If a skill invocation through the Skill tool fails, show the commands to run, with no automatic launch. Then rerun `K doctor --root .`: the final report shows `upgrade.changes` at 0.

The doctor only writes its journal `.harness/runs/harness-doctor-<timestamp>.jsonl` (`doctor` and `gate` events).

## `--scan <root> [--depth N]` mode

`K doctor scan --root <root> [--depth N]` (depth 3 by default; `N` integer ≥ 0, otherwise exit 2) returns one JSON line per equipped project, sorted by path: `path`, `equipped_by`, `skills` (installed version per skill), `lag` (`status`, `commits`), `last_cycle` (skill, date, verdict, from the timestamp **in the name** of the journal), `next` (the upgrade command if the project is behind). Show **one table line per project**. The scan is strictly read-only and **never** launches an upgrade, even in `auto` (UA-03): one line per project, give the `next` command to run in the project concerned.

## Mandatory rules

- Never modify a project file other than through the upgrade skills; never call `K upgrade apply` from this skill.
- Never launch `--rescan`: only propose it.
- All gates go through `K gate decide` / `K gate answer`, never decided by hand.

## Defaults under the `auto` policy (AP-09)

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to `K gate decide --autonomy` and to chained skills (AP-04). Default of each gate of this skill under `auto`, with its one-line justification (the one from the `K gate list` catalog):

- `harness-doctor.upgrade-blocks` → Run the upgrade — roadmap 4.2: a diff that only touches harness blocks is applied
- `harness-doctor.upgrade-other` → Do nothing — roadmap 4.2 reserves the automatic launch to diffs of blocks
- `harness-doctor.upgrade` → Run the upgrade — applied when UA-01 holds (blocks, stamp or untouched core only), otherwise proposed
