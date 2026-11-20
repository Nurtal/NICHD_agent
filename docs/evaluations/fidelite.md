# Fidélité comportementale du moteur

*Produit par `experiments/fidelity/run.py`. Chaque sonde pilote le moteur avec des énoncés étiquetés (classifieur manuel, sans LLM) sur 100 seeds. Les cibles viennent de la [confrontation à la littérature](../research/confrontation-modele-litterature.md) ; le plan est dans [docs/plans/adaptations-litterature.md](../plans/adaptations-litterature.md).*

| Piste | Mesure | Valeur | Cible | Atteinte |
|---|---|---|---|---|
| A1 | unités vraies à l'invitation suivante ; acquiescement à une suggestion fausse (accepté / rejeté) | 2.00 / 2.00 unités ; 41% / 29% (n = 49 / 49) | accepté > rejeté en unités ; rejeté > accepté en acquiescement | **non** |
| A2 | invention à la 1ʳᵉ, 2ᵉ, 3ᵉ, 4ᵉ question hors scénario identique ; réponses qui changent | 51% / 43% / 43% / 49% ; 52% de changements | invention croissante ; > 25 % de réponses qui changent | **non** |
| A3 | enfant réticent (s02) : tour moyen du dévoilement, 2 soutiens puis invitations / suggestives vraies | 5.0 / 2.0 | la pression ne doit pas être le chemin le plus rapide (invitations ≤ suggestives) | **non** |
| A6 | acquiescement à une suggestion fausse après 0 / 2 énoncés de soutien | 43% / 43% | baisse avec le soutien | **non** |
| A7 | invention à une question hors scénario après 0 / 3 règles énoncées (sans entraînement) | 51% / 36% | effet faible d'une règle seulement énoncée ; effet net après entraînement (lot 2) | — |
| A9 | s08, 3 récits puis 3 oui/non vrais : omission / déni / feinte d'ignorance / couverture / minimisation | 5% / 1% / 0% / 44% / 50% (n = 199) | omissions > dénis (Talwar et al., 2004) | oui |
| A10 | s02 : signes d'émotion au 4ᵉ récit, sans / avec 3 énoncés de soutien | 0.13 / 0.03 | plus de signes avec le soutien | **non** |
| A11 | s02 : variation d'activation au tour qui précède le dévoilement | +0.025 | hausse avant le dévoilement | oui |

**Pas encore mesurables** (champs ou mécanismes à venir) :

- A4 : « Raconte-moi la fin » ne livre que le segment final (lot 2 (indice de segment)).
- A5 : « oui » sans détail aux « Est-ce que tu te souviens… ? », décroissant avec l'âge (lot 2).
- A8 : plus de faits protégés révélés après la promesse de dire la vérité (lots 2 et 3).
- A12 : un silence de 10 s fait compléter la réponse (lot 5).
