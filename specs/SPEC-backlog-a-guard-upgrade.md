# SPEC — BACKLOG §8, part A: guard, hooks, upgrade, chain, version guard

Status: DELIVERED
Blocking questions: none
Files scope: skills/**, ci/**, .claude/harness/**, .claude/settings.json, .claude-plugin/**, specs/harness-v2/BACKLOG.md, README.md, .harness/tmp/**

## Context

Minor defects collected in `specs/harness-v2/BACKLOG.md` §8 (code reviews of Phases 3 to 7, real use on this repo). User decision (2026-11-06): fix them. Each item below is a behavior fix with its own behavior test. When an item turns out to be wrong or already fixed, say so in the report and skip it — do not invent work.

## Scope

1. **Bash guard reads heredoc bodies** (`hcore/guard.py`): the body of a heredoc (`<<EOF`, `<<'EOF'`, `<<-EOF`) is data, not commands; only the command line that opens it is analysed. A heredoc fed to a shell (`bash <<EOF`, `sh <<'EOF'`) is still analysed as commands.
2. **Globs under the scratch dir** (`hcore/guard.py`, `hcore/scope.py`): `rm -rf .harness/tmp/*` and `rm .harness/tmp/*.py` pass when the literal prefix before the first glob character is inside `<root>/.harness/tmp/` and contains no `..`; any other glob target stays blocked.
3. **Stop leaves the scope marker** (`factory-run`, `hcore/stops.py` or the stop path of `harness.py`): writing a STOP for a cycle deactivates that cycle's scope marker (same effect as `deactivate`), so a stopped cycle never leaves `.harness/runs/active/<session>.json` behind.
4. **Hook interpreter** (`hcore/hooks_install.py` and what writes the `hooks` key of `.claude/settings.json`): the hook command no longer hard-codes `py -3`; it uses the interpreter detected by `harness.py interp` at install time, and the generated shell wrapper falls back `python3` → `python` → `py -3` at run time so the safety net is active on Linux/macOS. Re-run `hooks install` on this repo's `.claude/settings.json` through `harness.py` (idempotent).
5. **Post-edit hook budget** (`hooks/hook.py`): the lint subprocess is bounded by the hook budget (killed at the budget, reported as a timeout), never left running after the hook returns.
6. **upgrade** (`hcore/upgrade.py`, `hcore/render.py`, `hcore/migrate.py`):
   - `union_tools` on a read-only `legacy` agent never touches the out-of-block `tools:` line;
   - at `apply`, a conversion candidate is re-checked against the sha recorded in the plan (refuse if it changed);
   - the UP-08 guard compares code-index's `TOOL_VERSION` to code-index's own version, not to `CORE_VERSION`;
   - no `*.upgrade-tmp` file is left after an exception (cleanup in `finally`);
   - `migrate` rewrites `findings.jsonl` only when its content changes;
   - `_set_header` only recognises header lines inside the header zone.
7. **batch `--resume`** (`hcore/batch.py`): a spec recorded `ineligible` is re-evaluated on resume (it may have become eligible).
8. **chain** (`hcore/chain.py`): a child that exits 0 without creating any run counts as a failure.
9. **Version guard** (`hcore/plugin.py`): the baseline is the last commit where the parsed `version` **value** of `.claude-plugin/plugin.json` changed (not `-G '"version"'`); a decreased version fails the guard (semver comparison).

10. **Literal delete targets** (real use, M4 cycle): a Verifier's `Remove-Item $base -Recurse -Force` on its own scratch folder was blocked (a variable target is unresolvable, which stays blocked by design) and stopped the cycle. The generated Builder and Verifier templates (both profiles) add one sentence: delete scratch files with a literal path under `.harness/tmp/` (no variable, no glob outside it). Then run `upgrade plan`/`apply` on this repo through `harness.py` so the repo factory gets it (headers and blocks only; house rules untouched).

## Acceptance criteria

- One behavior test per item (1 to 9), in the existing test modules of `skills/_core/tests/`.
- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passes (module by module if over 10 minutes).
- `bash ci/test-harness.sh` and `pwsh -NoProfile -File ci/test-harness.ps1` pass, `plugin-guard` included; `claude plugin validate .`.
- `.claude-plugin/plugin.json` bumped to the next patch version after the current one; `diff -rq skills/_core .claude/harness`: only `MANIFEST.json`.
- BACKLOG §8: each fixed item is marked fixed (one short line), skipped ones say why.

## Frugality rules (mandatory)

- Scratch files under `.harness/tmp/` only. Never write into the real `~/.claude/` or `HOME`.
- No tests reading prose; no mutation campaigns.
- Verifier: reads every changed code file in full; major defects only; minor ones to BACKLOG §8.

## Out of scope

Part B items (audit, lab, labels), `eval` analysis (by design), the `CLAUDE_SKILL_DIR` assumption (risk note), any commit or push.
