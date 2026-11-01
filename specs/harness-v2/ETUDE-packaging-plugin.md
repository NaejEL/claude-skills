# Étude — Remplacer `install_skills.*` par un plugin Claude Code ?

Statut : ÉTUDE (Phase 7 de `specs/harness-v2/ROADMAP.md`, sans implémentation). La décision revient à l'utilisateur.

## Question

Faut-il distribuer les skills de ce dépôt comme un plugin Claude Code (version, mise à jour, distribution), au lieu des liens créés par `install_skills.sh` (symlinks) et `install_skills.ps1` (jonctions) ?

## Sources

L'agent qui a rédigé cette étude n'avait pas d'accès au réseau. Les faits marqués [D] sont à reconfirmer à la lecture des pages citées avant toute décision.

- **[S1]** https://code.claude.com/docs/en/plugins : « Plugin structure overview », « Test your plugins locally » (`--plugin-dir`).
- **[S2]** https://code.claude.com/docs/en/plugins-reference :
  - « Plugin manifest schema » (`name`, `version`) ;
  - « Environment variables » (`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`) ;
  - « Plugin caching and file resolution » ;
  - « Version management » ;
  - « Plugin installation scopes » ;
  - « CLI commands reference » (`claude plugin install|update|validate`).
- **[S3]** https://code.claude.com/docs/en/plugin-marketplaces : « Create the marketplace file », « Plugin sources », « Host and distribute marketplaces ».
- **[S4]** https://code.claude.com/docs/en/discover-plugins : « Install plugins », « Configure auto-updates ».
- **[S5]** https://code.claude.com/docs/en/skills : « Where skills live » (espace de noms `plugin-name:skill-name`), « Available string substitutions » (`${CLAUDE_SKILL_DIR}`).
- **[S6]** https://code.claude.com/docs/en/settings : `enabledPlugins`, `extraKnownMarketplaces`.
- **[B5]** `specs/harness-v2/BACKLOG.md` §5, faits vérifiés le 2026-10-16 : pas d'installation de binaires système ; noms `/plugin:skill` ; `version` dans `plugin.json`.
- **[R1]** BACKLOG §7, recette R1 : `${CLAUDE_SKILL_DIR}` = chemin du lien ; `_core` sans `SKILL.md` n'est pas exposé.
- **[L]** Copie locale du plugin officiel `plugin-dev` : `C:\Users\fuzzz\.claude\plugins\marketplaces\claude-plugins-official\plugins\plugin-dev\skills\plugin-structure\SKILL.md`, sections « Directory Structure » et « Auto-Discovery Mechanism », et `references\manifest-reference.md`, section « Path Resolution » (`../` interdit dans les chemins de composants).

## Ce que ça apporte

1. **Une version déclarée** : `version` dans `.claude-plugin/plugin.json` [B5][S2]. Le tampon de la Phase 3 (« tag git ou hash ») et `/harness-doctor` ont enfin une source unique de version, lisible sans `.git`.
2. **Une mise à jour outillée** : `claude plugin update`, mise à jour de la marketplace, mise à jour automatique au démarrage si on l'active [S4][D]. Elle remplace « `git pull` du clone, puis relancer l'installeur ».
3. **La distribution** : ce dépôt peut être sa propre marketplace, avec `.claude-plugin/marketplace.json` et une source `./` [S3][D]. On installe sur une autre machine en deux commandes. En portée projet, `enabledPlugins` dans `.claude/settings.json` [S2][S6][D] fait proposer le harnais à un coéquipier qui clone un projet équipé.
4. **Plus de liens** : l'installation copie le plugin dans un cache [S2][D]. Il n'y a plus de jonctions ni de symlinks, plus de dépendance à `$HOME`, plus de conflit « dossier réel » (`install_skills.sh:190-192`). Le défaut potentiel de `ln -s` sous Git Bash (Phase 6, Q7) disparaît.
5. **Une disposition déjà compatible** : `skills/<nom>/SKILL.md` à la racine est la disposition par défaut d'un plugin [S1][L]. Il suffit d'ajouter `.claude-plugin/plugin.json` ; aucun skill n'est à déplacer.
6. **Une impossibilité levée** : un plugin peut livrer des agents fichiers (`agents/`) [S1][L]. La Phase 2 avait classé l'agent global `harness-scout` en [IMPOSSIBLE] I2. Ce n'est pas une obligation, seulement une possibilité.
7. **Une vérification sans LLM** : `claude plugin validate` [S2][D] donne à la Phase 6 un scénario d'installation de plus.

## Ce que ça casse

