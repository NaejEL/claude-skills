---
name: ai-lab-audit
description: Alias of /audit for an AI research project (fidelity, validity, leaks, biological analogies, roadmap) — now produces AUDIT.md. Use when the user wants an external review of an AI research project.
user-invocable: true
argument-hint: "[REPO] [--lenses \"fidelite;validite;fuites;bio;route\"] [--max-questions N] [--models \"role=modele;...\"] [--autonomy gate|auto]"
---

# AI Lab audit — alias of `/audit`

`/ai-lab-audit` is an alias of `/audit`, kept during version 2.0.0 and removed in the next version.

First display this sentence word for word, then:

1. Write `$ARGUMENTS` as is with the Write tool to `.harness/runs/ai-lab-audit-arguments.txt` (never through the shell), then call `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" audit alias-args --skill ai-lab-audit --arguments-file .harness/runs/ai-lab-audit-arguments.txt --skill-dir "${CLAUDE_SKILL_DIR}"` (`<PY>`: see `/software-factory`). The `arguments` field returned forces `--profile research`, keeps `--lenses`, `--max-questions` and the short aliases of `--models`, and adds `--via ai-lab-audit`; the `invoke` field is the effective name of `audit` for the Skill tool.
2. Invoke **inline** (without a sub-agent) the Skill tool on the skill named by `invoke` with these arguments. Fallback if the Skill tool is unavailable: read `${CLAUDE_SKILL_DIR}/../audit/SKILL.md` and follow its instructions with these arguments.

## Defaults under the `auto` policy (AP-09)

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to `K gate decide --autonomy` and to chained skills (AP-04). Default of each gate of this skill under `auto`, with its one-line justification (the one from the `K gate list` catalog):

- `ai-lab-audit.framing` → specs / make reliable — specs when a factory is present, otherwise list; make it reliable first (options: specs, list, ignore minors, make reliable, cheaper, roadmap, proposed order)
- `ai-lab-audit.selection` → All — the cap applies afterwards (options: All / Only the best ranked / None)
- `ai-lab-audit.final` → Write AUDIT-lab.md — the deliverable the audit was run for (options: Write AUDIT-lab.md / Readjust / Abandon)
