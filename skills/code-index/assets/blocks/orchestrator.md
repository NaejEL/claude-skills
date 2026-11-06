## Repository knowledge base (rgkb)

For `{{agent}}`, two anchor points, without renumbering the steps:

- **Before the first phase that spends** (Plan, Scoping): `{{interpreter}} .claude/rgkb/rgkb.py status`, then `{{interpreter}} .claude/rgkb/rgkb.py index` if the index is stale: scoping on a stale index produces a wrong plan, the most expensive error in the chain.
- **At the final recording**, after approval: propose `mcp__rgkb__note_add` notes for what the code does not say (a decision and its reason, a pitfall, a measured result, a sensitive area). `subject` = file path or symbol, otherwise a stable free-form subject; `source` = the spec or protocol; one or two `tags`. **One to three notes per cycle, no more**; never record what the index finds on its own. The final report cites the notes added and reminds that `.knowledge/` gets committed.
