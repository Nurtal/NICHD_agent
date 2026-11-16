# Criblage TTS — Kokoro vs Chatterbox (2026-11-16)

Corpus : 60 segments réellement envoyés à la voix par le moteur (plans d'élocution de sessions scriptées, s08 compris),
dont 19 fragments de 3 mots ou moins coupés par les pauses, plus « euh… ». Juge d'intelligibilité : Whisper large-v3.
Résultats bruts : [screening.md](screening.md), détail par segment : `eval.jsonl`.

| Variante | WER phrases | WER fragments | F0 médiane | Hallucinations | Synthèse / segment | Déterministe | GPU |
|---|---|---|---|---|---|---|---|
| **kokoro-siwis-child** | 5,4 % | 36,8 % | **266 Hz** | **0** / 60 | **0,10 s** | **oui** | **1,0 Go** |
| kokoro-siwis (adulte) | 3,8 % | 10,5 % | 215 Hz | 1 / 60 | 0,09 s | oui | 1,0 Go |
| chatterbox-clone-kchild | 5,8 % | 15,8 % | 236 Hz | 1 / 60 | 5,06 s | non | 4,4 Go |
| chatterbox-default (adulte) | 18,9 % | 216 % | 150 Hz | 14 / 60 | 3,66 s | non | 4,4 Go |
| chatterbox-default-child | 17,9 % | 216 % | 192 Hz | 15 / 60 | 5,62 s | non | 4,4 Go |

Repère : un enfant de 8 ans parle autour de 250 à 300 Hz, une femme adulte autour de 200 Hz.

## Constats

1. **La voix par défaut de Chatterbox est inutilisable en français.** C'est une voix grave, à 150 Hz. Sur 60 segments, elle hallucine 14 fois : du charabia anglais (« was fard, with head N… »), des répétitions, et un « euh » qui dure 5 s et devient « And cool, cool ».
2. **Chatterbox redevient fiable quand il clone une référence française**, ici l'extrait d'enfant Kokoro, entièrement synthétique. Son intelligibilité rejoint alors celle de Kokoro, mais :
   - il est 50 fois plus lent (5 s par segment, donc environ 20 s pour une réponse de 4 segments) ;
   - il n'est pas déterministe malgré la seed : l'audio ne se rejoue pas à l'identique ;
   - il occupe 4,4 Go de mémoire GPU.
3. **Kokoro voix d'enfant** :
   - F0 dans la plage d'un enfant (266 Hz) et aucune hallucination ;
   - intelligibilité proche de la voix adulte sur les phrases ;
   - déterministe ;
   - 0,1 s par segment et 1 Go, ce qui laisse la place au LLM sur le même GPU ;
   - réglage de débit natif et exact (1,31 pour 1,33 attendu).
4. **Points faibles communs aux deux moteurs** :
   - **Fragments.** Synthétisés isolément (« J'avais », « était là. »), ils perdent leur contexte et prennent une
     intonation de fin de phrase. C'est une limite de la conception actuelle (une synthèse par segment), pas seulement
     du modèle. La voix d'enfant Kokoro ajoute en plus un bref son d'attaque, que Whisper entend comme « Et ».
   - **« euh… » isolé** : correct avec Kokoro adulte, mais entendu « Zut » avec la voix d'enfant Kokoro.

## Recommandation

**Kokoro, voix d'enfant (ff_siwis × 1,25), comme voix par défaut.** C'est le seul candidat compatible avec l'invariant de
l'ADR 0002 : l'audio se rejoue à l'identique et les silences sont exacts. Il est aussi assez rapide pour l'oral.
Chatterbox avec clonage reste une option pour l'expressivité, à départager **à l'écoute**. Ces mesures ne disent rien du
naturel ni de l'âge perçu.

## Suites proposées

- **Synthétiser la phrase entière, puis insérer les pauses aux frontières de mots** (alignement ou durées prédites par
  Kokoro), au lieu de synthétiser chaque fragment séparément. Cela supprime l'intonation cassée et l'ambiguïté des
  fragments.
- **« euh »** : tester d'autres graphies (« euhhh », « heu ») ou un échantillon synthétique fixe réutilisé.
- **Rogner l'attaque** de la voix d'enfant (le bref son entendu « Et »).
- **Écoute** par l'équipe : un même ensemble de 8 segments pour chaque variante, avec un jugement à l'aveugle de l'âge
  perçu et du naturel.

## Suite : branchement de Kokoro et correction des fragments (2026-11-16)

Kokoro est branché derrière le port `Speaker` (`src/nichd_sim/voice/kokoro_speaker.py`). Il tourne dans un processus séparé,
lancé avec le Python de son propre venv (`kokoro_worker.py`).

**Correction des fragments.** La réponse entière, « euh » compris, est synthétisée en **un seul énoncé**. On la coupe
ensuite aux points de pause, au milieu de l'espace entre deux mots, d'après les **durées de phonèmes prédites par
Kokoro** (600 échantillons par unité), et on insère nos silences. Mesure sur 40 réponses réelles avec pauses
(`render_replies.py`, puis `eval_replies.py`, résultats dans [replies/report.md](replies/report.md)) :

| Mode | WER (réponse entière) | Réponses parfaites | « Et » parasite en tête |
|---|---|---|---|
| une synthèse par fragment (avant) | 9,2 % | 13 / 40 | 2 |
| **un énoncé coupé (après)** | **5,9 %** | **15 / 40** | **0** |

- Les écarts restants sont surtout des normalisations de Whisper (« Je sais pas » transcrit « Je ne sais pas »,
  « Monsieur » transcrit « M. »).
- **« euh » : Whisper n'est pas un juge fiable.**
  - Sur un segment isolé de 400 ms, il hallucine (« Au revoir », « Merci d'avoir regardé cette vidéo ! »).
  - En contexte, il écrit tantôt « Euh », tantôt « Re » : le [œ] de « euh » est proche du [ʁə] de « re », et
    Whisper a tendance à effacer les disfluences.
  - Le son brut, sans coupe, donne le même résultat : la coupe n'est pas en cause.
  - **Une écoute humaine est nécessaire.**
- **Coût** : 0,14 s pour une réponse de 3 morceaux, rendu identique d'une fois à l'autre (seed dérivée du texte).
