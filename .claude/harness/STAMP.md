# Le tampon `.claude/harness.json`

Fichier **versionné** de chaque projet équipé (aucune donnée propre à une machine : ni chemin absolu, ni clé `rg_path`, `harness.py stamp validate` les refuse). JSON strict, indentation 2, écriture atomique. Schéma `schema_version: 1`.

| Clé | Contenu |
| --- | --- |
| `schema_version` | `1`. Une autre valeur est refusée. |
| `autonomy` | `gate` ou `auto`. Posée à `auto` si absente ; une valeur existante n'est **jamais** modifiée par l'installation ni par l'upgrade. |
| `profiles[]` | `{name, added, by}`, en ajout seulement. |
| `skills` | Un objet par skill qui installe : `software-factory` et/ou `code-index` (`ai-lab` est le profil `research` de `software-factory`). |
| `migrations[]` | `{id, at, sources: [{path, sha256}]}`, en ajout seulement (registres de run déjà publiés). |
| `inferred_from` | Facultatif : génération estimée du projet sans tampon (`pre-core`, `core-<v>`) créé par le premier upgrade. |

## `skills.<skill>`

- `repo_commit`, `repo_describe`, `repo_dirty` : version du dépôt claude-skills qui a produit l'installation (`harness.py version`).
- `core_version` (software-factory) ou `tool_version` (code-index, `TOOL_VERSION` de rgkb).
- `installed_at` (fixé à la première écriture), `updated_at` (mis à jour par un apply qui change quelque chose) : ISO 8601, heure locale avec décalage, à la seconde.
- `options` : software-factory `stacks`, `interpreter`, `ci`, `code_index_offered` ; code-index `no_wire`, `hooks`, `interpreter`.
- `params` (software-factory) : les paramètres `judgement` des profils, rédigés une fois.
- `contributes` (code-index) : les outils que ce skill ajoute aux agents et aux scripts CI.
- `files` : `{"<chemin relatif>": {kind: generated|merged|copied|legacy, blocks: {"<bloc>": "<sha256>"}}}`.

## Règles

- Un tampon de la Phase 2 (`profiles` seul) passe au schéma 1 : toutes ses clés sont conservées, dans leur ordre, les nouvelles viennent après.
- Un apply sans changement ne touche pas le tampon (identique octet pour octet) ; un arrêt avant la fin le laisse inchangé, il est écrit en dernier.
- Un fichier `legacy` est un fichier généré conservé tel quel à la demande de l'utilisateur (gate `upgrade.convert`) : l'upgrade ne le modifie pas, le doctor le signale.
