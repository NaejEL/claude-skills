# SPEC — Noyau Python `skills/_core/` et journal de cycle, rebranchement de software-factory (factory-run) et ship-pr

Statut : APPROUVEE

Incrément 1 de la feuille de route `specs/harness-v2/ROADMAP.md`. Les corrections de cap sont consignées dans `specs/harness-v2/BACKLOG.md`.

## Contexte

**Le besoin.** Ce cycle produit le premier incrément de la feuille de route, et seulement lui. Deux principes le gouvernent.

1. **Code avant prose.** Tout ce qui est déterministe quitte les `SKILL.md` et devient du Python stdlib sous `skills/_core/` :
   - le parsing des blocs JSON de verdict ;
   - les compteurs d'itérations et de rondes ;
   - le registre cumulatif des findings ;
   - le journal de cycle ;
   - la décision de relancer un agent mort ;
   - la lecture de `models.json` et de `--models` ;
   - la fusion de `settings.json` et les blocs délimités.

   Les prompts ne gardent que le jugement : rôle, périmètre, interdits, format attendu.
2. **Mesurer avant d'étendre.** Un journal `.claude/runs/<skill>-<horodatage>.jsonl` fait partie de cet incrément.

Seuls `software-factory` (et le `factory-run` qu'il génère) et `ship-pr` sont rebranchés. Le comportement observable reste identique, à trois exceptions près, décidées par l'utilisateur :

- le journal apparaît ;
- le noyau est copié dans les projets équipés par software-factory (D1) ;
- `.claude/runs/` est exclu de git (D3).

**État actuel (commit de référence `BASE=7be1afb`).**

- **Seul précédent Python : `skills/code-index/assets/rgkb.py`.**
  - Stdlib uniquement, `from __future__ import annotations` (`rgkb.py:11`), constante `TOOL_VERSION` (`rgkb.py:26`).
  - Copié tel quel dans le projet sous `.claude/rgkb/` (`code-index/SKILL.md:27`, `:53`).
  - Interpréteur choisi parmi `python`, `python3`, `py -3` (`code-index/SKILL.md:41`).
- **Aucun dossier `tests/`.** Les portes de l'usine du dépôt ne connaissent que `bash -n` et `bats` (`.claude/agents/factory-builder.md:28-32`, `factory-verifier.md:17-20`). Sur la machine de l'utilisateur, `bats` et pytest sont absents, et `rg` n'est pas dans le PATH de Git Bash.
- **Règles déterministes encore en prose :**
  - `skills/software-factory/SKILL.md` :
    - fusions de settings et tasks (`:18`, `:121`, `:125-132`) ;
    - `.gitignore` (`:117`) ;
    - états de fichier (`:20`, `:144`) ;
    - gabarit `factory-run` (`:94-105`) ;
    - liste blanche CI (`:114`).
  - `skills/ship-pr/SKILL.md` :
    - bornes `--rounds`/`--themes` (`:16-17`) ;
    - agents morts (`:24`) ;
    - registre (`:27`, `:93`) ;
    - préflight (`:33-37`) ;
    - recherche ou création de PR (`:45-63`) ;
    - schémas JSON (`:87-89`, `:96-98`) ;
    - sortie de boucle (`:69-70`, `:100`) ;
    - commits, threads et merge (`:104-147`) ;
    - consignation et compteurs (`:149`, `:155`, `:172`).
- **Mode headless.** `ci/factory.sh:61` et le gabarit (`software-factory:114`) n'autorisent aucun interpréteur Python.
- **Installeurs.** `install_skills.sh:176` et `install_skills.ps1:168` lient **tout** sous-dossier de `skills/`. `skills/_core/` sera donc lié en `~/.claude/skills/_core` sans modifier les installeurs.
- **Doc Claude Code.** `${CLAUDE_SKILL_DIR}` est documenté. En revanche, la lecture d'un fichier hors du dossier du skill ne l'est pas, et la doc ne dit pas si cette variable donne le chemin du lien ou le chemin résolu. Le bloc `<usage>` (tokens, durée) renvoyé par l'outil Agent est observé mais non documenté.
- **Machine de l'utilisateur.** `python` est le stub du Microsoft Store, qui ne répond pas. `py -3` donne Python 3.9.13.

**Tailles mesurées** (`git show 7be1afb:<fichier> | wc -l`) :

| Fichier | Lignes à `BASE` | Cible (≤ ⌊2/3⌋) |
| --- | --- | --- |
| `skills/software-factory/SKILL.md` | 144 | ≤ 96 |
| `skills/ship-pr/SKILL.md` | 177 | ≤ 118 |

## Périmètre

1. **Créer `skills/_core/`**, en Python stdlib compatible 3.9, avec une constante de version du noyau. Le contenu :
   - parsing et validation des blocs JSON terminaux (verdict du Verifier, findings du relecteur, verdict du validateur) ;
   - compteurs d'itérations et de rondes, avec leurs bornes ;
   - registre cumulatif des findings (D2) ;
   - journal de cycle JSONL : écriture et sous-commande de validation de schéma ;
   - décision de relance d'un agent mort : une relance, puis échec explicite, sans consommer d'itération ni de ronde ;
   - lecture de `.claude/models.json` et de `--models`, **module seul, non branché** (D6) ;
   - fusion de `settings.json`, `tasks.json` et `.gitignore` ;
   - blocs délimités, **module seul, non utilisé par software-factory** (D9) ;
   - détection de l'interpréteur (D5) ;
   - séquences `gh`/`git` déterministes de ship-pr, dans la mesure nécessaire pour tenir la cible de lignes (D11) : préflight et ses messages d'arrêt, recherche ou création de PR, collecte du diff, réponse et résolution des threads, conditions et exécution du merge.

   Le code est exposé par une CLI unique (`<PY> skills/_core/<point d'entrée> <sous-commande> …`), pour que les `SKILL.md` l'appellent par Bash. Les tests unitaires sont en `unittest` stdlib, sous `skills/_core/tests/`.
2. **Inventaire des règles déplacées.** Chaque règle déterministe déplacée reçoit un identifiant. Elle est couverte par au moins un test, et le `SKILL.md` d'origine la pointe avec son identifiant et le module qui la porte. Inventaire minimal :
   - **ship-pr :**
     - `SP-01` : rondes `min(N,3)`, défaut 3 ; N ≤ 0 ou non entier → erreur explicite (D8) (`:16`) ;
     - `SP-02` : thèmes séparés par `;`, 4 au plus, 3 par défaut ; liste vide ou plus de 4 entrées → erreur explicite (D8) (`:17`, `:79-83`) ;
     - `SP-03` : bloc du relecteur (`:87-89`), sortie inexploitable = agent mort (`:24`) ;
     - `SP-04` : bloc du validateur (`:96-98`) ;
     - `SP-05` : thème mort → une relance → thème non couvert → merge refusé, pas de sortie anticipée sur son silence (`:24`) ;
     - `SP-06` : validateur mort → finding non validé, ni posté ni corrigé (`:24`) ;
     - `SP-07` : registre et dédoublonnage, REJETÉS compris (`:27`, `:93`) ;
     - `SP-08` : sortie de boucle par épuisement ou par plafond (`:69-70`, `:100`) ;
     - `SP-09` : finding confirmé non corrigé consigné (`:149`) ;
     - `SP-10` : compteurs bruts / confirmés / rejetés par ronde (`:155`, `:172`).

     S'y ajoutent `SP-11` et la suite pour chaque séquence `gh`/`git` déplacée.
   - **software-factory :**
     - `SF-01` : fusion de `permissions.deny` et correspondance avec la stack (`:121`, `:18`) ;
     - `SF-02` : fusion de `tasks.json` (`:125-132`) ;
     - `SF-03` : `.gitignore` sans doublon (`:117`) ;
     - `SF-04` : états de fichier (`:20`, `:144`).
   - **factory-run (gabarit) :**
     - `FR-01` : entrée sur une spec `Statut : APPROUVEE` (`:96`) ;
     - `FR-02` : succès si `APPROVED` et `tests_passed` (`:101`) ;
     - `FR-03` : 3 itérations puis échec explicite, jamais d'approbation par épuisement (`:99`, `:103`) ;
     - `FR-04` : agent mort ou sortie inexploitable → une relance sans consommer d'itération, puis échec explicite (`:104`).
3. **Rebrancher `skills/software-factory/SKILL.md`.**
   - En Phase 4, software-factory **copie** `_core` dans le projet sous `.claude/harness/`, tel quel, avec sa constante de version, sur le modèle de rgkb (D1).
   - Le gabarit `factory-run` qu'il génère appelle le noyau via `.claude/harness/`.
   - La liste blanche des scripts CI générés autorise l'interpréteur.
   - Le `.gitignore` généré exclut `.claude/runs/` (D3).
4. **Rebrancher `skills/ship-pr/SKILL.md`.**
   - ship-pr appelle le noyau via `${CLAUDE_SKILL_DIR}/../_core` (D1).
   - Il ajoute `.claude/runs/` à `.git/info/exclude` du dépôt cible s'il n'y figure pas déjà (D3).
5. **Journaliser chaque appel de sous-agent** de `factory-run` et de `ship-pr` dans `.claude/runs/<skill>-<AAAAMMJJ-HHMMSS>.jsonl` du dépôt cible. Une ligne par appel, avec :
   - `agent` ;
   - `model` ;
   - `duration_ms` ;
   - `iteration` (itération ou ronde) ;
   - `verdict` ;
   - `findings` : `{produced, validated, rejected}` ;
   - `tokens` (entier ou `null`).

   Le journal ne change aucun autre comportement. Le registre de ship-pr vit à côté : `.claude/runs/ship-pr-<horodatage>.registry.jsonl` (D2).
6. **Fixtures et rejeux.**
   - `tests/fixtures/` contient un projet jouet minimal.
   - Des tests de **rejeu scripté** exécutent la séquence d'appels au noyau prescrite par chaque `SKILL.md`, et produisent un journal (D4).
   - Les dépôts git jetables sont créés dans un dossier temporaire par les tests eux-mêmes.
7. **`README.md`** : un court paragraphe sur `_core` (D10). Il dit que ce n'est pas un skill, que l'installeur le lie, et que software-factory le copie dans les projets.
8. **`.gitignore` de ce dépôt** : ajouter `.claude/runs/` (D3) et `__pycache__/`.
9. **Ne toucher ni aux autres skills, ni à `install_skills.*`, ni à l'usine de ce dépôt** (`.claude/skills/factory-run/`, `.claude/agents/`, `ci/factory.*`) (D7).

**Définition opérationnelle de « comportement observable identique ».**

- **(a) Artefacts de software-factory.** Le noyau produit `settings.json`, `tasks.json` et `.gitignore` à partir des entrées de fixture. Ces fichiers sont égaux à des fichiers attendus versionnés : comparaison sur le JSON parsé, ordre des clés préservé. Une seconde application ne produit aucun changement, octet pour octet. Seuls ajouts admis : `.claude/runs/` dans `.gitignore` et la liste blanche de l'interpréteur.
- **(b) Gates et bornes.** Les tests rejouent les séquences suivantes :
  - 3 `CHANGES_REQUESTED` → échec avec les issues ;
  - `APPROVED` avec `tests_passed=false` → pas de succès ;
  - Verifier mort puis vivant → compteur inchangé ;
  - mort deux fois → échec explicite ;
  - thème mort deux fois → merge refusé ;
  - finding REJETÉ soumis à nouveau → écarté sans passer par le validateur.
- **(c) Messages.** Les messages d'arrêt existants restent présents à l'identique, dans le `SKILL.md` ou dans le noyau.
- **(d) Fichiers générés par software-factory.** La liste de chemins est la même qu'avant, plus `.claude/harness/**`.
- **(e) Gates humaines.** Les mêmes points `AskUserQuestion` restent, aux mêmes moments, avec les mêmes options.

## Critères d'acceptation

`<PY>` désigne l'interpréteur détecté (`py -3` sur la machine de l'utilisateur). Les tests sont lancés avec `-B` pour ne laisser aucun bytecode. `BASE=7be1afb`. Les recherches utilisent `grep` (`rg` est absent du PATH de Git Bash).

