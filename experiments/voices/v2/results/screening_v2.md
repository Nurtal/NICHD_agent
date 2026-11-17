# Criblage voix v2 — résultats objectifs

WER : Whisper large-v3 (« euh » et « hein » retirés des deux côtés). Réponses entières : synthétisées d'un bloc, pauses écrites « … ». F0 : un enfant de 8 ans parle vers 250–300 Hz.

| Variante | Moteur | WER phrases | WER fragments | WER réponses entières | Hallucinations | F0 médiane | Pauses rendues (réponses) | RTF |
|---|---|---|---|---|---|---|---|---|
| chatterbox3-synth_qwen_girl8 | chatterbox3 | 6.2% | 18.2% | 2.1% | 0 / 72 | 378 Hz | 5/7 | 1.25 |
| chatterbox3-synth_qwen_boy6 | chatterbox3 | 5.7% | 31.8% | 5.3% | 2 / 72 | 339 Hz | 4/7 | 1.36 |
| chatterbox3-mls_f1 | chatterbox3 | 3.3% | 27.3% | 1.1% | 0 / 72 | 232 Hz | 7/7 | 2.80 |
| chatterbox3-mls_f2 | chatterbox3 | 3.8% | 27.3% | 8.5% | 0 / 72 | 245 Hz | 6/7 | 4.07 |
| chatterbox3-cafe_04_neutre | chatterbox3 | 4.4% | 9.1% | 1.1% | 0 / 72 | 236 Hz | 7/7 | 4.27 |
| chatterbox3-synth_kokoro_child | chatterbox3 | 4.4% | 22.7% | 3.2% | 2 / 72 | 243 Hz | 3/7 | 4.59 |
| chatterbox3-cafe_04_peur | chatterbox3 | nan% | nan% | 5.3% | 0 / 12 | 318 Hz | 4/7 | 3.58 |
| chatterbox3-cafe_04_tristesse | chatterbox3 | nan% | nan% | 2.1% | 0 / 12 | 293 Hz | 3/7 | 3.22 |
| f5-synth_qwen_girl8 | f5 | 10.2% | 18.2% | 11.7% | 2 / 72 | 292 Hz | 1/7 | 2.09 |
| f5-synth_qwen_boy6 | f5 | 6.2% | 9.1% | 7.4% | 2 / 72 | 235 Hz | 3/7 | 1.76 |
| f5-mls_f1 | f5 | 37.8% | 109.1% | 41.5% | 17 / 72 | 235 Hz | 0/7 | 2.65 |
| f5-mls_f2 | f5 | 24.6% | 109.1% | 53.2% | 15 / 72 | 213 Hz | 3/7 | 1.69 |
| f5-cafe_04_neutre | f5 | 8.1% | 18.2% | 10.6% | 0 / 72 | 216 Hz | 2/7 | 1.25 |
| f5-synth_kokoro_child | f5 | 6.0% | 9.1% | 9.6% | 2 / 72 | 240 Hz | 2/7 | 1.19 |
| f5-cafe_04_peur | f5 | nan% | nan% | 14.9% | 0 / 12 | 273 Hz | 3/7 | 1.04 |
| f5-cafe_04_tristesse | f5 | nan% | nan% | 9.6% | 0 / 12 | 299 Hz | 4/7 | 0.87 |
| fish-synth_qwen_girl8 | fish | 3.4% | 13.6% | 2.1% | 0 / 72 | 340 Hz | 5/7 | 3.48 |
| fish-synth_qwen_boy6 | fish | 5.1% | 27.3% | 6.4% | 2 / 72 | 250 Hz | 1/7 | 3.62 |
| fish-mls_f1 | fish | 2.8% | 31.8% | 4.3% | 0 / 72 | 230 Hz | 4/7 | 4.13 |
| fish-mls_f2 | fish | 2.8% | 18.2% | 5.3% | 0 / 72 | 211 Hz | 7/7 | 3.44 |
| fish-cafe_04_neutre | fish | 3.1% | 22.7% | 4.3% | 0 / 72 | 225 Hz | 5/7 | 3.01 |
| fish-synth_kokoro_child | fish | 3.1% | 13.6% | 2.1% | 0 / 72 | 233 Hz | 4/7 | 2.94 |
| fish-cafe_04_peur | fish | nan% | nan% | 5.3% | 0 / 12 | 303 Hz | 7/7 | 2.99 |
| fish-cafe_04_tristesse | fish | nan% | nan% | 5.3% | 0 / 12 | 271 Hz | 7/7 | 3.00 |
| higgs-synth_qwen_girl8 | higgs | 5.1% | 4.5% | 2.1% | 1 / 72 | 342 Hz | 6/7 | 3.16 |
| higgs-synth_qwen_boy6 | higgs | 4.0% | 9.1% | 3.2% | 1 / 72 | 289 Hz | 7/7 | 5.62 |
| higgs-mls_f1 | higgs | 4.0% | 18.2% | 9.6% | 1 / 72 | 237 Hz | 6/7 | 5.85 |
| higgs-mls_f2 | higgs | 3.6% | 27.3% | 5.3% | 0 / 72 | 235 Hz | 6/7 | 2.25 |
| higgs-cafe_04_neutre | higgs | 3.6% | 9.1% | 2.1% | 0 / 72 | 227 Hz | 5/7 | 1.69 |
| higgs-synth_kokoro_child | higgs | 3.0% | 0.0% | 3.2% | 0 / 72 | 250 Hz | 5/7 | 1.73 |
| higgs-synth_qwen_girl8+fear | higgs | nan% | nan% | 2.1% | 0 / 12 | 282 Hz | 7/7 | 1.87 |
| higgs-synth_qwen_girl8+sadness | higgs | nan% | nan% | 2.1% | 0 / 12 | 302 Hz | 7/7 | 1.84 |
| higgs-synth_qwen_girl8+shame | higgs | nan% | nan% | 2.1% | 0 / 12 | 310 Hz | 6/7 | 1.86 |
| kyutai-mls10179 | kyutai | 2.8% | 22.7% | 3.2% | 0 / 72 | 274 Hz | 7/7 | 0.66 |
| kyutai-mls12080 | kyutai | 3.6% | 4.5% | 4.3% | 0 / 72 | 228 Hz | 7/7 | 0.69 |
| qwen-synth_qwen_girl8 | qwen | 3.0% | 13.6% | 4.3% | 0 / 72 | 357 Hz | 7/7 | 0.90 |
| qwen-synth_qwen_boy6 | qwen | 4.4% | 9.1% | 3.2% | 1 / 72 | 285 Hz | 7/7 | 1.09 |
| qwen-mls_f1 | qwen | 3.4% | 18.2% | 5.3% | 0 / 72 | 229 Hz | 6/7 | 2.12 |
| qwen-mls_f2 | qwen | 2.7% | 13.6% | 6.4% | 0 / 72 | 211 Hz | 5/7 | 2.97 |
| qwen-cafe_04_neutre | qwen | 3.4% | 0.0% | 2.1% | 0 / 72 | 220 Hz | 4/7 | 3.35 |
| qwen-synth_kokoro_child | qwen | 3.0% | 0.0% | 2.1% | 0 / 72 | 242 Hz | 7/7 | 3.36 |
| qwen-cafe_04_peur | qwen | nan% | nan% | 2.1% | 0 / 12 | 312 Hz | 5/7 | 3.38 |
| qwen-cafe_04_tristesse | qwen | nan% | nan% | 3.2% | 0 / 12 | 287 Hz | 5/7 | 3.62 |
| xtts-synth_qwen_girl8 | xtts | 7.8% | 45.5% | 4.3% | 4 / 72 | 307 Hz | 7/7 | 0.59 |
| xtts-synth_qwen_boy6 | xtts | 5.8% | 63.6% | 3.2% | 3 / 72 | 250 Hz | 7/7 | 0.61 |
| xtts-mls_f1 | xtts | 5.3% | 4.5% | 16.0% | 9 / 72 | 235 Hz | 7/7 | 1.13 |
| xtts-mls_f2 | xtts | 7.0% | 27.3% | 20.2% | 2 / 72 | 243 Hz | 7/7 | 1.59 |
| xtts-cafe_04_neutre | xtts | 6.7% | 4.5% | 4.3% | 7 / 72 | 232 Hz | 7/7 | 1.86 |
| xtts-synth_kokoro_child | xtts | 6.8% | 18.2% | 5.3% | 2 / 72 | 238 Hz | 6/7 | 1.89 |
| xtts-cafe_04_peur | xtts | nan% | nan% | 5.3% | 0 / 12 | 288 Hz | 7/7 | 1.92 |
| xtts-cafe_04_tristesse | xtts | nan% | nan% | 3.2% | 1 / 12 | 269 Hz | 7/7 | 2.12 |
| chatterbox-clone-kchild | v1 | 5.7% | 18.2% | nan% | 1 / 60 | 236 Hz | — | 1.60 |
| kokoro-siwis-child | v1 | 5.3% | 36.4% | nan% | 0 / 60 | 266 Hz | — | 0.03 |

