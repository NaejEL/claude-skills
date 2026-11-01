Piloter un cycle complet de l'usine logicielle de ce dépôt sur l'entrée `$ARGUMENTS`. Toi, session principale, tu es l'orchestrateur : tu ne rédiges ni code ni spec toi-même, tu délègues aux sous-agents `factory-planner`, `factory-builder` et `factory-verifier`, et tu tiens la gate humaine.

## Noyau

Les règles déterministes du cycle sont portées par la copie du noyau sous `.claude/harness/` : ne jamais les réimplémenter à la main. Ci-dessous, `H` désigne `{{interpreter}} .claude/harness/harness.py`. Chaque commande rend un objet JSON ; son champ `action` dicte la suite : ne jamais sauter un appel ni décider à la place du noyau.

**Chaque sous-agent lancé est consigné** par `H factory-run record --run <run> --agent <nom> --duration-ms <ms> --tokens <n>`. Sans durée : `H begin --run <run> --slot <nom>` juste avant l'agent ; une mesure manquante est journalisée `null`, jamais bloquante ; connue après l'appel, elle complète l'entrée par `H journal amend`. La sortie du Verifier est écrite telle quelle avec l'outil Write dans `.harness/runs/verifier-<n>.md`, puis passée par `--output` (jamais par stdin ni via le shell). `--dead` si l'agent est mort.

**Gates** : `H gate decide --run <run> --id <id>`, puis AskUserQuestion, puis `H gate answer --run <run> --id <id> --answer-file .harness/runs/gate-answer.txt` (réponse écrite par Write ; `reask` rendu : reposer la question). Sans interaction possible (headless), `H gate answer --run <run> --id <id> --headless`.

## 1. Qualifier l'entrée

Écrire `$ARGUMENTS` tel quel avec l'outil Write dans `.harness/runs/factory-run-arguments.txt`, puis `H factory-run start --arguments-file .harness/runs/factory-run-arguments.txt`. La commande ouvre le journal et rend `mode` : `build` (spec existante sous `specs/` avec `Statut : APPROUVEE`) → étape 3 ; `plan` → traiter `need` comme le besoin → étape 2. Elle retire l'option `--models "role=modele;…"` et rend `models` : passer à chaque sous-agent le paramètre `model` de l'outil Agent quand `pass_param` est vrai.

## 2. Phase Plan — gate humaine obligatoire

1. Lancer `factory-planner` avec le besoin intégral. Le consigner.
2. Poser les *Questions ouvertes* du brouillon (gate `factory-run.questions`).
3. Écrire `specs/SPEC-<slug>.md` avec en tête `Statut : PROPOSEE`.
4. Demander l'approbation explicite (gate `factory-run.approval`) ; itérer tant qu'elle manque ; approuvée, passer le statut à `APPROUVEE`.
5. Ne jamais construire sans spec approuvée.

## 3. Phase Build

Lancer `factory-builder` dans un contexte frais avec le chemin de la spec approuvée.

## 4. Phase Verify — boucle de correction, 3 itérations maximum

Lancer un `factory-verifier` neuf avec le chemin de la spec, consigner sa sortie, puis selon `action` : `success` (sortir) ; `fix` (relancer le Builder avec les issues complètes, puis un nouveau Verifier) ; `relaunch` (une fois, sans consommer d'itération) ; `fail` (échouer explicitement avec `reason` et les issues restantes). Ne jamais approuver par épuisement.

**Un Verifier muet n'est pas un Verifier satisfait.**

## 5. Rapport final

Spec et statut ; fichiers touchés (`git status --porcelain`) ; tests exécutés et exit codes ; verdict ; itérations ; chemin du journal ; prochaine action : relire le diff puis commiter soi-même. **Ne jamais commiter à sa place.**
