## Base de connaissance du dépôt (rgkb)

Pour `{{agent}}`, deux points d'ancrage, sans renuméroter les étapes :

- **Avant la première phase qui dépense** (Plan, Cadrage) : `{{interpreter}} .claude/rgkb/rgkb.py status`, puis `{{interpreter}} .claude/rgkb/rgkb.py index` si l'index est périmé : un cadrage sur index périmé produit un plan faux, l'erreur la plus chère de la chaîne.
- **À la consignation finale**, après approbation : proposer des notes `mcp__rgkb__note_add` pour ce que le code ne dit pas (décision et sa raison, piège, résultat chiffré, zone sensible). `subject` = chemin de fichier ou symbole, sinon sujet libre stable ; `source` = la spec ou le protocole ; un ou deux `tags`. **Une à trois notes par cycle, pas davantage** ; ne jamais consigner ce que l'index retrouve seul. Le rapport final cite les notes ajoutées et rappelle que `.knowledge/` se commite.
