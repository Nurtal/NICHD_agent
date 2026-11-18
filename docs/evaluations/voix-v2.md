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

## Écoute à l'aveugle (2026-11-17)

**Protocole.** Les extraits étaient anonymes et appariés en volume, dans un ordre aléatoire. L'écoute porte sur
6 réponses et 12 voix par réponse :

- la voix actuelle, seule puis avec le nouveau fond sonore ;
- pour chaque moteur, la variante « enfant » propre dont la hauteur est la plus proche de 300 Hz ;
- la meilleure voix adulte ;
- la fille de 8 ans rendue par Qwen ;
- Higgs « peur ».

Il y a eu **un seul auditeur** (l'utilisateur), qui a noté 71 extraits sur 72. Sa session avait été enregistrée
deux fois ; seule la dernière sauvegarde est comptée.

| Voix (moteur, référence) | Naturel | Fluidité | Âge le plus cité | Préférée |
|---|---|---|---|---|
| **Qwen3-TTS, fille de 8 ans conçue par Qwen** | **4,83** | **5,00** | 6–8 ans | **3 / 6** |
| Fish S2 Pro, même fille | 4,83 | 4,83 | 6–8 ans | 1 / 6 |
| Higgs, même fille + balise « peur » | 4,33 | 4,83 | 6–8 ans | 1 / 6 |
| Kyutai, lectrice adulte | 3,33 | 3,67 | 6–8 ans | 1 / 6 |
| XTTS, clone de la voix Kokoro enfant | 3,17 | 3,33 | 9–12 ans | 0 |
| Chatterbox v3, garçon de 6 ans | 3,17 | 3,67 | 6–8 ans | 0 |
| Qwen3-TTS, garçon de 6 ans | 3,00 | 3,67 | 9–12 ans | 0 |
| Higgs, garçon de 6 ans | 3,00 | 4,00 | 9–12 ans | 0 |
| Chatterbox v3, lectrice adulte | 2,83 | 2,67 | 9–12 ans | 0 |
| F5, garçon de 6 ans | 2,67 | 3,17 | 9–12 ans | 0 |
| Kokoro actuel + fond sonore | 1,00 | 1,00 | 9–12 ans | 0 |
| **Kokoro actuel** | **1,00** | **1,33** | 9–12 ans | 0 |

Détail par réponse : `experiments/voices/v2/listening/results_v2-1.md` (`analyze.py`).

**Lecture.**

1. **La voix actuelle est jugée la pire partout**, à 1 sur 5 sur les 6 réponses. Le fond sonore et les fondus
   seuls ne la sauvent pas : le problème est la voix elle-même, pas l'assemblage.
2. **La référence compte plus que le moteur.** Les trois voix en tête utilisent toutes la même fille de 8 ans
   conçue par Qwen. Le garçon de 6 ans plafonne à 3 sur 5, quel que soit le moteur, et paraît plus âgé
   (9–12 ans).
3. **Qwen3-TTS et Fish sont à égalité sur le naturel.** Qwen a toutes ses fluidités à 5 et 3 préférences sur 6.
   Il est aussi le seul sous licence libre (Apache-2.0), et il est plus rapide et plus léger que Fish.
4. **Higgs « peur » reste presque au niveau des meilleures** (4,33 / 4,83) : l'émotion par balises ne dégrade pas
   la voix.

**Limites.** L'écoute repose sur une seule personne. Le genre de la voix et la qualité de sa conception sont
confondus : une seule voix de fille, une seule de garçon. On ne sait donc pas si le garçon déplaît parce que
c'est un garçon ou parce que sa conception est moins réussie.

**Recommandation.** Adopter **Qwen3-TTS avec une voix d'enfant conçue par description**, dite d'un bloc (mode
natif).

## Banque de voix (2026-11-17)

Les scénarios mettent en scène des filles et des garçons de 5 à 12 ans. Une seule voix de fille de 8 ans ne
convient donc pas à tous. Il y a une voix par **genre × tranche d'âge du moteur** (`AgeBand` : 4–6, 7–9 et
10–12 ans).

