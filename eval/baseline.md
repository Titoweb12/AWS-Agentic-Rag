# Résultats de l'évaluation

Dernière mise à jour : 20 octobre 2026.

## Protocole

- 50 questions en anglais (46 avec réponse attendue, 4 refus attendus) et 12 questions multilingues (fr, it, de).
- Chaque question est posée 3 fois à chaque système (138 essais par système pour les questions à réponse).
- hit@5 : le passage attendu figure parmi les 5 retrouvés. Bon passage utilisé : il a été donné au générateur.
- Fidélité : toutes les affirmations de la réponse sont explicitement dans les passages donnés. Jugée par Claude Haiku, la même famille de modèle que le générateur.
- La ligne « Sources » est retirée de la réponse avant le juge.


## Résultats finaux (3 essais, 46 questions à réponse)

| Mesure | RAG naïf (prompt d'origine) | RAG naïf (prompt strict) | Agent |
|---|---|---|---|
| hit@5 | 96 % | 95 % | 97 % |
| Bon passage utilisé | 96 % | 95 % | 95 % |
| Réponse donnée | 99 % | 99 % | 96 % |
| Fidélité | 84 % | 96 % | 98 % |
| Langue correcte | 81 % | 100 % | 100 % |
| Refus attendus | 100 % | 100 % | 100 % |
| Reformulations (moyenne) | - | - | 0,12 |
| Appels au modèle par question | 2 | 2 | 4 minimum |

## Multilingue (hit@5 / langue correcte, 4 questions par langue, 3 essais)

| Langue | RAG naïf (d'origine) | RAG naïf (prompt strict) | Agent |
|---|---|---|---|
| fr | 100 % / 100 % | 100 % / 100 % | 100 % / 100 % |
| it | 83 % / 100 % | 75 % / 100 % | 100 % / 100 % |
| de | 100 % / 75 % | 100 % / 100 % | 100 % / 92 % |
## Corrections apportées à l'agent

1. Le juge de pertinence reçoit le passage entier (il était tronqué à 700 caractères).
2. Le routeur n'écarte plus les questions d'infrastructure formulées sans nommer de service.
3. Le générateur doit s'en tenir aux extraits, sans deviner de causes ni ajouter de conseils.

## Corrections de la mesure

- La ligne « Sources » était envoyée au juge de fidélité, ce qui faussait le score de l'agent (46 % mesuré au premier passage, contre 77 % après correction).
- Une question sur Lambda et S3 attendait un seul passage alors que deux répondaient : l'étiquette a été corrigée pour les deux systèmes.

## Jeu inédit (18 questions, figé avant la mesure, 3 essais)

16 questions à réponse (13 simples, 3 qui demandent deux services) et 2 refus attendus.

| Mesure | RAG naïf (d'origine) | RAG naïf (strict) | Agent |
|---|---|---|---|
| hit@5 | 75 % | 77 % | 73 % |
| Bon passage utilisé | 75 % | 77 % | 71 % |
| Réponse donnée | 98 % | 100 % | 85 % |
| Fidélité | 81 % | 96 % | 98 % |
| Langue correcte | 81 % | 100 % | 100 % |
| Refus attendus (2 questions) | 67 % | 50 % | 100 % |

Séparation questions simples et questions à deux services :

| Système | Simples : passage utilisé | Simples : réponse donnée | Simples : fidélité | Deux services : réponse donnée | Deux services : fidélité |
|---|---|---|---|---|---|
| RAG naïf (d'origine) | 92 % | 97 % | 84 % | 100 % | 67 % |
| RAG naïf (strict) | 95 % | 100 % | 95 % | 100 % | 100 % |
| Agent | 87 % | 100 % | 97 % | 22 % | 100 % |

- Le gain de fidélité et de langue dû au prompt strict se reproduit sur des questions inédites.
- Aucun avantage de l'agent sur la recherche : sur les questions simples il est un peu en dessous (environ une question sur 13).
- Aucun système ne retrouve les deux passages d'une question à deux services : une seule recherche ne couvre pas deux sujets. Le RAG naïf strict répond partiellement en signalant ce qui manque, l'agent refuse dans 7 essais sur 9.
- Refus attendus : le RAG naïf strict signale que Google Cloud n'est pas couvert puis ajoute des informations sur S3, ce que le juge compte comme une réponse. Sur 2 questions, ce n'est pas un résultat significatif.


## Limites

- Les corrections ont été choisies en regardant les échecs de ce même jeu de questions : risque de sur-ajustement.
- Contrôle effectué : le RAG naïf avec le même prompt strict que l'agent atteint 96 % de fidélité et 100 % de langue correcte. L'essentiel du gain de l'agent vient donc du prompt, pas du graphe. L'agent garde un avantage marginal (cas Lambda et S3, italien) au prix d'au moins deux fois plus d'appels au modèle.
- 46 questions répétées 3 fois ne valent pas 138 questions indépendantes.
- 46 questions sur 50 viennent de passages du corpus : hit@5 est optimiste.
- Peu de questions demandent plusieurs étapes : la boucle de reformulation est presque inutilisée.
- Le juge de fidélité est un LLM qui signale parfois des phrases triviales.
- Échec persistant de l'agent : « How do I enable S3 event notifications? » (3 essais sur 3).