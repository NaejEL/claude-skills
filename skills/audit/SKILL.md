---
name: audit
description: Unified read-only audit of a project — mapping, one auditor per lens (accumulation debt of a legacy repo, generation debt of an AI-generated project, review of an AI research project), adversarial validation, interactive prioritization, then a single AUDIT.md and specs. Use when the user wants to audit a project, know where to start attacking it, or get an upgrade roadmap.
context: fork
user-invocable: true
argument-hint: "[REPO] [--profile p[;p]] [--lenses \"l;…\"] [--max-specs N] [--max-findings N] [--max-questions N] [--models \"r=m;…\"] [--autonomy gate|auto]"
---

# Audit — unified diagnosis, a single `AUDIT.md`

Audit the project `REPO` (default: current folder) with the lenses of the active profiles and write **a single deliverable**, `AUDIT.md`, plus the retained specs. Replaces `/legacy-audit`, `/vibecode-audit` and `/ai-lab-audit`, kept as aliases. Never fix the project: moving on to execution is done through `/factory-run`.

## Deterministic core

Python code (standard library, ≥ 3.9) in `${CLAUDE_SKILL_DIR}/../_core/`: **AD** and **LN** (`hcore/profiles.py`), engine **AU-01** to **AU-16** (`audit.py`), **FD**, **RG**, **TS**, **SO** and **MG** (`unified.py`), **GT**. Call the CLI and follow its JSON output; never reimplement. `<PY>`: the first of `python`, `python3`, `py -3` that answers in under 5 s with a version ≥ 3.9 (see `/software-factory`). `K` = `<PY> <CORE>`, where `<CORE>` is the `path` returned by `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py" plugin core-path --root "<REPO>" --skill-dir "${CLAUDE_SKILL_DIR}"`: the plugin's own core in plugin mode, otherwise `.claude/harness/harness.py` of an equipped project, otherwise the `_core` beside this skill. Never cite `_core/harness.py` inside an equipped project: if `${CLAUDE_SKILL_DIR}/../_core` does not exist, `<CORE>` is `.claude/harness/harness.py`.

## Mandatory rules

- **Absolute read-only on the audited project.** Only writes: `AUDIT.md`, `specs/SPEC-leg-*`, `SPEC-vib-*` and `SPEC-lab-*`, `.harness/runs/` (the core refuses any other path). `ROADMAP-legacy.md`, `AUDIT-vibecode.md` and `AUDIT-lab.md` are never written, never modified.
- **"Zero findings" is a normal and acceptable answer**; this sentence appears verbatim in every auditor prompt. A silent lens is not a satisfied lens.
- **One auditor per lens**, its lens and nothing else, never two lenses in one auditor; at most 5 in parallel, beyond that in waves (`waves`, in profile → set → lens order).
- **Forbidden strings**: never write `Status:` followed by the status of a ready-to-build artifact (the core refuses it, FD-11). Specs are written by the core.
- Transit files: write with Write under `.harness/runs/`, never through stdin or the shell.

## Phase 1 — Arguments, profiles, lenses

1. Write `$ARGUMENTS` with Write to `.harness/runs/audit-arguments.txt`, extract `REPO`, `--via <alias>` (internal option) and the options from it. `K audit open --root "<REPO>" [--via <alias>]` opens the `audit-<timestamp>` journal and records the `alias` event in it.
2. **Active profiles**: `--profile`; otherwise `K stamp resolve --root "<REPO>"` (stamp, then earlier generated files); otherwise a **read-only** scout (Explore, see `/software-factory`, role `harness.scout`) whose verdict serves this audit and is **not written** to the stamp, gate `audit.profiles` (same semantics as `software-factory.profiles`: a clear proposal in `auto` → default, ambiguous → exit 1, headless `default` if clear).
3. `K audit plan --root "<REPO>" --profile "<p;p>" [--lenses …] [--max-specs N] [--max-findings N] [--max-questions N] --via …` returns `lenses` (default: union of the lenses; a lens or axis outside the active profile or unknown → exit 2; `securite` → `acces;injection;metier`), `waves` and `caps` (`legacy`: `--max-specs` ≤ 25 default 15; `vibecode`: `--max-findings` ≤ 30 default 15; `research`: `--max-questions` ≤ 12 default 6; option of an inactive set → exit 2).
4. One engine per active set, in stamp order: `K audit start --unified --skill legacy-audit|vibecode-audit|ai-lab-audit --root "<REPO>" --only "<retained lenses of the set>" --arguments-file …` (set `legacy` → `legacy-audit`, `vibecode` → `vibecode-audit`, `research` → `ai-lab-audit`). It probes git (`git_absent`: no git command afterwards), reads the factory and **resumes** `AUDIT.md` and every earlier deliverable not yet imported (statuses `FAIT`, `EN_COURS`, `TRANCHEE` preserved, numbering continued, `imports`, `import_warnings` to report). The arguments file carries only `REPO`, the set's cap and `--models`.