- [ ] **CA1 — Tests du noyau verts.**
  - Commande : `<PY> -B -m unittest discover -s skills/_core/tests -v`.
  - Attendu : exit 0, et au moins un test par module listé au point 1 du Périmètre.
- [ ] **CA2 — Stdlib seule, Python 3.9.**
  - Commande : `<PY> -B -I -S -m unittest discover -s skills/_core/tests`.
  - Attendu : exit 0, avec un `<PY> --version` en 3.9.x.
- [ ] **CA3 — Chaque règle déplacée est testée.**
  - Commande : pour chaque identifiant `SP-*`, `SF-*` et `FR-*` de l'inventaire, `grep -rl "<ID>" skills/_core/tests`.
  - Attendu : au moins un fichier par identifiant.
- [ ] **CA4 — Chaque règle déplacée est pointée.**
  - `grep -oE "SP-[0-9]{2}" skills/ship-pr/SKILL.md | sort -u | wc -l` ≥ 10, et égal au nombre d'identifiants `SP-*` de l'inventaire.
  - `grep -oE "(SF|FR)-[0-9]{2}" skills/software-factory/SKILL.md | sort -u | wc -l` = 8.
  - `grep -c "_core" skills/ship-pr/SKILL.md` ≥ 1.
  - `grep -cE "_core|\.claude/harness" skills/software-factory/SKILL.md` ≥ 1.
