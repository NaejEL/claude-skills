# Backlog — claude-skills v2

Mémoire de travail du chantier v2. Ce fichier prime sur `ROADMAP.md`, qui reste le texte d'origine, quand les deux divergent. Branche de travail actuelle : `v2/phase-1-core`. Spec en cours : `specs/SPEC-phase1-rebranchement.md` (APPROUVEE, état des lots en §8).

Dernière mise à jour : 2026-10-17.

---

## 1. Décisions de l'utilisateur

| Date | Décision |
|---|---|
| 2026-10-16 | `ROADMAP.md` est une **feuille de route**, pas un besoin. Un cycle `/factory-run` = **une** spec pour **un** incrément, plus en annexe la liste ordonnée des specs suivantes (titres et dépendances seulement). |
| 2026-10-16 | **Code avant prose.** Tout ce qui est déterministe sort des SKILL.md et passe en Python stdlib sous `skills/_core/` : parsing des blocs JSON de verdict, compteur d'itérations et de rondes, registre cumulatif (dédoublonnage, statuts), journal de cycle, relance d'un agent mort, lecture de `models.json` et de `--models`, fusion de `settings.json`, blocs délimités. Les prompts ne gardent que le jugement : rôle, périmètre, interdits, format attendu. Objectif chiffré : chaque SKILL.md touché perd **au moins un tiers** de ses lignes sans perdre de règle. Chaque règle déplacée est pointée vers le code qui la porte. |
| 2026-10-16 | **Mesurer avant d'étendre.** Le journal de cycle (`.harness/runs/<skill>-<horodatage>.jsonl` : agent, modèle, durée, itération, verdict, findings produits / validés / rejetés, tokens si disponibles) fait partie de l'incrément 1. **Aucun nouveau skill, aucun profil, aucun `/audit` unifié** avant une dizaine de cycles journalisés sur de vrais projets. |
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
| 7 | Politique d'autonomie | **livré en Phase 4** (gel levé par l'utilisateur, lot L12) : `specs/SPEC-phase4-5-autonomie-hooks.md` | 5 |
| 8 | Hooks Claude Code | **livré en Phase 5** (gel levé) : `specs/SPEC-phase4-5-autonomie-hooks.md` | 5, 7 |
| 9 | Profils | **livré en Phase 2** (gel levé par l'utilisateur) : `specs/SPEC-phase2-profils-audit.md` | 5 |
| 10 | Scout | **livré en Phase 2** (gel levé) | 9 |
| 11 | `/audit` unifié | **livré en Phase 2** (gel levé) | 3, 4, 5, 9 |
| 12 | File et worktrees | **livré en Phase 4** (gel levé) : `specs/SPEC-phase4-5-autonomie-hooks.md` | 5, 7 |
| 13 | Étude du packaging en plugin | à faire, document seul | 6 |

## 3. Questions ouvertes

| # | Question | Statut |
|---|---|---|
| Q-partage | Forme du partage de code entre skills globaux | **tranchée le 2026-10-16** : mixte. ship-pr via `${CLAUDE_SKILL_DIR}/../_core` (à confirmer par la recette R1), factory-run généré via une copie dans `.claude/harness/` (D1 de la spec 0) |
| Q-registre | Format JSONL du registre | **tranchée le 2026-10-16** : clés anglaises `file`/`line`/`title`/`verdict`, dédoublonnage sur fichier + titre normalisé, fichier dans `.harness/runs/` non versionné (D2 de la spec 0) |
| Q2 | Modèle par rôle : le paramètre `model` de l'outil Agent seul, ou aussi `model:` en frontmatter ? Contredit `ai-lab:135` (D1). | ouverte |
| Q3 | Sort de `/lab-run` : alias, orchestrateur distinct, ou orchestrateur générique ? | **tranchée en Phase 2** : seconde instance du gabarit commun, profil `research` imposé (LP-06) |
| Q4 | Enchaînements malgré `disable-model-invocation` (D3) | **tranchée** : processus enfant headless `claude -p` lancé par le noyau (CH-01), `disable-model-invocation` conservé sur factory-run ; recette R12 à faire |
| Q5 | Gate de pré-enregistrement du labo : reste-t-elle (a) ? | **tranchée** : reste (a), `stop_when` = le protocole déclare des questions bloquantes sans réponse ; défaut approuver |
| Q6 | Premier `--upgrade` d'un projet sans blocs (D5) | **tranchée** (Phase 3, CV) : conversion automatique si le fichier est `pristine` ou `suffix` par rapport à sa base git, sinon gate `upgrade.convert` (défaut : conserver) ; `--convert` pour forcer |
| Q8 | Registre versionné ou local : ce dépôt ignore déjà `AUDIT-*.md` | fusionnée dans Q-registre |
| Q9 | Schéma de finding unique, avec `occurrences[]` | ouverte, incréments 1 et 4 |
| Q10 | Format des profils : JSON, car la stdlib n'a pas de YAML | **tranchée en Phase 2** : `profile.json` plus fragments Markdown (PF-01) |
| Q11 | Corriger D8, C1, C2, C3 à part ? | ouverte, D8 = incrément 3 |
| Q13 | Emplacement des tests | **tranchée** : tests unitaires dans `skills/_core/tests/`, fixtures dans `tests/fixtures/` ; Phase 6 : scénarios de bout en bout dans `ci/scenarios/`, leurs projets jouets et sorties d'agents figées dans `ci/fixtures/` (voir §11) |
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
   - **Corrigé (phase 1)** : `ship-pr commit --summary-file` et `--not-fixed-file` (JSON `{"<id>": "<raison>"}`), `ship-pr pr --title-file` ; le SKILL.md prescrit ces fichiers, écrits par Write sous `.harness/runs/`. Tests : `test_replay.ShipPrReplayTest.test_untrusted_text_travels_by_file_drop_and_trailer`, `test_replay.UntrustedContentTest.test_skills_prescribe_files_for_untrusted_text_and_new_commands`.

### Défauts mineurs restants

- `--title`, `--target`, `--themes` et `--theme` passent par le shell. Ils viennent de sources fiables, mais `--slot reviewer:<thème>` n'est pas entre guillemets alors que les thèmes contiennent des espaces.
  - **Corrigé (phase 1)** : `--slot "reviewer:<thème>"` et `--slot "validator:<id>"` entre guillemets, `--title` remplacé par `--title-file` dans le SKILL.md. Test : `test_replay.UntrustedContentTest.test_skills_prescribe_files_for_untrusted_text_and_new_commands`.
- Après un 422 suivi d'un échec d'une autre nature (non 422) sur le repli au niveau fichier, le code se replie quand même sur `gh pr comment`.
  - **Corrigé (phase 1)** : arrêt exit 1, sans repli `gh pr comment`. Test : `test_ghflow.RoundFlowTest.test_sp16_file_level_failure_other_than_422_stops_without_pr_comment`.
- L'état n'est pas sauvegardé sur les chemins d'erreur : si le push échoue après le commit, ou si les threads sont interrompus, une relance re-poste les réponses.
  - **Corrigé (phase 1)** : le hash du commit et les issues sont consignés (`unpushed`) et sauvegardés avant le push ; une relance pousse sans recommiter, et `end-round` refuse tant que le push n'est pas fait. Chaque réponse postée, puis chaque thread traité, est marqué et sauvegardé avant le suivant. Tests : `test_ghflow.RoundFlowTest.test_sp17_failed_push_keeps_hash_and_relaunch_does_not_recommit`, `test_sp17_cli_failed_push_saved_then_resumed`, `test_sp18_interrupted_threads_never_repost_a_reply`, `test_shippr.ExitTest.test_sp17_round_does_not_end_on_an_unpushed_fix_commit`.
- Les fichiers de transit de `sf install` restent dans `.harness/runs/` si le skill s'arrête avant la Phase 5.
  - **Corrigé (phase 1)** : `sf install` supprime son fichier source situé sous `.harness/runs/` dès sa lecture (try/finally, installation réussie ou non). Test : `test_fusion.BacklogFixesTest.test_sf04_transit_file_removed_once_read_even_on_failure`.
- `parse_themes` rejette les thèmes en double, une règle hors D8.
  - **Corrigé (phase 1)** : erreur explicite conservée, alignée sur D8 (borne invalide = erreur explicite, jamais de correction silencieuse) : le message nomme le thème en double, et l'aide de `--themes` documente la règle. Test : `test_counters.ThemesTest.test_sp02_duplicate_theme_is_explicit_error_naming_it`.
- `copy-core` bloqué rend exit 0 avec `copied:false`, signalé trop faiblement.
  - **Corrigé (phase 1)** : exit 1 avec un message `STOP: core not copied` qui nomme les fichiers en cause ; le SKILL.md de software-factory dit de s'arrêter. Test : `test_fusion.BacklogFixesTest.test_d1_cli_blocked_copy_core_is_an_explicit_stop`.

### Revue ship-pr de la PR #2 (2026-10-17)

Premier passage réel de `ship-pr` rebranché sur le noyau. Sortie par épuisement en ronde 2. Journal : `.harness/runs/ship-pr-20261017-131818.jsonl`.

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
  - Les fichiers de transit de ship-pr (`pr-title.txt`, `pr-body.md`, `drop.txt`, `summary.txt`, `not-fixed.json`) n'étaient jamais supprimés, et un fichier périmé pouvait être réutilisé. **Corrigé (phase 1)** : chaque fichier lu sous `.harness/runs/` par `--title-file`, `--body-file`, `--reason-file`, `--summary-file` et `--not-fixed-file` est supprimé une fois consommé (try/finally). La relance de `commit` après un push en échec n'a pas besoin de ces fichiers. Tests : `test_replay.ShipPrReplayTest.test_transit_files_removed_once_consumed`, `test_ghflow.RoundFlowTest.test_sp17_cli_failed_push_saved_then_resumed`.
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
| L2 | JR-01, JR-02 ; gates GT-01 à GT-08 ; câblage software-factory (gabarit) et ship-pr (C3) | **fait**, commit `eb9fd93` ; 7 défauts mineurs du Verifier corrigés avec L5 et L6 (ci-dessous) |
| L3 | Modèles MD-01 à MD-08 ; câblage factory-run (gabarit) et ship-pr ; `--models` (X6) | **fait**, commit `eb9fd93` |
| L4 | Régénération de l'usine du dépôt (UF-01 à UF-07) | **livré, non commité** (arbre de travail), itération 2 du Verifier traitée, voir ci-dessous |
| L5 | Finding FD-01 à FD-11, registre projet RG-01 à RG-07 ; `comment_body` par FD-10 ; publication et lecture dans ship-pr (X4) | **fait**, commit `e9da1a4` ; test FD-08 durci avec L7 (texte intégral des deux critères `fuites`) |
| L6 | Stack ST-01 à ST-05, T-shirt TS-01 à TS-05, fusion générique FU-01 à FU-06, blocs BK-01 ; SF sur FU ; Phase 1 de software-factory sur ST | **fait**, commit `e9da1a4` ; BK-02 reste au lot L8 |
| L7 | Moteur d'audit AU-01 à AU-16 | **livré, non commité** (arbre de travail), itération 2 du Verifier traitée, voir ci-dessous ; SKILL.md des audits non rebranchés (L10 à L12) |
| L8 à L13 | Rebranchement de code-index, ai-lab, ai-lab-audit, legacy-audit, vibecode-audit, brainstorm | **livré, non commité** (arbre de travail), voir « L8 à L14 » ci-dessous |
| L14 | README, BACKLOG, rafraîchissement de `.claude/harness`, passage complet des CA | **livré, non commité** (spec `specs/SPEC-phase1-fin-L8-L14.md`) |

### L2 et L3 : ce qui est en place

- **Journal** : dix noms de skill admis (`journal.SKILLS`) ; une ligne sans `event` reste une ligne d'agent ; `event: "gate"` suit GT-07 (`phase` = `decision` puis `answer`).
- **Gates** : `hcore/gates.py`, catalogue des 27 gates (options citées telles qu'à BASE1, défaut, justification, repli headless). CLI `harness.py gate decide --id <id> [--run <run>]` et `gate answer --run <run> --id <id> (--answer | --answer-file | --headless | --default)`. Sans `--run`, `decide` ouvre un run du skill de la gate ; `ship-pr start --run <run>` poursuit le run ouvert par `ship-pr.target`. `auto` lu dans `.claude/harness.json` est appliqué comme `gate`, avec un avertissement journalisé (Q-G1).
- **Modèles** : `hcore/models.py`, 14 rôles fermés, migration `lab-models.json` → `models.json`, alias `lab`, préréglages `lab-inherit`, `lab-experts`, `lab-interpretation`, `lab-custom`, `economy`, `quality`. CLI `models resolve` et `models write`. `factory-run start` retire `--models` de `$ARGUMENTS` ; `ship-pr start --models`. Le modèle consigné au journal est celui du rôle quand `--model` est omis. `sf install --model-role <rôle>` écrit le bloc `# >>> harness.model >>>` dans le frontmatter de l'agent généré (X1).
- **Écart à la spec** : MD-03 (« valeur inconnue dans le fichier → `inherit` avec avertissement ») et la ligne correspondante de CA-18 sont remplacés par X8 : erreur explicite (exit 2). MD-09 est remplacé par X1.
- **Point d'attention** : un agent généré avant X1 (sans bloc) devient `personnalisé-conservé` à la relance de software-factory, et son bloc n'est pas ajouté. La mise à niveau relève de la Phase 3 (`--upgrade`).

### L5 et L6 : ce qui est en place

- **Finding** : `hcore/findings.py`, schéma FD-01 (plus `category`, `history`, `settled_by`, `deliverable_status`, `previous`, `split_from`, `milestone`), statuts et transitions FD-02, validateur `finding validate` (exit 1 si non conforme, extrait de plus de 3 lignes = avertissement), adaptateurs des 6 formats (`finding adapt`, `raw` = l'entrée), parseur unique des verdicts de validateur (`finding verdict`, SP-04 passe par lui), application d'un verdict (`finding apply`), spec factory depuis le gabarit `templates/spec-factory.md` (`finding spec`, jamais écrasée), note rgkb (`finding note`), chaînes interdites (`finding forbidden`, exit 1). `ghflow.comment_body` passe par `to_pr_comment` (identique à BASE1).
- **Registre projet** : `.claude/findings.jsonl`, une ligne par finding, trié, réécrit sous le verrou `.claude/findings.lock` ; les deux chemins sont ajoutés à `.git/info/exclude` (rien sans git). `ship-pr start` le lit (`project_findings`) ; `reviewer` écarte un finding REJECTED ou SETTLED antérieur (`previous` = `<statut>@<skill>`) et transmet FIXED / NOT_FIXED en `history` ; `end-round` le publie à la sortie de boucle (`project_registry`). CLI génériques `registry publish --run` et `registry check --file`.
- **Stack, T-shirt** : `hcore/stack.py` (`stack detect`, `stack journal`), `hcore/tshirt.py` (`tshirt --order LEG|COR|Q|VIB [--grouping] [--load-by]`). software-factory Phase 1 appelle `stack detect`.
- **Fusion générique** : `fusion.op_array_union`, `op_add_key`, `op_tasks`, `plan_json`, `plan_lines`, `plan_text`, `write_plans` ; SF-01 à SF-03 réexprimés dessus, sortie inchangée ; `union_tools` (FU-05), `union_allowed_tools` (FU-06) ; `blocks.upsert_rgkb` (BK-01). Pas encore de CLI pour FU-05 et FU-06 : leurs appelants arrivent avec L8 et L9.
- **Défauts L2 et L3 corrigés** : politique validée avant d'ouvrir un run (`gate decide`) ; réponse hors options : voir l'itération 2 ci-dessous ; gates déclarées `free` (`ship-pr.target`, `factory-run.need`, `factory-run.questions`, `lab-run.pi-questions`, `brainstorm.subject`, `brainstorm.round`) ; `--models` reconnu seulement en tête ou en fin de `$ARGUMENTS` et suivi de `role=modele[;…]` ; rôle répété dans `--models` = exit 2 ; ship-pr ≤ 1016 caractères par ligne ; règles citées littéralement dans les docstrings des tests (`tests/test_rules.py`) ; état `bloc-mis-à-jour` pour un agent personnalisé dont seul le bloc `harness.model` est réécrit.
- **Écarts à la spec** : CA-22 couvre le moteur sur des opérations du type code-index (`settings.json` JSONC, `.mcp.json`) ; les fixtures attendues propres à code-index et ai-lab viennent avec L8 et L9, qui portent les règles CX et AL. La partie legacy-audit de CA-16 est jouée par `registry check` : le rejeu complet de l'audit relève de L7 et L11.

### L5 et L6 : itération 2 du Verifier (2026-10-17)

- **ship-pr** : un champ de correction étranger à la source (par exemple `size_correction` chez un validateur ship-pr) est ignoré, comme avant le lot ; seul `SPLIT` hors vibecode-audit rend la sortie inexploitable.
- **FD-07** : une `false_occurrence` hors de l'échantillon décrémente aussi `count` ; `corrected_count: 0` (littéral du gabarit de prompt) vaut « non fourni ».
- **Gates** : une gate à plusieurs questions prend exactement une option valide par question, dans l'ordre (catalogue : questions séparées par ` ; `) ; une gate par thème (`legacy-audit.assignment`, `ai-lab-audit.selection`) prend 1 à 4 options de sa liste. Une réponse hors options (« Other ») ne tue plus le run : `gate answer` rend `action: reask` (exit 0), rien n'est journalisé, la question est reposée (prose de ship-pr et de software-factory).
- **Registre projet** : `ship-pr start` exclut dès le préflight `.harness/runs/`, `.claude/findings.jsonl`, `.claude/findings.lock` et `.claude/findings.jsonl.*.tmp` ; `.git/info/exclude` est réécrit sous verrou (`exclude.hcore-lock`, `runs.locked_file`) et atomiquement ; `end-round` publie avant de sauver l'état final (un `LockTimeout` laisse la ronde ouverte, relancer `end-round`).
- **Stack, aligné sur BASE1 pour software-factory** : `environment.yml` et `*.ipynb` donnent la famille `python` mais pas la stack `python` ; tous les dossiers de premier niveau sont examinés ; ST-04 exclut les dossiers de `legacy-audit:37` à toute profondeur (`bin` compris, comme le cite cette ligne) et ceux ajoutés par `code-index:49` (`data`, `models`, `runs`…) à la racine seulement.
- **FU-05** : `tools:` vide reste vide ; valeur entre guillemets et commentaire YAML de fin de ligne conservés. **FU-06** : `union_allowed_tools` rend `(texte, avertissements)` ; une valeur contenant l'autre guillemet, ou un `--allowedTools` sans valeur entre guillemets, est laissée telle quelle et signalée.
- **Données** : les textes français des livrables (`Réécriture d'historique`, les deux critères `fuites`, « Aucune », barèmes DEV et GPU) sont dans `skills/_core/templates/deliverables.json`.
- **Traçabilité** : LK-01 et LK-02 sont cités dans les tests ; `test_rules.py` contrôle aussi le préfixe LK.

### L7 et L4 : ce qui est en place (2026-10-17)

- **Moteur d'audit** (`hcore/audit.py`, CLI `harness.py audit …`) : profils des trois audits en données (unités, préfixes, plafonds, livrable, préfixe de spec, statuts, clé de dédup, numérotation, gates, compteurs, rôles de modèle) ; `audit start` (AU-01 à AU-03, `--models` retiré pour l'audit seulement, sonde git AU-12, reprise AU-09, run ouvert dans le dépôt audité, X5) ; `audit auditor` (AU-04, AU-06) ; `audit validator` (AU-05, FD-06, FD-07) ; `audit next` (AU-07, compteurs AU-13) ; `audit consolidate` (AU-08) ; `audit themes` (AU-16) ; `audit readjust` (AU-15) ; `audit render` (AU-10, AU-11) ; `audit spec` (AU-14) ; `audit publish` (RG-03, sans git si `GIT_ABSENT`).
- **Gabarits** : textes français des trois livrables dans `skills/_core/templates/audits.json` ; les sections et lignes de tableau servent aussi à relire un livrable existant (reprise par les noms de champs, pas par les en-têtes).
- **Rejeux** : `tests/test_audit.py` rejoue les trois audits par la CLI sur des sorties figées (`tests/fixtures/audit/<skill>.json`) et compare le livrable à `tests/fixtures/audit/<skill>.expected.md` ; chaque ligne de structure des squelettes de BASE1 (`skeletons.json`) s'y retrouve. CA-21, CA-29 et CA-30 y sont couverts ; CA-27 l'est pour la partie moteur (le rebranchement des SKILL.md reste à L10-L12).
- **Usine du dépôt** (L4) : `.claude/agents/factory-*.md`, `.claude/skills/factory-run/SKILL.md`, `ci/factory.sh|.ps1` régénérés par `sf install` (agents avec `--model-role`, bloc `harness.model` à `inherit`) ; `sf apply --stacks ""` rend `identique` pour `settings.json`, `tasks.json` et `.gitignore` ; `.claude/harness/` copié par `sf copy-core` (Q-C). Tests : `tests/test_repo_factory.py` (UF-01 à UF-07, CA-31).
- **Mutations** : 16 règles AU, 7 règles UF et FD-08 mutées une à une sur une copie jetable du dépôt : chaque mutation fait échouer son test.
- **Écarts** :
  - La régénération retire d'abord les six fichiers générés : SF-04 ne remplace jamais un fichier qui diffère, et des fichiers sans bloc `harness.model` resteraient `personnalisé-conservé` (point d'attention de L2-L3). Leurs personnalisations hors bloc sont reportées dans le contenu régénéré (contexte du dépôt, format de spec avec *Décisions*, message headless, options de `ci/factory.*`).
  - `stack detect` ne trouve aucune stack du noyau dans ce dépôt : `sf apply` reçoit une liste vide, et `unittest` est imposé explicitement aux portes du Builder et du Verifier (CA-31), avec l'interpréteur détecté `py -3` (`Bash(py *)` en liste blanche).
  - vibecode-audit : un même motif trouvé par deux auditeurs n'est pas écarté mais signalé (`merge`), la fusion VA-07 relevant de L12.
  - legacy-audit et ai-lab-audit : un finding `UNVALIDATED` reste hors du livrable (compté au rapport) ; vibecode-audit le livre marqué `non validé`.
  - Nouvelles sections de livrable, exigées par la prose mais absentes des squelettes : « Familles non auditées » (legacy-audit), « Lentilles non auditées » (ai-lab-audit), et en tête d'AUDIT-vibecode.md les encadrés « Ordre par défaut » (headless) et « Famille non auditée ».
- **Reste** : rafraîchir `.claude/harness/` après toute évolution de `skills/_core/` (`sf copy-core --refresh`, L14).

### L7 et L4 : itération 2 du Verifier (2026-10-17)

- **Copie du noyau** : `T` ne contrôle plus que la cohérence interne de `.claude/harness/` (copie reconnue, `harness.py version` rend son propre `CORE_VERSION`, aucun bytecode) : un lot qui touche au noyau ne fait plus échouer `T`. L'identité stricte se vérifie à la demande : `HARNESS_CHECK_COPY=1` ou `sf copy-core --check` (exit 1 si la copie diffère). `sf copy-core --refresh` remplace une copie reconnue (fichiers du noyau créés ou remplacés), ne touche jamais un fichier étranger (signalé dans `foreign`) et laisse intact, en exit 1, un `.claude/harness/` qui n'est pas une copie de noyau.
- **Reprise (AU-09)** : colonnes trouvées par l'en-tête du tableau ; colonne en plus et `|` non échappé dans un titre tolérés ; toute ligne de finding illisible (cellules manquantes, id absent, en-tête incomplet, ligne hors des sections connues, titre de bloc illisible) = arrêt explicite qui nomme le fichier et la ligne (exit 1), avant l'ouverture du run ; la numérotation part du plus grand id présent dans le texte.
- **Statuts repris** : une ligne vibecode « non validé » reste `UNVALIDATED` (jamais publiée) ; une ligne et un bloc du même id font un seul finding ; un événement `DUPLICATE` n'écrase jamais l'état final d'une clé dans le registre de run.
- **Reprise vibecode** : dédup par énoncé ou par ensemble d'occurrences des blocs de détail repris (vibecode-audit:82) ; un nouveau motif prend sa place dans l'ordre TS-03 au milieu des lignes reprises ; l'encadré de validation compte tous les motifs du rapport (repris compris : tableau d'attaque, liste courte, rejetés ; seuls ceux du tableau peuvent être `non validé`), gains rapides et critiques remontés aussi ; relancer sur le livrable produit rend un fichier identique, pour les trois audits.
- **Fusion vibecode** : un même motif de deux auditeurs donne un `merge` quel que soit l'ordre d'appel et le statut du jumeau.
- **Headless vibecode** : les mineurs suivent le défaut de `vibecode-audit.order` (« Les détailler ») ; un motif non validé n'est jamais mis en liste courte ; la fixture et son attendu sont corrigés.
- **Modèles en audit** : `audit start` résout les modèles sans rien écrire (`models.resolve_readonly`, `lab-models.json` lu en mémoire) ; aucun `.claude/models.json` n'est créé dans le dépôt audité, même en cas d'échec.
- **Divers** : `READJUST` lu dans le catalogue des gates (`readjust_option`) ; `TRANCHEE (journal <date>)` exige une date de calendrier valide ; `factory-run start` supprime son fichier de transit une fois lu ; usine du dépôt : `<PY>` selon la règle D5 dans le factory-run, le Builder, le Verifier et le Planner, liste blanche CI `Bash(python *)`, `Bash(python3 *)`, `Bash(py *)`.
- **Mutations** : 26 mutations de l'itération 2 (un par point corrigé et par mutant survivant signalé) tuées sur une copie jetable.

