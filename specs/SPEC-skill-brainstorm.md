# SPEC — Skill `brainstorm` : co-réflexion challengeante et convergente

Statut : APPROUVEE

## Contexte

Besoin exprimé par l'utilisateur, mot pour mot : « Un skil de brainstorm qui me challenge et propose des choses aux quelles je n'ai pas pensé, le sujet peut etre large, mais il faut aussi "une fin" le but c'est pas de proposer à l'infini c'est vraiment de coreflechir à une idée ».

Trois exigences en sortent : (a) **challenger** l'utilisateur plutôt que valider son idée ; (b) **apporter des angles non anticipés** par lui ; (c) **converger et se clore** — condition de terminaison explicite, pas de production indéfinie.

État du dépôt `/home/naej/repos/claude-skills` :

- Cinq skills existants, aucun ne couvre le brainstorm ou l'idéation : `skills/software-factory/SKILL.md`, `skills/ship-pr/SKILL.md`, `skills/legacy-audit/SKILL.md`, `skills/ai-lab/SKILL.md`, `skills/ai-lab-audit/SKILL.md`.
- Recouvrement partiel mais non redondant avec deux mécanismes existants : le cadrage d'une question de recherche de `ai-lab` et la production de questions candidates `Q-*` de `ai-lab-audit`. Les deux supposent un projet de recherche IA existant ; ici le sujet est libre.
- Conventions des `SKILL.md` de premier niveau à répliquer : frontmatter YAML à cinq clés (`name`, `description`, `context: fork`, `user-invocable: true`, `argument-hint`) ; titre H1 `# <Nom> — <sous-titre>` ; paragraphe d'intention ; section de parsing de `$ARGUMENTS` ; section `## Règles impératives (toutes les phases)` ; phases numérotées `## Phase N — <titre>` ; dernière phase = rapport final ; français, voix impérative.
- Garde-fous récurrents directement pertinents : plafond dur d'itérations (`min(N, 3)` dans `ship-pr`), sortie anticipée à épuisement, registre cumulatif empêchant la résurrection d'un élément écarté, agents parallèles par lentilles (4 dans `legacy-audit`, 5 dans `ai-lab-audit`), gate humaine `AskUserQuestion` avec arrêt explicite en mode headless, plafond de livrable (`--max-specs`, `--max-questions`).
- `install_skills.sh` (ligne 20) et `install_skills.ps1` (ligne 29) énumèrent tous les sous-dossiers de `skills/` ; aucun nom de skill n'y est codé en dur. Un nouveau skill est installable sans les modifier.
- `README.md` porte l'inventaire : une sous-section `### \`<nom>\`` par skill sous `## Skills`.
- Aucun test, aucun linter, aucun `.editorconfig`. `install_skills.sh` est modifié et non commité, sans lien avec ce besoin.

## Périmètre

1. Créer `skills/brainstorm/SKILL.md`, skill de premier niveau dédié à la co-réflexion challengeante sur un sujet fourni par l'utilisateur.
2. Frontmatter YAML conforme aux conventions des skills de premier niveau, `name: brainstorm`.
3. Corps structuré en phases numérotées, avec section de règles impératives, sur le modèle des quatre skills de premier niveau existants.
4. Spécifier le mécanisme de **challenge** : contredire, tester et mettre sous tension l'idée soumise ; interdire la validation complaisante.
5. Spécifier le mécanisme d'**angles non anticipés** : production explicite de pistes absentes de l'énoncé de l'utilisateur, marquées comme telles.
6. Spécifier l'architecture d'exécution : **agents « lentilles » parallèles**, cinq lentilles fixes, sur le modèle des auditeurs de `legacy-audit`.
7. Spécifier la **condition de terminaison** : plafond dur de 3 tours (paramétrable `--rounds N`, borné à `min(N, 3)`), sortie anticipée observable, phase finale de convergence qui clôt la session.
8. Spécifier une **gate humaine `AskUserQuestion` à chaque tour** et l'arrêt explicite en erreur si aucune interaction n'est possible.
9. Spécifier une **phase de reconnaissance du répertoire courant** avec budget de lecture plafonné.
10. Spécifier le **livrable** : synthèse en conversation, puis gate finale proposant son écriture dans un fichier ; plafond dur de 5 pistes retenues ; suggestion (sans exécution) de `/factory-run` ou `/lab-run` quand la piste retenue est implémentable.
11. Spécifier la **reprise** : si un fichier de synthèse antérieur sur le même sujet existe, le relire pour ne pas reproposer une piste déjà écartée.
12. Ajouter la sous-section `### \`brainstorm\`` dans `## Skills` de `README.md`.

## Critères d'acceptation

