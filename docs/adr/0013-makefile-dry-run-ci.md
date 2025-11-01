# 0013 – Garder le Makefile exécutable via CI

## Contexte

Suite à la décommission des anciens workflows GitHub Actions (ADR 0012), la
validation des recettes `make lint` et `make doctor` reposait uniquement sur des
exécutions locales. Lors des revues récentes, une indentation accidentelle en
espaces a cassé ces cibles : `make` refusait de parser le fichier et bloquait la
chaîne de validation.

## Décision

Nous ajoutons un workflow GitHub Actions minimaliste « Makefile validation ».
Ce workflow exécute `make --dry-run lint` puis `make --dry-run doctor`. Les
commandes `--dry-run` ne lancent aucun lint réel mais garantissent que `make`
parse correctement les recettes et détecte toute indentation invalide.

## Conséquences

- ✅ Réduction du risque de régression : chaque PR et push vers `main` doit avoir
  un Makefile syntaxiquement valide.
- ✅ Le workflow reste léger : aucune dépendance supplémentaire n'est installée,
  l'exécution est rapide.
- ⚠️ Les linters sous-jacents (`yamllint`, `ansible-lint`, etc.) ne tournent pas
  dans cette étape ; leur exécution reste à la charge des contributeurs ou
  d'autres pipelines spécialisés.
- 🔁 Les cibles `make lint` et `make doctor` gardent leur logique actuelle. En
  cas d'évolution future, adapter ce workflow pour viser de nouvelles recettes.
