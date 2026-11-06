# SPEC — English translation, part 2: verification, scratch files, gate tokens

Status: DELIVERED
Blocking questions: none
Files scope: skills/**, README.md, ci/**, .claude/harness/**, .claude-plugin/**, specs/harness-v2/BACKLOG.md, .harness/tmp/**

## Context

Part 1 (`specs/SPEC-english.md`, uncommitted diff in the working tree) translated the skills, docs and core templates to English and made the core accept English and French spec keywords. Its cycle stopped before verification: the Bash guard blocked the Builder deleting its own scratch scripts in `C:\tmp` (STOP `destructive`). The house-rules sections of `.claude/agents/*` and `.claude/skills/factory-run/SKILL.md` were translated by hand since.

User decision (2026-11-02): agents write their scratch files under `.harness/tmp/` (git-ignored), where `rm` is allowed; the guard stays strict everywhere else, outside the project included.

## Scope

1. **Scratch directory**:
   - the core guard (`hcore/guard.py` deletable callback and whatever decides "generated") treats every path under `<root>/.harness/tmp/` as deletable (files and folders, `rm -r` included), and nothing else new;
   - `.harness/tmp/` is git-ignored in projects the core equips (same mechanism as the existing `.harness/` ignore rules, if any; otherwise via the generated ignore block) and in this repo;
   - the generated agent templates (Builder and Verifier at least, both profiles) state: scratch files go under `.harness/tmp/`, never in the system temp or elsewhere outside the project.
2. **Gate answer tokens in English**: the tokens in `hcore/gates.py` (`approbation / itérer`, `approbation`, `saisie libre`, `Jalon 1 / Jalon 2 / Jalon dernier / Exclure de la roadmap`, and any other French token or label there) become English (`approval / iterate`, `free input`, `Milestone 1 / Milestone 2 / Last milestone / Exclude from roadmap`, …); the skills that quote them follow. Where the core compares an answer to a token, the French form is still accepted.
3. **Tighten back** `test_repo_factory.py`: now that the house rules are English, it expects the English wording only.
4. Bump `.claude-plugin/plugin.json` if the guard requires it (2.1.0 is already uncommitted: no further bump needed unless the guard says so). Refresh `.claude/harness/` (`sf copy-core --refresh`, `core history --rebuild`).

## Acceptance criteria

- Behavior tests: `rm -rf .harness/tmp/x` and `rm .harness/tmp/a.py` pass the guard; `rm C:/tmp/a.py`, `rm /tmp/a.py`, `rm -rf ..`, `rm ../other/.harness/tmp/a` stay blocked.
- Behavior test: a gate answered with the French token and one answered with the English token give the same decision.
- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passes (module by module if over 10 minutes).
- `bash ci/test-harness.sh` and `pwsh -NoProfile -File ci/test-harness.ps1` pass, `plugin-guard` included; `bash -n install_skills.sh`; `claude plugin validate .`.
- `diff -rq skills/_core .claude/harness`: only `MANIFEST.json`.
- **Verification of part 1** (the Verifier, reading): every `SKILL.md` frontmatter, the full `README.md`, the full `skills/software-factory/SKILL.md` and `skills/ship-pr/SKILL.md`, and the code diff of `hcore/specfile.py` (both keyword languages; a status transition keeps the spec's language; new specs written in English). Major = meaning changed, content dropped, broken command/flag/identifier, file left in French. A deterministic script (run by the Verifier, not a unit test) lists in-scope files still containing common French words; remaining hits must be quoted French keywords, legacy fixture references or names.

## Frugality rules (mandatory)

- Scratch files under `.harness/tmp/` only.
- Never **execute** `install_skills.*` against the real `HOME`.
- No tests reading SKILL.md prose; no mutation campaigns.
- Verifier: major defects only; minor ones to BACKLOG §8.

## Out of scope

Historical `specs/`, legacy fixtures, `.claude/agents/**` and `.claude/skills/**` (house rules already done by hand; their generated blocks are refreshed by `upgrade apply` only if the templates change — run it through `harness.py`, not with Write), M4, any commit or push.
