# Évaluation de la chaîne vocale (diction, mensonge, voix, transcription)

*Généré par `experiments/voice_eval/report.py` le 2026-11-16 à partir de `experiments/voice_eval/results/`. Plan et seuils fixés avant les mesures ; voir aussi [ADR 0002](../adr/0002-mensonge-diction-voix.md).*

## Synthèse

| Niveau | Contrôles réussis | Échecs | Rapportés |
|---|---|---|---|
| N2 | 10 | 0 | 0 |
| N0 | 13 | 0 | 0 |
| N1-auto | 5 | 0 | 0 |
| N1 | — | — | non lancé |
| N4 | 15 | 0 | 3 |
| N3 transcription | 3 | 0 | 4 |
| N3 classifieur | 0 | 5 | 2 |
| Coût | 0 | 0 | 6 |

## Ce que l'évaluation a trouvé et corrigé

1. **Mensonge trahi par une réponse rapide (N2).** Un mensonge hésitait *moins* que la vérité sur le même fait
   (AUC 0,22). En cause, deux asymétries : la charge émotionnelle et la charge de récupération en mémoire venaient
   des faits *dits*. La version de couverture « je suis tombée dans l'escalier » n'en avait donc presque pas, alors
   que l'enfant parle du même événement douloureux. **Correction** : un mensonge porte la charge émotionnelle et de
   récupération du fait qu'il cache. Le poids du mensonge est ensuite **calibré sur les paires contrôlées** :
   - le poids initial de 0,5 donnait d ≈ 1,2 et une AUC de 0,81, soit un faux indice dans l'autre sens ;
   - le nouveau poids de 0,15 donne d ≈ 0,38 et une AUC de 0,61, l'ordre de grandeur des méta-analyses
     (Sporer & Schwandt, 2006).
