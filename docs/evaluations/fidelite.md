# Fidélité comportementale du moteur

*Produit par `experiments/fidelity/run.py`. Chaque sonde pilote le moteur avec des énoncés étiquetés (classifieur manuel, sans LLM) sur 200 seeds. Les cibles viennent de la [confrontation à la littérature](../research/confrontation-modele-litterature.md) ; le plan est dans [docs/plans/adaptations-litterature.md](../plans/adaptations-litterature.md).*

| Piste | Mesure | Valeur | Cible | Atteinte |
|---|---|---|---|---|
| A1 | unités vraies à l'invitation suivante (accepté / rejeté) ; réponse donnée au rejet | 1.73 / 1.54 unités ; 63% répondent au rejet (n = 106 / 106) | accepté > rejeté ; une majorité répond au rejet (76–81 %, souvent par complaisance) | oui |
| A2 | invention à la 1ʳᵉ, 2ᵉ, 3ᵉ, 4ᵉ question hors scénario identique ; réponses qui changent | 47% / 56% / 59% / 71% ; 54% de changements | invention croissante ; > 25 % de réponses qui changent | oui |
| A3 | enfant réticent (s02) : tour moyen du dévoilement, 2 soutiens puis invitations / suggestives vraies | 5.0 / 9.0 | la pression ne doit pas être le chemin le plus rapide (invitations ≤ suggestives) | oui |
| A6 | acquiescement à une suggestion fausse après 0 / 2 énoncés de soutien | 40% / 34% | baisse avec le soutien | oui |
| A4 | « Raconte-moi la fin » : réponses qui ne livrent que le segment final | 100% | 100 % | oui |
| A5 | « oui » sans détail à « Tu te souviens qui… ? », à 5 / 8 / 11 ans | 46% / 29% / 12% | décroissant avec l'âge ; de l'ordre de 15 à 45 % chez les plus jeunes | oui |
| A7 | invention à une question hors scénario (8 ans) : sans règle / 3 règles énoncées / 3 entraînées | 28% / 24% / 21% | énoncée : effet faible ; entraînée : effet net | oui |
| A15 | « Pourquoi… ? » codé fermé : réponses oui/non | 0% | 0 % | oui |
| A9 | s08, 3 récits puis 3 oui/non vrais : omission / déni / feinte d'ignorance / couverture / minimisation | 7% / 4% / 0% / 41% / 48% (n = 417) | omissions > dénis (Talwar et al., 2004) | oui |
| A8 | s08 : faits protégés révélés après 4 récits, sans / avec promesse (sur 6) | 1.83 / 2.73 | plus de faits révélés avec la promesse | oui |
| A9 | s08 : la vérité échappe à la question de suite sur un mensonge, à 5 / 8 / 11 ans | 34% / 18% / 10% | décroissant avec l'âge | oui |
| A12 | s01 : unités vraies ajoutées par un tour d'attente après deux récits (même seed) | +0.64 ; 64% des enfants complètent | > 0, souvent | oui |
| A10 | s02 : signes d'émotion au 4ᵉ récit, sans / avec 3 énoncés de soutien | 0.17 / 0.20 | plus de signes avec le soutien | oui |
| A11 | s02 : variation d'activation au tour qui précède le dévoilement | +0.090 | hausse avant le dévoilement | oui |