### L7 et L4 : itération 3 du Verifier (2026-10-18)

- **Reprise vibecode après un SPLIT** : chaque part d'un `SPLIT` est dédoublonnée avant numérotation contre le rapport repris et contre le run (même énoncé ou même ensemble d'occurrences, vibecode-audit:82) ; une part déjà présente devient `DUPLICATE` et n'est jamais renumérotée. En amont, un motif dont les occurrences sont exactement l'union d'au moins deux parts (d'un même `split_from` du run, ou de blocs repris d'un même axe : le livrable ne garde pas le `split_from`) est écarté avant tout validateur.
- **Ordre explicite** : un `order` qui omet un id repris de la table d'attaque est refusé ; `audit start` (`resumed.ids`) et `audit consolidate` (`resumed_ids`) rendent les ids repris par section.
- **Colonne ajoutée par l'utilisateur** : une table reprise garde son en-tête ; les nouvelles lignes y reçoivent une cellule vide, la table reste alignée et relisible.
- **Copie du noyau** : `check_core_copy` et `refresh_core` comparent en octets et ne lisent jamais un fichier étranger (un binaire est signalé, intact) ; `--refresh` refuse (exit 1) une copie qui déclare une `CORE_VERSION` supérieure à celle du noyau, sauf `--force` (`--force` sans `--refresh` = exit 2) ; une copie aux fins de ligne CRLF reste reconnue.
- **D5 en headless** : `<PY>` est le champ `command` de `python .claude/harness/harness.py interp`, à défaut `python3 …`, puis `py -3 …` : trois commandes simples couvertes par `Bash(python *)`, `Bash(python3 *)`, `Bash(py *)` de `ci/factory.*` (la boucle shell, non couverte, a disparu du factory-run, du Builder, du Verifier et du Planner du dépôt). Le gabarit de software-factory n'est pas modifié : il écrit l'interpréteur retenu en clair et le met seul dans la liste blanche, ce qui fonctionne déjà en headless.
- **Mutations** : 15 mutations de l'itération 3 tuées ; les 26 de l'itération 2 rejouées, toutes tuées.

