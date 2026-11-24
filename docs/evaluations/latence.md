# Latence d'un tour vocal en direct

Mesure : `experiments/latency/run.py`. 29 répliques de l'interviewer (s01, s08), dites par la voix adulte Kokoro, puis toute la chaîne : Whisper, classifieur, moteur, réalisateur, filtre, voix de l'enfant. Les étapes s'enchaînent comme en direct. « Jusqu'au premier son » est la somme du calcul ; le silence que le moteur prévoit avant que l'enfant parle (diction) n'y est pas compté.

| Étape | base (méd. / p95) | cascade (méd. / p95) |
|---|---|---|
| Transcription (Whisper large-v3) | 0.4 s / 0.5 s | 0.5 s / 0.6 s |
| Classification | 10.9 s / 40.1 s | 4.1 s / 59.4 s |
| Réalisation (avec filtre et reprise) | 1.6 s / 2.1 s | 1.8 s / 2.5 s |
| Synthèse de la voix | 8.7 s / 16.7 s | 10.1 s / 23.0 s |
| Recalage des pauses et ambiance | 0.3 s / 0.7 s | 0.4 s / 0.9 s |
| **Jusqu'au premier son** | 25.0 s / 53.4 s | 22.9 s / 80.5 s |

**base** — modèle `qwen3.8:latest`, réflexion `medium`. Démarrage à froid : chargement du LLM 0.5 s, chargement de Whisper 3.9 s, chargement de la voix (QwenSpeaker) 15.7 s. Silence prévu avant la parole : médiane 1863 ms. Invite du classifieur : 9298–9541 jetons (qwen3.8:latest contexte 32768). Replis du réalisateur : 1 / 29. GPU pendant la mesure : 19908 MiB / 11651 MiB.

**cascade** — modèle `qwen3.8:latest`, réflexion `cascade`. Démarrage à froid : chargement du LLM 12.9 s, chargement de Whisper 6.4 s, chargement de la voix (QwenSpeaker) 22.0 s. Silence prévu avant la parole : médiane 1863 ms. Invite du classifieur : 9300–9543 jetons (qwen3.8:latest contexte 32768). Replis du réalisateur : 0 / 29. GPU pendant la mesure : 19628 MiB / 11898 MiB.

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

### Lot L1 : classifieur en cascade (`cascade`)

- **Réglage.** Une première réponse sans réflexion. Les types fermés ou orientés (suggestive, choix fermé, directive,
  composée, « autre »), le hors scénario et les sorties invalides passent ensuite une seconde fois, avec la réflexion
  `low`.
- **Choix de la règle.** Je l'ai fixée hors ligne. Les 133 énoncés du jeu de test ont été classés une fois sans
  réflexion, une fois en `low` et une fois en `medium` (`classify_testset.py`, puis `cascade.py`).
  - `low` en seconde passe fait mieux que `medium` (κ simulé 0,956 contre 0,930) et va plus vite.
  - Escalader aussi les invitations indicées et le soutien gagnerait encore un peu de κ, mais ferait monter la médiane
    à 14 s.
- **Mesure réelle** (`eval-classifier --think cascade`) :
  - type : κ 0,948, comme `medium` ;
  - cible : 83,3 %, contre 86,4 % ;
  - latence : médiane 5,0 s, contre 13,6 s.
- **En entretien** (tableau ci-dessus) :
  - la classification passe de 10,9 s à 4,1 s en médiane ;
  - 6 tours sur 29 escaladent ;
  - les questions de dévoilement, fermées et difficiles (« Comment est-ce que tu t'es fait ça ? », « Est-ce que
    quelqu'un t'a attrapé le bras ? »), restent longues : de 25 à 65 s ;
  - le premier son arrive en 22,9 s au lieu de 25,0 s, car la voix pèse maintenant le plus (10,1 s).
- **Pas de plafond de temps sur la seconde passe.** Simulé à 8, 10, 15 ou 20 s, un plafond garde la réponse rapide
  justement sur les énoncés où la réflexion corrige. Le κ retombe alors à 0,921.
- **Pistes pour les questions longues.** Rien n'est engagé.
  - **Préparer la réponse pendant que la seconde passe tourne** : moteur, réalisation et voix sur la réponse rapide,
    gardés si la vérification confirme. La réponse rapide est confirmée sur 42 des 57 énoncés escaladés, soit 74 %.
    Il faudrait un second emplacement Ollama (`OLLAMA_NUM_PARALLEL`). C'est un réglage du serveur partagé, à décider
    avec ses utilisateurs.
  - **Un modèle plus petit pour la seconde passe** : il faudrait le télécharger, ce qui demande ton accord.