- [ ] **CA5 — Un tiers de lignes en moins (cible ferme).**
  - `wc -l < skills/software-factory/SKILL.md` ≤ 96.
  - `wc -l < skills/ship-pr/SKILL.md` ≤ 118.
- [ ] **CA6 — Le jugement reste dans les prompts.** Chacune de ces commandes trouve au moins une correspondance :
  - `grep -F "zéro finding est une réponse acceptable et fréquente" skills/ship-pr/SKILL.md` ;
  - `grep -F "Ne jamais approuver par épuisement" skills/software-factory/SKILL.md` ;
  - `grep -F "Jamais d'amend, jamais de force-push" skills/ship-pr/SKILL.md` ;
  - `grep -F "Jamais de merge sans validation explicite" skills/ship-pr/SKILL.md`.
- [ ] **CA7 — Messages d'arrêt conservés.** Chaque message d'arrêt de `ship-pr/SKILL.md:33-36` à `BASE`, traduit en anglais le 2026-10-17 (« gh not authenticated », « no GitHub remote », « you are already on », « does not exist on origin »), est trouvé par `grep -rF` dans `skills/ship-pr/` ou `skills/_core/`.
- [ ] **CA8 — Frontmatter valide.**
  - La première ligne des deux `SKILL.md` est `---`.
  - La deuxième est `name: ship-pr`, respectivement `name: software-factory`.
  - Une ligne `description:` non vide figure avant le `---` de fermeture.