### L8 à L14 : ce qui est en place (2026-10-31)

Spec : `specs/SPEC-phase1-fin-L8-L14.md` (APPROUVEE), qui renvoie aux sections « Rebranchement, skill par skill » et « Découpage en lots » de `specs/SPEC-phase1-rebranchement.md`.

- **code-index (L8)** : D8 corrigé dans `assets/rgkb.py` (`init` ne réécrit jamais un `config.json` existant ; `hooks install` ne remplace pas un `config.json` illisible ; un marqueur de fin de bloc absent est refusé au lieu de tronquer le hook, comme `blocks.py` ; `TOOL_VERSION` 1.0.1). `hcore/cx.py` porte CX-01 à CX-16 ; CLI `harness.py cx args|rg|survey|install|register|scope|wire`. SKILL.md : 189 → 89 lignes. Tests : `tests/test_cx.py` (équivalence BK-02 comprise).
- **ai-lab et lab-run (L9)** : `hcore/lab.py` (AL-01 à AL-09, scripts `ci/lab.*` rendus depuis `templates/lab-ci.sh|ps1`), `hcore/labrun.py` (LR-01 à LR-09, machine d'états, C2 : Builder, Verifier et experts morts sont relancés une fois), `verdicts.parse_lab_verifier`. CLI `lab apply|ci` et `lab-run start|record`. SKILL.md : 231 → 99 lignes. Tests : `tests/test_lab.py`, dont les scripts `ci/lab.sh` joués avec un faux `claude`.
- **Audits (L10 à L12)** : le moteur existait ; ajouts : pré-finding de la famille hygiène si `GIT_ABSENT` (LA-03), `lab` et `subagent_type` par lentille dans `audit start` (AA-05), `audit settle` (AA-10, comparaison de dates), `audit plan` (plafonds `--max-specs`, `--max-questions` et `--max-findings`, mapping finding → spec, charge, gains rapides), `tshirt --cap`, 5 occurrences au plus avec le `count` réel (VA-04), surface non auditable de sévérité au moins `major` (VA-06), ordre de validation partielle (VA-09), liens de spec en `/` (LA-09). SKILL.md : legacy-audit 163 → 85, ai-lab-audit 145 → 91, vibecode-audit 191 → 106. Tests : `tests/test_audit_skills.py` (un test de comportement par règle AA, LA, VA).
- **brainstorm (L13)** : `hcore/bs.py` (BS-01 à BS-12), CLI `bs args|resume|round|render|finish`. X5 : aucune écriture avant la gate finale — le noyau est sans état, la session lui passe le sien sur l'entrée standard (heredoc à délimiteur quoté) ; `bs finish` écrit le journal et, sur *Écrire la synthèse*, `BRAINSTORM-<slug>.md` (FD-11 vérifié, lignes de l'ancienne section « Angles écartés » conservées). SKILL.md : 103 → 56 lignes. Tests : `tests/test_bs.py`.
- **L14** : README (paragraphe par skill rebranché, `.claude/models.json`, migration de `lab-models.json`, paragraphe `_core`), `.claude/harness/` rafraîchi par `sf copy-core --refresh`.
- **À noter** : un cycle `/brainstorm` ne crée un dossier `.harness/runs/` que s'il atteint sa gate finale. Un test de l'usine du dépôt (`test_repo_factory`, UF-01) compare les blocs `harness.model` des agents au `.claude/models.json` local de l'utilisateur (non versionné) : il échoue tant que les agents n'ont pas été régénérés avec ces modèles.
- **Recettes restantes (utilisateur)** : R4 (`/code-index` deux fois sur une fixture personnalisée), R5 (`/ai-lab` sur un `lab-models.json`), R6 (chaque audit sur fixture), R7 (`/brainstorm` interactif).

