---
name: factory-run
description: Lance un cycle de l'usine logicielle (Planner → gate humaine sur la spec → Builder → Verifier avec boucle de correction) sur un besoin ou une spec approuvée.
disable-model-invocation: true
argument-hint: "<besoin | chemin d'une spec approuvée>"
---

Piloter un cycle complet de l'usine logicielle du dépôt `claude-skills` sur l'entrée `$ARGUMENTS`. Toi, session principale, tu es l'orchestrateur : tu ne rédiges ni code ni spec toi-même, tu délègues aux sous-agents `factory-planner`, `factory-builder` et `factory-verifier`, et tu tiens la gate humaine.

Rappel du contexte du dépôt, à transmettre tel quel aux sous-agents s'ils en ont besoin : dépôt de skills Claude Code, un skill par dossier `skills/<nom>/SKILL.md` (Markdown français, frontmatter YAML), scripts d'installation jumeaux `install_skills.sh` (Bash, `set -euo pipefail`) et `install_skills.ps1` (PowerShell, `$ErrorActionPreference = 'Stop'`), inventaire dans `README.md`. Aucune compilation. Portes de vérification : `bash -n` sur les scripts Bash, `bats tests/` si des tests `*.bats` existent, validité du frontmatter des `SKILL.md` touchés.

## 1. Qualifier l'entrée

Si `$ARGUMENTS` est le chemin d'un fichier existant sous `specs/` **et** que ce fichier contient une ligne de statut `Statut : APPROUVEE`, considérer la spec comme approuvée et sauter directement à l'étape 3.

Sinon, traiter `$ARGUMENTS` comme un besoin exprimé en langage naturel. Si `$ARGUMENTS` est vide, demander le besoin à l'utilisateur avant toute chose.

## 2. Phase Plan — gate humaine obligatoire

1. Lancer le sous-agent `factory-planner` avec le besoin intégral en entrée. Ne pas reformuler le besoin à sa place.
2. À son retour, lire la section *Questions ouvertes* du brouillon. Poser ces questions à l'utilisateur avec `AskUserQuestion` (une question par point, avec des options concrètes tirées du brouillon). S'il n'y a aucune question ouverte, passer directement au point 3.
3. Intégrer les réponses au brouillon, puis écrire `specs/SPEC-<slug-du-besoin>.md` (créer `specs/` si besoin ; slug en minuscules, mots séparés par des tirets, sans accent). Le fichier commence par :

   ```markdown
   # SPEC — <titre>

   Statut : PROPOSEE
   ```

   suivi des sections *Contexte*, *Périmètre*, *Critères d'acceptation*, *Hors-périmètre*, *Risques*, *Décisions* (les réponses de l'utilisateur, question par question).
4. Présenter la spec à l'utilisateur et demander une **approbation explicite**. Tant qu'il n'approuve pas, itérer : intégrer ses remarques, réécrire la spec, redemander. En cas d'approbation, remplacer `Statut : PROPOSEE` par `Statut : APPROUVEE`.
5. **Si aucune interaction utilisateur n'est possible (exécution headless, `claude -p`), s'arrêter immédiatement en erreur explicite** : « Cycle headless impossible sur un besoin : fournir le chemin d'une spec déjà approuvée (`Statut : APPROUVEE`). » Ne jamais construire sans spec approuvée, sous aucun prétexte.

## 3. Phase Build

Lancer le sous-agent `factory-builder` dans un **contexte frais**, en lui passant le chemin de la spec approuvée et la consigne de s'y tenir strictement, de couvrir chaque critère d'acceptation, de passer les portes de vérification du dépôt avant de rendre la main, et de ne pas commiter.

## 4. Phase Verify — boucle de correction, 3 itérations maximum

Initialiser un compteur d'itérations à 1, puis :

1. Lancer un sous-agent `factory-verifier` **neuf, en contexte vierge** (jamais celui du Builder), avec le chemin de la spec approuvée. Récupérer l'unique bloc JSON terminal de sa réponse.
2. Si `verdict` vaut `APPROVED` **et** `tests_passed` vaut `true` : sortir de la boucle, le cycle est un succès.
3. Sinon, si le compteur est strictement inférieur à 3 : relancer `factory-builder` (contexte frais) avec le chemin de la spec **et la liste complète des `issues`** du Verifier — pour chacune : `file`, `severity`, `description` — avec la consigne de corriger chaque issue sans régresser sur les critères déjà satisfaits. Incrémenter le compteur, puis reprendre au point 1 avec un **nouveau** Verifier.
4. Si le compteur atteint 3 et que le verdict n'est toujours pas `APPROVED` : **échouer explicitement**. Publier la liste complète des issues restantes, avec leur sévérité et leur fichier, et indiquer que la spec ou l'implémentation demande un arbitrage humain. **Ne jamais approuver par épuisement**, ne jamais reformuler un `CHANGES_REQUESTED` en succès partiel.

## 5. Rapport final

Conclure par un rapport structuré :

- **Spec** : chemin et statut.
- **Fichiers touchés** : sortie de `git status --porcelain`, commentée en une ligne par fichier.
- **Tests** : commandes exécutées par le Verifier et leur exit code.
- **Verdict** : `APPROVED` ou `CHANGES_REQUESTED`, avec les issues restantes le cas échéant.
- **Itérations** : nombre de passages dans la boucle Verify.
- **Prochaine action** : inviter l'utilisateur à relire le diff (`git diff`) puis à commiter lui-même. **Ne jamais commiter à sa place.**