- [ ] **CA9 — Schéma du journal vérifié par commande.** La sous-commande de validation du noyau, appliquée à un journal :
  - rend exit 0 si chaque ligne est un objet JSON portant `agent`, `model`, `duration_ms`, `iteration`, `verdict`, `findings` (avec `produced`, `validated` et `rejected` entiers ≥ 0) et `tokens` (entier ou `null`) ;
  - rend un exit ≠ 0 sur une ligne sans `verdict` et sur une ligne qui n'est pas du JSON. Ces deux contre-tests sont des tests unitaires.
- [ ] **CA10 — Nom de fichier du journal.** Les journaux produits par les tests ont un nom conforme à `^(factory-run|ship-pr)-[0-9]{8}-[0-9]{6}\.jsonl$`.
- [ ] **CA11 — Le journal ne salit pas git.** Dans un dépôt git jetable où le noyau a appliqué l'exclusion de ship-pr (`.git/info/exclude`) puis écrit un journal et un registre, `git status --porcelain` ne liste aucun chemin sous `.claude/runs/`. Il en va de même avec le `.gitignore` produit par la fusion de software-factory. L'exclusion est idempotente : une seconde application n'ajoute pas de ligne.
- [ ] **CA12 — Fusions identiques à l'existant (SF-01 à SF-03).** Tests unitaires sur fixtures, inclus dans CA1, couvrant :
  - clé tierce préservée ;
  - `deny` sans doublon ;
  - tâches et inputs existants préservés ;
  - les trois tâches Factory et l'input `factorySpec` présents une seule fois ;
  - ligne `.gitignore` ajoutée une seule fois ;
  - seconde application identique, octet pour octet.
- [ ] **CA13 — Mode headless possible.**
  - `grep -nE "Bash\((py|python3?) " skills/software-factory/SKILL.md` ≥ 1 (liste blanche CI du gabarit).
  - `grep -n "\.claude/harness" skills/software-factory/SKILL.md` ≥ 1 (copie du noyau dans le projet).
- [ ] **CA14 — Détection de l'interpréteur.** Des tests unitaires, avec des exécutables simulés, vérifient trois cas :
  - un candidat qui ne répond pas avant le délai (comme le stub du Store) est écarté sans bloquer ;
  - un candidat en version < 3.9 est écarté ;
  - l'ordre `python` → `python3` → `py -3` est respecté.
