# Voix de l'enfant v2 : clonage sur références ouvertes, sept moteurs

*Criblage du 2026-11-17. Scripts et chiffres complets : `experiments/voices/v2/` et
[`results/screening_v2.md`](../../experiments/voices/v2/results/screening_v2.md). Voir aussi [voix.md](voix.md) (v1)
et [ADR 0002](../adr/0002-mensonge-diction-voix.md).*

## Pourquoi

La voix actuelle manque de fluidité et sonne synthétique. Elle est faite avec Kokoro `ff_siwis`, dont la hauteur et
les formants sont montés ×1,25 par rééchantillonnage. La réponse est coupée aux pauses puis recollée avec des
silences numériques. Quatre causes probables :

1. le décalage ×1,25 donne une voix « accélérée » ;
2. les silences sont parfaitement nuls et les coupures s'entendent ;
3. les « euh » sont dits comme des mots ;
4. il n'y a aucun contrôle de l'émotion.

Le criblage v1 montrait déjà que le clonage améliore nettement l'intelligibilité.

## Ce qui a été fait

- **Références de clonage**, jamais la voix d'un enfant réel (ADR 0002) :
  - 4 lectrices adultes de MLS French (CC BY 4.0) ;
  - 2 actrices adultes de CaFE (CC BY-NC-SA 4.0), en neutre, peur et tristesse ;
  - 3 voix d'enfant **entièrement synthétiques** :
    - une fille de 8 ans et un garçon de 6 ans, conçus par description avec Qwen3-TTS VoiceDesign ;
    - la voix Kokoro enfant actuelle.
- **Sept moteurs**, un environnement Python chacun. Chaque moteur dit, pour chaque référence, deux ensembles :
  - les 61 segments du criblage v1 (phrases et fragments) ;
  - 12 **réponses entières synthétisées d'un bloc**, avec leurs « … » et leurs « euh ».

  Les variantes d'émotion (réponses seulement) sont :
  - les références CaFE « peur » et « tristesse » ;
  - pour Higgs, les balises `<|emotion:fear|>`, `sadness` et `shame`.
- **Assemblage** (`nichd_sim.voice.render.RenderStyle`, facultatif, défaut inchangé) :
  - un fond sonore de pièce à −58 dBFS au lieu du silence numérique ;
  - des fondus de 30 ms ;
  - un mode « natif » : la réponse est dite d'un bloc et sa chronologie est mesurée sur l'audio.

## Moteurs retenus et écartés

