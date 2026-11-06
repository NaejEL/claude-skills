# SPEC — Guard: strict whitelist for heredoc bodies (fix the part A bypasses)

Status: DELIVERED
Blocking questions: none
Depends on: SPEC-backlog-b-audit-labels
Files scope: skills/**, .claude/harness/**, .claude-plugin/**, specs/harness-v2/BACKLOG.md, .harness/tmp/**

## Context

Part A (`SPEC-backlog-a-guard-upgrade`, item 1) made heredoc bodies data; part B re-analysed `$( )` in unquoted bodies. An independent review then bypassed the guard (real hook, exit 0) with:
- a `<<EOF` inside a shell comment: `echo hi # <<EOF` + `rm -rf src` + `EOF` (also `#<<EOF`, `# note <<EOF`);
- an escaped delimiter: `cat <<E\OF` + `x` + `EOF` + `rm -rf src`;
- a shell reached through wrapper options or glued syntax: `sudo -u root bash <<EOF`, `cat <<EOF | sudo -u root sh`, `timeout 5 bash <<EOF`, `bash<<EOF`, `cat <<EOF | (sh)`, `| { sh; }`, `| ssh host sh`, `bash -s -- -abc <<EOF`;
- also unanalysed: `bash <<< 'rm -rf x'`, `source /dev/stdin <<EOF`, `. /dev/stdin <<EOF`.

User decision (2026-11-06): **strict whitelist, fail closed**.

## Scope

1. `hcore/guard.py`: a heredoc body is treated as data **only if all** of these hold; otherwise the whole body is analysed as commands (the behavior before part A):
   - the delimiter is a quoted plain word: `<<'WORD'` or `<<"WORD"` (also with `-`), `WORD` matching `[A-Za-z_][A-Za-z0-9_]*`;
   - no unquoted `#` appears before the `<<` on that line;
   - the piece of the command line that owns the heredoc is, after stripping `VAR=value` assignments only (no wrapper stripping), one of: `cat`, `tee <file>`, `py`, `py -3`, `python`, `python3` (each optionally followed by `-`), or `git commit` with `-F -` / `--file=-` / `-F-`;
   - nothing else on the line pipes into or out of that piece (`|`), and the line holds no other heredoc.
   Remove the part B "substitutions in unquoted body" logic if it becomes dead code; keep the part B tests that still apply (they must still BLOCK).
2. Here-strings `<<<` are analysed as commands when fed to a shell or to `source`/`.`; `source /dev/stdin` and `. /dev/stdin` with a heredoc are analysed as commands.
3. `hcore/migrate.py` (missed by part A, item 6): rewrite `findings.jsonl` only when its content changes; behavior test (mtime or bytes unchanged on a second run).
4. Generated hook wrapper (`hcore/hooks_install.py`): an interpreter candidate is used only if it actually runs (`"$p" -c ""` succeeds), so a Windows Store `python3`/`python` stub is skipped; if none runs, the wrapper prints one warning line to stderr (still exit 0, as HK-04 requires).
5. `skills/_core/profiles/research/install.md` names the English lab task labels the code now writes.
6. Bump `.claude-plugin/plugin.json` to the next patch; refresh `.claude/harness/` (`sf copy-core --refresh`, `core history --rebuild`).

## Acceptance criteria

- Behavior tests in `skills/_core/tests/test_hook_guard.py` (or the existing guard test module), each through `analyze()` **and** at least a few through the real hook (`hooks/hook.py pre-bash` with a JSON payload):
  - BLOCK: every bypass listed in Context; `cat <<EOF` with `$(rm -rf /)` in the body; `bash <<'EOF'`/`sh <<EOF` with `rm -rf x`; `cat <<'EOF' | sh` with `rm -rf x`; `cat <<EOF; rm -rf src`; `rm -rf .harness/tmp/../src`.
  - PASS: `cat <<'EOF'` with `rm -rf /` in the body; `py -3 - <<'EOF'` and `python3 - <<'EOF'` with Python mentioning `rm -rf`; `git commit -F - <<'EOF'` with a message mentioning `rm -rf`; `rm -rf .harness/tmp/x`; `rm .harness/tmp/*.py`.
- `cd skills/_core/tests && py -3 -B -m unittest discover -s . -t .` passes (module by module if over 10 minutes); `bash ci/test-harness.sh` and `pwsh -NoProfile -File ci/test-harness.ps1` pass.
- `diff -rq skills/_core .claude/harness`: only `MANIFEST.json`.

## Frugality rules (mandatory)

- Scratch files under `.harness/tmp/` only, deleted with literal paths. Never write into the real `~/.claude/` or `HOME`.
- No tests reading prose; no mutation campaigns.
- Verifier: reads `guard.py` in full and **tries to bypass it** (comments, escaped/odd delimiters, wrappers with options, glued `<<`, pipes into subshells or groups, here-strings, CRLF); major defects only; minor ones to BACKLOG §8.

## Out of scope

`eval` (by design), any other guard category, any commit or push.
