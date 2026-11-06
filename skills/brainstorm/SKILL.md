---
name: brainstorm
description: Brainstorming and ideation as a challenging, convergent co-reflection on a free-form subject — five parallel lenses in a fresh context (implicit assumptions, radical alternatives, counter-examples, cost and feasibility, second-order effects) that contest the submitted idea and produce angles absent from the statement, a human gate at every round, a hard cap of 3 rounds then forced convergence to a synthesis of at most 5 leads. Use when the user wants to be challenged on an idea and bring out what they have not thought of, with an explicit end rather than an endless flow of ideas.
context: fork
user-invocable: true
argument-hint: "[subject or idea to challenge] [--rounds N]"
---

# Brainstorm — challenging, convergent co-reflection

Take an idea submitted by the user and put it under tension rather than validate it: at each round, launch five parallel lenses in a fresh context, bring up the angles the statement did not anticipate, confront the user through a human gate, and **close** — three rounds at most, then a forced convergence to five leads at most. This is not a volume idea generator: its success is measured by the quality of the ending it produces.

## Deterministic core

The deterministic rules are Python code (standard library, ≥ 3.9) in `${CLAUDE_SKILL_DIR}/../_core/`: never reimplement them, call the `harness.py` CLI (`bs`) and follow its JSON output. Rules: **BS-01** to **BS-12** (`hcore/bs.py`), **GT-01** to **GT-08** (dialogue gates: always `ask`, GT-04), **JR-01**, **JR-02**. **Interpreter**: `<PY>` = the first of `python`, `python3`, `py -3` that answers in under 5 s with a version ≥ 3.9: `t=; command -v timeout >/dev/null && t="timeout 5"; for c in python python3 "py -3"; do $t $c -c "import sys; print(sys.version_info >= (3, 9))" 2>/dev/null | grep -q True && { echo "$c"; break; }; done`; `K` = `<PY> "${CLAUDE_SKILL_DIR}/../_core/harness.py"`.

**No disk write before the final gate** (X5): the core is stateless, the session holds its own state (registry, round, gate answers) and passes it **on standard input**, in a quoted-delimiter heredoc (`K bs round <<'BS' … BS`), never as an argument or file. The journal is written with the synthesis, at the final gate.

## Mandatory rules (all phases)

- **Contest the submitted idea, systematically.** Each round produces at least one named objection to the statement: an assumption taken for granted, a case where the idea does not hold, an unquantified cost. State it plainly, with what grounds it.
- **No complacent or default approval.** Never a compliment as an opener, never "good idea" without a test that establishes it, never a lead retained solely because it comes from the user. Agreement is legitimate only with the observable reason that made the objection fall. A round that found nothing to contest says so as is — that is a result, not a failure to hide behind filler ideas.
- **Mark each lead `[in the brief]` or `[outside the brief]`** (`enonce` / `hors-enonce`): present, even in embryo, in `SUBJECT` or in an answer of the user, or absent from everything they wrote. **At least one `[outside the brief]` lead per round**; if the lenses return none, say so — that is the trigger for the early exit, never a pretext to invent.
- **Cumulative registry of discarded leads** `{title, marking, round, reason, by whom}` for the whole session. A lead in the registry is **never** re-proposed, neither as is, nor reworded, nor re-split: the core removes identical titles (BS-03); **rewording stays your judgement** — flag it in one line and remove it.
- **Sorting belongs to the user** (gates, AskUserQuestion). Without possible interaction (headless, `claude -p`, no interactive terminal), **stop with an explicit error** before the first round: "/brainstorm is inherently dialogued: it co-reflects with the user round by round and cannot produce a synthesis without their arbitration. Relaunch in an interactive session." Neither synthesis nor file.
- **Frugality**: lenses = sub-agents in a fresh context receiving the round briefing and their lens alone, never "explore everything".

## Phase 1 — Arguments, resume and anchoring

1. `K bs args <<'BS'` + `$ARGUMENTS` + `BS` returns `subject` (BS-01: all non-option tokens, word for word), `rounds` (BS-02: `--rounds` bounded to `min(N, 3)`, default 3; non-integer or `< 1` → explicit error), `slug` and `path` `BRAINSTORM-<slug>.md` (BS-09). **Empty subject**: before any reconnaissance and any sub-agent, gate `brainstorm.subject` ("What do you want us to co-reflect on?", option "free input", free input).
2. **Resume** (BS-10): `K bs resume --path <path>` loads the "Angles écartés" section of the file of the same subject into the registry from round 1 (failing that, judge whether another `BRAINSTORM-*.md` overlaps the subject); report "session resumed from `<file>`".
3. **Anchoring, hard budget of 12 files read**: if `SUBJECT` has nothing to do with the current directory, cut short ("reconnaissance cut short: the subject is unrelated to the current directory"); otherwise `README.md`, `CLAUDE.md`, the 2-level tree and the files named by the subject, never exploring beyond. Produce the **anchoring** in a few lines (subject, resume, relevance, files read, constraints, `rounds`).

