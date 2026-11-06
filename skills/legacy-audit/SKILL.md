---
name: legacy-audit
description: Alias of /audit for the accumulated debt of a legacy repo (hygiene, portability, quality, safety net) — now produces AUDIT.md and the LEG specs. Use when the user wants to audit a legacy repo and get a modernization roadmap.
user-invocable: true
argument-hint: "[REPO] [--categories \"hygiene;portabilite;qualite;filet\"] [--max-specs N] [--models \"role=modele;...\"] [--autonomy gate|auto]"
---

# Legacy audit — alias of `/audit`

`/legacy-audit` is an alias of `/audit`, kept during version 2.0.0 and removed in the next version.

First display this sentence word for word, then:

1. Write `$ARGUMENTS` as is with the Write tool to `.harness/runs/legacy-audit-arguments.txt` (never through the shell), then call `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" audit alias-args --skill legacy-audit --arguments-file .harness/runs/legacy-audit-arguments.txt --skill-dir "${CLAUDE_SKILL_DIR}"` (`<PY>`: see `/software-factory`). The `arguments` field returned translates `--categories` into `--lenses`, forces `--profile software` and adds `--via legacy-audit`; the `invoke` field is the effective name of `audit` for the Skill tool.
2. Invoke **inline** (without a sub-agent) the Skill tool on the skill named by `invoke` with these arguments. Fallback if the Skill tool is unavailable: read `${CLAUDE_SKILL_DIR}/../audit/SKILL.md` and follow its instructions with these arguments.

## Defaults under the `auto` policy (AP-09)

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to `K gate decide --autonomy` and to chained skills (AP-04). Default of each gate of this skill under `auto`, with its one-line justification (the one from the `K gate list` catalog):

- `legacy-audit.framing` → 3 / risk first — close to 'make it reliable first' (roadmap 4.2) (options: 2, 3, 4, risk first, quick wins, foundations, proposed order)
- `legacy-audit.assignment` → none (stop) — the computation belongs to Phase 4 (options: Milestone 1 / Milestone 2 / Last milestone / Exclude from roadmap)
- `legacy-audit.final` → Generate roadmap + specs — the deliverable the audit was run for (options: Generate roadmap + specs / Readjust / Abandon)