- Mineur (relecture L8-L14, 2026-10-31) : `lab-ci.sh` cherche `Statut : PRE-ENREGISTRE` par grep sur n'importe quelle ligne, alors que `labrun.entry` exige la ligne exacte.
- Mineur (relecture Phase 2, 2026-11-01) : `SPEC-vib-*` non produit (E-A2, SO-02/AD-08/AD-10) ; `allowed_writes` de vibecode-audit n'inclut pas `SPEC-vib-*`.
- Mineur (relecture Phase 2) : l'ordre des sections de `AUDIT.md` diffère de SO-01 (blocs conservés à l'intérieur de chaque jeu ; tri par `audit.PROFILES`, pas par ordre du tampon).
- Mineur (relecture Phase 2) : cadrage en deux gates au lieu d'une seule (AD-08/E-A5).
- Mineur (relecture Phase 2) : le test des écarts attendus (`expected-gaps.json`) ne vérifie que les identifiants.
- Mineur (relecture Phase 2) : `loop.route --models` avec un rôle hors profil rend un exit 2 peu explicite.
- Mineur (relecture Phase 2) : `cmd_sf_args` appelle `profiles.discover()` deux fois.

---

### Revue de code Phase 3 : mineurs à reprendre (2026-11-01)

- `union_tools` sur un agent en lecture seule `legacy` touche la ligne `tools:` hors bloc (`upgrade.py:434-440`).
- Le candidat de conversion n'est pas revérifié contre le sha du plan à l'application (`upgrade.py:719-729`).
- Le `TOOL_VERSION` de code-index est comparé à `CORE_VERSION` dans la garde UP-08 (`upgrade.py:232`).
- Un fichier `*.upgrade-tmp` peut rester après une exception (`upgrade.py:666`).
- `migrate` réécrit tout `findings.jsonl` (`migrate.py:61-65`).
- `_set_header` reconnaît une ligne d'en-tête hors de la zone d'en-tête (`render.py:200-211`).
- Reprise d'un lot (`--resume`) : le statut `ineligible` est conservé tel quel.
- `hook.py` post-edit : le budget de 5 s est plus court que `timeout_s` (30 s) du lint, ce qui peut laisser un lint orphelin.
- `.claude/settings.json` : le hook code en dur `py -3` ; le filet de sécurité est silencieusement inactif sous Linux/macOS sans le lanceur `py`.
- `eval` n'est pas analysé par la garde (hors périmètre par conception, risque I3).
- `chain` : un enfant sorti en 0 sans aucun run n'est pas compté comme un échec (seuls `is_error` et un wrapper mort le sont).
- `test_fb04_a_spec_whose_dependency_is_in_the_batch_waits_for_its_merge` : un échec isolé sous charge (`git worktree add failed`), qui ne se reproduit pas seul.
- Essai réel de `/audit` (hello world) : le chemin `_core/harness.py` cité par le skill n'existe pas dans le projet, et l'agent s'est rabattu sur `.claude/harness/harness.py`.
- Essai réel de `/audit` : après une erreur de nommage de champ (`difficulty` au lieu de la taille), un run `vibecode-audit` est resté orphelin dans `.harness/runs/`.
- Phase 7 : la garde de version se repère sur `-G '"version"'` : un commit qui modifie une autre ligne du manifeste contenant `"version"` déplace la base. Une baisse de version passe aussi pour une hausse.
- Phase 7 : la détection du mode plugin suppose que `CLAUDE_SKILL_DIR` reste le chemin du lien, non résolu (recette R1). Si Claude Code le résolvait un jour, une installation par liens rendrait `harness:<skill>`.
- Phase 7 : `test_repo_factory` ne teste plus l'idempotence du bloc modèle (`harness.model`), car ce bloc a disparu au passage en core 4.0.
- Corrigé en Phase 7 : `queue.scan` plantait quand le worktree d'une spec mergée était retiré pendant le parcours. C'était la cause des échecs intermittents de fb02, fb04 et fb05.
- English translation (2026-11-02): user-visible French labels remain in `hcore/cx.py` (`Index: réindexer`, the search prompt) and `hcore/lab.py` (`Lab: nouvelle expérience`); French state words in `fusion.py`, `hooks_install.py`, `queue.py` (`créé`, `fusionné`, `mergée`); French quotes in `audit.py` comments; `unified.py:1742` cites only `Défaut :`; `brainstorm` keeps `SUJET`, `[énoncé]` and the quoted heading "non retenus dans ce cycle".
- English translation: the guard rejects globs, so a recursive delete of `.harness/tmp/` with a `*` glob is blocked (naming the folder passes).
- Real use: the Bash guard analyses the body of a heredoc as commands (a Python heredoc quoting a delete command was blocked).
- English translation: `test_px03` no longer compares the extracted Phase 2 sentences (the French BASE2 copies are legacy fixtures); it only checks the inventory is well formed.
- Real use: a cycle whose Builder hits the Bash guard stops (`destructive`) without deactivating its scope marker; `factory-run` could run `deactivate` on that stop.