| Moteur | Modèle | Licence | Chargement | Mémoire GPU | Déterministe | Fréquence |
|---|---|---|---|---|---|---|
| chatterbox3 | chatterbox3 | MIT (filigrane Perth dans l'audio) | 48.7 s | 4.11 Go | non | 24000 Hz |
| f5 | RASPIAUDIO/F5-French-MixedSpeakers-reduced | CC-BY-NC-4.0 | 38.9 s | 0.92 Go | oui | 24000 Hz |
| fish | fishaudio/s2-pro | Fish Audio Research License (non commerciale) | 128.2 s | None Go | oui | 44100 Hz |
| higgs | multimodalart/higgs-audio-v3-tts-4b-transformers | Boson Higgs TTS 3 research / non-commercial | 27.0 s | 19.04 Go | oui | 24000 Hz |
| kyutai | kyutai/tts-1.6b-en_fr | CC-BY-4.0 (voix : licences CML-TTS) | 50.5 s | 4.4 Go | oui | 24000 Hz |
| qwen | Qwen/Qwen3-TTS-12Hz-1.7B-Base (+VoiceDesign) | Apache-2.0 | 6.8 s | 10.18 Go | oui | 24000 Hz |
| xtts | xtts | Coqui Public Model License (non commerciale) | 27.1 s | 2.1 Go | oui | 24000 Hz |

## Segments signalés (6 au plus par variante)

- `chatterbox3-synth_qwen_boy6` c04 « Non. » → « Non... » (1.6 s)
- `chatterbox3-synth_qwen_boy6` c36 « Son vélo était jaune. » → « Son vélo était jaune. D'après Taxion... » (3.1 s)
- `chatterbox3-synth_kokoro_child` c04 « Non. » → « Non, non. » (1.9 s)
- `chatterbox3-synth_kokoro_child` r04 « Non. » → « Non. Non. » (1.6 s)
- `f5-synth_qwen_girl8` c37 « Oui. Samedi vers dix heures. » → « Samedi vers 10h » (1.3 s)
- `f5-synth_qwen_girl8` c44 « J'aime bien jouer aux Lego. » → « J'ai bien joué le goût ! » (1.2 s)
- `f5-synth_qwen_boy6` c37 « Oui. Samedi vers dix heures. » → « Samedi vers 10h. » (1.6 s)
- `f5-synth_qwen_boy6` r01 « Euh… je sais pas trop. » → « U, je ne sais pas trop. » (1.4 s)
- `f5-mls_f1` c13 « La télé était allumée. » → « L'aller était allumé. » (1.1 s)
- `f5-mls_f1` c14 « Le monsieur au blouson rouge est parti en courant. Mamie a téléphoné à quelqu'un. » → « Et puis ils ont partagé au blouson rouge et parti en courant m'a téléphoné à quelqu'un. » (3.6 s)
- `f5-mls_f1` c15 « C'était mon anniversaire, samedi. Il y avait mes copains Tom et Inès. » → « Et l'heure de 10 ans partagée, c'était mon annivers samedi et mes copains tôt vendredi. » (3.0 s)
- `f5-mls_f1` c20 « C'était un mercredi, il y avait pas école. Je faisais du toboggan. » → « Et la petite partagée, c'était un mercredi, j'y vais pas, je faisais du toboggan. » (2.8 s)
- `f5-mls_f1` c21 « Le monsieur a appelé la police. » → « Se rendez à appeler la police. » (1.3 s)
- `f5-mls_f1` c26 « Oui. C'était dimanche soir. » → « Cité dimanche soir » (1.2 s)
- `f5-mls_f2` c17 « C'était à la maison, dans la cuisine. » → « Les enfants du loup s'étaient à la maison dans la cuisine. » (2.5 s)
- `f5-mls_f2` c21 « Le monsieur a appelé la police. » → « Du loup, le monsieur appelait la police. » (2.0 s)
- `f5-mls_f2` c23 « On a mangé un gâteau au chocolat. » → « Pointe du Loup en a mangé un gâteau au chocolat. » (2.2 s)
- `f5-mls_f2` c37 « Oui. Samedi vers dix heures. » → « Sous-titrage Société Radio-Canada » (1.8 s)
- `f5-mls_f2` c44 « J'aime bien jouer aux Lego. » → « Kiloum, j'aime bien jouer au logo. » (1.7 s)
- `f5-mls_f2` c47 « C'était dimanche soir. Maman était partie travailler. » → « En disant foin du loup, c'était dimanche soir. Maman était partie travailler. » (3.5 s)
- `f5-synth_kokoro_child` c46 « Après on a mangé une pizza avec l'équipe. » → « Apprennent à manger une pizza avec l'équipe. » (2.4 s)
- `f5-synth_kokoro_child` r01 « Euh… je sais pas trop. » → « Hum, je ne sais pas trop. » (1.3 s)
- `fish-synth_qwen_boy6` c13 « La télé était allumée. » → « La télé a été allumée. » (1.7 s)
- `fish-synth_qwen_boy6` c35 « Jade a pleuré très fort. » → « J'ai déploré très fort. » (1.8 s)
- `higgs-synth_qwen_girl8` c41 « Dimanche on est allés au zoo. J'étais avec mon papi. J'ai vu une girafe qui mangeait des feuilles. » → « – Sous-titrage FR 2021 » (24.5 s)
- `higgs-synth_qwen_boy6` c42 « J'étais au parc avec ma mamie. C'était au parc à côté de l'école. » → « J'étais au parc avec ma mamie.  avec ma mamie. C'était au parc à » (32.3 s)
- `higgs-mls_f1` c14 « Le monsieur au blouson rouge est parti en courant. Mamie a téléphoné à quelqu'un. » → « Le monsieur au blouson rouge est parti en courant.  – Sous-titrage FR 2021  Sous-titrage FR ? » (81.6 s)
- `qwen-synth_qwen_boy6` c37 « Oui. Samedi vers dix heures. » → « Oui, samdi veldizo ! » (2.4 s)
- `xtts-synth_qwen_girl8` c13 « La télé était allumée. » → « Et à tes lignes que tu es allumée. » (2.2 s)
- `xtts-synth_qwen_girl8` c35 « Jade a pleuré très fort. » → « J'aide à pleurer très fort. » (2.7 s)
- `xtts-synth_qwen_girl8` c37 « Oui. Samedi vers dix heures. » → « Oui. Où ? Samedi vers 10h. » (3.3 s)
- `xtts-synth_qwen_girl8` r04 « Non. » → « Non, non. » (1.8 s)
- `xtts-synth_qwen_boy6` c04 « Non. » → « Non, qu'est-ce qu'il y a ? Qu'est-ce qu'il y a ? » (3.6 s)
- `xtts-synth_qwen_boy6` c26 « Oui. C'était dimanche soir. » → « Oui, oui. C'était dimanche soir. C'était dimanche soir. » (6.0 s)
- `xtts-synth_qwen_boy6` c37 « Oui. Samedi vers dix heures. » → « Oui, moi. Sandy, vers 10h. » (4.2 s)
- `xtts-mls_f1` c04 « Non. » → « Non. » (2.5 s)
- `xtts-mls_f1` c06 « dans l'escalier. » → « dans l'escalier » (7.9 s)
- `xtts-mls_f1` c16 « J'avais un bleu sur le bras. » → « j'avais un bleu sur le bras » (12.9 s)
- `xtts-mls_f1` c18 « Oui. C'était mardi après l'école, vers cinq heures. » → « Oui, un des ordonnances, monsieur Josh. C'était mardi après l'école. Vers cinq heures. » (9.3 s)
- `xtts-mls_f1` c20 « C'était un mercredi, il y avait pas école. Je faisais du toboggan. » → « C'était un mercredi. Il n'y avait pas école. Je faisais du toboggan. Je faisais du toboggan. » (17.6 s)
- `xtts-mls_f1` c26 « Oui. C'était dimanche soir. » → « Oui, c'était dimanche soir. C'était dimanche soir. » (7.8 s)
- `xtts-mls_f2` c33 « Oui. Il avait un couteau. » → « Oui. Oui. Il avait un couteau. Et sur le poignet, pas trop dessus. » (6.9 s)
- `xtts-mls_f2` r04 « Non. » → « Non. Je ne suis pas venu d'être ici. Au revoir. » (11.8 s)
- `xtts-cafe_04_neutre` c04 « Non. » → « Non, mais... » (1.8 s)
- `xtts-cafe_04_neutre` c12 « J'ai gagné à la pêche aux canards. » → « Et elle a l'air à la pêche au canard. » (3.0 s)
- `xtts-cafe_04_neutre` c26 « Oui. C'était dimanche soir. » → « Oui, car non, c'était dimanche soir. » (3.7 s)
- `xtts-cafe_04_neutre` c33 « Oui. Il avait un couteau. » → « Oui, moins clair l'air. Il avait un couteau. » (3.8 s)
- `xtts-cafe_04_neutre` c37 « Oui. Samedi vers dix heures. » → « Oui, oui. Samedi, vers 10h. » (4.2 s)
- `xtts-cafe_04_neutre` c47 « C'était dimanche soir. Maman était partie travailler. » → « C'était dimanche soir. Ouais, il y a des... Maman était partie travailler. » (6.0 s)
- `xtts-synth_kokoro_child` c04 « Non. » → « Maman, n'est-ce pas ? » (1.7 s)
- `xtts-synth_kokoro_child` c37 « Oui. Samedi vers dix heures. » → « Oui. Mouais. Samedi vers 10h. » (3.9 s)
- `xtts-cafe_04_tristesse` r04 « Non. » → « Non, ni... » (1.8 s)
- `chatterbox-clone-kchild` c05 « était là. » → « était là. » (3.5 s)
