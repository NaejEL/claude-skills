---
name: factory-queue
description: The project's spec queue — lists the specs in specs/ with their derived status (proposed, blocked, in progress, delivered, merged), their dependencies and their priority, then, with `run`, builds and delivers each eligible spec one after another in headless child processes (factory-run then ship-pr). Use when the user wants to see where their specs stand, or to run the pending specs (for example those written by /audit) without intervening.
user-invocable: true
argument-hint: "[run] [--only \"a;b\"] [--target <branch>] [--autonomy gate|auto]"
---

# Factory queue — run the specs, one by one

With no argument, **list** the specs; with `run`, **run** them sequentially. The skill builds nothing itself: each spec is handed to a child `claude -p "/factory-run …"` (fresh context, no question possible), which the Skill tool cannot load (`factory-run` is not invocable by another skill).

## Deterministic core

Python code (standard library, ≥ 3.9) in `${CLAUDE_SKILL_DIR}/../_core/`: **FQ-01** to **FQ-10** (`hcore/queue.py`), **CH** (`chain.py`), **WT** (`worktrees.py`), **SX** (`stops.py`), **AP** (`gates.py`). Call the CLI and follow its JSON; never reimplement. Exit 1 = explicit stop: show the stderr line `STOP: … (see <file>)` as is (the file `.harness/runs/STOP-*.md` says what to do) and stop. Exit 2 = usage error. `<PY>`: first of `python`, `python3`, `py -3` that answers in under 5 s with a version ≥ 3.9. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

## List (no argument)

`K queue list --root . [--target <branch>]` returns, for each spec in `specs/*.md` of the current tree and of the registry worktrees, in queue order (topological, then `Priority`, then name): `id`, `title`, `status`, `approved`, `depends_on` and `unsatisfied`, `priority`, `worktree`, `last_run`, `interrupted`, plus `errors` (cycle, unknown dependency: the specs concerned are ineligible) and `warnings` (`git fetch` failure: the local reference is used). Statuses: **merged** (`DELIVERED` on `origin/<target>`), **delivered** (`DELIVERED` locally or in a worktree), **in progress** (active run for less than 2 h; beyond that `interrupted`), **blocked** (`BLOCKED` with unanswered questions), **proposed** (or "proposed (answers ready)"). Show a table, the errors and the warnings. `K queue next` returns the next eligible spec.

## Run (`run`)

1. **Policy**: `run` requires `auto` (FQ-09) — `--autonomy auto` or the stamp; otherwise `gate` stop "requires --autonomy auto" (children can raise no question). Gate `factory-run.approval` and co.: never raised here.
2. **Target**: `--target`, otherwise `ship_pr.target` from the stamp, otherwise `origin/HEAD`.
3. `K queue run --root . --target <target> [--only "a;b"] --autonomy auto` (long call: launch it in the background with the Bash tool and read `.harness/runs/factory-queue-<timestamp>.jsonl`, or follow its output). The core checks (FQ-08) the factory is installed, the tree is clean, the current branch is or can be switched to the target; takes the coordinator lock (a single one per repository, FQ-07); then loops: next eligible spec (proposed or answers ready, dependencies merged, never attempted in this run) → child `factory-run <spec> --ship <target>` (CH-01) → wait → `git checkout <target>` and `git pull --ff-only` (dirty tree → `gate` stop). A PR left open does not stop the queue, its dependents remain ineligible; a failed or stopped child stops the queue (`child` stop, the spec is not rerun).
4. Report: specs built, PRs merged or left open, leftovers and the reason for each (`left`), paths of the journal and of the STOPs.

## Defaults under the `auto` policy

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to each child (AP-04). This skill raises no gate itself.

## Mandatory rules

- Never launch `factory-run` through the Skill tool nor by hand: only `K queue run` launches the children.
- Never delete or move a worktree or a `STOP-*.md` file; never commit or push in place of the core.
- Never `/factory-queue run` on this repository without an explicit request from the user.
