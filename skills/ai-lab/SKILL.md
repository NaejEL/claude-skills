---
name: ai-lab
description: Alias of /software-factory for an AI research project — installs the multi-agent laboratory (Research Director, Neuroscience and Math experts, Builder, Verifier) and the /lab-run skill, forcing the research profile. Use when the user wants to initialize or install their AI lab in a research project (architecture PoC, bio-inspired mechanism, ablation study).
user-invocable: true
argument-hint: "[research question or hypothesis to handle first | --upgrade [--convert]]"
---

# AI Lab — alias of `/software-factory --profile research`

This skill carries no rule: the laboratory is the factory's `research` profile, installed by `/software-factory` (single entry point, Phase 2). It is kept with no deadline, so as not to break anything.

## Execution

0. **`--upgrade [--convert]`** (EP-10): `K sf args --via ai-lab --arguments-file …` (arguments written by Write) returns `translated`; invoke `software-factory` with this translation, **without** `--profile research`: all the profiles in the stamp are updated. Laboratory updates therefore go through `/software-factory --upgrade`.
1. Obtain the effective name of `software-factory`: `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" plugin skill-name --skill software-factory --skill-dir "${CLAUDE_SKILL_DIR}"` (field `name`), to be used in step 0 as well. Invoke **inline** (without a sub-agent) the Skill tool on this name with the arguments `--profile research` followed by `$ARGUMENTS` as is (the research question, if any, becomes the first need).
2. Fallback if the Skill tool is unavailable: read `${CLAUDE_SKILL_DIR}/../software-factory/SKILL.md` and follow its instructions with these same arguments.
3. On a project already equipped with the `software` profile, the `research` profile is **added** to the `.claude/harness.json` stamp, nothing is removed.

After installation, the scientific loop is launched with `/lab-run "<question>"` or `/lab-run suivant`, and headless with `ci/lab.sh experiments/EXP-x.md`.

## Defaults under the `auto` policy (AP-09)

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to `K gate decide --autonomy` and to chained skills (AP-04). Default of each gate of this skill under `auto`, with its one-line justification (the one from the `K gate list` catalog):

- `ai-lab.models` → All inherited — no extra cost (options: All inherited / experts / interpretation / Custom)
- `ai-lab.code-index` → refuse — the knowledge base adds a versioned folder (options: install / refuse)
- `lab-run.pi-questions` → none (stop) — nothing to invent in the PI's place (option: "Questions for the PI")
- `lab-run.preregistration` → approval (options: approval / iterate) — stop if `stop_when` = input:blocking_unanswered — roadmap 4.2 applied to the research artefact: pre-registered unless the protocol declares an unanswered blocking question
- `lab-run.consignation` → approval — logged, marked 'to be reviewed' (ai-lab:188)
