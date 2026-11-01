# SPEC — Somme d'une liste vide

Statut : APPROUVEE

## Contexte

`src/sum.js` additionne une liste de nombres.

## Perimetre

Ajouter un test `node --test` qui verifie que `sum([])` vaut `0` et que `sum([1, 2, 3])` vaut `6`.

## Criteres d'acceptation

- [ ] `npm test` sort en 0 et execute au moins deux assertions sur `sum`.

## Hors-perimetre

Toute autre fonction.
