# SPEC — BACKLOG §8, part B: audit, lab, profiles, remaining French labels

Status: DELIVERED
Blocking questions: none
Depends on: SPEC-backlog-a-guard-upgrade
Files scope: skills/**, ci/**, .claude/harness/**, .claude-plugin/**, specs/harness-v2/BACKLOG.md, README.md, .harness/tmp/**

## Context

Second half of the BACKLOG §8 minors (Phase 1-2 reviews, real use of `/audit`, English translation leftovers). User decision (2026-11-06): fix them. Each item is a behavior fix with its own behavior test; an item that turns out wrong or already fixed is reported and skipped.

## Scope

0. **Guard regression from part A (priority)** (`hcore/guard.py`): part A made heredoc bodies pure data, but in an **unquoted** heredoc (`<<EOF`, `<<-EOF`) the shell still expands `$( )` and backticks, so `cat <<EOF` + `$(rm -rf /)` + `EOF` now passes. Fix: in an unquoted heredoc body, the command substitutions (`$( )`, backticks) are analysed as commands; the rest of the body stays data. A quoted delimiter (`<<'EOF'`, `<<"EOF"`) keeps the whole body as data. Behavior tests for both, and for a heredoc fed to a shell (still fully analysed).
1. **lab CI** (`skills/_core/templates/lab-ci.sh|ps1`): the pre-registration check matches the exact status line that `labrun.entry` requires, not `Statut : PRE-ENREGISTRE` anywhere in the file.
2. **vibecode lens set**: `SPEC-vib-*` specs are produced as the profile declares (E-A2, SO-02, AD-08, AD-10) and `allowed_writes` of the vibecode set includes `SPEC-vib-*`.
3. **`AUDIT.md` section order** follows SO-01: sections ordered by the order of the active profiles in the stamp, blocks kept inside each set.
4. **Audit framing**: one framing gate instead of two (AD-08, E-A5), unless the two answer different policy kinds — then keep two and record why in the BACKLOG line.
5. **`loop.route --models`** with a role outside the profile: explicit error message naming the role and the allowed roles (exit 2 kept).
6. **`cmd_sf_args`** calls `profiles.discover()` once.
7. **`/audit` core path**: the skill text and the core never point to `_core/harness.py` inside an equipped project; the path used is `.claude/harness/harness.py` (or the plugin's own core when run from the plugin, as `plugin skill-name` does for names).
8. **Orphan audit run**: when `audit start` (or a later audit step) fails on invalid input, the run it opened is closed with a failure status, never left `running` in `.harness/runs/`.
9. **Remaining French user-facing strings in the core**: `hcore/cx.py` task labels and prompts (`Index: réindexer`, the search prompt), `hcore/lab.py` (`Lab: nouvelle expérience`), state words printed to the user in `fusion.py`, `hooks_install.py`, `queue.py` (`créé`, `fusionné`, `mergée`…), `unified.py:1742` (cite both `Default:` and `Défaut :`), and `skills/brainstorm/SKILL.md` labels (`SUJET`, `[énoncé]`, `[hors énoncé]`, the quoted heading "non retenus dans ce cycle"). Where a French word is **parsed** from existing files (legacy deliverables, existing VS Code tasks to merge with), the French form stays accepted; what the core **writes** is English. Existing generated `tasks.json` entries with the French label are recognised as the same task (no duplicate on re-install).
10. **`expected-gaps.json` test** checks each gap's justification field, not only the ids.

## Acceptance criteria

- One behavior test per item (0 to 10), in the existing test modules of `skills/_core/tests/`.
- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passes (module by module if over 10 minutes).
- `bash ci/test-harness.sh` and `pwsh -NoProfile -File ci/test-harness.ps1` pass, `plugin-guard` included; `claude plugin validate .`.
- `.claude-plugin/plugin.json` bumped to the next patch version; `diff -rq skills/_core .claude/harness`: only `MANIFEST.json`.
- BACKLOG §8: each fixed item marked fixed, skipped ones say why.

## Frugality rules (mandatory)

- Scratch files under `.harness/tmp/` only. Never write into the real `~/.claude/` or `HOME`.
- No tests reading SKILL.md prose; no mutation campaigns.
- Verifier: reads every changed code file in full; major defects only; minor ones to BACKLOG §8.

## Out of scope

Part A items, legacy fixtures, historical `specs/`, any commit or push.
