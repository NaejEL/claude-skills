# Backlog — claude-skills v2

Mémoire de travail du chantier v2. Ce fichier prime sur `ROADMAP.md`, qui reste le texte d'origine, quand les deux divergent. Branche de travail actuelle : `v2/phase-1-core`. Spec en cours : `specs/SPEC-phase1-rebranchement.md` (APPROUVEE, état des lots en §8).

Dernière mise à jour : 2026-10-17.

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
   - **Corrigé (phase 1)** : verrou OS exclusif `<run>.lock` (`fcntl.flock` / `msvcrt.locking`, libéré par l'OS à la mort du détenteur, délai de 120 s puis arrêt exit 1), tenu par chaque commande CLI sur un run existant pendant tout le cycle lecture → modification → écriture ; écriture atomique conservée, `os.replace` réessayé sur `PermissionError` sous Windows. Tests : `test_runs_lock.ConcurrencyTest.test_parallel_reviewers_and_validators_lose_nothing` (4 `reviewer` puis 12 `validator` en sous-processus parallèles, 3 essais), `test_runs_lock.LockTest` (`test_lock_held_by_another_process_times_out`, `test_orphan_lock_released_when_its_holder_dies`, `test_cli_waits_then_stops_with_exit_1_on_lock_timeout`, `test_replace_retried_on_permission_error`).
2. **`skills/ship-pr/SKILL.md` : `--summary "<résumé>"` et `--not-fixed "<id>:<raison>"` passent par le shell.**
   - Ce texte est dérivé des findings, entre guillemets doubles. Des backticks ou un `$()` y sont exécutés, et le commit `fix(review)` est corrompu sans retour possible, puisque l'amend est interdit.
   - Le défaut existait déjà à `BASE`, mais il contredit la règle que le skill pose lui-même.
   - Correction : options `--summary-file` / `--not-fixed-file`, écrites par Write.
   - **Corrigé (phase 1)** : `ship-pr commit --summary-file` et `--not-fixed-file` (JSON `{"<id>": "<raison>"}`), `ship-pr pr --title-file` ; le SKILL.md prescrit ces fichiers, écrits par Write sous `.claude/runs/`. Tests : `test_replay.ShipPrReplayTest.test_untrusted_text_travels_by_file_drop_and_trailer`, `test_replay.UntrustedContentTest.test_skills_prescribe_files_for_untrusted_text_and_new_commands`.

### Défauts mineurs restants

- `--title`, `--target`, `--themes` et `--theme` passent par le shell. Ils viennent de sources fiables, mais `--slot reviewer:<thème>` n'est pas entre guillemets alors que les thèmes contiennent des espaces.
  - **Corrigé (phase 1)** : `--slot "reviewer:<thème>"` et `--slot "validator:<id>"` entre guillemets, `--title` remplacé par `--title-file` dans le SKILL.md. Test : `test_replay.UntrustedContentTest.test_skills_prescribe_files_for_untrusted_text_and_new_commands`.
- Après un 422 suivi d'un échec d'une autre nature (non 422) sur le repli au niveau fichier, le code se replie quand même sur `gh pr comment`.
  - **Corrigé (phase 1)** : arrêt exit 1, sans repli `gh pr comment`. Test : `test_ghflow.RoundFlowTest.test_sp16_file_level_failure_other_than_422_stops_without_pr_comment`.
- L'état n'est pas sauvegardé sur les chemins d'erreur : si le push échoue après le commit, ou si les threads sont interrompus, une relance re-poste les réponses.
  - **Corrigé (phase 1)** : le hash du commit et les issues sont consignés (`unpushed`) et sauvegardés avant le push ; une relance pousse sans recommiter, et `end-round` refuse tant que le push n'est pas fait. Chaque réponse postée, puis chaque thread traité, est marqué et sauvegardé avant le suivant. Tests : `test_ghflow.RoundFlowTest.test_sp17_failed_push_keeps_hash_and_relaunch_does_not_recommit`, `test_sp17_cli_failed_push_saved_then_resumed`, `test_sp18_interrupted_threads_never_repost_a_reply`, `test_shippr.ExitTest.test_sp17_round_does_not_end_on_an_unpushed_fix_commit`.
- Les fichiers de transit de `sf install` restent dans `.claude/runs/` si le skill s'arrête avant la Phase 5.
  - **Corrigé (phase 1)** : `sf install` supprime son fichier source situé sous `.claude/runs/` dès sa lecture (try/finally, installation réussie ou non). Test : `test_fusion.BacklogFixesTest.test_sf04_transit_file_removed_once_read_even_on_failure`.
- `parse_themes` rejette les thèmes en double, une règle hors D8.
  - **Corrigé (phase 1)** : erreur explicite conservée, alignée sur D8 (borne invalide = erreur explicite, jamais de correction silencieuse) : le message nomme le thème en double, et l'aide de `--themes` documente la règle. Test : `test_counters.ThemesTest.test_sp02_duplicate_theme_is_explicit_error_naming_it`.
- `copy-core` bloqué rend exit 0 avec `copied:false`, signalé trop faiblement.
  - **Corrigé (phase 1)** : exit 1 avec un message `STOP: core not copied` qui nomme les fichiers en cause ; le SKILL.md de software-factory dit de s'arrêter. Test : `test_fusion.BacklogFixesTest.test_d1_cli_blocked_copy_core_is_an_explicit_stop`.

### Revue ship-pr de la PR #2 (2026-10-17)

Premier passage réel de `ship-pr` rebranché sur le noyau. Sortie par épuisement en ronde 2. Journal : `.claude/runs/ship-pr-20261017-131818.jsonl`.

- **Corrigé dans `cfea95e`** : `commit_round` acceptait un id en double. Le commit était poussé, puis l'état n'était pas sauvegardé.
- **Friction constatée** : SKILL.md SP-07 demande d'« écarter au jugement » un doublon sémantique. Le noyau n'a aucune sous-commande pour le faire, donc il faut un validateur même pour un doublon évident. Le finding a été rejeté sur la forme, mais la friction est réelle. À trancher : une sous-commande `drop`, ou retirer la consigne.
  - **Corrigé (phase 1)** : `ship-pr drop --run <run> --finding <id> --of <id> [--reason-file <fichier>]` passe un candidat PENDING de la ronde à l'état `DUPLICATE` (état et registre), le compte dans `duplicates`, refuse un `--of` inconnu ; `end-round` ne l'attend plus. SP-07 du SKILL.md prescrit `K drop`. Tests : `test_shippr.SemanticDuplicateTest`, `test_replay.ShipPrReplayTest.test_untrusted_text_travels_by_file_drop_and_trailer`.
- **Journal** : une durée est restée `null` quand la notification de fin d'un agent arrive après l'enregistrement de son résultat.
  - **Corrigé (phase 1)** : `harness.py journal amend --run <run> --slot <slot> --duration-ms N --tokens N` complète la dernière entrée du slot (valeurs `null` seulement ; une valeur déjà consignée est conservée et signalée ; jamais bloquant) ; complétion différée documentée dans les deux SKILL.md. Test : `test_journal.RunFilesTest.test_journal_amend_completes_last_entry_of_the_slot`.
- **Message de commit `fix(review)`** : il est écrit par le noyau, sans la ligne d'attribution `Co-Authored-By`.
  - **Corrigé (phase 1)** : `ship-pr commit --trailer "<ligne>"` (répétable), ajouté après une ligne vide ; le SKILL.md demande de passer le trailer d'attribution de l'environnement s'il en existe un. Tests : `test_ghflow.RoundFlowTest.test_sp17_trailers_added_after_a_blank_line`, `test_replay.ShipPrReplayTest.test_untrusted_text_travels_by_file_drop_and_trailer`.
- **Itération 2 du lot L1 (Verifier, CHANGES_REQUESTED)** :
  - `drop` acceptait un cycle (`drop A --of B` puis `drop B --of A`), et le vrai finding disparaissait. **Corrigé (phase 1)** : un `--of` déjà `DUPLICATE` est refusé, la cible reste un finding validé ou à valider. Test : `test_shippr.SemanticDuplicateTest.test_sp07_drop_refuses_a_cycle_or_a_chain_of_duplicates`.
  - `--not-fixed-file` gardait en silence la dernière valeur d'une clé en double. **Corrigé (phase 1)** : `object_pairs_hook` qui refuse la clé en double (exit 2). Test : `test_replay.ShipPrReplayTest.test_not_fixed_file_duplicate_key_refused`.
  - Un résumé sur plusieurs lignes collait un corps au sujet du commit, sans ligne vide. **Corrigé (phase 1)** : refusé (exit 2 dans la CLI, arrêt avant tout appel git dans `commit_round`). Test : `test_replay.ShipPrReplayTest.test_multiline_summary_refused_before_any_commit`.
  - Les fichiers de transit de ship-pr (`pr-title.txt`, `pr-body.md`, `drop.txt`, `summary.txt`, `not-fixed.json`) n'étaient jamais supprimés, et un fichier périmé pouvait être réutilisé. **Corrigé (phase 1)** : chaque fichier lu sous `.claude/runs/` par `--title-file`, `--body-file`, `--reason-file`, `--summary-file` et `--not-fixed-file` est supprimé une fois consommé (try/finally). La relance de `commit` après un push en échec n'a pas besoin de ces fichiers. Tests : `test_replay.ShipPrReplayTest.test_transit_files_removed_once_consumed`, `test_ghflow.RoundFlowTest.test_sp17_cli_failed_push_saved_then_resumed`.
- **`--not-fixed` en double** (constaté en phase 1) : `--not-fixed A:r1 --not-fixed A:r2` s'écrasaient dans un dict.
  - **Corrigé (phase 1)** : refusé (exit 2), y compris entre `--not-fixed` et `--not-fixed-file`. Tests : `test_ghflow.RoundFlowTest.test_sp09_not_fixed_given_twice_refused_by_the_cli`, `test_replay.ShipPrReplayTest.test_untrusted_text_travels_by_file_drop_and_trailer`.

### Code en anglais (décision de l'utilisateur, 2026-10-17)

Le code est en anglais, y compris les commentaires, les identifiants et les textes publiés : commentaires de PR, messages de commit, messages d'arrêt. La prose Markdown reste en français. Le noyau a été traduit en conséquence et le critère CA7 a été adapté. Restent en français, parce que ce sont des formats partagés et que les renommer changerait le comportement :

- les états de fichier `créé` / `fusionné` / `identique` / `personnalisé-conservé`, communs avec ai-lab, code-index et le README ;
- les marqueurs `<!-- x:debut -->` / `<!-- x:fin -->` ;
- la ligne `Statut : APPROUVEE` des specs ;
- le libellé de tâche `Factory: nouvelle spec (session)`, qui sert de clé de dédoublonnage dans les projets déjà équipés.

À faire dans un incrément ultérieur, avec une migration : ajouter la règle « code en anglais » aux templates d'agents générés par `software-factory` (builder, et planner pour les specs), sur suggestion de l'utilisateur.

### Recette R1 (2026-10-17, faite en headless)

Projet jetable, avec `.claude/skills/probe` (jonction Windows) et `.claude/skills/realprobe` (vrai dossier). `.claude/skills/_core` est une jonction vers ce dépôt. Commande : `claude -p "/probe"` (Claude Code 2.1.301), avec `MSYS_NO_PATHCONV=1` pour empêcher Git Bash de convertir le `/`.

- `${CLAUDE_SKILL_DIR}` vaut le chemin du lien, sans résolution de la jonction. `${CLAUDE_SKILL_DIR}/../_core/harness.py version` rend `{"core_version": "1.0.0"}`, dans les deux cas.
- `/_core` répond « isn't a command available » : `_core`, sans SKILL.md, n'est pas exposé comme skill.
- Les installeurs lient chaque dossier de `skills/`, `_core` compris (`install_skills.sh:176`, `install_skills.ps1:167`).

Résultat : **R1 OK**. Le partage `${CLAUDE_SKILL_DIR}/../_core` est confirmé.

---

## 8. Phase 1 — état des lots (2026-10-17)

Spec : `specs/SPEC-phase1-rebranchement.md`, statut APPROUVEE, décisions X1 à X11 et Q-G1 (la section « Décisions » prime sur le reste de la spec).

| Lot | Contenu | État |
|---|---|---|
| L0 | Recette R1 et arbitrage X1 à X11 | **fait** (R1 OK, §7 ; décisions du 2026-10-17 dans la spec) |
| L1 | Corrections §7 : verrou, `--summary-file`, `--not-fixed-file`, `--title-file`, `--trailer`, `drop`, `journal amend` | **fait**, commit `31579e0` ; reliquat (fichier de transit déjà consommé = exit 2 explicite) livré avec L2 |
| L2 | JR-01, JR-02 ; gates GT-01 à GT-08 ; câblage software-factory (gabarit) et ship-pr (C3) | **livré, non commité** (arbre de travail) |
| L3 | Modèles MD-01 à MD-08 ; câblage factory-run (gabarit) et ship-pr ; `--models` (X6) | **livré, non commité** (arbre de travail) |
| L4 | Régénération de l'usine du dépôt (UF-01 à UF-07) | à faire (dépend de L2, L3) |
| L5 | Finding FD-01 à FD-11, registre projet RG-01 à RG-07 | à faire |
| L6 | Stack, T-shirt, fusion générique, blocs | à faire |
| L7 | Moteur d'audit AU-01 à AU-16 | à faire |
| L8 à L13 | Rebranchement de code-index, ai-lab, ai-lab-audit, legacy-audit, vibecode-audit, brainstorm | à faire |
| L14 | README, BACKLOG, rafraîchissement de `.claude/harness`, passage complet des CA | à faire |

### L2 et L3 : ce qui est en place

- **Journal** : dix noms de skill admis (`journal.SKILLS`) ; une ligne sans `event` reste une ligne d'agent ; `event: "gate"` suit GT-07 (`phase` = `decision` puis `answer`).
- **Gates** : `hcore/gates.py`, catalogue des 27 gates (options citées telles qu'à BASE1, défaut, justification, repli headless). CLI `harness.py gate decide --id <id> [--run <run>]` et `gate answer --run <run> --id <id> (--answer | --answer-file | --headless | --default)`. Sans `--run`, `decide` ouvre un run du skill de la gate ; `ship-pr start --run <run>` poursuit le run ouvert par `ship-pr.target`. `auto` lu dans `.claude/harness.json` est appliqué comme `gate`, avec un avertissement journalisé (Q-G1).
- **Modèles** : `hcore/models.py`, 14 rôles fermés, migration `lab-models.json` → `models.json`, alias `lab`, préréglages `lab-inherit`, `lab-experts`, `lab-interpretation`, `lab-custom`, `economy`, `quality`. CLI `models resolve` et `models write`. `factory-run start` retire `--models` de `$ARGUMENTS` ; `ship-pr start --models`. Le modèle consigné au journal est celui du rôle quand `--model` est omis. `sf install --model-role <rôle>` écrit le bloc `# >>> harness.model >>>` dans le frontmatter de l'agent généré (X1).
- **Écart à la spec** : MD-03 (« valeur inconnue dans le fichier → `inherit` avec avertissement ») et la ligne correspondante de CA-18 sont remplacés par X8 : erreur explicite (exit 2). MD-09 est remplacé par X1.
- **Point d'attention** : un agent généré avant X1 (sans bloc) devient `personnalisé-conservé` à la relance de software-factory, et son bloc n'est pas ajouté. La mise à niveau relève de la Phase 3 (`--upgrade`).
