## Repository knowledge base (rgkb)

You have the `mcp__rgkb__*` tools (equivalent CLI: `{{interpreter}} .claude/rgkb/rgkb.py`). For `{{agent}}`:

- Start with `mcp__rgkb__status`: if the index is stale, take it into account and say so, without reindexing.
- Ask for a file's card (`mcp__rgkb__file_card`) before reading it in full.
- Before concluding that a symbol does not exist or is used nowhere, call `mcp__rgkb__definition` then `mcp__rgkb__neighbors`: an empty `Grep` proves nothing.
- Consult `mcp__rgkb__notes` **before** forming an opinion and cite the `n-…` identifier of any note it relies on.
- Never write a note: you are read-only.