- [ ] **CA15 — Rejeu factory-run.** Un test de rejeu scripté de la séquence factory-run produit un `.claude/runs/factory-run-*.jsonl` dans un dossier temporaire. Le rejeu enchaîne :
  - Builder ;
  - Verifier `CHANGES_REQUESTED` ;
  - Builder ;
  - Verifier mort ;
  - Verifier `APPROVED`.

  Le journal produit :
  - passe CA9 ;
  - contient des lignes `agent=factory-builder` et `agent=factory-verifier` ;
  - a toutes ses lignes avec `iteration` ≤ 3 ;
  - montre que le Verifier mort n'a pas consommé d'itération.
- [ ] **CA16 — Rejeu ship-pr.** Un test de rejeu scripté de la séquence ship-pr (thèmes, validateur, sortie par épuisement) produit un `.claude/runs/ship-pr-*.jsonl` et un `.registry.jsonl`. Le journal passe CA9, contient au moins une ligne par thème lancé, et a `iteration` ≤ 3. Le registre contient un finding REJETÉ, et sa nouvelle soumission en ronde 2 n'atteint pas le validateur.
- [ ] **CA17 — Zéro diff sur ce qui ne bouge pas.**
  - Commande : `git diff --exit-code 7be1afb -- skills/ai-lab skills/ai-lab-audit skills/brainstorm skills/code-index skills/legacy-audit skills/vibecode-audit install_skills.sh install_skills.ps1 .claude/skills .claude/agents ci/factory.sh ci/factory.ps1`.
  - Attendu : exit 0, et `git status --porcelain -- <mêmes chemins>` vide.
- [ ] **CA18 — Pas d'artefact parasite.** `git status --porcelain` ne liste ni `__pycache__/`, ni `.pyc`, ni journal, ni fichier temporaire de test.

**Recette par l'utilisateur, hors portes du Verifier :**

- **R1** : lancer l'installeur, puis un skill sonde, pour vérifier que `${CLAUDE_SKILL_DIR}/../_core` est atteint et que `_core` n'apparaît pas comme skill parasite dans `/skills`.
- **R2** : `/software-factory` sur `tests/fixtures/`, puis un cycle `/factory-run` réel. Le journal produit passe CA9.
- **R3** : `/ship-pr` sur un dépôt GitHub jetable. Le journal passe CA9.

## Hors-périmètre

- Profils, scout, `/audit` unifié, versioning / upgrade / doctor, politique d'autonomie, hooks Claude Code, file et worktrees, packaging. Ils sont listés en annexe.
- Tout nouveau skill.
- Rebrancher `ai-lab`, `ai-lab-audit`, `legacy-audit`, `vibecode-audit`, `brainstorm` ou `code-index`.
- Régénérer l'usine de ce dépôt (D7).
- Brancher `models.json` / `--models` (D6) et utiliser les blocs délimités dans les fichiers générés (D9).
- Le bug `rgkb.py init` qui écrase `.knowledge/config.json` (`rgkb.py:568`).
- La dédup sémantique (« même sujet », `ship-pr:93`). Elle reste au jugement du prompt ; le noyau ne porte que la clé déterministe.
- Ajouter `--models` à l'`argument-hint`. Ajouter une option `--dry-run` à ship-pr.
- Tout commit, push, ou exécution de `install_skills.*` par le Builder.

## Risques

- **Partage non documenté.** `${CLAUDE_SKILL_DIR}/../_core` et un `_core/` sans `SKILL.md` dans `~/.claude/skills` ont un comportement non documenté. La recette R1 le tranche. En cas d'échec, ship-pr bascule vers une copie de `_core` dans son propre dossier, ce qui relève d'une spec corrective.
- **Le noyau ne relance pas un agent lui-même.** Il porte la décision (relancer, échouer, compter) ; l'orchestrateur LLM l'exécute. La règle n'est déterministe que si le prompt appelle le noyau à chaque transition. Un appel oublié reproduit le défaut actuel sans le signaler.
- **Tokens et durée.** Ils dépendent du bloc `<usage>`, non documenté. S'il est absent, `tokens` vaut `null` et la durée vient d'horodatages pris par le noyau autour de l'appel.
- **Cible −⅓ ferme sur ship-pr.** Elle impose de sortir des séquences `gh`/`git` dans le noyau (D11), donc d'en tester une partie avec un `gh` et un `git` simulés. Le risque est de déplacer de la logique sans la couvrir.
- **Permissions interactives.** Chaque appel au noyau par Bash peut déclencher une demande de permission. C'est acceptable dans ce cycle, et c'est à mesurer avec le journal.
- **Usine du dépôt dérivée (D7).** Le Verifier de ce cycle ne connaît pas `unittest` dans ses portes. L'orchestrateur lui passe explicitement CA1 à CA18.
- **Copie dans les projets (D1).** Elle crée une seconde copie du noyau par projet, à resynchroniser lors de futures mises à jour. C'est l'objet de la spec « versioning / upgrade » en annexe.