**Conception** (`voice_bank.py`). Pour chacune des 5 cases nouvelles, Qwen3-TTS VoiceDesign a produit 4 voix
candidates : 2 descriptions × 2 graines. Toutes sont entièrement synthétiques. Chaque candidate a ensuite été
clonée par Qwen3-TTS Base sur 4 réponses, comme le fera le moteur. La case fille 7–9 ans garde la voix validée
par la première écoute.

**Mesure automatique** (`bank_eval.py`). Les 20 candidates passent : WER moyen de 0 à 8 %, sans hallucination.
Leur F0 va de 211 à 401 Hz.

**Écoute à l'aveugle** (`build_bank_listening.py`). Pour chaque case, chaque voix dit deux réponses à la suite.
L'auditeur note, choisit sa voix préférée par case, et le choix est sans ambiguïté :

| Case | Voix retenue | Naturel / fluidité | Âge perçu | F0 |
|---|---|---|---|---|
| Fille 4–6 ans | `fille_5_7_a2` | 4 / 5 | moins de 6 ans | 321 Hz |
| Fille 7–9 ans | fille de 8 ans (première écoute) | 4,8 / 5 | 6–8 ans | 333 Hz |
| Fille 10–12 ans | `fille_11_12_b1` | 4 / 5 | 9–12 ans | 218 Hz |
| Garçon 4–6 ans | `garcon_5_7_b2` | 5 / 5 | moins de 6 ans | 298 Hz |
| Garçon 7–9 ans | `garcon_8_10_b2` | 5 / 5 | 6–8 ans | 284 Hz |
| Garçon 10–12 ans | `garcon_11_12_a2` | 4 / 4 | 9–12 ans | 248 Hz |

L'âge perçu correspond à la case pour chacune des voix retenues. Le garçon 10–12 ans reste la case la plus
faible : les deux candidates « b » ont été perçues comme adolescentes ou trop jeunes. Le détail est dans
`experiments/voices/v2/listening/results_bank-1.md`.

## Intégration dans le moteur

- **Banque** : `src/nichd_sim/data/voices/`, 6 clips de référence en FLAC (1,2 Mo) avec leur texte et leur
  description, dans `voices.json`.
- **Profil** : un nouveau champ facultatif `child_profile.voice` (`fille` | `garcon`), renseigné dans les 8
  scénarios d'après l'accord de leur fiche (« est entendu » ou « est entendue »). Seule la voix l'utilise : la
  didascalie reste neutre (ADR 0003). Sans ce champ, on prend la voix de fille de la tranche d'âge.
- **Voix** : `QwenSpeaker` (`qwen_speaker.py` et `qwen_worker.py`, dans le venv `.envs/qwen`). Elle est
  choisie par défaut quand ce venv est installé, sinon Kokoro, sinon `tone`. Le mode texte n'a besoin d'aucune
  voix.
- **Rendu natif aux pauses du moteur.**
  - La réponse est dite d'un bloc, avec ses « … » et ses « euh… ». Chaque pause est ensuite **recalée sur la
    durée prévue par le moteur**. C'est le moteur qui décide de l'hésitation (ADR 0002) ; la voix ne décide
    que du son.
  - La voix ne pause pas toujours là où le texte l'écrit : elle peut pauser aussi à une virgule, ou dire
    « euh… non » d'un trait. Tout silence d'au moins 30 ms est donc candidat à la coupe, ainsi que les creux
    d'énergie proches de l'endroit attendu (avec une pénalité). Chaque pause prévue prend le candidat le plus
    proche de sa place dans le texte, par programmation dynamique.
  - Sur la session de démonstration (Emma, 9 réponses), toutes les pauses sont recalées au plan. Whisper
    retrouve le bon texte dans chaque morceau découpé : aucune coupe ne tombe au milieu d'un mot.
- **Coût** : environ 5 Go de mémoire graphique (float16). Sur une TITAN RTX, une réponse prend 2 à 5 s si elle
  est courte, environ 15 s si elle est longue. La latence n'est pas une priorité pour l'instant.
- **Démo de l'avatar** régénérée avec la nouvelle voix :
  - `avatar_sessions/emma-demo` ;
  - vidéos locales `docs/presentation/demo-avatar-emma-voix-v2.mp4` et `…-voix-v2-carte.mp4`.