| Point | Verdict | Détail |
| --- | --- | --- |
| Installation de ripgrep | Perte limitée | Un plugin n'installe pas de binaire [B5]. Mais `code-index` propose déjà lui-même l'installation de `rg`, sous gate `code-index.rg-install` (CX-02, `code-index:38`). Seule perte : `rg` n'est plus installé d'avance, avant le premier `/code-index`. |
| Jonctions Windows | Disparaissent | Plus nécessaires pour l'usage (point 4). Pour développer ce dépôt : `claude --plugin-dir <dépôt>` charge le plugin en place [S1][D]. |
| Modifications du dépôt invisibles | **Nouveau piège** | Le cache est indexé par version [S2][D] : un contenu modifié sans changement de `version` n'est pas redistribué. C'est l'équivalent exact du piège NuGet « même version, contenu différent » de la règle globale de l'utilisateur. Une garde est indispensable : un test qui refuse tout changement sous `skills/` depuis la dernière étiquette sans hausse de `version`. |
| `${CLAUDE_SKILL_DIR}/../_core` | Probablement OK, recette P1 obligatoire | Les fichiers hors de la racine du plugin ne sont pas copiés dans le cache [S2][D], et `../` est interdit dans les chemins de composants du manifeste [L]. Mais `skills/ship-pr/../_core` = `skills/_core`, qui est **dans** la racine et donc copié. `${CLAUDE_SKILL_DIR}` désigne le sous-dossier du skill dans le plugin [S5][D]. Un `_core` sans `SKILL.md` n'est pas découvert comme skill [L], comme en mode liens [R1]. On garde `${CLAUDE_SKILL_DIR}/../_core`, qui marche dans les deux modes, plutôt que `${CLAUDE_PLUGIN_ROOT}`, qui n'existe qu'en plugin. |
| Chemin du cache variable | OK | Le chemin change à chaque version [S2][D] : rien de persistant ne doit y pointer. Vérifié dans le code : `sf copy-core` copie le noyau sous `.claude/harness/` (`software-factory:67`), `rgkb.py` est copié sous `.claude/rgkb/` (`code-index:53`), et `.mcp.json` ne contient aucun chemin absolu (`code-index:29`). Les hooks de la Phase 5 doivent pointer vers `.claude/harness/`, jamais vers `${CLAUDE_PLUGIN_ROOT}`. |
| Projets déjà équipés | Aucune rupture technique | Ils exécutent leur copie `.claude/harness/`. Le tampon de la Phase 3 note un hash git, absent du cache : la version doit venir de `plugin.json`, et les tampons existants doivent pouvoir être rapprochés (étiquette git = `version`). |
| Noms préfixés | **Casse** | Les skills deviennent `/<plugin>:<skill>` [B5][S5]. Sont touchés : (1) les textes qui citent `/ship-pr`, `/audit`, `/software-factory --upgrade`, `/harness-doctor` ou `/code-index` (rapports, `STOP-*.md`, README, blocs générés) ; (2) les invocations par l'outil Skill des alias (AX-01, AX-04 de la Phase 2) et les enchaînements de la Phase 4 ; (3) tout `claude -p "/ship-pr …"`. Ne sont pas touchés `/factory-run` et `/lab-run`, qui sont des skills **projet**. La forme courte, sans préfixe, n'est pas confirmée : recette P3. |
| Double installation pendant la transition | Casse si non traitée | Liens et plugin ensemble = chaque skill apparaît deux fois (`/ship-pr` et `/<plugin>:ship-pr`), avec des descriptions en double dans le contexte. La migration doit retirer les liens. |
| Hooks dans le plugin | À ne pas faire | `hooks/hooks.json` est actif partout où le plugin est activé [S1][L]. Les hooks de la Phase 5 doivent être contextuels (§5) : ils restent dans le `settings.json` du projet. |
| Python | Inchangé | Prérequis dans les deux modes. |

## Plan de migration (si la réponse est oui)

- **M0 — Recettes** (ci-dessous) sur une copie : d'abord `--plugin-dir`, puis marketplace locale. Un échec de P1 ou de P3 arrête le plan.
- **M1 — Manifestes.**
  - Ajouter `.claude-plugin/plugin.json` (`name`, `version`) et `.claude-plugin/marketplace.json` (source `./`) à la racine.
  - Ajouter la garde de version (tableau ci-dessus) et `claude plugin validate .` aux scénarios de `ci/test-harness.*`.
  - Aucun skill modifié.
- **M2 — Indépendance au mode.**
  - Les textes et invocations qui citent une autre commande reçoivent du noyau le nom effectif (`/ship-pr` ou `/<plugin>:ship-pr`), au lieu de l'écrire en dur.
  - Le tampon et `/harness-doctor` lisent la version dans `plugin.json` quand il existe.
  - `--upgrade` régénère les blocs qui citent des commandes.
- **M3 — Une version à double canal.**
  - `install_skills.*` reste, affiche un avertissement de retrait et la commande d'installation du plugin.
  - Il gagne une option qui retire **seulement** les liens qu'il a créés, vers ce dépôt.
  - README : section « Installer » avec les deux voies.
- **M4 — Version suivante.** `install_skills.*` est retiré, et `rg` est confié à `code-index` (déjà en place).
- **Projets équipés.** Rien à faire de leur côté : `/harness-doctor --scan` signale le changement de source de version, et `--upgrade` met à jour les blocs.

## Recettes préalables