## Phase 2 — Common mapping

Union of the steps of the active sets: 2-3 level tree, `K stack detect --root "<REPO>"` (bounds: beyond 2000 files, `sampled`, 3 levels, 40 files per auditor), manifests, README, LICENSE, CI, tests, `git_absent`, factory and lab present; depending on the set, `map_text` steps (`K profile show <profile>`, `lens_sets[]`): scientific corpus and journal resume (`research`); trust boundaries, generation signals, reimplementation pairs, deterministic checks, distribution artifact (`vibecode`).

## Phase 3 — Lens auditors

Per wave, **in a single message**, one auditor per lens (`subagent_type` of the lens when the lab is present, otherwise Explore; `model` parameter of the `model_role` when `pass_param` is true, never for `inherit`). Prompt = map, the lens `fragment_text` (`K profile show <profile>`, `lenses[]`) and `critical_text`, reading budget, ban on writing (and on executing, except `allowed_exec`), verifiable proof (file + line + excerpt ≤ 3 lines), T-shirt scale (`size_scale`: `dev`, or GPU cost for questions) and the set's final JSON block. Properties: `debt` (framing of the debt), `shape` (`pattern`: `{pattern, occurrences[≤5], count, sampled}`; `occurrence`: these fields are refused), `ordering`, `unauditable` (lens dead twice: `finding` "unauditable surface" major, or `mark` "not audited"), `no_run` and `no_protocol` (no run, no protocol for research lenses). Each return: `K audit auditor --run <set run> --unit <unit> --output <file> [--dead] --duration-ms <ms> --tokens <n>`.

## Phase 4 — Adversarial validation

For each `to_validate` (duplicates dropped without a validator, all sets combined), a mini-validator (role `audit.validator`, or `lab.validator` for `research`) challenges the proof, the severity and the size; accepted verdict fields = the lens `validator_fields`; for `journal_check`, grep the journal before confirming. `K audit validator …`, then `K audit next` and `K audit consolidate` per set (zero CONFIRMED → Phase 6).

## Phase 5 — Interactive prioritization (gates, at most 4 questions per call)

`audit.software.framing` (milestones, dominant criterion) and `audit.software.assignment` (at most 3 calls) if `legacy`; `audit.software.order` (attack order, fate of minors) if `vibecode`, and `audit.drop-security` only if `vibecode` is partial and excludes `securite`; `audit.research.framing` and `audit.research.selection` (at most 2 calls) if `research`. Each gate: `K gate decide --root "<REPO>" --run <audit> --id …`, AskUserQuestion, `K gate answer … --answer-file` (`reask` → ask the question again). Headless: `stop` for `legacy` and `research` (the whole audit stops before writing), `default` flagged at the top for `vibecode`. Rendering data: the set's JSON file, then `K audit plan --run <set run> --data-file …`. Final gate `audit.final`: **Write AUDIT.md (+ specs)** / **Readjust** (once) / **Abandon**.

**`auto` policy** (`--autonomy auto` or stamp; PZ-01 to PZ-05): no framing question. `K audit prioritize --run <set run> [--max-specs N] [--autonomy auto]` returns the computed milestones ("make it reliable first": milestone 1 = `critical`, 2 = `major`, 3 = `minor`, a prerequisite moves up to the earliest milestone of its dependents, empty milestones removed), the ranks and the `Priority` of each finding, and logs the decision with these values; the assignment of findings is that of this computation (nothing is excluded, the cap then applies in milestone order). `vibecode` set: "Severity first", minors "Detail them"; `research` set: questions sorted by decreasing severity then increasing cost, all retained then capped. Even headless, `/audit` goes through to `AUDIT.md` with no human answer (`audit.final` writes). Each gate is still decided by `K gate decide --autonomy <effective>`.

