---
name: factory-batch
description: Batch of specs in parallel — builds several specs at once, each in its own git worktree (up to 4 headless children), then delivers them one at a time in queue order (rebase onto the target, ship-pr, merge, cleanup). Use when the user wants to run several independent specs faster than /factory-queue, without touching their own worktrees.
disable-model-invocation: true
user-invocable: true
argument-hint: "<glob…> [--parallel N] [--target <branch>] [--autonomy gate|auto] [--resume <id>]"
---

# Factory batch — several specs in parallel, a single ship at a time

Build in parallel the specs designated by the globs, each in a git worktree created by the harness, then deliver them **one at a time**. No other skill chains this skill (`disable-model-invocation: true`).

## Deterministic core

Python code (standard library, ≥ 3.9) in `${CLAUDE_SKILL_DIR}/../_core/`: **FB-01** to **FB-08** (`hcore/batch.py`), **FQ** (`queue.py`), **WT** (`worktrees.py`), **CH** (`chain.py`), **SX** (`stops.py`). Call the CLI and follow its JSON; never reimplement. Exit 1 = explicit stop: show the stderr line `STOP: … (see <file>)` as is and stop; the file `.harness/runs/STOP-*.md` gives the resume command. Exit 2 = usage error (`--parallel` not an integer or < 1). `<PY>`: first of `python`, `python3`, `py -3` that answers in under 5 s with a version ≥ 3.9. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

## Flow

1. **Policy**: like `/factory-queue run`, `auto` is required (FQ-09, FB-07); a single coordinator per repository (FQ-07).
2. `K batch run --root . <glob…> [--parallel N] [--target <target>] --autonomy auto [--resume <id>]` (long call: launch it in the background with the Bash tool and follow `.harness/runs/factory-batch-<timestamp>.jsonl`). `--parallel`: default 2, capped at 4. The core expands and sorts the globs, reports ineligible specs (`not_eligible`), then for each slot: worktree `<repo>.harness-wt/<slug>` on branch `factory/<slug>` from `origin/<target>` (the spec is transferred there if it differs from the base, the original is moved under `.harness/runs/handoff/`), then a child `factory-run <spec> --deliver-only`.
3. **Ship**: one at a time, in queue order. Before each ship, the local branch (never pushed) is rebased onto `origin/<target>`; a trivial conflict (regenerable `.knowledge/` artifacts) is resolved, any other conflict cancels the rebase, stops launches, waits for running children then stops with type `conflict` (the worktree is kept). The ship is a child `ship-pr <target> --spec <spec>` in the worktree; PR merged → the worktree's journals are copied under `.harness/runs/wt-<slug>/`, then the worktree and its local branch are deleted (never forced); PR left open → worktree kept.
4. `--resume <id>` resumes a stopped batch (state `.harness/runs/factory-batch-<timestamp>.state.json`).
5. Report: state of each spec (merged, left open, failed, ineligible), paths of the worktrees kept, of the journal and of the STOPs.

## Defaults under the `auto` policy

The `--autonomy gate|auto` option (AP-03) applies to this run only, never writes `.claude/harness.json` and is passed to each child (AP-04). This skill raises no gate itself.

## Mandatory rules

- The harness never touches the main worktree nor the user's: every operation requires the path to be in the registry **and** listed by `git worktree list`. Never `prune`, `remove --force`, nor `move`, `lock`, `unlock`.
- A repository whose `origin/<target>` base lacks `.claude/harness/` and `.claude/settings.json` stops (`gate`): "commit the harness files first".
- Never `/factory-batch` on this repository without an explicit request from the user.
