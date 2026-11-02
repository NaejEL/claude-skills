---
name: code-index
description: Installs in the current project a local knowledge server backed by ripgrep — a code index (symbols, graph, notes, sqlite cache) versioned under .knowledge/ so it travels from user to user through git — exposed to agents by a stdio MCP server and by an equivalent CLI. Detects an already installed software factory (/factory-run) or AI lab (/lab-run) and wires their agents to it without rewriting them. Use when the user wants to add indexed search and the shared knowledge base to a repository, new or already equipped.
context: fork
user-invocable: true
argument-hint: "[--reindex] [--no-wire] [--upgrade] [--autonomy gate|auto]"
---

# Code Index — local knowledge server backed by ripgrep

Install **rgkb** in the current project, a local knowledge base for the repository: ripgrep indexes the code, the artifacts that come out of it (files, symbols, mention graph, sqlite cache) and the **notes written by humans and by agents** live under `.knowledge/`, **versioned in the repository**. A `git clone` is therefore enough to get the knowledge accumulated by other users: nothing to rebuild, nothing to relearn.

The server (`assets/rgkb.py`, standard library, no dependency) is exposed as a **stdio MCP server** for sub-agents and as a **CLI** for Bash and headless use. This skill installs it, registers it, indexes, and **wires the agents already present** (software factory, AI lab) to it without rewriting their prompts.

The rule that justifies the whole: *the index regenerates, the notes do not*. A lost symbol is found again by reindexing; the reason a function must not be called twice can only be found if someone wrote it down. The first role of rgkb is to bring down into the repository what every session rediscovers.

## Deterministic core

The deterministic rules are Python code (standard library, **≥ 3.9: prerequisite of this skill**, X9) in `${CLAUDE_SKILL_DIR}/../_core/`: `harness.py` CLI, `hcore/` package. Never reimplement them: call the CLI and follow its JSON output. Rules: **CX-01** to **CX-16** (`hcore/cx.py`, on `fusion.py` FU-01 to FU-06, `blocks.py` BK-01, `stack.py` ST-01 to ST-03), **GT-01** to **GT-08** (gates), **JR-01**, **JR-02** (journal).

