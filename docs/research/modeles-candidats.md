# Modèles candidats pour la voix de l'enfant

*16 novembre 2026. Sources : bibliothèque Ollama (ollama.com/library, consultée le 16/11/2026) et Hugging Face. Liste exécutable : `experiments/models/candidates.yaml`. Pipeline : `experiments/models/README.md`.*

## Contraintes

- **Local, open source, via Ollama** : modèles de la bibliothèque Ollama ou fichiers GGUF de Hugging Face (`ollama pull hf.co/<dépôt>`).
- **2 × TITAN RTX, 48 Go de VRAM** : en Q4_K_M, jusqu'à ~35 B entièrement sur GPU avec notre contexte (32 k jetons). Un 70 B (~43 Go) passe à condition de réduire le contexte (`num_ctx` 8 k). Au-delà (MoE de plus de 100 B, `mistral-large`, `deepseek-v4`, `kimi`, `glm-5.x`…) : hors de portée.
- **Usage** : réaliser en français oral d'enfant des décisions prises par le moteur, en obéissant strictement à la consigne (ne rien ajouter, ne rien contredire). Les critères qui comptent :
  1. **obéissance à la consigne de mise en mots**, mesurée par le taux de repli sur gabarit (2 % pour `qwen3.8` et `gemma4`, 12 % pour `phi4` et `mistral` 7B dans l'ablation v2) ;
  2. **naturel du français oral** (registre d'enfant, pas de tournures traduites de l'anglais) ;
  3. **diversité des familles**, pour l'argument de robustesse dans une publication ;
  4. **latence** raisonnable (moins de 3 s par tour en moyenne).

## Exclus

- **Modèles pour le code** (`qwen3-coder`, `devstral`, `codestral`, `flint`, `ripple-preview`…) : hors sujet.
- **Modèles orientés agents et appels d'outils** (`granite4.x`, `lfm2.5`, `muse-glimmer`, `nemotron-*-lightning`, `laguna-*`) : optimisés pour l'appel d'outils, pas pour une voix de personnage.
- **Modèles de raisonnement purs** (`deepseek-r1`, `phi4-reasoning`, `magistral`, `qwq`) : latence élevée pour des réponses de quelques mots, sans bénéfice attendu sur une mise en mots contrainte.
- **Petits modèles (< 4 B)** : trop faibles pour respecter la consigne. Le repli observé croît déjà fortement sous 10 B.
- **`ornith:35b`** (déjà installé) : présenté comme orienté code et agents.

## Candidats

| Prio. | Modèle | Famille | ~Go | Pourquoi |
|---|---|---|---|---|
| réf. | `qwen3.8`, `phi4`, `gemma4`, `mistral` | — | — | Déjà dans l'ablation v2. |
| 1 | `mistral-small3.2:24b` | Mistral | 15 | Laboratoire français : a priori le meilleur français oral de cette taille, et un bon suivi de consigne. Remplacerait `mistral` 7B. |
| 1 | `gemma4:31b` | Gemma | 20 | Effet de la taille dans une famille déjà testée. |
| 1 | `gpt-oss:20b` | gpt-oss | 14 | Nouvelle famille (OpenAI). Réflexion impossible à couper : niveau `low`. Français probablement moins naturel. |
| 1 | `olmo-3.1:32b` | OLMo | 20 | Entièrement ouvert, y compris les données d'entraînement : argument de reproductibilité. |
| 2 | `aya-expanse:32b` | Aya | 20 | Multilingue de Cohere, conçu pour les langues autres que l'anglais. |
| 2 | `mistral-nemo:12b` | Mistral | 7 | Taille intermédiaire, bon en français, rapide. |
| 2 | `qwen3.6:27b` | Qwen | 17 | Version précédente du modèle par défaut : sensibilité à la version. |
| 2 | `llama3.3:70b` | Llama | 43 | Le plus gros possible ici (contexte réduit à 8 k) : un témoin 100 % LLM plus fort tient-il la réticence ? Lent (3 à 4 h). |
| 3 | `hf.co/OpenLLM-France/Lucie-7B-Instruct-v1.1-gguf` | Lucie | 5 | Modèle francophone (OpenLLM-France / Linagora), entraîné majoritairement sur du français. GGUF officiel. |
| 3 | `hf.co/jpacifico/Chocolatine-2-14B-Instruct-v2.0.3-Q4_K_M-GGUF` | Chocolatine | 9 | Réglage fin français, publié par son auteur, bien classé sur les classements francophones. |
| 3 | `hf.co/mradermacher/Claire-Mistral-7B-0.1-GGUF:Q4_K_M` | Claire | 4 | Entraîné sur des transcriptions de conversations orales en français : registre oral. Non instruit, il risque d'ignorer la consigne. |

**Vérifications (16/11/2026)** : les tags Ollama de `mistral-small3.2:24b`, `gemma4:31b`, `olmo-3.1:32b-instruct` et `qwen3.6:27b` existent. Pour OLMo, la variante `-instruct` est préférée à la variante `-think`. Les trois dépôts Hugging Face existent et contiennent un fichier Q4_K_M. Le `gemma4:latest` de l'ablation v2 est la variante E4B (8 B paramètres, 4 B effectifs). Les descriptions des modèles postérieurs à mi-2026 viennent des fiches ollama.com.

**Hugging Face, côté francophone** : une recherche des GGUF « french » triés par téléchargements renvoie surtout des réglages fins anciens ou petits. On y trouve French-Alpaca (Llama 3 8B, Mistral 7B, Phi-3), des variantes françaises de Llama 2 13B et de Llama 3.2 3B, French-Aya-Expanse-8B, ainsi que des modèles de traduction ou de synthèse vocale. Aucun ne dépasse les modèles généralistes récents de la liste. On ne garde que Lucie, Chocolatine et Claire, qui ont une raison d'être propre.

## Protocole

1. **Tri rapide** (`screen.py`, ~5 min par modèle) : tient-il entièrement en mémoire GPU ? Puis 7 entretiens hybrides, avec le taux de repli, les motifs de rejet du filtre, la latence, les sorties de rôle et les mots anglais. On élimine les modèles qui replient sur plus de ~10 % des tours ou qui ne tiennent pas sur le GPU.
2. **Ablation complète** (3 conditions × 7 scénarios × 3 graines) sur les modèles retenus. Durée estimée : 30 à 70 min par modèle de 20–32 B.
3. **Jugement humain du naturel du français** : les métriques automatiques ne le mesurent pas. Un échantillon de réponses par modèle, à comparer en aveugle, servira à choisir le modèle par défaut et préparera l'évaluation par des formateurs NICHD.