- [ ] CA1 — Le fichier `skills/brainstorm/SKILL.md` existe.
- [ ] CA2 — Le frontmatter est délimité par une ligne `---` en ligne 1 et une seconde ligne `---` ; le bloc entre les deux parse comme un mapping YAML valide.
- [ ] CA3 — Le frontmatter contient `name: brainstorm`, valeur strictement identique au nom du dossier parent.
- [ ] CA4 — Le frontmatter contient une `description` non vide en français mentionnant explicitement les trois éléments du besoin : le brainstorm/idéation, le fait de challenger, la convergence/terminaison.
- [ ] CA5 — Le frontmatter contient `context: fork`, `user-invocable: true` et `argument-hint`, comme les quatre skills de premier niveau existants.
- [ ] CA6 — L'`argument-hint` mentionne le sujet et l'option `--rounds`.
- [ ] CA7 — Le corps commence par un titre H1 au format `# <Nom lisible> — <sous-titre>`, suivi d'un paragraphe d'intention.
- [ ] CA8 — Le fichier contient la section `## Règles impératives (toutes les phases)` (chaîne exacte).
- [ ] CA9 — Le fichier contient au moins quatre sections `## Phase N — <titre>`, numérotées consécutivement à partir de 1, sans trou.
- [ ] CA10 — Le fichier contient une section décrivant le parsing de `$ARGUMENTS`, couvrant au minimum : le sujet (argument principal), l'option `--rounds N`, et le comportement si le sujet est absent (demander le sujet à l'utilisateur avant toute chose).
- [ ] CA11 — Les règles impératives imposent explicitement de **contester** l'idée soumise et interdisent l'approbation complaisante ou par défaut (au moins une puce pour chacune des deux exigences).
- [ ] CA12 — Le skill impose que chaque piste proposée soit **marquée comme issue de l'énoncé ou hors énoncé**, et exige qu'au moins une piste hors énoncé soit produite à chaque tour.
- [ ] CA13 — Le skill énumère explicitement **cinq lentilles fixes** confiées à des sous-agents lancés en parallèle : hypothèses implicites, alternatives radicales, contre-exemples et cas limites, coût et faisabilité, effets de second ordre. Les cinq sont nommées et décrites en une ligne chacune.
- [ ] CA14 — Le skill précise que les cinq agents de lentille sont lancés **en parallèle, en contexte vierge**, et qu'ils ne voient pas les conclusions des autres avant la synthèse du tour.
- [ ] CA15 — Le skill définit un plafond dur de **3 tours**, paramétrable par `--rounds N` borné à `min(N, 3)`, et indique le comportement au plafond : passage forcé à la phase de convergence.
- [ ] CA16 — Le skill définit une **condition de sortie anticipée** formulée comme un test observable sur le résultat d'un tour (aucun angle hors énoncé nouveau survivant au tour), et non comme une appréciation subjective.
- [ ] CA17 — Le skill spécifie une gate `AskUserQuestion` **à la fin de chaque tour**, présentant à l'utilisateur les angles du tour et lui demandant lesquels creuser, écarter ou amender.
- [ ] CA18 — Le skill spécifie l'arrêt explicite en erreur si aucune interaction utilisateur n'est possible (exécution headless), avec un message indiquant que le skill est intrinsèquement dialogué.
- [ ] CA19 — Les règles impératives interdisent la relance d'une piste déjà écartée, via un **registre cumulatif** des pistes écartées et de leur raison, conservé d'un tour à l'autre.
- [ ] CA20 — Le skill contient une **phase de reconnaissance** du répertoire courant, avec un budget de lecture plafonné exprimé par un nombre entier explicite de fichiers, et la consigne de ne pas explorer au-delà.
- [ ] CA21 — La phase de reconnaissance prévoit le cas où le sujet n'a **aucun rapport avec le répertoire courant** : la reconnaissance est alors écourtée et signalée comme telle, sans bloquer la session.
- [ ] CA22 — Le skill spécifie la **reprise** : recherche d'un fichier de synthèse antérieur portant sur le même sujet ; s'il existe, relecture et chargement de son registre de pistes écartées dans le registre du tour 1.
- [ ] CA23 — La dernière phase est un **rapport final de convergence** qui clôt la session et énumère au minimum : l'idée après confrontation, les angles retenus, les angles écartés avec leur raison.
- [ ] CA24 — Le rapport final applique un **plafond dur de 5 pistes retenues**, énoncé par un entier explicite, avec la consigne de hiérarchiser et trancher si davantage ont survécu.
- [ ] CA25 — Le rapport final comporte une **gate `AskUserQuestion` proposant l'écriture de la synthèse dans un fichier** ; le chemin du fichier est spécifié de façon déterministe (nom dérivé du sujet, répertoire courant) ; en cas de refus, rien n'est écrit sur disque.
- [ ] CA26 — Le rapport final **suggère** `/factory-run` ou `/lab-run` quand une piste retenue est implémentable, avec la consigne explicite de ne jamais lancer cette commande à la place de l'utilisateur.
- [ ] CA27 — Le fichier est intégralement rédigé en français, en voix impérative dans le corps des phases ; les blocs de code éventuels ne contiennent que des exemples d'invocation, des gabarits de sortie ou du JSON de contrat, comme dans les skills existants.
- [ ] CA28 — `README.md` contient une nouvelle sous-section `### \`brainstorm\`` située entre la ligne `## Skills` et la ligne `## Ajouter un skill`, décrivant le skill, son invocation dans un bloc `text`, et mentionnant explicitement sa condition de terminaison.
- [ ] CA29 — Ni `install_skills.sh` ni `install_skills.ps1` ne sont modifiés par ce changement (hors modification non commitée préexistante de `install_skills.sh`, étrangère à cette spec).
- [ ] CA30 — `bash -n install_skills.sh` sort en code 0 (non-régression).
- [ ] CA31 — Le nombre de dossiers sous `skills/` passe de 5 à 6 et chacun contient un `SKILL.md`.
- [ ] CA32 — Aucun `skills/*/SKILL.md` existant n'est modifié.

