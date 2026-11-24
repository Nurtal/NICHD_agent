# Latence d'un tour vocal en direct

Mesure : `experiments/latency/run.py`. 29 répliques de l'interviewer (s01, s08), dites par la voix adulte Kokoro, puis toute la chaîne : Whisper, classifieur, moteur, réalisateur, filtre, voix de l'enfant. Les étapes s'enchaînent comme en direct. « Jusqu'au premier son » est la somme du calcul ; le silence que le moteur prévoit avant que l'enfant parle (diction) n'y est pas compté.

| Étape | base (méd. / p95) |
|---|---|
| Transcription (Whisper large-v3) | 0.4 s / 0.5 s |
| Classification | 10.9 s / 40.1 s |
| Réalisation (avec filtre et reprise) | 1.6 s / 2.1 s |
| Synthèse de la voix | 8.7 s / 16.7 s |
| Recalage des pauses et ambiance | 0.3 s / 0.7 s |
| **Jusqu'au premier son** | 25.0 s / 53.4 s |

**base** — modèle `qwen3.8:latest`, réflexion `medium`. Démarrage à froid : chargement du LLM 0.5 s, chargement de Whisper 3.9 s, chargement de la voix (QwenSpeaker) 15.7 s. Silence prévu avant la parole : médiane 1863 ms. Invite du classifieur : 9298–9541 jetons (qwen3.8:latest contexte 32768). Replis du réalisateur : 1 / 29. GPU pendant la mesure : 19908 MiB / 11651 MiB.

## Constats

Mesure de référence du 2026-11-23 (`base`), avec les GPU presque libres (un autre utilisateur occupait environ 1 Go).

- **Environ 25 s en médiane avant que l'enfant parle**, et jusqu'à 61 s.
  - Deux étapes font presque tout le temps : la classification et la voix.
  - Whisper, le moteur, le réalisateur et le recalage des pauses pèsent moins de 2,5 s à eux quatre.
- **Classification : le temps part dans la réflexion, pas dans l'invite.**
  - **Invite :** elle compte environ 9 400 jetons et tient sans troncature dans le contexte de 32 768. Ollama la relit
    en entier à chaque tour (`prompt_eval_count` complet, environ 1,8 s). Le réalisateur passe par le même modèle entre
    deux classifications, et cela vide le cache de préfixe d'Ollama.
  - **Réflexion :** elle produit de 290 à 2 280 jetons, à environ 45 jetons par seconde, soit de 7 à 50 s. Les questions
    les plus difficiles coûtent le plus, par exemple « Comment est-ce que tu t'es fait ça ? » (50 s).
  - Le levier principal est donc de réfléchir moins souvent (lot L1). Rendre le cache de préfixe réutilisable ne
    gagnerait qu'environ 1,5 s.
- **La voix Qwen est plus lente que le temps réel.** Elle met environ 1,5 s de calcul par seconde de parole
  (16,6 s de parole en 33,7 s).
  - Elle ne démarre qu'une fois la réponse entière synthétisée, ce qui donne 8,7 s en médiane.
  - Le démarrage à froid du modèle de voix coûte 15,7 s, à faire avant l'entretien.
  - **Conséquence pour le lot L2 :** découper la réponse aux pauses fera parler l'enfant plus tôt. Mais à ce rythme, la
    lecture rattrapera la synthèse, et il y aura des trous. Il faut d'abord mesurer la vitesse de Qwen seule et chercher
    à l'accélérer, ou ne découper que là où les pauses prévues masquent le retard.
- **Le silence que le moteur prévoit avant la parole (1,9 s en médiane) peut absorber une partie du calcul** au lieu
  de s'y ajouter (lot L2).
- **Un énoncé très court a été mal transcrit** : « Et après ? », dit par la voix adulte Kokoro, est devenu « Il est
  prêt. ». C'est une erreur sur 29. À surveiller en direct avec le micro.