2. **« euh » trop courts (N0).** 8 % des « euh » rendus par Kokoro duraient moins de 250 ms (jusqu'à 130 ms), plus
   proches d'un accroc que d'une hésitation. **Correction** : le worker Kokoro étire tout « euh » de moins de
   300 ms à environ 380 ms, hauteur conservée. 99,7 % passent désormais.
3. **Bruit pris pour de la parole (N4).** À 10 dB de rapport signal sur bruit, la détection par énergie prenait
   le bruit pour une prise de parole dès la première trame (erreur de 349 ms). **Correction** dans
   `Audio.voiced_bounds` : seuil relatif au niveau de bruit, plusieurs trames fortes consécutives exigées, et
   hystérésis pour les attaques douces. L'erreur tombe à 15 ms.
4. **Le point d'interrogation perdu (N3, non corrigé).** La transcription coûte au classifieur Δκ = 0,055 à 0,066
   sans bruit (seuil 0,05), 0,10 à 10 dB. Sur les 45 basculements, toutes conditions confondues :
   - 28 viennent d'un **« ? » perdu**. Une question fermée dite par l'intonation (« Il y avait un chien ? ») est
     transcrite comme une affirmation et devient suggestive ;
   - 7 viennent d'une autre ponctuation (« . » ↔ « , », qui transforme deux phrases en question composée) ;
   - seulement 10 viennent de mots mal reconnus, surtout à 10 et 5 dB (dont une hallucination de Whisper sur un
     « Hmm »).
   Le classifieur n'est donc pas gêné par les mots mais par la ponctuation, que Whisper déduit et que le
   classifieur prend pour un signal fiable. Pistes, à valider :
   - dire au classifieur que la ponctuation d'une transcription n'est pas fiable ;
   - rétablir le « ? » d'après la montée de F0 en fin d'énoncé ;
   - amorcer Whisper avec des questions (`initial_prompt`).
5. **Mesures elles-mêmes vérifiées.**
   - N0 : sur une vérité parfaite (voix `tone`), la segmentation retrouve tous les silences, à 4 ms près ; une
     diction cassée fait chuter le rappel des silences à 0,34.
   - N1 : des auditeurs simulés attentifs passent les contrôles, des auditeurs au hasard échouent.
   - N1 : le contrôle « mensonge au hasard » n'est valide que si les mêmes auditeurs perçoivent l'hésitation,
     car des auditeurs inattentifs sont eux aussi au hasard.

## N2 — Plausibilité du comportement simulé

≈ 3 000 réponses simulées (8 scénarios + 2 variantes de s08, 10 seeds, 3 styles d'interviewer), puis 802 **paires contrôlées mensonge/vérité** : même session, même question sur le même fait protégé, seule la volonté de cacher change.

| Métrique | Valeur | Cible | | Note |
|---|---|---|---|---|
| Silence initial moyen : bavardage < réponse < réticence (ms) | 649 < 1851 < 2089 | ordre respecté, p < 0,01 | ✅ | p = 1e-166 ; 1e-13 |
| Charge de récupération moyenne 4–6 > 7–9 > 10–12 | 0.35 > 0.27 > 0.17 | ordre respecté | ✅ |  |
| Mensonge vs vérité (paires contrôlées) : d de Cohen, silence initial | 0.315 | 0,1 ≤ d ≤ 0,5 | ✅ | 802 paires |
| AUC « détecteur de mensonge » sur le silence initial | 0.599 | 0,55 ≤ AUC ≤ 0,65 | ✅ |  |
| d de Cohen, tous indices audibles (silences + « euh ») | 0.382 | 0,1 ≤ d ≤ 0,5 | ✅ |  |
| AUC « détecteur de mensonge » sur tous les indices audibles | 0.611 | 0,55 ≤ AUC ≤ 0,65 | ✅ |  |
| Silence initial : médiane (ms) | 1.55e+03 | 500–2000 | ✅ |  |
| Silence initial : p95 (ms) | 2.51e+03 | < 5000 | ✅ |  |
| Part des mensonges (dont omissions) parmi les hésitations fortes (≥ 0,6) | 0.149 | < 0,40 | ✅ | 1330 hésitations fortes ; mensonge cause dominante : 2% |
| … dans les seuls scénarios avec mensonge (s08 et variantes) | 0.286 | < 0,40 | ✅ | 692 hésitations fortes |

## N0 — Fidélité du rendu : l'audio fait-il ce que la décision demande ?

456 réponses rendues avec Kokoro (échantillon stratifié par niveau d'hésitation) : leur plan d'élocution sert de vérité terrain. On y ajoute des rendus contrôlés (mêmes textes à plusieurs débits et volumes). Segmentation par énergie, audibilité jugée par Whisper large-v3, « euh » contrôlés par pYIN.

| Métrique | Valeur | Cible | | Note |
|---|---|---|---|---|
| Silence initial : erreur absolue moyenne (ms) | 15.6 | < 30 | ✅ | 456 réponses |
| Silence initial : erreur p95 (ms) | 20 | < 60 | ✅ |  |
| Rappel des silences planifiés (≥ 300 ms) | 1 | ≥ 0,95 | ✅ | 706 silences |
| Erreur de durée des silences retrouvés (ms) | 13 | < 50 | ✅ |  |
| Pauses non planifiées (≥ 300 ms) par réponse | 0.16 | < 0,2 | ✅ | 73 au total |
| Spearman ρ : hésitation décidée ↔ silence total mesuré | 0.9 | ≥ 0,8 | ✅ |  |
| « euh » voisés et de durée plausible (250–700 ms) | 0.997 | ≥ 0,95 | ✅ | 325 « euh », tous voisés ; 0 trop courts (min 331 ms) ; contrôle acoustique, pas perceptif |
| Audibilité des unités (ancres retrouvées par Whisper) | 0.978 | ≥ 0,95 | ✅ | 415 unités |
| Déterminisme (même réponse → même audio) | 1 | 1 | ✅ |  |
| Débit : erreur relative de durée vs 1/débit (textes identiques) | 0.0175 | < 0,05 | ✅ |  |
| Débit : Spearman ρ (débit demandé ↔ vitesse mesurée) | 0.961 | ≥ 0,7 | ✅ |  |
| Volume « bas » vs normal (dB) | -4.41 | −4,4 ± 1 | ✅ |  |
| Volume « chuchoté » vs normal (dB) | -8.94 | −9,1 ± 1 | ✅ |  |

## N1-auto — Indicateurs objectifs de fluidité (proxy de la perception)

Indicateurs connus pour prédire la fluidité perçue (Cucchiarini, Strik & Boves, 2002, *JASA* 111(6)), mesurés dans la réponse (silence initial exclu) sur les réponses d'au moins 8 mots, où des pauses internes sont possibles. **Proxy, pas preuve perceptive.**

| Métrique | Valeur | Cible | | Note |
|---|---|---|---|---|
| Débit (syllabes/s, pauses comprises) ↔ hésitation | -0.848 | ρ ≤ −0,7 | ✅ | 135 réponses ≥ 8 mots ; toutes (358) : ρ = -0.71 |
| Longueur moyenne des segments de parole ↔ hésitation | -0.659 | ρ ≤ −0,6 | ✅ | 135 réponses ≥ 8 mots ; toutes (358) : ρ = -0.26 |
| Proportion de temps de parole ↔ hésitation | -0.812 | ρ ≤ −0,7 | ✅ | 135 réponses ≥ 8 mots ; toutes (358) : ρ = -0.50 |
| Pauses silencieuses par minute ↔ hésitation | 0.632 | ρ > 0 | ✅ | 135 réponses ≥ 8 mots ; toutes (358) : ρ = 0.33 |
| « euh » par minute ↔ hésitation | 0.292 | ρ > 0 | ✅ | 135 réponses ≥ 8 mots ; toutes (358) : ρ = 0.26 |

## N1 — Test d'écoute à l'aveugle

Lot préparé (`experiments/voice_eval/listening/`), **pas encore lancé** : aucun auditeur pour l'instant.

*Pas encore de résultats.*

## N4 — Tours de parole et interruptions

≈ 430 échanges à vérité terrain connue (silence de tête exact, voix adulte Kokoro), `after_ms` tiré dans [−6 s ; +3 s], sans bruit et avec bruit blanc à 20, 10 et 5 dB de rapport signal sur bruit.

| Métrique | Valeur | Cible | | Note |
|---|---|---|---|---|
| Erreur sur l'instant de prise de parole, propre (ms, moyenne) | 7.26 | < 50 | ✅ | p95 = 16 ms ; 108 échanges |
| Moment de l'interruption bien classé (aucune / silence initial / pause / phrase), propre | 1 | ≥ 0,95 | ✅ |  |
| Unités non dites : précision / rappel, propre | 1.00 / 1.00 | ≥ 0,95 / ≥ 0,95 | ✅ | 50 unités coupées |
| Énoncés non entendus (rejetés), propre | 0 | 0 | ✅ |  |
| Erreur sur l'instant de prise de parole, 20 dB (ms, moyenne) | 5.62 | < 50 | ✅ | p95 = 15 ms ; 108 échanges |
| Moment de l'interruption bien classé (aucune / silence initial / pause / phrase), 20 dB | 1 | ≥ 0,95 | ✅ |  |
| Unités non dites : précision / rappel, 20 dB | 1.00 / 1.00 | ≥ 0,95 / ≥ 0,95 | ✅ | 46 unités coupées |
| Énoncés non entendus (rejetés), 20 dB | 0 | 0 | ✅ |  |
| Erreur sur l'instant de prise de parole, 10 dB (ms, moyenne) | 14.5 | < 100 | ✅ | p95 = 47 ms ; 108 échanges |
| Moment de l'interruption bien classé (aucune / silence initial / pause / phrase), 10 dB | 1 | ≥ 0,95 | ✅ |  |
| Unités non dites : précision / rappel, 10 dB | 1.00 / 1.00 | ≥ 0,95 / ≥ 0,95 | ✅ | 45 unités coupées |
| Énoncés non entendus (rejetés), 10 dB | 0 | 0 | ✅ |  |
| Erreur sur l'instant de prise de parole, 5 dB (ms, moyenne) | 48.5 | rapporté | — | p95 = 116 ms ; 108 échanges |
| Moment de l'interruption bien classé (aucune / silence initial / pause / phrase), 5 dB | 0.972 | rapporté | — |  |
| Unités non dites : précision / rappel, 5 dB | 1.00 / 0.97 | rapporté | — | 38 unités coupées |
| Énoncés non entendus (rejetés), 5 dB | 0 | 0 | ✅ |  |
| Faux positifs : enregistrements sans parole pris pour un énoncé | 0 | < 0,02 | ✅ | silence et bruit blanc à −50, −40, −30 dBFS |
| Cohérence texte/voix sans interruption (décisions et rappel identiques) | 1 | 1 | ✅ | 104 comparaisons |

## N3 — Transcription de l'interviewer (pilote synthétique)

Les 104 énoncés du jeu de test du skill, dits par 3 pseudo-locuteurs tirés de la seule voix française de Kokoro (hauteur et débit variés). **Optimiste** : de vraies voix seront plus difficiles.

| Métrique | Valeur | Cible | | Note |
|---|---|---|---|---|
| WER, locuteur « grave-lent », sans bruit | 0.0389 | < 0,10 | ✅ | énoncés ≤ 3 mots : 16.7% ; synthétique, optimiste |
| WER, locuteur « moyen », sans bruit | 0.045 | < 0,10 | ✅ | énoncés ≤ 3 mots : 41.7% ; synthétique, optimiste |
| WER, locuteur « aigu-rapide », sans bruit | 0.0399 | < 0,10 | ✅ | énoncés ≤ 3 mots : 16.7% ; synthétique, optimiste |
| WER, locuteur « moyen », 20 dB | 0.0512 | rapporté | — | énoncés ≤ 3 mots : 66.7% |
| WER, locuteur « moyen », 10 dB | 0.0542 | rapporté | — | énoncés ≤ 3 mots : 66.7% |
| WER, locuteur « moyen », 5 dB | 0.0645 | rapporté | — | énoncés ≤ 3 mots : 116.7% |
| Noms propres correctement transcrits (sans bruit) | 0.844 | rapporté | — | 96 occurrences |

## N3 — Ce que la transcription coûte au classifieur

Même classifieur et mêmes réglages qu'en production (LLM, réflexion par défaut), sur le texte d'origine puis sur les transcriptions.

| Métrique | Valeur | Cible | | Note |
|---|---|---|---|---|
| κ du classifieur sur le texte d'origine (référence) | 0.978 | rapporté | — | qwen3.8:latest, réflexion medium |
| Δκ texte → transcription, « grave-lent » | 0.0548 | ≤ 0,05 | ❌ | κ = 0.923 ; 5 énoncé(s) basculé(s) en erreur ; synthétique |
| Δκ texte → transcription, « moyen » | 0.0656 | ≤ 0,05 | ❌ | κ = 0.912 ; 6 énoncé(s) basculé(s) en erreur ; synthétique |
| Δκ texte → transcription, « aigu-rapide » | 0.0656 | ≤ 0,05 | ❌ | κ = 0.912 ; 6 énoncé(s) basculé(s) en erreur ; synthétique |
| Δκ texte → transcription, « moyen », 20 dB | 0.0873 | ≤ 0,05 | ❌ | κ = 0.891 ; 8 énoncé(s) basculé(s) en erreur ; synthétique |
| Δκ texte → transcription, « moyen », 10 dB | 0.0986 | ≤ 0,05 | ❌ | κ = 0.879 ; 9 énoncé(s) basculé(s) en erreur ; synthétique |
| Δκ texte → transcription, « moyen », 5 dB | 0.12 | rapporté | — | κ = 0.858 ; 11 énoncé(s) basculé(s) en erreur ; synthétique |

## Coût (rapporté seulement)

Latences mesurées sur la station (2 × TITAN RTX), sans autre charge GPU.

| Métrique | Valeur | Cible | | Note |
|---|---|---|---|---|
| Latence, synthèse (Kokoro, réponse entière) | p50 0.17 s, p95 0.48 s | rapporté | — | 20 mesures |
| Latence, transcription (Whisper large-v3) | p50 0.50 s, p95 0.68 s | rapporté | — | 20 mesures |
| Latence, classification (qwen3.8:latest, réflexion medium) | p50 10.69 s, p95 33.64 s | rapporté | — | 10 mesures |
| Latence, réalisation (qwen3.8:latest) | p50 2.20 s, p95 2.72 s | rapporté | — | 10 mesures |
| Tour vocal complet (somme des médianes, hors silence simulé) | 13.6 s | rapporté | — | optimisation prévue plus tard |
| Mémoire GPU des modèles vocaux (Kokoro + Whisper) | 4.3 Go | rapporté | — |  |

## Limites

- **Pas encore de perception humaine.** N1-auto est un proxy. Le test d'écoute (78 extraits, environ 30 minutes
  par auditeur) est prêt mais n'a pas été passé.
- **Transcription mesurée sur voix synthétique.** Les résultats sont optimistes. Les énoncés très courts (relances
  NICHD : « Et après ? », « Hmm hmm ») sont le point faible, en partie parce que Kokoro dit mal « hmm ».
- **Une seule voix française** dans Kokoro (`ff_siwis`). La voix d'enfant en est dérivée (hauteur et formants × 1,25).
- **Prosodie des questions synthétique.** L'intonation montante de Kokoro sur les questions fermées n'est pas
  celle d'un interviewer réel. La part des « ? » perdus est à remesurer sur de vraies voix.
- **Paramètres estimés.** Le poids du mensonge est calibré sur un ordre de grandeur de la littérature (adultes,
  méta-analyses), pas sur des données d'enfants en audition.

## Rejouer

```bash
uv run python experiments/voice_eval/n2_plausibility.py         # N2 (sans audio, ~1 min)
uv run python experiments/voice_eval/make_corpus.py             # corpus N0 (Kokoro, ~1 min)
experiments/voice_eval/run_voice_env.sh n0_fidelity.py          # N0 + N1-auto (~2 min)
experiments/voice_eval/run_voice_env.sh n0_sanity.py            # contrôle des mesures N0
uv run python experiments/voice_eval/n4_turn_taking.py          # N4 (~5 min)
uv run python experiments/voice_eval/n3_stt.py                  # N3 transcription (~5 min)
uv run python experiments/voice_eval/n3_classifier.py           # N3 classifieur (~2 h, LLM)
uv run python experiments/voice_eval/cost.py                    # coût
uv run python experiments/voice_eval/report.py                  # ce rapport
```