**Interpreter** (CX-03: a name resolved through the PATH, **never** the project's venv, `.mcp.json` being versioned): `<PY>` = the first of `python`, `python3`, `py -3` that answers in under 5 s with a version ≥ 3.9: `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`. No candidate: say so; blocking for the MCP server, the CLI remains usable. `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`, `R` = `<PY> .claude/rgkb/rgkb.py`.

**Gates**: `K gate decide --root . --id <id>` (returns `decision`), AskUserQuestion, then `K gate answer --run <run> --id <id> --answer "<option>"`; when no interaction is possible (headless): `--headless`, and apply the returned fallback.

## Mandatory rules (all phases)

- **No placeholder**: every generated or modified file is complete and operational. No TODO, no invented command.
- **Merge, never overwrite** (FU-01): `.mcp.json`, `.claude/settings.json`, `.vscode/tasks.json`, `.gitignore` and existing agents are merged by the core, never edited by hand: no key removed, no task lost, no prompt rewritten — a delimited, re-entrant section is **added**. JSONC and comments are preserved; an unreadable file makes the command fail without modifying anything: report it.
- **`assets/rgkb.py` is copied as is** (CX-05). If an adaptation seems necessary, report it in the report instead of applying it.
- **`.knowledge/` is versioned.** Never add it to `.gitignore`; if an existing rule excludes it, `K cx scope` adds the counter-rule `!.knowledge/**` (CX-10): say so in the report. The only unversioned file in the folder is `config.local.json`.
- **Nothing machine-specific in a versioned file**: `.mcp.json` and `.knowledge/config.json` carry only commands resolved through the PATH, never an absolute path. Any local setting (path of `rg`, personal exclusions) goes in `.knowledge/config.local.json`.
- **Never commit.** The final report says what to commit, the user decides.
- **Idempotence**: rerunning on an equipped project destroys nothing; each file is reported with the state returned by the core (created / merged / identical / customized-kept, CX-16).

## `--upgrade` mode (CX-17 to CX-22)

`/code-index --upgrade` updates an existing installation, without rebuilding the index. It excludes `--reindex` (exit 2); `no_wire` is read from the buffer (or deduced from the blocks present), never asked again. `K cx args --arguments-file …` returns `upgrade`.

1. `K upgrade plan --root . --skill code-index --interpreter "<PY>"`: `rgkb.py` follows CX-05 (a newer project `TOOL_VERSION` is kept and reported), the `rgkb` blocks of wired files are **rendered from the templates** `assets/blocks/{read-only,builder,orchestrator}.md` (RD-06) and replaced in place, the CX-06 to CX-08 and CX-15 merges are completed, `config.json` only receives the CX-08 merge (never rewritten), git hooks declared (`auto` or `commit`) but missing are reinstalled (class `local`), and `contributes` (the 7 `mcp__rgkb__*` tools and the CLI) is updated in the buffer. The tool lists of files in the harness layout come from `contributes` (rendered by `/software-factory --upgrade`); `legacy` files receive the FU-05 and FU-06 union as at installation.
2. **Show the full diff** of the plan, then `K upgrade apply --root . --plan <plan>`. A second pass gives an empty plan.
3. The `.knowledge/` index is not rebuilt (that is `--reindex`): report the `stale` state from `R status`.

## Phase 1 — Prerequisites and repository state

1. **Arguments** (CX-01): write `$ARGUMENTS` as is with the Write tool to `.harness/runs/code-index-arguments.txt`, then `K cx args --arguments-file .harness/runs/code-index-arguments.txt` returns `reindex` (Phase 4 with `index --force`), `no_wire` (Phase 6 skipped and reported) and `extra`: any other content is recalled in the report without being interpreted.
2. **ripgrep**: `K cx rg` (CX-02) returns the version, or the install command of the machine's package manager. Absent: gate `code-index.rg-install` (options *chosen command* (chosen command) / *local fallback* (local fallback)); on agreement, **run the returned command yourself**. On Windows, `rg` only appears after the PATH is refreshed: recheck, and report "new terminal required" rather than a failure. Never pin another piece of software's binary (VS Code, Copilot) in a versioned file; on refusal or failure, **local** fallback: `.knowledge/config.local.json` with `{"rg_path": "..."}`. Continue in all cases; without `rg`, phases 4 onward stop cleanly and the report gives the command to rerun.
3. **Interpreter**: `<PY>` (see above), or `K interp`.
4. **State** (CX-04): `K cx survey --root .` returns, without modifying anything, git and `.gitignore`, factory and lab present, prior installation, stack markers and bulky folders.

## Phase 2 — Server installation (CX-05)

`K cx install --root . --asset "${CLAUDE_SKILL_DIR}/assets/rgkb.py"` copies to `.claude/rgkb/rgkb.py`: absent → *created*; identical → nothing; asset `TOOL_VERSION` greater than or equal → overwritten and **announced** (artifacts remain readable, the schema is versioned in `manifest.json`); project version greater → *customized-kept*, reported.

## Phase 3 — MCP server registration (CX-06, CX-07, CX-15)

`K cx register --root . --interp "<PY>"` merges in one go: `.mcp.json` (`mcpServers.rgkb`, `py -3` → `-3` at the head of `args`, never an absolute path); `.claude/settings.json` (`enabledMcpjsonServers` += `rgkb`; `permissions.allow` += the 7 **read** tools `mcp__rgkb__*` and `Bash(<PY> .claude/rgkb/rgkb.py *)`; `permissions.deny` += `index.sqlite` and `graph.json`, made to be queried, not loaded into context); `.vscode/tasks.json` (input `rgkbQuery` and five "Index: …" tasks, `windows` variant). Never `note_add` nor `reindex` as automatic permission: they are the only two tools that write to versioned files.

## Phase 4 — Index scope and first indexing

`R init` creates `.knowledge/` (`config.json`, `notes.jsonl`, `README.md`, `.gitattributes`, `.gitignore`) and **never rewrites an existing `config.json`** (CX-09). Then `K cx scope --root .` (CX-08) completes `exclude` with `!<folder>/**` for each bulky folder detected, removing nothing, `rg_path` remaining `null`. Index: `R index` (`--force` if `--reindex`); note files, symbols, edges, notes, languages. Checks to report:

- file count far above the expected size: an exclusion is missing — say so, with the offending folder that `R symbols --limit 20` makes visible;
- `symbols` at 0 while the project has code: language not covered by the `rgkb.py` patterns — report it frankly;
- `R status` must return `"stale": false`.

## Phase 5 — Versioning and git hooks

The `!.knowledge/**` counter-rule is set by `K cx scope` (CX-10); nothing else is added to `.gitignore`. Do not commit: the report gives the exact list of paths.

**Reindexing hooks** — gate `code-index.hooks` (options `hooks install` / `--with-commit` / refuse; headless: nothing installed): `R hooks install` (default) or `R hooks install --with-commit`, then report the state of each hook.

- **By default**: `post-merge` (`git pull`) and `post-rewrite` (rebase) reindex afterwards, write only if the content changed and never make git fail.
- **`--with-commit`** adds `pre-commit`: it reindexes and stages `.knowledge/` before each commit, so **every commit carries an index consistent with its code** and a branch switch never dirties the tree. This is the consistent option, at the price of a hook that adds files to every commit.
- **`post-checkout` is not installed**, and this is not an oversight: reindexing after a branch switch dirties the tree every time, and git then refuses the next checkout ("local changes would be overwritten"). With `pre-commit` it has nothing left to do. Never add it at an agent's request.

`.git/hooks/` is not versioned, but `hooks install` writes the **intent** to `.knowledge/config.json` (key `hooks`: `off` / `auto` / `commit`), versioned: `status` and `index` reconcile the local hooks with it, so the first cycle of a user who just cloned installs them on their side. `hooks remove` sets `off`. The block is delimited by `# >>> rgkb >>>` / `# <<< rgkb <<<`: a third party's hook is completed, never overwritten (BK-02). `RGKB_NO_HOOK=1` neutralizes them on an ad hoc basis.

## Phase 6 — Wiring existing agents and skills (CX-12 to CX-14)

Skipped if `--no-wire`. The block content comes from the **templates** `assets/blocks/{read-only,builder,orchestrator}.md` (RD-06, parameterized by the interpreter and the agent name: nothing is written anew for the agent concerned, which makes `--upgrade` idempotent): `K cx wire --root . --interp "<PY>"`, without `--blocks-file` (targets present in `survey`: `factory-planner`, `factory-verifier`, `lab-director`, `lab-neuro`, `lab-math`, `lab-verifier`, `factory-builder`, `lab-builder`, `factory-run`, `lab-run`). The core sets a re-entrant `<!-- rgkb:debut -->` … `<!-- rgkb:fin -->` block per target (replacing it if it exists), completes `tools` of agents with a restrictive list with the 7 read tools (an agent does not see MCP tools not named in it; without a `tools` field, nothing is added) and the `--allowedTools` list of `ci/factory.*` and `ci/lab.*`, removing nothing.

**6a. Read-only agents** (`factory-planner`, `factory-verifier`, `lab-director`, `lab-neuro`, `lab-math`, `lab-verifier`) — the block requires: start with `mcp__rgkb__status` (stale index: take it into account and say so, without reindexing); ask for a file's card (`mcp__rgkb__file_card`) before reading it in full; before concluding that a symbol does not exist or is used nowhere, `mcp__rgkb__definition` then `mcp__rgkb__neighbors` (an empty `Grep` proves nothing); consult `mcp__rgkb__notes` **before** forming an opinion and cite the `n-…` identifier of a note it relies on. These agents never write a note.

**6b. Agents that touch code** (`factory-builder`, `lab-builder`, without `tools`) — the block requires: get your bearings before writing (`definition`, `neighbors` on the symbols that the spec or protocol names); read `notes` on the files to modify; reindex after modification (`mcp__rgkb__reindex` or `R index`) so the Verifier works on an up-to-date index; record **no interpretation** as a note: the Builder reports, it does not conclude.

**6c. Orchestration skills** (`factory-run`, `lab-run`) — two anchor points, without renumbering the steps: **before the first phase that spends** (Plan, Scoping), `R status` then `R index` if stale (scoping on a stale index produces a wrong plan, the most expensive error in the chain); **at the final recording**, after approval, propose `mcp__rgkb__note_add` notes for what the code does not say (a decision and its reason, a pitfall, a measured result, a sensitive area): `subject` = file path or symbol, otherwise a stable free-form subject; `source` = the spec or protocol; one or two `tags`. **One to three notes per cycle, no more**: a base that records everything is no longer readable. Never record what the index finds on its own. The final report cites the notes added and reminds that `.knowledge/` gets committed.

## Phase 7 — Final report

- **prerequisites**: ripgrep version (or the action to obtain it), interpreter chosen;
- **files** and their state (CX-16): server, `.mcp.json`, `settings.json`, `.knowledge/*`, `tasks.json`, agents and skills wired;
- **index**: files, symbols, edges, languages, Phase 4 warnings; **wiring**: named list, or `--no-wire`;
- **to commit**: `.knowledge/` (except `config.local.json`), `.claude/rgkb/rgkb.py`, `.mcp.json` and the merged configurations — this list, and only this list, makes the base travel;
- **second user**, in three lines: after `git clone` the base is queryable without rebuilding anything; hooks install themselves on the first `status` or `index` if the repository declares them; only `rg` may be missing for them — they then create their `config.local.json` with their `rg_path`;
- **usage**: agents use `mcp__rgkb__*` without typing anything; in a session `R search "pattern"`, `R neighbors <symbol>`; without hooks, `R index` by hand.

Remind that a restart of Claude Code is needed to load the MCP server from `.mcp.json`, the CLI working immediately.

## Defaults under the `auto` policy (AP-09)

The `--autonomy gate|auto` option (AP-03) applies to this run only and never writes `.claude/harness.json`; it is passed to `K gate decide --autonomy` and to chained skills (AP-04). Default of each gate of this skill under `auto`, with its one-line justification (the one from the `K gate list` catalog):

- `code-index.rg-install` → local fallback — a system dependency is not installed unasked; local fallback reported
- `code-index.hooks` → hooks install — the default stated by code-index:113
