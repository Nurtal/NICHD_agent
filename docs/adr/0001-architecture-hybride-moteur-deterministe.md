# ADR 0001 — Architecture hybride : comportement déterministe, LLM limité à la réalisation linguistique

- **Statut** : accepté
- **Date** : 2026-11-12
- **Contexte détaillé** : [design.md](../design.md)

## Contexte

Le simulateur doit faire jouer à un enfant un entretien NICHD qui peut être long. Trois exigences pèsent sur l'architecture :

1. **Cohérence du personnage** : l'enfant ne doit ni oublier ni inventer des faits au fil de l'entretien, en dehors des effets voulus (contamination par suggestion).
2. **Mesurabilité** : les métriques (informations exactes, contamination) supposent de savoir précisément ce que l'enfant a révélé et d'où viennent les faits erronés.
3. **Contrôle du contenu** : le sujet est sensible. Les révélations doivent rester non explicites, et rien ne doit fuiter en dehors de ce qui a été décidé.

Un LLM qui jouerait seul l'enfant à partir du scénario complet ne satisfait aucune de ces trois exigences de façon fiable. Il dérive sur les entretiens longs, ses révélations ne sont ni traçables ni reproductibles, et le scénario entier présent dans le prompt risque de fuiter.

## Décision

1. **Un moteur de comportement déterministe** (une machine à états, déterministe pour une seed donnée) décide à chaque tour de l'**acte de langage** de l'enfant et des **unités d'information autorisées**. Il se fonde sur le type de question, la phase, l'état de l'enfant et des paramètres sourcés dans la littérature.
2. **Le LLM local (`qwen3.8` via Ollama) n'intervient que pour transformer cette décision en énoncé d'enfant** plausible en français. **Il ne voit jamais le scénario complet**, seulement les unités autorisées du tour, le profil verbal et un historique court.
3. **Un filtre de sortie** (lexique interdit et contrôle de fuite fondé sur les ancres du scénario) vérifie chaque réponse. En cas d'échec : une régénération, puis une réponse type.
4. **Un classifieur unique** (le même LLM, température 0, JSON contraint, guidé par un skill NICHD versionné) étiquette chaque énoncé de l'interviewer. **Sa sortie alimente à la fois le moteur et l'évaluation**, pour que la réaction de l'enfant et le feedback ne puissent pas diverger.
5. **Les métriques sont calculées sans LLM**, à partir de l'état du moteur et des classifications.
6. **Tout est journalisé** dans un JSON par session, ce qui permet le rejeu.

## Conséquences

### Positives

- **Reproductibilité décisionnelle** : à scénario, seed et classifications identiques, mêmes révélations et mêmes contaminations.
- **Métriques exactes et gratuites** : le moteur sait ce qu'il a révélé et la source de chaque contamination.
- **Surface de fuite réduite** par construction. Les tentatives d'injection n'ont rien à extraire.
- Moteur, phases et métriques sont **testables unitairement sans LLM**.
- Les paramètres psychologiques sont **explicites, sourcés et ajustables**, ce qui ouvre la voie à des analyses de sensibilité.

### Négatives / risques

- **Le classifieur devient le point critique** : une erreur de classification produit à la fois une mauvaise réaction de l'enfant et un mauvais feedback. Mitigation : jeu de test disjoint, objectif κ ≥ 0,70, mode formateur qui rend la classification visible.
- **Le réalisme dépend de la richesse du moteur** : un enfant piloté par des règles peut sembler mécanique. Mitigation : la variation de surface est assurée par le LLM, et le réalisme sera validé en aveugle par des formateurs (hors v1).
- **Deux appels LLM par tour** (classification, puis réalisation) : la latence est à mesurer dès la tranche verticale. Repli : classifieur sur `qwen3:14b`.
- **Paramètres partiellement estimés** : la littérature donne surtout des ordres de grandeur. Les valeurs extrapolées sont marquées `estimated` et relues par un expert.
- **Coût de rédaction des scénarios** plus élevé (segments, unités, ancres, événement neutre) qu'un simple texte libre.

## Alternatives écartées

- **LLM seul jouant l'enfant à partir du scénario complet** : écarté pour les raisons du contexte (dérive, opacité, fuite).
- **Deux classifieurs distincts** (l'un pour le moteur, l'autre pour l'évaluation) : écarté, risque de divergence entre réaction et feedback.
- **Évaluateur distant** (modèle propriétaire via API) : écarté pour garder tout en local (coût, maîtrise de l'environnement, confidentialité des transcriptions).
- **Reproductibilité textuelle stricte** (même texte au caractère près) : écartée, coûteuse (figer matériel et versions) et sans intérêt pédagogique. Le rejeu depuis le journal suffit.