- **P1** : depuis un skill du plugin installé par marketplace locale (donc depuis le cache), `${CLAUDE_SKILL_DIR}/../_core/harness.py version` répond, sous Windows et sous Git Bash ; `_core` n'apparaît pas dans `/skills`.
- **P2** : `sf copy-core` lancé depuis le cache produit un `.claude/harness/` complet, `profiles/` compris.
- **P3** : `/ship-pr` en forme courte fonctionne-t-il, ou seulement `/<plugin>:ship-pr` ? Même question en headless (`claude -p`, `MSYS_NO_PATHCONV=1`) et par l'outil Skill depuis un alias.
- **P4** : hausse de `version` → `claude plugin update` → nouveau chemin de cache, et un projet équipé fonctionne toujours. Sans hausse : pas de mise à jour, ce qui confirme le piège.
- **P5** : coexistence liens + plugin observée, puis retrait des liens.
- **P6** : `claude plugin validate .` sur le dépôt.

## Recommandation

**Oui, en différé et sous condition.**

Pour :
- L'objectif de la ROADMAP est « un harnais versionné […] capable de se mettre à jour ». Côté skills globaux, c'est exactement ce que le plugin fournit (version, mise à jour, distribution), alors que les liens n'ont aucune notion de version.
- La disposition du dépôt est déjà celle d'un plugin.
- Les projets équipés ne dépendent pas du mode d'installation, grâce aux copies `.claude/harness/` et `.claude/rgkb/`.
- La perte sur ripgrep est couverte par `code-index`.

Contre, à peser :
- Les noms préfixés, si P3 échoue sur la forme courte.
- La discipline de version obligatoire, sans quoi le cache sert un contenu périmé.
- Un gain de distribution faible tant qu'il n'y a qu'un utilisateur. Sur cette machine, l'installeur n'a même jamais été lancé (BACKLOG §5).

Conditions :
1. Ne pas migrer avant la Phase 3 livrée, puisque c'est elle qui consomme la version, ni avant la Phase 6, qui doit tester les deux modes.
2. P1 et P3 doivent passer.
3. La garde de version doit être en place dès M1.

Si P1 ou P3 échoue : rester sur `install_skills.*` et versionner par étiquette git seulement.

## Résultats des recettes (2026-11-01)

Exécutées sur une copie (`git archive HEAD`) avec `.claude-plugin/plugin.json` et `marketplace.json` (source `./`), et un skill `probe` jetable. P4 a utilisé un `CLAUDE_CONFIG_DIR` temporaire, pour ne pas toucher au `~/.claude` réel. Coût en modèle : moins de 0,01 $.

| Recette | Résultat | Détail |
| --- | --- | --- |
| Nom | **Échec du nom `claude-skills`** | `claude plugin validate` refuse : « Plugin name "claude-skills" is reserved ». Un nom tiers ne peut pas commencer par `claude-`. Il faut un autre nom. |
| P1 | Passe (`--plugin-dir`) | `${CLAUDE_SKILL_DIR}` = `<plugin>/skills/probe`, et `${CLAUDE_SKILL_DIR}/../_core/harness.py version` répond (`core_version 4.0.0`). `_core` n'apparaît pas parmi les commandes. Depuis le cache, `harness.py` répond aussi quand on l'appelle par son chemin. Seul l'appel via un skill chargé depuis le cache n'a pas été fait, faute de session authentifiée dans la configuration isolée. |
| P2 | Passe | `sf copy-core` lancé depuis le plugin produit un `.claude/harness/` complet, `profiles/` compris. |
| P3 | Passe | Les skills sont exposés sous `/harness:<skill>`, mais la forme courte `/probe` fonctionne aussi en headless (`claude -p`). |
| P4 | Piège confirmé | Le cache est indexé par version (`cache/<marketplace>/<plugin>/<version>/`). Un contenu modifié sans hausse de `version` n'arrive pas dans le cache, et `claude plugin update` répond « already at the latest version ». Après une hausse à 2.0.1, une nouvelle entrée de cache apparaît avec le contenu à jour. La garde de version est donc indispensable. Avec une marketplace de type dossier local, la CLI dit pourtant que le plugin « is read from its folder […] Edits there take effect at the next session start ». Le chemin réellement chargé est à confirmer en session. |
| P5 | Sans objet ici | `~/.claude/skills` ne contient aucun lien vers ce dépôt (l'installeur n'a jamais tourné). Il n'y a donc pas de doublon à observer sur cette machine. |
| P6 | Passe | `claude plugin validate .` passe une fois le nom changé, avec deux avertissements : `author` et la description de la marketplace. |

Conclusion : P1, P2, P3 et P6 passent. Les conditions 2 et 3 de la recommandation sont tenables, mais il faut un nom qui ne commence pas par `claude-`.

Point à trancher par l'utilisateur : le nom du plugin. `harness` donne `/harness:ship-pr`, mais aussi `/harness:harness-doctor`. `claude-skills` est plus long, sans redondance. La règle commune « pas d'autre renommage » interdit de renommer les skills pour compenser.
