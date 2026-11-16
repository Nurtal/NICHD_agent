# Évaluation de la chaîne vocale

Plan et seuils fixés **avant** les mesures. Rapport généré : [docs/evaluations/voix.md](../../docs/evaluations/voix.md).

| Niveau | Question | Script | Environnement |
|---|---|---|---|
| N2 | Le comportement simulé est-il plausible ? L'hésitation trahit-elle le mensonge (elle ne doit le faire que faiblement) ? | `n2_plausibility.py` (+ `lie_pairs.py`) | projet |
| N0 | L'audio fait-il ce que la décision demande (silences, débit, volume, « euh », audibilité) ? | `make_corpus.py` puis `n0_fidelity.py` | projet puis voix |
| N1-auto | Les indicateurs objectifs de fluidité suivent-ils l'hésitation ? | `n0_fidelity.py` | voix |
| N1 | Un humain entend-il l'hésitation, et pas le mensonge ? | `listening/` | projet + navigateur |
| N4 | Les interruptions sont-elles détectées et l'enfant repris correctement, même avec du bruit ? | `n4_turn_taking.py` | projet |
| N3 | Que coûte la transcription au classifieur ? | `n3_stt.py` puis `n3_classifier.py` | projet |
| Coût | Latence par étape, mémoire | `cost.py` | projet |

- **Environnement projet** : `uv run python experiments/voice_eval/<script>`.
- **Environnement voix** (numpy, librosa, faster-whisper) : `experiments/voice_eval/run_voice_env.sh <script>`.
  Installation : [experiments/voices/README.md](../voices/README.md).
- Résultats bruts : `results/*.json` ; audio non versionné.
- Les mesures elles-mêmes sont vérifiées : `n0_sanity.py` (vérité parfaite, diction cassée) et
  `listening/simulate_ratings.py` (auditeurs simulés attentifs ou au hasard).

## Test d'écoute (N1) — quand des auditeurs seront disponibles

```bash
uv run python experiments/voice_eval/listening/build_pack.py   # (re)construit le lot (78 extraits, ~30 min par auditeur)
cd experiments/voice_eval/listening && python3 -m http.server 8600 --bind 127.0.0.1
# depuis votre poste : ssh -L 8600:127.0.0.1:8600 <station>, puis http://localhost:8600/rate.html
# chaque auditeur télécharge ecoute_<id>.json → à déposer dans listening/ratings/
uv run python experiments/voice_eval/listening/analyze.py
```

La page ne charge que `pack/tasks.json`, qui ne contient ni l'hésitation décidée, ni la cause, ni le mensonge :
la vérité (`pack/design.json`) ne sert qu'à l'analyse. L'ordre des extraits est tiré au hasard pour chaque auditeur.

## Voix réelles (N3) — plus tard

Déposer `recordings/ts001.wav … ts104.wav` (les énoncés de `src/nichd_sim/skill/testset.jsonl` lus à voix haute),
puis relancer `n3_stt.py` et `n3_classifier.py --conditions réel:None`. Un locuteur « réel » s'ajoute alors aux
pseudo-locuteurs synthétiques.
