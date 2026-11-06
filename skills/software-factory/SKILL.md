---
name: software-factory
description: Installs the multi-agent factory of the current project, single entry point — detects the applicable profiles (software, AI research, …) through a scout, generates the sub-agents, the /factory-run orchestration skill, the CI scripts, the token-economy rules and the VS Code tasks. Use when the user asks to initialize or install their software factory or research lab in a project, or to search for new profiles (--rescan).
context: fork
user-invocable: true
argument-hint: "[--profile p[;p] | --rescan | --upgrade [--convert]] [--autonomy gate|auto] [optional description of the first need]"
---

# Software Factory — factory installation, single entry point

Install in the current project the multi-agent factory of each applicable **profile** (`software`: Planner, Builder, Verifier; `research`: Director, Neuro, Math, Builder, Verifier), orchestrated by the project skill `/factory-run`, in session as well as in headless CI. The user remains the Product Owner: no requirement is invented on their behalf, a human gate validates the spec before any construction. A profile is a data folder under `${CLAUDE_SKILL_DIR}/../_core/profiles/` (roles, lenses, orchestrator, detection): adding one changes no code.

Arguments (EP-01, `K sf args --arguments-file …`, file written by Write): `--profile p[;p]` skips the scout and the gate (unknown profile → exit 2); `--rescan` relaunches the scout; both together → exit 2; `--upgrade [--convert]` updates an equipped project (section "`--upgrade` mode", exclusive of `--profile` and `--rescan`). The rest of `$ARGUMENTS` is the first need, kept as is, to be recalled in the final report with the matching `/factory-run` command.

## Deterministic core

