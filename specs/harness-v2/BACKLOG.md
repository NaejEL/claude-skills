# Backlog — claude-skills v2

Mémoire de travail du chantier v2. Ce fichier prime sur `ROADMAP.md`, qui reste le texte d'origine, quand les deux divergent. Branche de travail actuelle : `v2/increment-1-noyau`. Spec en cours : `specs/SPEC-noyau-core-journal.md`.

Dernière mise à jour : 2026-10-16.

---

## 1. Décisions de l'utilisateur

| Date | Décision |
|---|---|
| 2026-10-16 | `ROADMAP.md` est une **feuille de route**, pas un besoin. Un cycle `/factory-run` = **une** spec pour **un** incrément, plus en annexe la liste ordonnée des specs suivantes (titres et dépendances seulement). |
| 2026-10-16 | **Code avant prose.** Tout ce qui est déterministe sort des SKILL.md et passe en Python stdlib sous `skills/_core/` : parsing des blocs JSON de verdict, compteur d'itérations et de rondes, registre cumulatif (dédoublonnage, statuts), journal de cycle, relance d'un agent mort, lecture de `models.json` et de `--models`, fusion de `settings.json`, blocs délimités. Les prompts ne gardent que le jugement : rôle, périmètre, interdits, format attendu. Objectif chiffré : chaque SKILL.md touché perd **au moins un tiers** de ses lignes sans perdre de règle. Chaque règle déplacée est pointée vers le code qui la porte. |
| 2026-10-16 | **Mesurer avant d'étendre.** Le journal de cycle (`.claude/runs/<skill>-<horodatage>.jsonl` : agent, modèle, durée, itération, verdict, findings produits / validés / rejetés, tokens si disponibles) fait partie de l'incrément 1. **Aucun nouveau skill, aucun profil, aucun `/audit` unifié** avant une dizaine de cycles journalisés sur de vrais projets. |
| 2026-10-16 | Incrément 1 : rebranchement de **deux** skills seulement, `software-factory` (avec le `factory-run` qu'il génère) et `ship-pr`. Les autres ne bougent pas. |
| 2026-10-16 | Pas de `/ship-pr` ni de push sans demande explicite sur ce dépôt : le harnais ne s'auto-modifie pas en autonomie. Une phase = une branche, diff montré, accord, merge. |

---

## 2. Incréments

Ordre repris de l'annexe de `specs/SPEC-noyau-core-journal.md`, qui fait foi.

| # | Incrément | Statut | Dépend de |
|---|---|---|---|
| 0 | Noyau `_core` en Python, journal de cycle, rebranchement de software-factory / factory-run et de ship-pr | **ÉCHEC du cycle** (2026-10-16, 3 itérations, CHANGES_REQUESTED, 2 défauts majeurs restants, voir §7). Arbitrage humain requis : `specs/SPEC-noyau-core-journal.md` | — |
| 1 | Régénération de l'usine de ce dépôt (factory-run, agents, `ci/factory.*`) | à faire | 0 |
| 2 | Rebranchement de code-index, avec le correctif `rgkb init` qui écrase `config.json` (D8 de la Phase 0) | à faire | 0 |
| 3 | Rebranchement d'ai-lab et d'ai-lab-audit (modèles par le noyau) | à faire | 0 |
| 4 | Rebranchement de legacy-audit, vibecode-audit et brainstorm | à faire | 0 |
| 5 | Analyse des journaux sur au moins 10 cycles réels | à faire | 0, plus 10 cycles |
| 6 | Versioning / upgrade / doctor du noyau distribué | à faire | 0, 2 |
| 7 | Politique d'autonomie | **gelé** jusqu'à la fin du 5 | 5 |
| 8 | Hooks Claude Code | gelé | 5, 7 |
| 9 | Profils | gelé | 5 |
| 10 | Scout | gelé | 9 |
| 11 | `/audit` unifié | gelé | 3, 4, 5, 9 |
| 12 | File et worktrees | gelé | 5, 7 |
| 13 | Étude du packaging en plugin | à faire, document seul | 6 |

## 3. Questions ouvertes

| # | Question | Statut |
|---|---|---|
| Q-partage | Forme du partage de code entre skills globaux | **tranchée le 2026-10-16** : mixte. ship-pr via `${CLAUDE_SKILL_DIR}/../_core` (à confirmer par la recette R1), factory-run généré via une copie dans `.claude/harness/` (D1 de la spec 0) |
| Q-registre | Format JSONL du registre | **tranchée le 2026-10-16** : clés anglaises `file`/`line`/`title`/`verdict`, dédoublonnage sur fichier + titre normalisé, fichier dans `.claude/runs/` non versionné (D2 de la spec 0) |
| Q2 | Modèle par rôle : le paramètre `model` de l'outil Agent seul, ou aussi `model:` en frontmatter ? Contredit `ai-lab:135` (D1). | ouverte |
| Q3 | Sort de `/lab-run` : alias, orchestrateur distinct, ou orchestrateur générique ? | ouverte, incrément 4 ou 8 |
| Q4 | Enchaînements malgré `disable-model-invocation` (D3) | ouverte, incrément 5 |
| Q5 | Gate de pré-enregistrement du labo : reste-t-elle (a) ? | ouverte, incrément 5 |
| Q6 | Premier `--upgrade` d'un projet sans blocs (D5) | ouverte, incrément 7 |
| Q8 | Registre versionné ou local : ce dépôt ignore déjà `AUDIT-*.md` | fusionnée dans Q-registre |
| Q9 | Schéma de finding unique, avec `occurrences[]` | ouverte, incréments 1 et 4 |
| Q10 | Format des profils : JSON, car la stdlib n'a pas de YAML | ouverte, incrément 8 |
| Q11 | Corriger D8, C1, C2, C3 à part ? | ouverte, D8 = incrément 3 |
| Q13 | Emplacement des tests | **tranchée** : tests unitaires dans `skills/_core/tests/`, fixtures dans `tests/fixtures/` |
| Q14 | ship-pr et brainstorm consomment le noyau sans devenir des profils | ouverte |

Autres décisions de la spec 0 (2026-10-16) : interpréteur détecté à l'exécution avec délai d'expiration ; `models.json` et blocs délimités sous forme de modules seuls, non branchés ; usine du dépôt inchangée ; bornes invalides = erreur explicite ; cible −⅓ ferme, quitte à sortir aussi les séquences `gh`/`git` de ship-pr.

Q1 (forme du noyau), Q7 (contenu de la Phase 1), Q12 (vérification sans fixture) et Q15 (une spec par phase) ont été **tranchées** par les décisions du 2026-10-16 : noyau en Python stdlib, une spec par incrément, journal dans l'incrément 1.

---

## 4. Inventaire de la Phase 0 (2026-10-16)

### Contradictions entre la feuille de route et le code

- **D1** : `ai-lab/SKILL.md:135` interdit `model:` dans le frontmatter des agents. Le seul mécanisme vérifié est le paramètre `model` de l'outil Agent, qui prime sur le frontmatter selon la doc.
- **D2** : aucun rôle `lab.*` n'existe. Les clés sont `director.cadrage`, `director.interpretation`, `neuro`, `math`, `builder`, `verifier`, `validator` (`ai-lab:147-155`).
- **D3** : `factory-run` et `lab-run` portent `disable-model-invocation: true` (`software-factory:89`, `ai-lab:170`), ce qui verrouille tout enchaînement automatique.
- **D4** : `models.json`, `--models`, le journal et le registre partagé sont des changements de comportement visibles. → Décision du 2026-10-16 : le journal est accepté comme seule nouveauté visible.
- **D5** : les fichiers générés par `software-factory` et `ai-lab` n'ont **aucun bloc délimité**. Ils sont générés en entier, avec un statut « personnalisé-conservé ».
- **D6** : la fusion de `settings.json` et les blocs `<!-- rgkb -->` sont de la **prose**, pas du code. Seul `# >>> rgkb >>>` (hooks git) est en code (`rgkb.py:766`).
- **D7** : `code-index` modifie déjà hors bloc : la liste `tools` des agents et `--allowedTools` des scripts `ci/*`.
- **D8** : **bug, perte de données.** `rgkb.py init` réécrit `.knowledge/config.json` avec `DEFAULT_CONFIG` (`rgkb.py:568`, vérifié). Comme `/code-index` relance `init`, chaque relance perd les réglages de l'utilisateur.
- **D9** : les `Q-*` de ai-lab-audit visent `/lab-run`, pas `/factory-run`.
- **D10** : une comparaison avant/après d'un cycle LLM ne peut pas être exacte au mot près. Il faut une comparaison structurelle.

### Dérives constatées

- **C1** : le `factory-run` de ce dépôt a dérivé de son template. La règle « Verifier muet » manque, et `factory-planner.md:13` ne liste que 5 skills sur 8.
- **C2** : `lab-run` n'applique pas la règle « agent mort » dans sa boucle Verify ni à l'interprétation.
- **C3** : le comportement de `ship-pr` en mode headless n'est spécifié nulle part, alors qu'il comporte 4 gates.
- **C4** : les deux installeurs lient tout sous-dossier de `skills/`. Un `skills/_core/` serait lié sans `SKILL.md`.

### Duplications (résumé)

- **Gate AskUserQuestion** : 11 points, avec 4 comportements headless différents (arrêt, défaut appliqué et signalé, rien installé, non spécifié).
- **Validateur** : 4 formats JSON incompatibles (ship-pr, legacy-audit, vibecode-audit, ai-lab-audit). Les Verifiers de la factory et du labo valident une implémentation, pas un finding.
- **Registre** : en mémoire dans ship-pr ; un schéma par audit ; aucun partage.
- **Détection de stack** : 6 copies, avec des listes de marqueurs qui divergent.
- **Fusion settings, tasks, .gitignore** : en prose, dans software-factory, ai-lab et code-index.
- **Modèle par rôle** : seulement ai-lab, lab-run et ai-lab-audit, sur des jeux de rôles différents.
- **T-shirt** : trois audits ; ai-lab-audit ajoute un barème GPU.
- **Mode headless** : `ci/factory.*` et `ci/lab.*`, avec un `--max-turns` différent (100 / 150) et un statut attendu différent (`APPROUVEE` / `PRE-ENREGISTRE`).
- **Règle « agent mort »** : copiée dans 7 skills.

### Gates classées (proposition)

- **(a)** pré-enregistrement de lab-run ; arbre sale dans ship-pr ; merge de ship-pr (aujourd'hui).
- **(b)** questions du Planner ; installation de code-index (6b) ; profil de modèles ; conflit dans ship-pr ; jalons et thèmes des audits ; `--axes` de vibecode ; hooks git de code-index.
- **(c)** approbation de la spec (selon la section 4.2 de la feuille de route) ; besoin vide ; cible absente dans ship-pr ; écriture des livrables ; consignation dans le journal du labo ; installation de rg.

Le détail complet, avec `fichier:ligne`, a été rendu en conversation le 2026-10-16. Il pourra être reconstitué en relançant `factory-planner` sur la Phase 0 de `ROADMAP.md`.

---

## 5. Faits vérifiés (doc Claude Code et machine)

### Doc officielle (code.claude.com/docs/en/skills.md, sub-agents.md, hooks.md, headless.md, plugins/*)

**Skills**
- `${CLAUDE_SKILL_DIR}` et `${CLAUDE_PROJECT_DIR}` sont documentés.
- Lire le dossier d'un **autre** skill n'est **pas** documenté.
- « Every skill needs a SKILL.md. »

**Sous-agents et modèles**
- Le paramètre `model` de l'outil Agent prime sur le frontmatter, qui accepte `sonnet`, `opus`, `haiku`, `fable`, un ID complet ou `inherit`.
- Un sous-agent peut lancer des sous-agents, jusqu'à 3 niveaux, et peut invoquer des skills.

**Hooks**
- Un hook déclaré dans le frontmatter d'un skill reste actif **jusqu'à la fin de la session**, pas seulement pendant le skill. Pour limiter un hook à un skill, il faut un garde dans le script (fichier marqueur, `agent_type` lu sur stdin).
- PreToolUse : exit 2 bloque, ou `permissionDecision: deny`.
- Les hooks s'appliquent aussi aux sous-agents.

**Headless et évaluation**
- `claude -p` : `AskUserQuestion` est retiré par `--permission-prompts none` ; sans ce flag, le comportement n'est pas documenté.
- `claude plugin eval` sait préparer une fixture (`scaffold_script`), mais **aucun grader n'exécute de commande shell**. Il faut donc des scripts de test maison.

**Plugins**
- Pas d'installation de binaires système (ripgrep).
- Les noms deviennent `/plugin:skill`.
- `version` dans `plugin.json`.

### Machine de l'utilisateur (observé le 2026-10-16)

- `~/.claude/skills/` ne contient **aucun** lien vers claude-skills, seulement `synced/`. L'installeur n'a pas été lancé sur cette machine.
- `python` est le stub du Microsoft Store et ne répond pas ; `py -3` donne Python 3.9.13 ; pytest est absent. Les tests seront donc en `unittest` et le code compatible 3.9.
- L'outil Agent renvoie un bloc d'usage (`subagent_tokens`, `tool_uses`, `duration_ms`) dans sa notification de fin. C'est observé, pas documenté, et c'est une source possible pour les tokens du journal.

---

## 6. Hors périmètre de l'incrément 1 (rappel)

Profils, scout, `/audit`, versioning / upgrade / doctor, politique d'autonomie, hooks Claude Code, file et worktrees, packaging, skills autres que `software-factory` et `ship-pr`.

---

## 7. Résultat du cycle de l'incrément 0 (2026-10-16)

Le cycle s'est arrêté en **échec explicite** après 3 itérations Build/Verify. Le Verifier rendait encore CHANGES_REQUESTED, avec `tests_passed: true`. Le code est dans l'arbre de travail de la branche `v2/increment-1-noyau`, non commité.

- Les 18 critères d'acceptation passent : 133 tests, `software-factory` = 96 lignes, `ship-pr` = 112 lignes.
- 18 défauts trouvés lors des itérations 1 et 2 ont été corrigés, puis reproduits comme corrigés par un Verifier neuf.

### Défauts majeurs restants

1. **`skills/_core/hcore/runs.py` : aucun verrou sur `.state.json`.** C'est une régression par rapport à `BASE`, où l'état restait en mémoire.
   - Des appels concurrents `K reviewer` ou `K validator` perdent des mises à jour. Sur 8 essais : 7 donnent des identifiants en collision, 8 perdent un thème, et certains lèvent une `PermissionError` sur `os.replace` sous Windows.
   - Conséquence possible : un verdict appliqué au mauvais finding, qui est ensuite posté sur la PR.
   - Correction : un verrou de fichier autour de `load`/`save`, et/ou des appels strictement séquentiels prescrits, avec un test de concurrence.
2. **`skills/ship-pr/SKILL.md` : `--summary "<résumé>"` et `--not-fixed "<id>:<raison>"` passent par le shell.**
   - Ce texte est dérivé des findings, entre guillemets doubles. Des backticks ou un `$()` y sont exécutés, et le commit `fix(review)` est corrompu sans retour possible, puisque l'amend est interdit.
   - Le défaut existait déjà à `BASE`, mais il contredit la règle que le skill pose lui-même.
   - Correction : options `--summary-file` / `--not-fixed-file`, écrites par Write.

### Défauts mineurs restants

- `--title`, `--target`, `--themes` et `--theme` passent par le shell. Ils viennent de sources fiables, mais `--slot reviewer:<thème>` n'est pas entre guillemets alors que les thèmes contiennent des espaces.
- Après un 422 suivi d'un échec d'une autre nature (non 422) sur le repli au niveau fichier, le code se replie quand même sur `gh pr comment`.
- L'état n'est pas sauvegardé sur les chemins d'erreur : si le push échoue après le commit, ou si les threads sont interrompus, une relance re-poste les réponses.
- Les fichiers de transit de `sf install` restent dans `.claude/runs/` si le skill s'arrête avant la Phase 5.
- `parse_themes` rejette les thèmes en double, une règle hors D8.
- `copy-core` bloqué rend exit 0 avec `copied:false`, signalé trop faiblement.