## Décisions

Réponses de l'utilisateur le 2026-10-16.

- **D1 — Partage du code.** Mixte.
  - ship-pr (skill global) appelle `${CLAUDE_SKILL_DIR}/../_core`, sous réserve de la recette R1.
  - Le `factory-run` généré utilise une copie de `_core` dans le projet, sous `.claude/harness/`, à la manière de rgkb. Le dossier versionné en plus dans les projets est un écart accepté.
- **D2 — Registre.**
  - Format : une ligne JSON par finding, clés anglaises `file`/`line`/`title`/`verdict` alignées sur les blocs existants. C'est un sur-ensemble de `{fichier, ligne, résumé, verdict}`.
  - Dédup déterministe sur `file` + titre normalisé.
  - Statuts : `CONFIRMED`, `REJECTED`, `UNVALIDATED`, `FIXED`, `NOT_FIXED`.
  - Emplacement : `.claude/runs/`, durée de vie du run, non versionné.
- **D3 — Exclusion git du journal.**
  - software-factory ajoute `.claude/runs/` au `.gitignore` généré.
  - ship-pr l'ajoute à `.git/info/exclude` du dépôt cible.
  - Ce dépôt l'ajoute à son `.gitignore`.
- **D4 — Exécutions à blanc.**
  - Critères automatiques : rejeu scripté des séquences d'appels au noyau.
  - Recettes manuelles par l'utilisateur : R2 et R3.
  - Fixture dans `tests/fixtures/`, dépôts git jetables en dossier temporaire.
- **D5 — Interpréteur.** Détection à l'exécution `python` → `python3` → `py -3`, chacun avec délai d'expiration et vérification de version (plancher 3.9).
- **D6 — models.json / --models.** Module et tests seulement, non branché.
- **D7 — Usine de ce dépôt.** Inchangée ; sa régénération est une spec suivante.
- **D8 — Bornes non définies.** Erreur explicite : `--rounds` ≤ 0 ou non entier, `--themes` vide ou à plus de 4 entrées.
- **D9 — Blocs délimités.** Module et tests seulement, non utilisé par software-factory.
- **D10 — README.** Un paragraphe sur `_core`.
- **D11 — Cible −⅓.** Ferme pour les deux skills. Pour ship-pr, les séquences `gh`/`git` déterministes (préflight, recherche de PR, threads, merge) passent dans le noyau si c'est nécessaire pour tenir ≤ 118 lignes.

## Annexe — specs suivantes, ordonnées

0. *(cette spec)* Noyau `_core`, journal de cycle, rebranchement de software-factory / factory-run et de ship-pr.
1. Régénération de l'usine du dépôt (instance `factory-run`, agents `factory-*`, `ci/factory.*`) depuis le gabarit rebranché. Dépend de : 0.
2. Rebranchement de code-index sur le noyau, et correction de l'écrasement de `.knowledge/config.json` par `rgkb init`. Dépend de : 0.
3. Rebranchement d'ai-lab et d'ai-lab-audit (affectation de modèles par le module du noyau). Dépend de : 0.
4. Rebranchement de legacy-audit, vibecode-audit et brainstorm. Dépend de : 0.
5. Analyse des journaux, agrégat sur au moins 10 cycles réels. Dépend de : 0, plus 10 cycles journalisés.
6. Versioning / upgrade / doctor du noyau distribué. Dépend de : 0, 2.
7. Politique d'autonomie. Dépend de : 5.
8. Hooks Claude Code. Dépend de : 5, 7.
9. Profils. Dépend de : 5.
10. Scout. Dépend de : 9.
11. `/audit` unifié. Dépend de : 3, 4, 5, 9.
12. File et worktrees. Dépend de : 5, 7.
13. Packaging. Dépend de : 6.