The deterministic rules are Python code (standard library, ≥ 3.9) in `${CLAUDE_SKILL_DIR}/../_core/`: CLI `harness.py`, package `hcore/`, profiles `profiles/`. Never reimplement them: call the CLI and follow its JSON output. Rules: **PF** (`profiles.py`), **HJ** (`stamp.py`), **VS** (`version.py`), **CO** (`history.py`), **RD**/**EN** (`render.py`), **UP** (`upgrade.py`), **MI** (`migrate.py`), **CV** (`convert.py`), **SC** (`scout.py`), **AR** (`gates.py`), **EP**, **LP** (`loop.py`), **SF-01** to **SF-04** (`fusion.py`), **ST-01** to **ST-04** (`stack.py`), **FR-01** to **FR-04**, **LR-01** to **LR-09**, **GT-01** to **GT-08**, **MD-01** to **MD-08**, **JR-01**, **JR-02**.

**Interpreter** (rule D5, `hcore/interp.py`): `<PY>` = the first of `python`, `python3`, `py -3` that answers in under 5 s with a version ≥ 3.9, via `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`. No candidate → stop: the generated factory depends on it. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

## Mandatory rules (all phases)

- **No placeholder**: every generated file is complete and operational (no TODO, no pseudo-code, no invented command). Every command written in a prompt or script comes from detection, never from a guess.
- **Merge, never overwrite**: `.claude/settings.json`, `.vscode/tasks.json` and `.gitignore` are created or merged by the core (additive union, never hand-edited). An existing unreadable file makes the command fail without modifying anything.
- **Generated files** (SF-04): write each content as is with the Write tool under `.harness/runs/`, then `K sf install --dest <path> --source <this file>`; never through stdin or the shell (the content carries `$ARGUMENTS`, backticks, apostrophes). The core creates, recognizes the identical, or returns `customized-kept` (to be reported); it deletes the transit file as soon as it reads it.
- **Idempotence**: relaunching destroys nothing. An added profile writes only its files, its orchestrator block and the union of its entries (EP-05); another profile's files are returned `identique` or `customized-kept`.

## Phase 1 — Profiles (SC, AR, EP-02, EP-03)

`K stamp resolve --root .`: `stamp` or `inferred` → profiles read, **no scout**; `none` → scout. With `--rescan`, always the scout. With `--profile`, `K stamp add --root . --profiles "<p;p>" --by forced` later (Phase 6).

**Scout.** `K scout signals --root .` returns the deterministic evidence and the `judgement` criteria. Launch the Agent tool (`subagent_type: Explore`, read-only, `model` parameter of the `harness.scout` role when `pass_param` is true) with `${CLAUDE_SKILL_DIR}/../_core/scout/prompt.md`, the `scout.md` fragments of `K profile show <name>` and these criteria; it returns a JSON block `{"signals", "uncertainties"}`. Write this block with Write, then `K scout verdict --root . --signals <file>` (evidence checked, score, `proposal`, `clear`, verdict under `.harness/runs/scout-*.json`). Dead agent or unusable output: relaunch **once**, then `--scout-failed` (a silent scout is not an agreeing scout).

**Gate `software-factory.profiles`** (one multiple-choice question per profile, score and status in the label, 4 choices at most; options "proposed profiles" / "Abandon"). `K gate decide --root . --id software-factory.profiles [--ambiguous --verdict <scout-*.json>]`: `--ambiguous` when `clear` is false. `auto` autonomy and clear proposal → `default`; ambiguous proposal → exit 1, with the verdict path and the resume `/software-factory --profile <p>[;<p>]`. Then `K gate answer … --answer-file`, or `--default`, or `--headless` (`reask` answer → ask the question again). `--rescan`: `K stamp compare --root . --verdict <scout-*.json>` returns `added`, `kept`, `vanished`; only additions are proposed, `vanished` is reported and never removed; nothing to add → no gate nor write, report "no new profile".

## Phase 2 — Detection

`K stack detect --root .` (ST-01 to ST-04) returns manifests, `families` and `stacks`. Read the manifests for the real build, test and lint commands; then follow `install_text` of `K profile show <name>` for each retained profile (profile-specific detection: corpus and hardware for `research`). The core is copied in Phase 5; without a test command, the Builder will initialize the standard tooling (to be reported).

## Phases 3 to 5 — Deterministic generation (EP-11, RD-01 to RD-07)

The `.claude/agents/` sub-agents, the `.claude/skills/<orchestrator>/SKILL.md` orchestrators, the `ci/*` scripts, the copy of the core `.claude/harness/` (with `MANIFEST.json`), the merges (`settings.json`, `tasks.json`, `.gitignore`), the `lab-models.json` migration and the `.claude/harness.json` stamp are produced **in a single plan** by the core, without the LLM writing any file: each file is written in the layout **version header, `harness.*` blocks, free zones outside blocks** (`harness.frontmatter`, `harness.body`, `harness.profile.<name>`, `harness.ci`). A block's content is a pure function of the profile fragment and the parameters: same inputs give the same bytes, which makes `--upgrade` idempotent.

1. **Parameters** (RD-03, RD-04). The `detected` parameters (stacks, interpreter) are computed by the core. The profile's `judgement` parameters (`params[]` of `K profile show <name>`: build, test, lint commands, cited conventions, extra CI tools) are **written once**: read the manifests returned by `K stack detect --root .`, write a JSON object `{"test_command": "…", …}` with Write to `.harness/runs/sf-params.json`. A parameter already recorded in the stamp is never asked again.
2. **Plan**: `K upgrade plan --root . --skill software-factory --profiles "<p;p>" --by scout|forced|inferred|fallback [--params-file .harness/runs/sf-params.json] --interpreter "<PY>"`. An `action` field equal to `fill_params` (required parameters missing, nothing written) sends back to step 1. Otherwise the command writes `.harness/runs/upgrade-<timestamp>.plan.json` and `.diff`, without touching the project.
3. **Core copy** (D1, CO-04): a customized file of `.claude/harness/` stops everything (exit 1, `core not upgraded`); nothing is written, **no stamp** (EP-07); the message gives the restoration then `/software-factory --upgrade`. Never a mixed core.
4. **Apply**: `K upgrade apply --root . --plan <plan> [--decisions-file …]`. All or nothing, stamp last. An existing file without a block (earlier installation) is converted losslessly if it stayed as generated or received only an addition at the end of the file; otherwise it is kept as is and reported `legacy` (gate `upgrade.convert`, see the `--upgrade` section).
5. **Orchestrators** (EP-06, LP): the generated body of `factory-run` routes the input (`H factory-run start`: ready artifact → owner profile in `build`, `suivant` → `research`, `--profile p`, free text → gate `factory-run.profile`, option "profile of the need", default "first profile of the stamp" (the first profile of the stamp)), with **one `harness.profile.<name>` block per active profile**. Cycle gates: gate `factory-run.questions` ("draft options", default "Planner default" (the Planner's default)), gate `factory-run.approval` ("approval" / "iterate"). If `research` is active, `lab-run` is the second instance of the template (`K factory-run start --orchestrator lab-run`). Gate `factory-run.ship` (CH-02, options "deliver and run ship-pr" / "do not deliver", default **deliver** in `auto`, headless fallback: suggestion only) after a successful cycle. Each sub-agent is recorded there by `H factory-run record --run <run> --agent <name> --duration-ms <ms> --tokens <n>` (output written with Write; `--dead` if dead; `H journal amend` completes a measure known after the call). Each agent's model comes from `.claude/models.json` (absent: `inherit`), written in the `harness.frontmatter` block. The core strips `--models "role=model;…"` from the `factory-run` input (valid for this cycle only): pass each sub-agent the role's `model` parameter when `pass_param` is true, never for `inherit`. Fallback without plan (SF-04, X1: the core then writes the `# >>> harness.model >>>` block): `K sf install --dest <path> --source <file written by Write> --model-role factory.planner|factory.builder|factory.verifier` installs a hand-written file, never overwriting; the normal path is the plan above.
6. **Merges** (SF-01 to SF-03, union of profiles) and gate `ai-lab.models` if `research` (see `install_text`) are part of the same plan; the report refers to `--upgrade` for any kept file.

## `--upgrade` mode (EP-08 to EP-11, UP, CV, MI, CO)

`/software-factory --upgrade [--convert]` updates a project that is **already equipped**, for **all** the profiles of the stamp. It excludes `--profile` and `--rescan` (exit 2), and any other content next to `--upgrade` (exit 2); `/ai-lab --upgrade` translates to `--upgrade` **without** `--profile research`. Only delimited blocks are regenerated; everything outside blocks is preserved (invariant checked before writing). It is idempotent: relaunched with no change, it produces no diff.

1. `K version` (repo version) then `K stamp resolve --root .`: source `none` → stop, `project not equipped: run /software-factory`. A project without a stamp is detected by its generated files (`generation`: `pre-core`, `core-<v>`, `stamp-phase2`); the stamp is created at the end of the first successful upgrade (`inferred_from`).
2. `K upgrade plan --root . --skill software-factory [--convert] --interpreter "<PY>"` (`fill_params` step of the previous section if needed). A project installed by a harness newer than the repo is refused (`newer harness`, exit 1): no going back, update claude-skills (`git pull`) first.
3. **Display the full diff** (`.diff`, untruncated) before the apply, with the class of each change: `header`, `block`, `merge`, `copy`, `create`, `convert`, `migrate`, `stamp`.
4. **Gate `upgrade.convert`** if the plan carries `gate.files`: generated files with local changes (`modified`) or never committed (`untracked`). Options "Keep as is" (default) / "Convert (backup)". `K gate decide --root . --id upgrade.convert`, AskUserQuestion, `K gate answer --run <run> --id upgrade.convert --answer "<option>"`; write the decision with Write to `.harness/runs/upgrade-decisions.json` (`{"files": {"<path>": "keep|convert"}, "source": "user|headless|default"}`). `--convert` means "Convertir" for all these files (logged). Without interaction: `default` fallback.
5. `K upgrade apply --root . --plan <plan> [--decisions-file .harness/runs/upgrade-decisions.json]`: checks the project has not changed since the plan (`plan is stale` otherwise: replan), backs up each modified file under `.harness/runs/upgrade-<timestamp>/backup/`, writes all or nothing, the stamp last, and logs one `upgrade` event per file.
6. Report: state of each file and its class, backup path, new version, remaining `legacy` files (to convert with `--convert`), old audit deliverables "repris par le prochain /audit", `extra` files of `.claude/harness/` (never deleted). Does not launch `code-index --upgrade`: that is the role of `/harness-doctor`.

A hand-edited block is replaced (backup): customization is done **outside blocks**.

## Phase 6 — Knowledge base, stamp, report

Gate `software-factory.code-index` **only once** whatever the number of profiles: `K gate decide --root . --id software-factory.code-index`, AskUserQuestion (install / refuse, default refuse), `K gate answer --run <run> … --answer "<install|refuse>"`; agreement → skill `code-index`; headless: `--headless` (`skip` fallback). Never install without agreement.

**Autonomy and hooks** (AP-05, HK-06): `K stamp autonomy --root . [--autonomy gate|auto]` writes `"autonomy": "auto"` if the key is absent (or the given value) and never replaces an existing value; the retained value appears in the report. Hooks are installed by `K hooks install --root . --py "<PY>" [--lint-file .harness/runs/lint.json]` (additive merge of `.claude/settings.json`, JSONC kept; `--lint-file` = Write list `[{"glob", "argv" with `{file}`, "timeout_s"}]` of only the lint commands actually configured, in check mode); `--upgrade` regenerates them. State in the report that hooks only take effect in the next session (or after review in `/hooks`).

**Last**, once generation succeeded: `K stamp add --root . --profiles "<p;p>" --by scout|forced|inferred|fallback` (HJ-05; never a removal). Report: stack, interpreter, profiles and `by`, state of each file (created / merged / identical / personnalisé-conservé) `.claude/harness/` included, models, usage (`/factory-run "need"`; CI `ci/factory.sh specs/SPEC-x.md`) and, if `$ARGUMENTS` contained a need, `/factory-run "<the need>"`.

## Defaults under the `auto` policy (AP-09)

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to `K gate decide --autonomy` and to the chained skills (AP-04). Default of each gate of this skill in `auto`, with its one-line justification (the one from the `K gate list` catalog):

- `software-factory.code-index` → refuse — the knowledge base adds a versioned folder; installation stays possible at any time
- `factory-run.need` → none (stop) — a need cannot be guessed (free input)
- `software-factory.profiles` → proposal — a clear scout proposal is taken; an ambiguous one is never guessed
- `upgrade.convert` → Keep as is — a file with local changes is converted to blocks only when asked