## Hors-périmètre

- Toute modification de `install_skills.sh` et `install_skills.ps1`.
- Toute modification des skills existants `software-factory`, `ship-pr`, `legacy-audit`, `ai-lab`, `ai-lab-audit`.
- L'ajout d'un framework de test, d'un linter, d'un `.editorconfig` ou de fichiers `tests/*.bats` : le dépôt n'en a aucun et le besoin n'en demande pas.
- La génération de sous-agents `.claude/agents/*.md` dans un projet cible (mécanisme propre à `software-factory` et `ai-lab`).
- La production directe de `specs/SPEC-*.md` par le skill : le rapport final se limite à suggérer la commande.
- L'exécution du script d'installation : l'utilisateur le relance lui-même après le commit.
- Le commit : le Builder ne commite pas.

## Risques

- **Recouvrement fonctionnel avec `ai-lab`** : la phase de cadrage de `ai-lab` fait déjà du questionnement adversarial d'une idée. La `description` de `brainstorm` doit être assez distincte pour ne pas capter les invocations destinées à `/ai-lab`, `/ai-lab-audit` ou `/legacy-audit` — la sélection se fait sur la base des `description`.
- **Tension challenge / terminaison** : 3 tours est le compromis retenu, aligné sur la constante du dépôt. Trop bas, le challenge devient cosmétique ; trop haut, le skill reproduit le défaut dénoncé par le besoin.
- **Critères qualitatifs non auditables** : « challenger » et « angles non anticipés » sont qualitatifs par nature. CA11, CA12, CA16 et CA19 les rendent vérifiables en exigeant des sorties observables (marquage des pistes, registre, condition d'arrêt testable) plutôt que des déclarations d'intention.
- **Coût de la reconnaissance sur un sujet large** : le besoin autorise un sujet large tandis que la reconnaissance lit le répertoire courant. Sans le budget de CA20 et l'échappatoire de CA21, le skill peut déclencher une exploration coûteuse sans rapport avec le sujet.
- **Divergence README / skills** : omettre CA28 laisserait un skill installé mais absent de la seule documentation du dépôt.
- **Bruit dans le commit** : `install_skills.sh` est modifié et non commité ; un `git add -A` embarquerait ce changement étranger. Le Builder ne commite pas, la responsabilité reste à l'utilisateur.

## Décisions

- **Q1 — Nom du skill** : `brainstorm`. Dossier `skills/brainstorm/`, invocation `/brainstorm`. Littéral, colle au vocabulaire du besoin, risque de collision faible avec les autres `description`.
- **Q2 — Plafond d'itérations** : 3 tours, paramétrable `--rounds N` borné dur à `min(N, 3)`. Aligné sur la constante déjà partagée par `ship-pr`, `software-factory` et `ai-lab` ; l'utilisateur peut demander moins, jamais plus.
- **Q3 — Nature de la fin** : synthèse restituée en conversation, puis gate finale demandant à l'utilisateur s'il veut qu'elle soit écrite dans un fichier. Pas d'écriture systématique.
- **Q4 — Architecture d'exécution** : sous-agents « lentilles » parallèles, cinq lentilles fixes (hypothèses implicites, alternatives radicales, contre-exemples et cas limites, coût et faisabilité, effets de second ordre), sur le modèle des quatre auditeurs de `legacy-audit`. Sans couche de validation adversariale supplémentaire.
- **Q5 — Chaînage** : le rapport final suggère `/factory-run` ou `/lab-run` quand la piste retenue est implémentable, sans jamais lancer la commande. Modèle de `legacy-audit` Phase 7.
- **Q6 — Périmètre du sujet** : reconnaissance du répertoire courant, systématique, avec budget de lecture plafonné. Le skill lit le projet courant pour ancrer le brainstorm.
- **Q7 — Forme du challenge** : gate humaine à chaque tour. Le skill pose ses contre-arguments, l'utilisateur répond, le tour suivant part de sa réponse. C'est le mécanisme de co-réflexion demandé.
- **Q8 — Volume du livrable** : plafond dur de 5 pistes retenues, non paramétrable. Force la hiérarchisation, cohérent avec l'exigence de « fin ».
- **Q9 — Reprise** : si un fichier de synthèse antérieur sur le même sujet existe dans le répertoire courant, le skill le relit et charge son registre de pistes écartées, pour ne pas les reproposer. Idempotence sur le modèle de `legacy-audit` et `ai-lab-audit`.