## Phase 2 — Challenge round: five lenses in parallel

At each round, **in a single message**, the five fixed lenses in a fresh context: none sees the others. **`hypotheses`** (what the statement takes for granted and which, if false, brings the idea down), **`alternatives`** (other ways to reach the goal, including doing nothing or acting upstream), **`contre-exemples`** (cases, precedents or volumes where the idea breaks or produces the opposite), **`cout`** (time, money, complexity, maintenance, skills; what makes it infeasible here), **`second-ordre`** (perverse incentives, dependencies, effects on other actors, exit cost once it works). Each prompt contains: `SUBJECT` word for word, the anchoring, the round state (number, arbitrations), the registry list forbidden from re-proposal, its lens **and nothing else**, the mandatory marking, "never validate the idea by default: your output contains at least one named objection", the sentence "**returning fewer leads than a maximum is a normal and acceptable answer**", the ban on writing to disk, and a single final JSON block of at most 4 leads (BS-04):

```json
{"pistes": [{"id": "HYP-01", "lens": "hypotheses", "origine": "enonce|hors-enonce",
  "titre": "short wording", "these": "the claim in one sentence",
  "appui": "fact, precedent, excerpt ≤ 3 lines, or explicit reasoning",
  "consequence": "what it changes for the idea if true", "question_a_trancher": "the question to ask, in one sentence"}],
 "objection_principale": "the strongest objection to the statement, in one sentence"}
```

**A silent lens is not a lens with no objection.** Pass the five extracted blocks to the core (`null` for a dead agent): `K bs round <<'BS' {"round": n, "rounds": R, "lenses": {…}, "discarded": […], "relaunched": […]} BS`. `action: relaunch` → relaunch the named lenses **once** and call again with `relaunched`; then `synthesize`: the lens that is still silent is **named** (`missing_lenses`) in the round synthesis, in the gate and in the file, and the **early exit is disabled for this round** (BS-05).

## Phase 3 — Round synthesis and human gate

In the main session: `pistes` (deduplicated by the core against the registry, `removed` to report), grouped by tension (lenses that contradict each other are a result, not to be smoothed over), ranked by strength of support, with their marking, thesis, support and consequence, **the round's main objection first**. If `early_exit` (BS-06: no `[outside the brief]` lead survived): announce "early exit: no new off-statement angle at round <n>" and go to Phase 4. Otherwise, gate `brainstorm.round` (mandatory at the end of each round): for the main angles **Dig** (the next round starts from there) / **Discard** (to the registry, with its reason, definitively) / **Amend** (the amended version replaces the original), plus **continue** or **converge**. Group the angles by question, always offer free input. If `converge` and `ceiling` (BS-07): "cap of <rounds> rounds reached, moving to convergence", no extra round even if requested; otherwise, if the user continues, next round.

## Phase 4 — Convergence and final gate

No new lead here: the sorting of what survived. Rank the leads (strength of support, effect on the initial idea, cost) and **decide**: the core retains the **top 5** (BS-08, hard non-configurable cap) and files the others under "Angles not retained in this cycle" with their rank; never hand the decision back to the user to avoid deciding. Write `idea` (the idea after confrontation: what holds, what moved, what fell) and `objections` (those that held, and why), then `K bs render --root . <<'BS' {"subject", "idea", "objections", "ranked": [{"title", "marking", "body"}], "discarded": [{"title", "marking", "round", "reason", "by"}], "played", "rounds", "end": "ceiling|early|requested", "missing_lenses"} BS` returns the synthesis (BS-11): deliver it **in the conversation**. **Chaining suggestion** if an angle is directly implementable: `/factory-run "<the angle worded as a need>"` or `/lab-run "<the angle worded as a falsifiable question>"` — display it, **never launch it**, otherwise suggest nothing.

**Final gate** `brainstorm.write`: **Write the synthesis** / **Write nothing**. Then `K bs finish --root . <<'BS' {…same data, "gates": [{"id", "answer"}] for each gate asked, "write_answer": "<option>"} BS`: it writes the journal `.harness/runs/brainstorm-<timestamp>.jsonl` (the gates asked, then the last one) and, on *Écrire*, `BRAINSTORM-<slug>.md` (FD-11 checked) **keeping all the lines of the former "Angles écartés" section** (BS-10) so that a later session does not resurrect them. On *Write nothing*, no synthesis file: say so explicitly.
