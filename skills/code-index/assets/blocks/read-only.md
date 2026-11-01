## Base de connaissance du dépôt (rgkb)

Tu disposes des outils `mcp__rgkb__*` (CLI équivalente : `{{interpreter}} .claude/rgkb/rgkb.py`). Pour `{{agent}}` :

- Commence par `mcp__rgkb__status` : si l'index est périmé, tiens-en compte et dis-le, sans réindexer.
- Demande la fiche d'un fichier (`mcp__rgkb__file_card`) avant de le lire en entier.
- Avant de conclure qu'un symbole n'existe pas ou n'est utilisé nulle part, appelle `mcp__rgkb__definition` puis `mcp__rgkb__neighbors` : un `Grep` vide ne prouve rien.
- Consulte `mcp__rgkb__notes` **avant** de formuler un avis et cite l'identifiant `n-…` de toute note sur laquelle il repose.
- N'écris jamais de note : tu es en lecture seule.
