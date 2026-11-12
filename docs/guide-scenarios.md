# Guide de rédaction des scénarios

Une fiche de scénario est un fichier YAML dans `scenarios/`. Elle décrit **ce qui s'est réellement passé** (les faits de référence) et **qui est l'enfant** (le profil). Le moteur de comportement décide, à partir d'elle, de ce que l'enfant révèle à chaque question ; le LLM ne voit jamais la fiche complète, seulement les unités autorisées pour le tour.

Vérifiez toujours une fiche avant de l'utiliser :

```bash
uv run nichd-sim check-scenario scenarios/ma_fiche.yaml
```

Une **erreur** rend la fiche inutilisable ; un **avertissement** signale un problème probable. Les tests du dépôt exigent zéro erreur et zéro avertissement.

## Contenu autorisé en v1

- Aucun contenu sexuel. Les maltraitances physiques, la négligence, les violences dont l'enfant est témoin, les vols, accidents, conflits sont possibles.
- Révélations **non explicites** : « il m'a tapé dans le dos », pas de description détaillée des coups ni des blessures.
- Personnages et faits **entièrement fictifs**.
- Toute fiche commence en `status: draft` ; seul un formateur NICHD la passe en `validated`.

## Structure

```yaml
id: s04_exemple              # identifiant unique, = nom du fichier sans .yaml
version: "0.1.0"             # à incrémenter à chaque modification (le rejeu vérifie la version)
title: "Prénom, âge — résumé"
status: draft
intake_context: >            # ce que l'apprenant sait AVANT l'entretien (jamais les faits)
  ...
child_profile:
  name: Prénom
  age: 8                     # 4 à 12 ans → bande 4_6, 7_9 ou 10_12
  reluctance: 0.5            # 0 = parle tout de suite ; ≥ 0.9 = ne dévoilera jamais
  verbal_skills: 0.5         # quantité de détails par invitation
  suggestibility: 0.5        # propension à acquiescer aux suggestions
target_event:                # l'événement objet de l'audition
  segments: [before, during, after]   # dans cet ordre, chacun présent au plus une fois
neutral_event:               # événement neutre récent, pour la pratique narrative
  segments: [...]
parameter_overrides: {}      # facultatif : surcharge de paramètres (voir src/nichd_sim/data/parameters.yaml)
```

## Unités d'information

Chaque unité est **un fait vérifiable**, formulé comme l'enfant le dirait :

```yaml
- id: d_pousse              # unique dans toute la fiche (préfixes conseillés : b_, d_, a_, n_)
  category: what            # who, what, where, when, frequency
  centrality: central       # central : le cœur des faits ; peripheral : détail
  value: "le monsieur au blouson rouge a poussé Monsieur Bertin"
  anchors: [poussé, pousser]
```

- **Ordre** : à l'intérieur d'un segment, les unités sont dans l'ordre chronologique ; une invitation ouverte livre d'abord les unités centrales, dans cet ordre.
- **Centralité** : visez au moins 5 unités centrales dans l'événement cible (qui, quoi, où, quand) ; les détails périphériques n'émergent qu'avec des invitations indicées ou des questions ciblées.
- **Fréquence** : pour des faits répétés, une unité `frequency` (« il l'a déjà fait d'autres fois ») ; les épisodes multiples ne sont pas encore modélisés.

## Ancres : la règle la plus importante

Les ancres servent à deux contrôles automatiques sur chaque réponse de l'enfant :

1. **Omission** : si l'unité est autorisée, la réponse doit contenir au moins une de ses ancres. ⇒ **au moins une ancre doit figurer dans la valeur** (sinon erreur).
2. **Fuite** : si l'unité n'est pas autorisée, aucune de ses ancres ne doit apparaître. ⇒ les ancres doivent être **spécifiques** à l'unité.

Bonnes ancres : noms propres (`Bertin`, `Karim`), objets ou actions distinctifs (`portefeuille`, `poussé`, `blouson rouge`). La comparaison ignore accents et majuscules et tolère les flexions (`poussé` couvre `poussait`).

À éviter (avertissement) : mots du quotidien (`maison`, `école`, `déjà`, `soir`, `dame`, `parti`…) et ancres partagées par deux unités.

## Calibrer le profil

| Profil | Effet observable |
|---|---|
| `reluctance` 0.2 | dévoile à la première incitation de transition |
| `reluctance` 0.6 | 3 incitations ouvertes environ, moins avec du soutien |
| `reluctance` ≥ 0.9 | aucun dévoilement, sauf si le soutien fait baisser la réticence |
| `verbal_skills` 0.3 / 0.8 | 1–2 / 3–5 unités par invitation selon l'âge |
| `suggestibility` 0.2 / 0.8 | acquiescement rare / fréquent aux suggestions fausses |

## Vérifier en jeu

```bash
uv run nichd-sim check-scenario scenarios/ma_fiche.yaml
uv run nichd-sim play scenarios/ma_fiche.yaml --trainer                      # sans LLM
uv run nichd-sim play scenarios/ma_fiche.yaml --trainer --classifier llm --realizer llm
```

En mode formateur, surveillez les lignes `[filtre]` : des rejets répétés sur une unité signalent souvent une ancre mal choisie ou une valeur difficile à reformuler.
