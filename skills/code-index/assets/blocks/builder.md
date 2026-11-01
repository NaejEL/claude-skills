## Base de connaissance du dépôt (rgkb)

Tu disposes des outils `mcp__rgkb__*` (CLI équivalente : `{{interpreter}} .claude/rgkb/rgkb.py`). Pour `{{agent}}` :

- Situe-toi avant d'écrire : `mcp__rgkb__definition` et `mcp__rgkb__neighbors` sur les symboles que la spec ou le protocole nomme.
- Lis `mcp__rgkb__notes` sur les fichiers à modifier.
- Après modification, réindexe (`mcp__rgkb__reindex` ou `{{interpreter}} .claude/rgkb/rgkb.py index`) pour que le Verifier travaille sur un index à jour.
- Ne consigne **aucune interprétation** en note : tu rapportes, tu ne conclus pas.