## 9. Phase 3 — état (2026-11-01)

Spec : `specs/SPEC-phase3-upgrade-doctor.md` (détail) et `specs/SPEC-phase3-run.md` (périmètre du run). Livré dans l'arbre de travail, non commité : version du dépôt (`hcore/version.py`), tampon complet (`stamp.py`, `STAMP.md`), historique du noyau et MANIFEST (`history.py`), rendu déterministe et en-têtes (`render.py`), conversion Q6 (`convert.py`), migrations (`migrate.py`), moteur d'upgrade (`upgrade.py`), `doctor.py`, `scan.py`, skill `harness-doctor`, `--upgrade` sur `software-factory`, `ai-lab` et `code-index`.

Points d'attention pour la suite :
- **Fragments de corps** : les profils `software` ont des fragments de corps dédiés (`profiles/software/bodies/`) ; ceux du profil `research` sont dérivés de leurs fragments de mission (`render.mission_parts`), à réécrire en vrais prompts.
- **Recettes** R12 à R16 restent à faire par l'utilisateur (lien installé, commentaires YAML dans le frontmatter, invocation de skill par le doctor, upgrade d'un vrai projet, scan de la machine).
- **Contributions** : `code-index --upgrade` pose `contributes` au tampon ; la liste `tools:` des agents dans la mise en page du harnais n'est mise à jour que par le `--upgrade` suivant de `software-factory` (UP-12).
- **`history.json`** doit être régénéré (`harness.py core history --rebuild`) après chaque commit qui touche `skills/_core/` ; `core history --check` est une porte du Builder.
- Mineurs du Verifier à consigner ici.

