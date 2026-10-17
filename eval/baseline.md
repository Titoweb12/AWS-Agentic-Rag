# Mesure de départ (avant toute correction)

- Date : 17 octobre 2026
- 1 essai par question (aucune répétition)
- 50 questions en anglais (46 avec réponse, 4 refus attendus) et 12 questions multilingues
- Juge de fidélité : Claude Haiku, la même famille de modèle que le générateur
- Fidélité = toutes les affirmations de la réponse sont explicitement dans les passages donnés

## Questions à réponse (46)

| Mesure | RAG naïf | Agent |
|---|---|---|
| hit@5 | 93 % | 87 % |
| Bon passage utilisé | 93 % | 78 % |
| Réponse donnée | 100 % | 80 % |
| Fidélité | 83 % | 46 % |
| Langue correcte | 80 % | 100 % |
| Refus attendus (4) | 100 % | 100 % |
| Reformulations (moyenne) | - | 0,20 |

## Multilingue (hit@5 / langue correcte, 4 questions par langue)

| Langue | RAG naïf | Agent |
|---|---|---|
| fr | 100 % / 100 % | 100 % / 100 % |
| it | 75 % / 100 % | 75 % / 100 % |
| de | 100 % / 75 % | 100 % / 100 % |

## Limites

- Un seul essai : les écarts de quelques points ne sont pas significatifs.
- 46 questions sur 50 viennent de passages du corpus, donc hit@5 est optimiste.
- Quand le routeur refuse une question, aucune recherche n'a lieu et hit@5 vaut non.