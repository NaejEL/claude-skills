---
name: vibecode-audit
description: Alias of /audit for an AI-generated project (access, injection, business logic, maintainability, evolvability) — now produces AUDIT.md. Use when the user wants to know where to start on an AI-generated project.
user-invocable: true
argument-hint: "[REPO] [--axes \"securite;maintenabilite;evolutivite\"] [--max-findings N] [--models \"role=modele;...\"] [--autonomy gate|auto]"
---

# Vibecode audit — alias of `/audit`

`/vibecode-audit` is an alias of `/audit`, kept during version 2.0.0 and removed in the next version.

First display this sentence word for word, then:

1. Write `$ARGUMENTS` as is with the Write tool to `.harness/runs/vibecode-audit-arguments.txt` (never through the shell), then call `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" audit alias-args --skill vibecode-audit --arguments-file .harness/runs/vibecode-audit-arguments.txt --skill-dir "${CLAUDE_SKILL_DIR}"` (`<PY>`: see `/software-factory`). The `arguments` field returned expands the axes of `--axes` into lenses, forces `--profile software` and adds `--via vibecode-audit`; the `invoke` field is the effective name of `audit` for the Skill tool.
2. Invoke **inline** (without a sub-agent) the Skill tool on the skill named by `invoke` with these arguments. Fallback if the Skill tool is unavailable: read `${CLAUDE_SKILL_DIR}/../audit/SKILL.md` and follow its instructions with these arguments.

## Defaults under the `auto` policy (AP-09)

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to `K gate decide --autonomy` and to chained skills (AP-04). Default of each gate of this skill under `auto`, with its one-line justification (the one from the `K gate list` catalog):

- `vibecode-audit.drop-security` → keep — security is the priority axis (options: confirm removal / keep)
- `vibecode-audit.order` → Severity first / Detail them — marked default at :115; detailing loses nothing (options: Severity first / Quick wins / Everything that blocks / Keep the order ; minors: Detail them / List them in one line / Omit them)
- `vibecode-audit.final` → Write AUDIT-vibecode.md — the deliverable the audit was run for (options: Write AUDIT-vibecode.md / Readjust / Abandon)