## 10. Phases 4 et 5 — état (2026-11-01)

Spec : `specs/SPEC-phase4-5-autonomie-hooks.md` (détail) et `specs/SPEC-phase4-5-run.md` (périmètre du run). Livré dans l'arbre de travail, non commité : politique `autonomy` (AP), fichiers `STOP-*.md` (SX), spec `BLOQUEE` et statuts (BQ), merge automatique de ship-pr (SM), enchaînements par processus enfant headless (CH), priorisation calculée des audits (PZ), upgrade automatique du doctor (UA), `/factory-queue` (FQ), worktrees (WT), `/factory-batch` (FB), hooks Claude Code (HK, HG, HP, HD, HR, HL).

Points d'attention pour la suite :
- **Recettes** de la spec Phases 4-5 (R12 à R18, à ne pas confondre avec R12 à R16 de la Phase 3) restent à faire par l'utilisateur : `claude -p` imbriqué, `${CLAUDE_SESSION_ID}`, shell des hooks sous Windows, `additionalContext` / `systemMessage` / `continue: false`, prise en compte des hooks en cours de session, `/factory-queue run` et `/factory-batch` réels sur un dépôt jetable.
- Les statuts de spec ne sont pas écrits dans le code : ils viennent des artefacts des profils (`status_proposed`, `status_blocked`, `status_ready`, `status_delivered`).
- `harness-doctor` : en `auto`, `K doctor auto-upgrade --plan` lit le plan écrit par `K upgrade plan` (les types `header`, `merge`, `copy`, `local`, `stamp`, `block` sont sûrs ; `create`, `convert`, `migrate`, ou un fichier de la gate `upgrade.convert` font proposer au lieu de lancer). Les anciennes gates `harness-doctor.upgrade-blocks` et `-other` restent au catalogue.
- Gates de dialogue (`brainstorm.*`) : pas de défaut `auto`, donc pas de ligne « Défauts en politique `auto` » dans `skills/brainstorm/` (intouché).
- Le moteur de chaînage lance `claude` détaché via un wrapper (`chain exec`) qui tue l'arbre au timeout ; la détection « en cours » d'une spec repose sur `updated_at` du fichier d'état (risque I5).
- Mineurs du Verifier à consigner ici.

