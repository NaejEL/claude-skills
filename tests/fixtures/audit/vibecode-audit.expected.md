# Audit vibecode — poc-genere

Généré par /vibecode-audit le 2026-10-17. Axes : sécurité, maintenabilité, évolutivité. Audit complet.

> **Ordre par défaut.** Aucune interaction n'était possible : l'ordre d'attaque et le sort des motifs mineurs sont les défauts du skill, sans arbitrage de l'utilisateur.

> **Famille non auditée : injection.** Son auditeur n'a rendu aucun bloc JSON exploitable après une relance : elle figure parmi les surfaces non auditables.

> **Portée et limites de cet audit.** Diagnostic statique en lecture seule, produit par un modèle de
> langage. Il ne remplace pas une revue de sécurité applicative : aucun accès à l'environnement
> d'exécution, aux identifiants, à la configuration réelle des services tiers ni au trafic ; aucun
> test d'intrusion. L'auditeur partage une partie des angles morts du modèle qui a produit le code —
> l'absence de finding sur une famille ne prouve rien. Les surfaces listées ci-dessous n'ont pas pu
> être auditées du tout.
>
> **Validation.** 5 motifs sur 6 ont passé la validation adversariale. Les autres sont
> marqués `non validé` : ils n'ont pas été réfutés, ils n'ont pas été vérifiés.
>
> **Les difficultés sont des ordres de grandeur, pas des estimations.** Elles varient d'un audit à
> l'autre sur le même code. La gravité, elle, est stable : c'est sur elle que repose l'ordre.

## Surfaces non auditables
| Surface | Pourquoi | Ce qu'il faudrait pour la couvrir |
|---|---|---|
| famille injection | auditeur sans bloc JSON exploitable après une relance (sévérité major) | relancer l'audit de cette famille |
| dépendances installées | aucun outil d'audit de vulnérabilités disponible | un audit des dépendances par le gestionnaire de paquets |

## Par où attaquer
Ordre retenu : gravité d'abord, tous axes confondus, puis pondération sécurité > maintenabilité > évolutivité. 6 motifs, 20 occurrences au total.

| # | ID | Motif | Axe | Sév. | Occ. | Diff. | Risque rég. | Validé | Dépend de | Statut |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | VIB-01 | Les points d'entrée de modification ne vérifient pas l'appartenance de la ressource | sécurité | critical | 13 | M | élevé | oui | — | A_FAIRE |
| 2 | VIB-02 | Le schéma de données est modifié sans historique de migration | évolutivité | critical | 1 | L | élevé | non validé | — | A_FAIRE |
| 3 | VIB-03 | Le montant de la commande est fourni par le client | sécurité | major | 2 | S | moyen | oui | — | A_FAIRE |
| 4 | VIB-04 | Les règles d'âge divergent entre client et serveur | maintenabilité | major | 2 | S | moyen | oui | — | A_FAIRE |
| 5 | VIB-05 | Le formatage des dates est réécrit localement | maintenabilité | minor | 1 | XS | moyen | oui | — | A_FAIRE |
| 6 | VIB-06 | Des commentaires paraphrasent le code | maintenabilité | minor | 1 | XS | faible | oui | — | A_FAIRE |

Gains rapides (XS/S de sévérité major ou critical) : VIB-03, VIB-04. Signalés, sans remonter dans l'ordre.

Critiques remontés depuis un autre axe que la sécurité : VIB-02 (évolutivité). Remontée délibérée — la gravité prime sur l'axe.

## Motifs détaillés
### VIB-01 — Les points d'entrée de modification ne vérifient pas l'appartenance de la ressource
- **Axe / sévérité / difficulté** : sécurité / critical / M — **occurrences** : 13 (échantillon ci-dessous)
- **Risque de régression** : élevé — aucun test sur ces points d'entrée, 14 appelants *(information, n'entre pas dans l'ordre)*
- **Impact** : un utilisateur modifie la ressource d'autrui en changeant l'identifiant
- **Occurrences** : `api/orders.js:42`, `api/users.js:88`, `api/items.js:17`, `api/carts.js:9`, … (+9)
- **Correction du motif** : vérifier l'appartenance côté serveur dans une couche commune
- **Statut** : A_FAIRE

### VIB-02 — Le schéma de données est modifié sans historique de migration
- **Axe / sévérité / difficulté** : évolutivité / critical / L — **occurrences** : 1
- **Risque de régression** : élevé — toute la persistance en dépend *(information, n'entre pas dans l'ordre)*
- **Impact** : impossible de rejouer la base ailleurs
- **Occurrences** : `db/schema.sql:1`
- **Correction du motif** : introduire des migrations versionnées
- **Statut** : A_FAIRE

### VIB-03 — Le montant de la commande est fourni par le client
- **Axe / sévérité / difficulté** : sécurité / major / S — **occurrences** : 2
- **Risque de régression** : moyen — deux appelants, un test de paiement *(information, n'entre pas dans l'ordre)*
- **Impact** : paiement d'un montant arbitraire
- **Occurrences** : `api/checkout.js:21`, `api/refund.js:8`
- **Correction du motif** : recalculer les montants côté serveur
- **Statut** : A_FAIRE

### VIB-04 — Les règles d'âge divergent entre client et serveur
- **Axe / sévérité / difficulté** : maintenabilité / major / S — **occurrences** : 2
- **Risque de régression** : moyen — trois fichiers sans tests *(information, n'entre pas dans l'ordre)*
- **Impact** : des saisies acceptées côté client sont refusées côté serveur
- **Occurrences** : `web/form.js:30`, `api/users.js:12`
- **Correction du motif** : une seule source des règles
- **Statut** : A_FAIRE

### VIB-05 — Le formatage des dates est réécrit localement
- **Axe / sévérité / difficulté** : maintenabilité / minor / XS — **occurrences** : 1
- **Risque de régression** : moyen — trois fichiers sans tests *(information, n'entre pas dans l'ordre)*
- **Impact** : des saisies acceptées côté client sont refusées côté serveur
- **Occurrences** : `web/date.js:4`
- **Correction du motif** : une seule source des règles
- **Statut** : A_FAIRE

### VIB-06 — Des commentaires paraphrasent le code
- **Axe / sévérité / difficulté** : maintenabilité / minor / XS — **occurrences** : 1
- **Risque de régression** : faible — commentaires seulement *(information, n'entre pas dans l'ordre)*
- **Impact** : bruit à la lecture
- **Occurrences** : `api/orders.js:3`
- **Correction du motif** : dire pourquoi, pas quoi
- **Statut** : A_FAIRE

## Motifs non détaillés dans ce cycle
| ID | Motif | Axe | Sévérité | Occ. | Raison (mineur / au-delà du plafond) |
|---|---|---|---|---|---|

## Motifs rejetés à la validation
| ID | Motif | Raison |
|---|---|---|

## Suite
Ce rapport diagnostique ; il ne remédie pas. Pour en tirer un plan exécutable :
`/legacy-audit "./poc-genere"` — qui produit roadmap et specs, et couvre en complément la dette
d'accumulation que le présent audit ne cherche pas.