## Phase 6 — Generation (the only phase that writes)

1. Per set: `K audit render --run <set run> --data-file …` prepares the section block (nothing is written under the old name). Then `K audit assemble --root "<REPO>" --set-run <run> [--set-run <run>] --profiles "<p;p>" --lenses "<l;l>" [--sampled]` writes `AUDIT.md`: header "Generated by /audit on …" ("Généré par /audit le …"), profiles, lenses, complete or sampled, `<!-- harness:import … -->` lines + "Repris depuis", each set's block in stamp order, "Suite". Idempotent: same inputs, same date → identical file.
2. **Specs**: for each spec of the plan (`legacy` set; `vibecode` set when `legacy` is active too and a pattern is assigned to a milestone: `SPEC-vib-<nn>-<slug>.md`, alone it writes none; and `research` set if `software` is active or the factory is present and chosen), JSON of the judgement sections `{context, scope, criteria[], out_of_scope, risks, depends_on[], priority}` (`depends_on` = spec names of the prerequisites, `priority` = the rank returned by `prioritize`: the core writes `Blocking questions: none`, `Depends on:` and `Priority:` under `Status:`) then `K audit spec --run … --finding … --sections … --number <n> --slug …`; never overwritten. `Q-*` questions are launched by `/factory-run --profile research "<question>"`; the two criteria imposed on `fuites` are kept.
3. `K audit publish --run <set run> --deliverable` for each set (project registry).

## Phase 7 — Final report

Map (project, stack, size, git, complete or sampled, imports and warnings); table per lens (raw, confirmed, rejected or deduplicated; split and occurrences for `pattern`; corrections and questions for `research`); unauditable surfaces; files written (`AUDIT.md` and specs, with the rendered state); chaining (CH-04, gate `audit.chain`): `K audit chain-plan --root "<REPO>" --only "<written specs>" --run <run>` returns `chain` and `only` (PZ order); if `chain` is true, invoke through the Skill tool `factory-queue run --only "<only>" --autonomy <effective>` (the audit writes only its deliverables, execution happens in children, AD-10); next action (`/factory-run "specs/SPEC-…"`, `/factory-run --profile research "<question>"`); what remains. Families with no finding are not families with no defect.

## Defaults under the `auto` policy (AP-09)

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to `K gate decide --autonomy` and to the chained skills (AP-04). Default of each gate of this skill in `auto`, with its one-line justification (the one from the `K gate list` catalog):

- `audit.research.framing` → specs / make reliable — specs when a factory is present, otherwise list; make it reliable first (options: specs, list, ignore minors, make reliable, cheaper, roadmap, proposed order)
- `audit.research.selection` → All — the cap applies afterwards (options: All / Only the best ranked / None)
- `audit.software.framing` → 3 / risk first — computed by PZ-01 and PZ-02: make it reliable first, milestones computed (roadmap 4.2) (options: 2, 3, 4, risk first, quick wins, foundations, proposed order)
- `audit.software.order` → Severity first / Detail them — marked default in the attack order; detailing loses nothing (options: Severity first / Quick wins / Everything that blocks / Keep the order ; minors: Detail them / List them in one line / Omit them)
- `audit.software.assignment` → PZ-02 computation — milestones computed by PZ-02 from the severity, nothing is excluded (options: Milestone 1 / Milestone 2 / Last milestone / Exclude from roadmap)
- `audit.profiles` → proposal — read-only scout verdict, used for this audit and never written to the stamp (options: proposed profiles / Abandon)
- `audit.drop-security` → keep — security is the priority axis (options: confirm removal / keep)
- `audit.final` → Write AUDIT.md (+ specs) — the deliverable the audit was run for
- `audit.chain` → run the queue — roadmap 4.2: the specs written are queued when a software factory is present (options: run the queue / do not run)