## 11. Phase 6 — état (2026-11-01)

Spec : `specs/SPEC-phase6-tests-harnais.md` (détail) et `specs/SPEC-phase6-run.md` (périmètre du run). Livré dans l'arbre de travail, non commité : lanceurs `ci/test-harness.sh` et `ci/test-harness.ps1`, runner `ci/scenarios/` (un module par scénario), fixtures `ci/fixtures/` (`toy-py`, `legacy-node`, `agents`, `expected`), faux `gh` complété (`pr checks`, protection de branche, `--body-file`, `--delete-branch`), README « Tester le harnais ».

Statut des scénarios : `install-fresh`, `upgrade-legacy`, `factory-auto`, `stop-iteration3`, `shippr-automerge`, `models-absent`, `models-legacy` passent ; `install-skills` passe sous PowerShell et est `SKIP` sous Git Bash (Q7) ; `hook-diff` passe (défaut révélé corrigé, voir ci-dessous) ; `live-*` n'ont pas été lancés (coût).

Points d'attention pour la suite :
- **Défaut révélé par `hook-diff.0` — corrigé** : `ship-pr start` pose maintenant `"status": "running"` dans l'état du run, et `skills/ship-pr/SKILL.md` prescrit `activate` après `start` et `deactivate` en fin de cycle ; le hook de diff s'applique donc à un vrai cycle `ship-pr` et `hook-diff.0` passe.
- **Écarts de la spec Phase 6 retenus** : `install_skills.sh|.ps1` sont inchangés (consigne du run) ; ils sont donc lancés avec un `HOME`/`USERPROFILE` temporaire plutôt qu'avec `--target`/`-TargetRoot` (IN-01 non réalisé, `$HOME` d'un nouveau processus `pwsh` suit l'environnement). Le hook signale une erreur interne par un `systemMessage` sur stdout et `hook-errors.jsonl` (décision HK-04 de la Phase 5), pas sur stderr. `copy-core` ajoute `MANIFEST.json`, seul écart toléré de `install-fresh.3`. Les assertions de `install-fresh` suivent le plan unique de la Phase 3 (`upgrade plan` puis `apply`) et non `sf install` fichier par fichier.
- **Dérive du corps généré de `factory-run` — corrigée** : `profiles/software/bodies/orchestrator.md` est désormais l'unique source de la procédure (`factory-run bind`, `spec settle`, `activate`/`deactivate`, politique `auto`, livraison) ; `profiles/software/orchestrator.md` ne porte plus que le frontmatter et renvoie à ce fragment. Le corps du Planner a aussi reçu les champs de la Phase 4 (`Questions bloquantes`, `Défaut :`, `Périmètre fichiers`). Le test de rendu `test_render` vérifie que le corps d'une installation neuve égale le fragment ; `factory-auto` contrôle que le skill installé prescrit les commandes qu'il rejoue. Le profil `research` n'avait pas de dérive (corps tiré de son seul `orchestrator.md`).
- `history.json` a été régénéré (`core history --rebuild`) parce que `skills/_core/tests/fake_gh.py` fait partie du noyau ; `.claude/harness/` rafraîchi par `sf copy-core --refresh`.
- La suite unitaire complète dure plus de 10 minutes sur cette machine (754 tests) : à lancer par tranches de modules sous un délai d'outil de 10 minutes.
- Recettes R12 (`--live`) et R13 (`ship-pr` réel sur un dépôt jetable) restent à faire par l'utilisateur.
- Mineurs du Verifier à consigner ici.

