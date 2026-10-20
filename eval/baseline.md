# Résultats de l'évaluation

Dernière mise à jour : 20 octobre 2026.

## Protocole

- 50 questions en anglais (46 avec réponse attendue, 4 refus attendus) et 12 questions multilingues (fr, it, de).
- Chaque question est posée 3 fois à chaque système (138 essais par système pour les questions à réponse).
- hit@5 : le passage attendu figure parmi les 5 retrouvés. Bon passage utilisé : il a été donné au générateur.
- Fidélité : toutes les affirmations de la réponse sont explicitement dans les passages donnés. Jugée par Claude Haiku, la même famille de modèle que le générateur.
- La ligne « Sources » est retirée de la réponse avant le juge.

## Résultats finaux (3 essais, 46 questions à réponse)

| Mesure | RAG naïf | Agent, avant corrections (1 essai) | Agent, après corrections |
|---|---|---|---|
| hit@5 | 96 % | 89 % | 97 % |
| Bon passage utilisé | 96 % | 83 % | 95 % |
| Réponse donnée | 99 % | 85 % | 96 % |
| Fidélité | 84 % | 77 % | 98 % |
| Langue correcte | 81 % | 100 % | 100 % |
| Refus attendus | 100 % | 100 % | 100 % |
| Reformulations (moyenne) | - | 0,19 | 0,12 |

## Multilingue (hit@5 / langue correcte, 4 questions par langue, 3 essais)

| Langue | RAG naïf | Agent |
|---|---|---|
| fr | 100 % / 100 % | 100 % / 100 % |
| it | 83 % / 100 % | 100 % / 100 % |
| de | 100 % / 75 % | 100 % / 92 % |

## Corrections apportées à l'agent

1. Le juge de pertinence reçoit le passage entier (il était tronqué à 700 caractères).
2. Le routeur n'écarte plus les questions d'infrastructure formulées sans nommer de service.
3. Le générateur doit s'en tenir aux extraits, sans deviner de causes ni ajouter de conseils.

## Corrections de la mesure

- La ligne « Sources » était envoyée au juge de fidélité, ce qui faussait le score de l'agent (46 % mesuré au premier passage, contre 77 % après correction).
- Une question sur Lambda et S3 attendait un seul passage alors que deux répondaient : l'étiquette a été corrigée pour les deux systèmes.

## Limites

- Les corrections ont été choisies en regardant les échecs de ce même jeu de questions : risque de sur-ajustement.
- Le prompt de l'agent est plus strict que celui du RAG naïf : le gain de fidélité ne peut pas être attribué au seul graphe.
- 46 questions répétées 3 fois ne valent pas 138 questions indépendantes.
- 46 questions sur 50 viennent de passages du corpus : hit@5 est optimiste.
- Peu de questions demandent plusieurs étapes : la boucle de reformulation est presque inutilisée.
- Le juge de fidélité est un LLM qui signale parfois des phrases triviales.
- Échec persistant de l'agent : « How do I enable S3 event notifications? » (3 essais sur 3).