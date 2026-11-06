# SPEC — Translate the harness to English (skills, docs, core templates)

Statut : APPROUVEE
Questions bloquantes : aucune
Périmètre fichiers : skills/**, README.md, ci/**, .claude/agents/**, .claude/skills/**, .claude/harness/**, .claude-plugin/**, specs/harness-v2/BACKLOG.md, tests/fixtures/**

## Context

User decision (2026-11-01): the whole harness becomes English — Markdown prose included, which reverses the earlier "Markdown prose in French" house rule. Code, comments and strings are already English. This cycle is also the first real-use test of the harness on itself (version guard, repo factory, upgrade).

## Scope

1. **Translate to English** every French Markdown/prose file under:
   - `skills/*/SKILL.md` (14 skills, frontmatter `description` included; `name` unchanged);
   - `skills/_core/` Markdown and data: `profiles/**`, `templates/**`, `scout/**`, `STAMP.md`, `hooks/**` docs, and any French user-facing text in JSON data files;
   - `README.md`, `ci/**` (docs and messages);
   - the repo factory `.claude/agents/factory-*.md` and `.claude/skills/factory-run/SKILL.md`, including the out-of-block "house rules" section: the rule becomes "Code, comments, strings **and Markdown prose** in English".
   Translation is faithful: same structure, same headings order, same level of detail, no content added or dropped, no rewording of meaning. Command names, flags, file names, identifiers and finding IDs stay as they are.
2. **Spec keywords, both languages accepted** (`skills/_core/hcore/specfile.py` and every other place that parses or writes them — queue, stops, prioritize, convert, upgrade, templates):
   - accept the English forms `Status:` (`PROPOSED | APPROVED | BLOCKED | DELIVERED`), `Blocking questions:`, `Files scope:`, `Priority:`, `Depends on:`, `Answer:`, `none` — **and** keep accepting the French forms (`Statut :`, `PROPOSEE/APPROUVEE/BLOQUEE/LIVREE`, `Questions bloquantes :`, `Périmètre fichiers :`, `Priorité :`, `Dépend de :`, `Réponse :`, `aucune`), case- and spacing-tolerant as today;
   - everything the core **writes** (new specs from templates or audit conversion, status transitions such as `→ DELIVERED`, BLOCKED markers) uses English; a status transition on an existing French spec keeps that spec's language (it rewrites `Statut : APPROUVEE` to `Statut : LIVREE`, never mixes);
   - no migration of existing specs in equipped projects.
3. **Version**: bump `.claude-plugin/plugin.json` to `2.1.0` (the version guard must pass).
4. Refresh `.claude/harness/` with `py -3 skills/_core/harness.py sf copy-core --root . --refresh` and `core history --rebuild` as needed; then `upgrade plan`/`apply` the repo factory so its generated blocks are English (`.claude/agents`, `.claude/skills/factory-run`, `ci/factory.*`), keeping the out-of-block house rules (translated).

## Fixtures

- `tests/fixtures/**` and `ci/fixtures/**` that represent **legacy or user projects** (French old installs, legacy deliverables, migration inputs) are **not** translated: migration and upgrade tests depend on them.
- Fixtures that are **expected outputs** of current templates (e.g. expected merge results, generated files) are regenerated from the code, never hand-edited, and only where a test requires it.

## Acceptance criteria

- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passes (may be run module by module if over 10 minutes).
- `bash ci/test-harness.sh` and `pwsh -NoProfile -File ci/test-harness.ps1` pass, `plugin-guard` included.
- `bash -n install_skills.sh` passes; `claude plugin validate .` passes.
- Behavior tests for the keywords: an English spec and a French spec each parse to the same status/perimeter/priority/dependencies/blocking questions; a status transition keeps each spec's language; a spec produced by the core is English.
- No French prose left in the translated scope: a deterministic check (a script run by the Verifier, not a unit test reading prose) lists files in scope that still contain common French words; the remaining hits are only quoted French keywords, legacy fixture references or names.
- `.claude/harness/` equals `skills/_core/` except `MANIFEST.json` (`diff -rq`).

## Frugality rules (mandatory)

- Never **execute** `install_skills.*` against the real `HOME`.
- No tests that read SKILL.md prose; no mutation campaigns.
- The Verifier reads **every** new or changed code file in full and samples the translated Markdown (at least every SKILL.md frontmatter and one full SKILL.md, plus the README), reporting **major** defects only (meaning changed, content dropped, broken command/flag, untranslated file). Minor ones go to BACKLOG §8.
- Translate file by file with Write; do not load the whole repo into context at once.

## Out of scope

`specs/**` other than this spec and the BACKLOG line(s), legacy fixtures, M4 (removing `install_skills.*`), any commit or push.