## 12. Phase 7 — plugin `harness`, étapes M1 à M3 (2026-11-01)

- Livré : `.claude-plugin/plugin.json` (`harness` 2.0.0) et `marketplace.json` (source `./`) ; garde de version `harness.py plugin version-guard` (scénario `plugin-guard`) ; scénario `plugin-validate` (SKIP sans `claude`) ; nom effectif `harness.py plugin skill-name` (alias AX-01/AX-04, `ai-lab`, `harness-doctor`) ; version du tampon lue dans `plugin.json` avec repli sur git (VS-05) ; `install_skills.*` avec avertissement de retrait et `--unlink` / `-Unlink` (scénario `install-unlink`) ; README « Installer ».
- Garde : sans commit antérieur de `plugin.json`, elle passe (`no_baseline`). Une fois ce fichier commité, tout changement sous `skills/` exige de relever `version`.
- Le tampon d'un projet équipé note désormais la `version` du plugin (p. ex. `2.0.0`) au lieu du hash git ; les anciens tampons (hash git) restent reconnus par leur commit.
- Les chaînes `claude -p "/factory-run …"` et le corps de l'orchestrateur généré gardent la forme courte (P3 : elle fonctionne en headless) ; le nom effectif n'est pas propagé dans les copies projet, qui ne connaissent pas le mode d'installation.
- Échecs préexistants de `test_repo_factory` (6 tests, `.claude/agents`, `ci/factory.sh`), antérieurs à cette phase (commit c3c3f3d) ; ils ne dépendent pas des fichiers modifiés ici.
- `history.json` régénéré, `.claude/harness/` rafraîchi. M4 reste hors périmètre.