| Moteur | Modèle | Licence | Mémoire GPU | Déterministe |
|---|---|---|---|---|
| Qwen3-TTS | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` (+ VoiceDesign) | Apache-2.0 | 10 Go | oui |
| Higgs TTS 3 | `multimodalart/higgs-audio-v3-tts-4b-transformers` (fp32) | Boson, recherche / non commerciale | 19 Go | oui |
| Fish S2 Pro | `fishaudio/s2-pro` (fp16, serveur API) | Fish Audio Research License (non commerciale) | ~20 Go | oui |
| Chatterbox multilingue v3 | `ResembleAI/chatterbox` (t3 v3) | MIT, filigrane Perth dans l'audio | 4 Go | **non** |
| XTTS v2 | `coqui/XTTS-v2` | Coqui Public Model License (non commerciale) | 2 Go | oui |
| F5-TTS français | `RASPIAUDIO/F5-French-MixedSpeakers-reduced` | CC BY-NC 4.0 | 1 Go | oui |
| Kyutai TTS | `kyutai/tts-1.6b-en_fr` | CC BY 4.0, voix CML-TTS | 4 Go | oui |

Écartés :

- **Voxtral TTS** : vllm 0.34 impose torch cu130, que le pilote 575 refuse, et vllm-omni est incompatible avec
  cette version. De plus, il n'a que des voix préréglées.
- **Fish Audio S2 Drama** : il faut au moins 48 Go en FP8, et les cartes Turing n'ont pas de FP8.
- **Pocket TTS** : modèle à accès restreint, sans jeton Hugging Face.
- **F5 québécois** : accent inadapté ; remplacé par sa base en français de France.

Kyutai n'accepte que des voix précalculées, toutes adultes : il ne peut pas cloner une voix d'enfant.

## Résultats objectifs

Mesures automatiques :

- **Intelligibilité** : WER Whisper large-v3, « euh » et « hein » retirés.
- **Hallucinations** : phrase inventée, ou durée hors de proportion avec le texte.
- **Hauteur de voix** : F0 médiane, un enfant de 8 ans parle vers 250–300 Hz.
- **Pauses** : nombre de « … » écrits qui sont vraiment rendus par une pause.

Le tableau ci-dessous garde, pour chaque moteur, ses meilleures variantes et sa variante « enfant ».

| Variante | WER phrases | WER réponses entières | Hallucinations | F0 | Pauses rendues |
|---|---|---|---|---|---|
| **qwen-synth_qwen_girl8** | 3,0 % | 4,3 % | 0 / 72 | 357 Hz | 7/7 |
| **qwen-synth_qwen_boy6** | 4,4 % | 3,2 % | 1 / 72 | 285 Hz | 7/7 |
| **fish-synth_qwen_girl8** | 3,4 % | 2,1 % | 0 / 72 | 340 Hz | 5/7 |
| **higgs-synth_qwen_girl8** | 5,1 % | 2,1 % | 1 / 72 | 342 Hz | 6/7 |
| **higgs-synth_qwen_boy6** | 4,0 % | 3,2 % | 1 / 72 | 289 Hz | 7/7 |
| higgs-synth_qwen_girl8 + peur / tristesse / honte | — | 2,1 % | 0 / 12 | 282–310 Hz | 6–7/7 |
| chatterbox3-synth_qwen_girl8 | 6,2 % | 2,1 % | 0 / 72 | 378 Hz | 5/7 |
| chatterbox3-cafe_04_neutre | 4,4 % | 1,1 % | 0 / 72 | 236 Hz | 7/7 |
| xtts-synth_qwen_girl8 | 7,8 % | 4,3 % | 4 / 72 | 307 Hz | 7/7 |
| kyutai-mls10179 (adulte) | 2,8 % | 3,2 % | 0 / 72 | 274 Hz | 7/7 |
| f5-synth_qwen_boy6 | 6,2 % | 7,4 % | 2 / 72 | 235 Hz | 3/7 |
| f5-mls_f1 | 37,8 % | 41,5 % | 17 / 72 | 235 Hz | 0/7 |
| *v1 : kokoro-siwis-child (voix actuelle)* | 5,3 % | — | 0 / 60 | 266 Hz | — |
| *v1 : chatterbox-clone-kchild* | 5,7 % | — | 1 / 60 | 236 Hz | — |

Ce que montrent les chiffres :

1. **La hauteur d'enfant vient de la référence, pas du moteur.** Cloner une adulte donne 210–245 Hz quel que soit
   le moteur. Les voix d'enfant conçues avec Qwen donnent 285–380 Hz, sans le décalage ×1,25 qui produit l'effet
   « voix accélérée ».
2. **Qwen3-TTS, Fish S2 Pro et Higgs sont les plus propres.**
   - Ils se trompent sur 2 à 4 % des mots des réponses entières et n'inventent presque jamais de phrase.
   - Ils rendent la plupart des pauses écrites.
   - Qwen est le seul sous licence Apache-2.0 ; il est aussi rapide, environ 1 fois le temps réel par lots de 8.
3. **Les réponses dites d'un bloc sont aussi intelligibles que les phrases isolées**, et les « … » y deviennent de
   vraies pauses. Le mode natif est donc viable. Il éviterait les coupures recollées.
4. **Les étiquettes d'émotion de Higgs** ne coûtent rien en intelligibilité et montent la hauteur de 30 à 60 Hz.
   Elles pourraient relier l'activation du moteur d'état à la voix. Reste à savoir à l'écoute si l'émotion
   s'entend.
5. **F5 n'est pas fiable** en français avec des références de livres audio, et **Chatterbox v3 n'est pas
   déterministe**, ce qui casse le rejeu à l'identique.

Limites :

- Les **RTF** mesurés sont pessimistes, parce que plusieurs moteurs partageaient une carte graphique.
- Whisper écrit « 10h » pour « dix heures », ce qui gonfle un peu tous les WER de la même façon.
- Les **fragments** (1 à 3 mots) restent mal transcrits par tous les moteurs : le WER sur 22 mots y est très
  bruité.
- **Rien ici ne mesure le naturel ni la fluidité.**

## Écoute à l'aveugle (à faire)

La page `experiments/voices/v2/listening/` présente 6 réponses et 12 voix par réponse, dans un ordre aléatoire et
sans nom de modèle, toutes au même volume :

- la voix actuelle, seule puis avec le nouveau fond sonore ;
- pour chaque moteur, la variante « enfant » propre dont la hauteur est la plus proche de 300 Hz ;
- la meilleure voix adulte ;
- la fille de 8 ans rendue par Qwen ;
- Higgs « peur ».

Chaque voix est notée sur trois critères : naturel (1–5), fluidité (1–5) et âge perçu. On choisit aussi une voix
préférée par réponse. `analyze.py` dépouillera les notes. **L'intégration du gagnant (PR b) attend cette écoute.**
