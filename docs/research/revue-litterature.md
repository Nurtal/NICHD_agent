# Revue de littérature : simulateurs d'enfants pour l'entraînement aux auditions selon le protocole NICHD

*Date de la recherche : 13 novembre 2026. Les sources ont été consultées via les pages éditeurs, Crossref, OpenAlex, Europe PMC/PubMed Central, arXiv et ACL Anthology. Sauf mention « (non vérifié) », chaque chiffre provient du résumé ou du texte intégral de la source primaire.*

---

## 1. Résumé

- **Les avatars algorithmiques sont bien établis.** Le groupe Santtila / Pompedda / Haginoya ([« Avatar Training »](#q1)) publie depuis 2014 environ 15 études : avatars de 4 et 6 ans, mémoires prédéfinies, règles probabilistes de suggestibilité, retour sur le type de question et sur l'exactitude de la conclusion. Une méga-analyse (N = 394, 2 208 entretiens) montre un effet robuste du feedback. Deux études montrent un transfert vers de vrais entretiens, une autre un maintien à 4 et 6 mois.
- **Les enfants pilotés par un LLM existent aussi depuis 2022 (SimulaMet / OsloMet).** Ces systèmes reposent sur GPT-3 affiné sur des entretiens simulés. Ni la suggestibilité ni la cohérence n'y sont modélisées explicitement, et le réalisme est évalué surtout par questionnaires de QoE. Défauts documentés : l'avatar répond aussi longuement aux questions « Te souviens-tu… ? » qu'aux invitations ouvertes, et la langue générée est trop avancée pour l'âge simulé.
- **La classification automatique des questions est mature en anglais :** RoBERTa, κ = 0,93–0,97 sur environ 350 000 questions réelles. Nous n'avons **trouvé aucun classifieur publié pour le français**, ni aucun suivi automatique des phases du protocole.
- **Ce que nous apportons :** un **découplage explicite** entre un moteur de comportement déterministe calibré sur la littérature et la seule réalisation linguistique par un LLM local. Cela rend mesurable la contamination face à une vérité terrain. Le travail le plus proche est un agent BDI + LLM pour former les écoutants d'une ligne d'aide à l'enfance (IVA 2025), qui ne vise ni les auditions judiciaires ni la suggestibilité. Le reste de l'apport tient au français, au déploiement local et à la séparation entre phases et métriques.
- **L'angle de publication le plus défendable :** démontrer la **fidélité comportementale**, c'est-à-dire reproduire les relations empiriques entre type de question, exactitude et contamination, ce que les avatars LLM purs ne font pas. Il faut aussi une validation externe du classifieur : notre κ = 0,978 est mesuré sur 104 énoncés que nous avons écrits nous-mêmes.

---

<a id="q1"></a>
## 2. Question 1 : entraînement avec des avatars d'enfants simulés

### 2.1 Comment l'avatar décide de ses réponses

**Avatar Training (Åbo Akademi / Turku, Gloucestershire, Meiji Gakuin, NYU Shanghai)**

- **Jeu de cas.** 16 avatars répartis à parts égales selon l'âge (4 ou 6 ans), la vérité terrain (abus ou non) et l'émotion affichée (pleurs ou non). Chaque avatar a une « mémoire » prédéfinie qui contient des détails pertinents (l'abus ou une explication alternative) et des détails neutres.
- **Version initiale, avec opérateur humain.** Un opérateur classe chaque question en temps réel. Ce code déclenche un algorithme propre à chaque âge, fondé sur la recherche sur la mémoire et la suggestibilité, qui sélectionne un **clip vidéo préenregistré** (Pompedda et al., 2022, méga-analyse).
  - Exemple de règle décrit : si la question porte sur un détail absent de la mémoire, l'avatar répond « Non ». Si la question est répétée, l'avatar de 4 ans passe à « Oui » avec une **probabilité de 0,50**.
  - Les questions à choix multiples sur un détail absent amènent « parfois » l'enfant à choisir une option (Pompedda et al., 2017). La probabilité exacte n'est pas publiée.
- **Validation des algorithmes par corrélations** (méga-analyse) :
  - questions recommandées et détails pertinents : r = 0,79 ;
  - questions non recommandées et détails erronés : r = 0,57 ;
  - questions recommandées et conclusion correcte : r = 0,36.
- **Version automatisée « AI Avatar » (Haginoya et al., 2023).** Ce n'est **pas un modèle génératif**. La question est classée automatiquement, puis une réponse prédéfinie est sélectionnée.
  - Chaque avatar a 9 détails pertinents, révélés un par un dans un ordre fixe.
  - Seules les questions recommandées peuvent faire émerger un détail : **probabilité de 20 % par question à 4 ans et de 25 % à 6 ans**.
  - Les détails erronés naissent des questions non recommandées qui contredisent la mémoire.
  - Des mots-clés thématiques (par exemple « papa ») déclenchent des réponses spécifiques.
- **Typologie de codage** (méga-analyse, tableau 2) :
  - questions recommandées : facilitateurs, invitations, directives ;
  - questions non recommandées : option-posing, suggestives spécifiques et non spécifiques, répétitions, questions trop longues ou peu claires, questions de fantaisie.

**LiveSim (Université Griffith, M. Powell)** : l'apprenant **choisit une question dans un arbre d'options**, et l'avatar répond avec le niveau de détail correspondant au type de question. Une analyse d'usage porte sur 606 professionnels formés entre 2009 et 2018 (Røed, Powell et al., 2023, *Child Abuse & Neglect*). Voir aussi Powell, Guadagno et Benson (2014) pour les activités d'apprentissage sur ordinateur.

### 2.2 Études et résultats

| Référence | Dispositif / protocole | N | Résultat principal |
|---|---|---|---|
| Pompedda, Zappalà & Santtila (2015), *Psychol. Crime & Law* | 4 avatars ; feedback (type de question + conclusion) contre aucun | 21 étudiants | Le groupe avec feedback pose plus de questions ouvertes, trouve plus de détails corrects et tire plus de conclusions correctes dans les deux derniers entretiens, après environ 1 h de formation |
| Pompedda, Antfolk, Zappalà & Santtila (2017), *Front. Psychol.* | 4 conditions : contrôle, feedback de résultat, feedback de processus, feedback combiné | 48 | Le feedback combiné est le plus efficace sur les questions recommandées. Conclusions correctes : 29 % (combiné) contre 17 % (contrôle), différence non significative avec le contrôle seul |
| Krause et al. (2017), *Appl. Cogn. Psychol.* | 8 entretiens ; contrôle, feedback, feedback + réflexion | 59 | Effet du feedback confirmé ; la réflexion n'ajoute rien |
| Haginoya et al. (2020), *Front. Psychol.* | 6 entretiens en ligne, Japon | 32 | Questions recommandées : 45 % → 65 % avec feedback, contre 43 % → 42 % en contrôle ; 7 participants sur 17 montrent un changement fiable |
| Haginoya, Yamamoto & Santtila (2021), *Child Abuse & Neglect* | Feedback, modélisation (vidéos de bonnes et mauvaises pratiques), ou les deux | 32 psychologues cliniciens | La combinaison feedback + modélisation fait mieux que le feedback seul dès le 2ᵉ entretien |
| Pompedda et al. (2020), *Nordic Psychology* | Entraînement sur avatars, puis **entretiens avec de vrais enfants de 4–6 ans** ayant vu un événement mis en scène | 40 psychologues + 69 étudiants (76 + 116 entretiens d'enfants) | Transfert : plus de questions recommandées ; plus de détails corrects dans l'étude I |
| Kask et al. (2022), *Front. Psychol.* | Policiers estoniens ; **transcriptions d'auditions réelles** avant et après | 22 recrutés (17 analysés) ; 36 enfants | Proportion de questions recommandées en audition réelle : 0,48 → 0,59 ; questions suggestives −71 % ; pas d'effet sur la révélation |
| **Pompedda, Zhang, Haginoya & Santtila (2022), méga-analyse**, *J. Police Crim. Psychol.* | Données brutes de 9 études ; modèles mixtes | 394 participants, 2 208 entretiens | Effets robustes du feedback × tour sur les questions recommandées (B = 2,03), les détails et les conclusions (OR = 1,39 par tour). Modélisation : OR = 5,05 sur la conclusion. Changement fiable chez 22,6 % (4 tours) à 80 % (8 tours) des participants |
| Zhang et al. (2023), *PLOS ONE* | Feedback × formulation d'hypothèses, Chine | 81 étudiants | Le feedback améliore la qualité ; la formulation d'hypothèses seule augmente les questions non recommandées |
| Haginoya et al. (2023), *Front. Psychol.* | **AI Avatar entièrement automatisé** (classifieur + réponses), 2 entretiens | 42 professionnels | Les groupes feedback et modélisation s'améliorent, pas le contrôle (interaction F(10,70) = 2,72, p = 0,007) |
| Segal et al. (2022/2024), *Psychol. Crime & Law* 30 | Réactions émotionnelles et réalisme perçu face aux avatars (abus confirmé contre infirmé) | 30 | Plus d'émotions négatives quand l'abus est confirmé ; l'effet est plus fort quand l'avatar est perçu comme plus réel |
| Haginoya et al. (2025), *Child Protection and Practice* | 28 combinaisons de composantes de modélisation, en crowdsourcing | 1 168 non-spécialistes | Les vidéos de bonnes pratiques aident ; **les vidéos de mauvaises pratiques nuisent** ; les points d'apprentissage et les issues de cas ont peu d'effet |
| Pompedda, Segal et al. (2025), *Appl. Cogn. Psychol.* | Avatars, puis répétition à 4 mois | 31 travailleurs de la protection de l'enfance + 35 étudiants | Pas de déclin substantiel à 4 mois ; l'expérience professionnelle ne modère pas l'effet |
| Haginoya, Sun & Santtila (2025), *Behav. Sci. & Law* | AI Avatar ; rappels à 6 mois, ou à 1 et 6 mois | **478 policiers** | Gain initial sur les questions recommandées et les détails pertinents ; le double rappel maintient mieux les acquis |

**Points clés pour nous**

1. Le **feedback combiné (processus + résultat)** est l'ingrédient actif, et la vérité terrain connue est ce qui le rend possible. C'est exactement notre « score de contamination ».
2. Le **transfert vers de vrais entretiens** est démontré, mais sur de petits effectifs. Les études réunissant N > 400 sont récentes (2025).
3. La **modélisation** (exemples vidéo) renforce l'effet du feedback, alors que les mauvais exemples sont contre-productifs. C'est une implication de conception directe pour un retour qui montrerait des « contre-exemples ».
4. Toutes ces études portent sur des avatars de **4–6 ans**. Nous n'avons trouvé aucune étude publiée sur des avatars de 7–12 ans dans ce paradigme (non trouvé, ce qui ne prouve pas leur absence).

### 2.3 Revues et synthèses

- La **méga-analyse** de Pompedda et al. (2022) est la synthèse quantitative de référence.
- L'**éditorial** de Kask, Baugerud et Volbert (2024, *Frontiers in Psychology*, 15) introduit un numéro thématique « Technological solutions helping to train specialists' interviewing skills ».
- Le **livre blanc de l'European Association of Psychology and Law** (Korkman et al., 2024, *Psychol. Crime & Law*) recommande une formation spécialisée et un feedback continu.
- Lamb et al. (2007) et La Rooy et al. (2015) passent en revue le protocole NICHD et sa diffusion internationale.

---

<a id="q2"></a>
## 3. Question 2 : enfants simulés pilotés par des LLM (2022–2026)

### 3.1 SimulaMet / OsloMet / UiT (Hassan, Salehi, Riegler, Baugerud, Røed, Halvorsen, Johnson, Lison)

| Référence | Architecture | N | Résultats / évaluation |
|---|---|---|---|
| Hassan et al. (2022), ACM IMX workshop ([10.1145/3534085.3534340](https://doi.org/10.1145/3534085.3534340)) | Prototype VR : modèles de dialogue, avatar parlant | Personnels de la protection de l'enfance | Étude de QoE et d'apprentissage ; prototype bien reçu |
| Salehi et al. (2022), *BDCC* 6(2):62 | Comparaison de composants : langue, voix, émotion, visuel | 3 études subjectives | L'architecture est affinée au fil des études ; le réalisme est jugé important par les experts |
| Hassan et al. (2022), IEEE ISM ; Hassan et al. (2023), *Sci. Rep.* 13:20403 | Dialogue construit avec **RASA**, entraîné sur des entretiens simulés selon la méthode DCM norvégienne ; classifieur **GPT-3 davinci affiné** ; 4 interfaces (VR, 2D, audio, texte) | 21 | Classifieur : 87 % d'exactitude équilibrée (ouvertes contre fermées). VR jugée la plus réaliste (76 %). **Le modèle de dialogue lui-même n'a pas été évalué** |
| Røed et al. (2023), *Front. Psychol.* | **GPT-3 davinci affiné** sur des transcriptions de 700 entretiens simulés (Griffith) ; cas « Lisa », 6 ans, violence physique | 30 étudiants (12 avec feedback / 18 sans) | Questions ouvertes : 0,5 → 4,3 (séance 3) dans le groupe avec feedback. **Aucun mécanisme dédié à la cohérence ou à la suggestibilité** : la réactivité vient uniquement des données d'entraînement. Cohérence perçue d'environ 3,4 sur 5 |
| Baugerud et al. (2024), *Child Maltreatment* 30(2) | GPT-3 affiné (741 entretiens simulés), VR, centres d'appui aux enfants aux États-Unis | 68 professionnels | L'avatar répond « comme les enfants » à la plupart des types de questions, **mais il est presque aussi prolixe aux questions « Do you know/remember » qu'aux invitations**. Un réglage plus fin de la productivité est nécessaire. Le cas d'abus sexuel est plus prolixe que le cas de violence physique |
| Salehi et al. (2024), MMVE '24 ; Salehi et al. (2024), *IEEE Access* 12 | GPT-3 affiné intégré dans Unity, 2D contre 3D | 36 (MMVE) | La 3D améliore la présence, la fidélité et l'empathie ; la 2D est plus utilisable. La **pertinence et le détail des réponses** influencent plus l'empathie que la fidélité visuelle |
| Ko et al. (2025), *Appl. Cogn. Psychol.* | GPT-3 + one-shot prompting, fillette de 8 ans | 18 professionnels dentaires et médicaux | **Aucune amélioration significative**, avec ou sans feedback direct |
| Brubacher et al. (2025), *Appl. Cogn. Psychol.* | Entretiens qualitatifs après 10 min avec le chatbot | 28 formateurs et experts | Appréciation de l'autonomie et du feedback. Inquiétudes : le chatbot doit simuler les objectifs pédagogiques et offrir un retour nuancé |
| Salehi et al. (2025), *Nordic Machine Intelligence* 5(1) | MetaHuman + Audio2Face | 70 | La congruence entre voix et visage conditionne le réalisme perçu ; la voix TTS d'adulte est un facteur confondant |
| Hassan, Halvorsen, Johnson & Lison (2025), arXiv:2510.24250 | 5 LLM (GPT-4, NorMistral, NorBLOOM…), norvégien, enfants de 5 et 9 ans ; évaluation à l'aveugle face à de vraies transcriptions | 11 professionnels de l'éducation | ICC = 0,75 ; **la plupart des modèles produisent une langue plus avancée que l'âge cible** ; GPT-4 et NorBLOOM-7b s'en sortent relativement bien |

**Cohérence, suggestibilité et contrôle du contenu dans ces travaux.** Aucun article SimulaMet consulté ne décrit de module explicite de suggestibilité, de mémoire de référence ou de filtre de contenu. Le comportement « réaliste » est attendu de l'affinage sur des entretiens simulés où un adulte jouait l'enfant. Le réalisme est mesuré par questionnaires de QoE et de présence, et à l'aveugle par des experts (Hassan et al., 2025).

### 3.2 Groupe Santtila / Haginoya / Järvilehto : les LLM comme interviewers, pas comme enfants

| Référence | Objet | N | Résultat |
|---|---|---|---|
| Sun et al. (2025), *PLOS ONE* 20(2) | ChatGPT-3.5 interroge de **vrais enfants** de 6–8 ans | 78 enfants | Le LLM obtient plus d'informations correctes par question (0,90 contre 0,46) et moins d'informations fausses au total, mais moins d'informations correctes au total |
| Järvilehto et al. (2025), *Behav. Sci. & Law* 44 | Formulation de questions : tâche statique et tâche face à des **avatars AI** | 60 + 60 humains, GPT-4, Llama-2 ; 32 + 32 + GPT-4 | Tâche statique : GPT-4 fait mieux que les psychologues (67,8 % d'invitations). Tâche dynamique : **GPT-4 fait moins bien que les professionnels** (8,69 contre 18,75 questions recommandées) |
| Järvilehto et al. (2026), *Journal of Psychology and AI* 2(1) | Rapport et questions générés par LLM avec de vrais enfants | 2 expériences | Le rapport mené par le LLM améliore l'engagement et le rappel ; questions autonomes moins ouvertes et plus d'erreurs sur les détails centraux |
| Järvilehto et al. (2025), *Psychol. Crime & Law* | Génération d'hypothèses avant l'audition | 141 humains + 2 LLM | GPT-4 produit des hypothèses plus nombreuses, plus spécifiques et plus complètes |
| Santtila et al. (2025), *Acta Psychologica* 258 | Les LLM prédisent-ils les résultats d'études sur la mémoire et la suggestibilité des enfants ? | 4 LLM, 4 800 prédictions | 65 % d'exactitude, contre 57 % pour les professionnels dans les études antérieures |

### 3.3 Autres groupes et travaux connexes

- **Al Owayyed, Denga & Brinkman (2025), IVA '25, TU Delft.** Agent **hybride BDI (règles) + LLM** qui simule un enfant dans le chat d'une ligne d'aide. Le LLM sert à reconnaître l'intention, à générer la réponse et à prendre le relais quand aucune règle ne s'applique. Dans une étude intra-sujets (N = 37), l'agent est jugé plus crédible que la version purement à règles. **C'est l'architecture la plus proche de la nôtre**, mais elle ne vise ni l'audition judiciaire, ni la suggestibilité, ni la vérité terrain.
- **Chan et al. (2024), CrimRxiv/arXiv.** Un chatbot génératif qui pose des questions suggestives multiplie par environ 3 les faux souvenirs immédiats d'adultes témoins (N = 200). C'est un argument pour un filtre de contenu et pour la sensibilisation à la contamination.
- **Li & Cai (2025), IDC '25.** Humains virtuels pilotés par LLM pour **interviewer** des enfants de 6–12 ans dans un contexte de design. Ce n'est pas un contexte forensique.
- **Du et al. (2025), ACL.** Patients standardisés simulés par LLM (agent coevolution). C'est l'analogue médical : il montre qu'ACL accepte ce type de simulateur d'entraînement.
- Un outil commercial (« EchoMind ») est mentionné par un magazine policier, sans publication évaluée par les pairs (non vérifié).

---

<a id="q3"></a>
## 4. Question 3 : classification automatique des questions d'interviewers

| Référence | Méthode | Données | Catégories | Performance |
|---|---|---|---|---|
| Garcia (2022), thèse, Griffith, citée par Szojka et al. (2025) | Règles (« can you / do you » = fermée) | Prompts de transition de 341 entretiens | Ouverte / fermée | κ = 0,93 avant ajustement des règles ; 100 % après ajustement sur **le même** échantillon (non vérifié directement : rapporté par Szojka et al.) |
| Haginoya et al. (2023) | **XGBoost** sur n-grammes de caractères (1–5), règles si-alors, liste de mots-clés suggestifs, Jaccard pour les répétitions | 8 754 questions japonaises (entretiens avec avatars) | 11 types → recommandée / non recommandée | 71 % sur le jeu de test. Face aux codeurs humains : 52 % sur 11 types (κ = 0,42), 72 % sur 2 classes (κ = 0,49) |
| Hassan et al. (2023), *Sci. Rep.* | **GPT-3 davinci affiné**, température 0 | 58 transcriptions pour l'entraînement (14 types), 40 pour le test (2 015 ouvertes / 400 fermées) | Ouverte / fermée | 87 % d'exactitude équilibrée. Szojka et al. recalculent κ ≈ 0,55 et une sensibilité de 65 % pour les fermées |
| Røed et al. (2023), *Front. Psychol.* | GPT-3 davinci affiné | Entraîné sur 700 entretiens simulés ; testé sur 3 206 questions (120 entretiens avec avatar) | Ouverte / rappel indicé / fermée | κ = 0,80 (86,7 % / 87,4 % / 85,3 %) |
| **Szojka, Yashraj & Lyon (2025)**, *Law & Human Behavior* 49 | **RoBERTa** affiné, validation croisée ; modèle public | **351 920 questions réelles** : 1 435 entretiens forensiques + 416 témoignages au procès, enfants de 3–17 ans ; test sur 52 354 questions | Invitation / question wh- / option-posing / non-question | 95 % (κ = 0,93) ; 98 % (κ = 0,97) après correction des erreurs des codeurs humains |
| Szojka, Yashraj & Lyon (2026), *Legal & Criminol. Psychol.* | RoBERTa, mêmes données | 351 920 questions | + questions « tag » et « Do you know » | 95 % (κ = 0,94) ; sensibilités de 96 % et 94 % pour les deux nouvelles catégories |
| Siskou & Espinoza (2024), SICon@ACL | GPT-4o sans entraînement préalable | Audiences de libération conditionnelle (Californie) | Types de questions | F1 = 0,91 (domaine voisin, adultes) |
| Ardulov et al. (2018), arXiv | Résumé et modélisation thématique, entraînement lexical (accommodation) | Entretiens forensiques | Productivité de l'enfant (pas les questions) | Pas de chiffres dans le résumé |

**Ce qui ressort**

- Le meilleur résultat publié est **κ ≈ 0,93–0,97, sur des données réelles et massives, en anglais, avec 4 à 6 catégories**.
- Aucune étude trouvée ne :
  - porte sur le **français** ;
  - distingue **invitation et invitation indicée** de façon automatique (Lamb et al., 2003, montrent pourtant que les invitations indicées produisent 18 % des détails) ;
  - suit **automatiquement les phases** du protocole (rapport, règles de base, pratique narrative, transition, phase substantive, clôture).
- **Notre κ = 0,978 sur 104 énoncés que nous avons écrits** n'est pas comparable à ces chiffres. L'échantillon est petit, les énoncés sont rédigés par les concepteurs eux-mêmes (risque de circularité) et la distribution n'est pas naturelle. Szojka et al. montrent par ailleurs qu'un pourcentage d'accord élevé peut masquer un κ modéré quand les classes sont déséquilibrées.

---

<a id="q4"></a>
## 5. Question 4 : bases empiriques pour paramétrer un enfant simulé

### 5.1 Productivité et exactitude par type de question (terrain et analogue)

- **Les invitations produisent environ 50 % des détails, quel que soit l'âge** (130 entretiens, enfants de 4–8 ans). Les invitations indicées en produisent 18 %, et leur rendement augmente avec l'âge. Les indices fondés sur une action sont les plus efficaces (Lamb et al., 2003).
- **Les réponses aux invitations sont 3 à 5 fois plus informatives** que les réponses aux questions ciblées (Lamb et al., 2007, revue). Plus de 80 % des premières révélations d'enfants d'âge préscolaire surviennent en réponse à des invitations dans les entretiens menés avec le protocole.
- **Révélation initiale suite à une question ouverte : 89 % avec le protocole contre 36 % sans** (100 enfants de 4–12 ans ; Sternberg et al., 2001). Même avec le protocole, les questions option-posing et suggestives produisent encore environ un quart des détails (Lamb et al., 2007).
- **Exactitude sur le terrain.** Les détails fournis par les victimes sont plus souvent confirmés par les auteurs lorsqu'ils ont été obtenus par invitation. Mais 66,6 % des détails ne sont ni confirmés ni contredits par l'auteur (43 victimes de 9,8 ans en moyenne ; Lamb et al., 2007, *ACP*).
- **Les contradictions internes ne proviennent jamais d'invitations** et proviennent de façon disproportionnée de questions suggestives (24 entretiens, 7 enfants ; Lamb & Fauchier, 2001).
- **Étude analogue avec le protocole NICHD** (128 enfants de 5–7 ans, 4–6 semaines après l'événement) : exactitude globale élevée quel que soit le type de question. Les erreurs portent surtout sur des détails périphériques et viennent plutôt des questions directives et oui/non (Brown et al., 2013). Les taux exacts par type de question n'ont pas été consultés (texte intégral non accessible).
- **Âge préscolaire, échantillon national norvégien** : 4 % d'invitations principales, 96 % d'invitations indicées. Elles font émerger une information forensiquement pertinente dans environ 70 % et 83 % des cas respectivement (Johnson et al., 2025).
- **Proportion d'enfants qui ne révèlent pas l'abus** : plus d'un tiers des victimes présumées (Hershkowitz et al., 2005, 2007, cités par Lamb et al., 2007). Le protocole révisé (soutien non suggestif) augmente le taux d'allégations dans des cas corroborés (Hershkowitz, Lamb & Katz, 2014 ; N = 426).

### 5.2 Acquiescement et biais de réponse

- **Questions oui/non (Fritzley & Lee, 2003, 4 expériences)** :
  - à 2 ans, biais « oui » constant ;
  - à 3 ans, période de transition ;
  - à **4–5 ans, aucun biais pour les questions compréhensibles, et un biais « non » pour les questions incompréhensibles**.
  - Fritzley, Lindsay & Lee (2013 ; 200 enfants de 2–5 ans, questions sur des actions) retrouvent le même schéma. Le délai fait augmenter les « non ».
- **Okanda & Itakura (2010 ; 135 enfants de 3–6 ans)** :
  - biais « oui » généralisé à 3 ans ;
  - partiel à 4 ans ;
  - **absent à 5 ans** ;
  - biais « non » à 6 ans pour certaines questions (expressions faciales).
- **Questions sans réponse possible (Waterman, Blades & Spencer, 2001 ; 128 enfants de 5–9 ans)** : **la majorité des enfants répondent « oui » ou « non » à une question fermée à laquelle on ne peut pas répondre**, alors que la majorité disent « je ne sais pas » à une question wh- équivalente. Chez les adultes, un peu plus d'un cinquième répondent quand même. Waterman et al. (2004 ; 149 enfants de 5–9 ans) trouvent que les « je ne sais pas » augmentent quand l'interviewer était absent de l'événement.
- **Biais de récence** : les enfants de 3–5 ans choisissent préférentiellement la **seconde** option d'une question à choix forcé, et ce biais s'atténue avec l'âge (Mehrani & Peterson, 2015). Les pourcentages n'ont pas pu être consultés (non vérifié).

> **Implication pour la calibration (5–12 ans) :** la littérature ne justifie pas un « biais oui » marqué au-delà de 4–5 ans pour les questions **compréhensibles**. Le risque principal est que l'enfant **réponde quand même** à une question fermée sans réponse possible ou mal comprise, au lieu de dire « je ne sais pas ». À cet âge, l'acquiescement devrait donc dépendre de la compréhensibilité et de la connaissance de l'enfant, plutôt que de s'appliquer uniformément.

### 5.3 Répétition, suggestion et contamination

- **Répétition des questions** : plus d'un quart des réponses changent, en général avec une baisse d'exactitude, surtout après la première répétition. Pour les questions sans réponse possible, **plus la question est répétée, plus l'enfant invente** (156 enfants de 4–9 ans ; Krähenbühl, Blades & Eiser, 2009). Poole et White (1991) donnent des données complémentaires sur la répétition entre entretiens (chiffres non relevés).
- **Stéréotype et suggestion (Leichtman & Ceci, 1995 ; N = 176, 3–6 ans)** : peu de faux rapports dans le groupe contrôle, beaucoup après suggestions, et des niveaux élevés quand on combine stéréotype et suggestion, avec un net effet de l'âge en faveur des plus âgés. Le chiffre souvent cité de **72 % des 3–4 ans** qui rapportent un méfait dans la condition combinée n'a été vu que dans des sources secondaires (non vérifié dans la source primaire).
- **Désinformation par les parents (Poole & Lindsay, 2001 ; 3–8 ans)** : beaucoup d'enfants rapportent des événements fictifs **dès les questions ouvertes**, sans effet de l'âge dans cette phase. L'exactitude chute aux questions directes, surtout chez les plus jeunes, et seuls les plus âgés se rétractent après des consignes de surveillance de la source.
- **Question suggestive de type « tag »** : 20 % de faux « oui » dans une étude de terrain simulée (visite d'un clown ; Finnilä et al., 2003, cité par Pompedda et al., 2022). La source primaire n'a pas été consultée (non vérifié).
- **Différences individuelles (Bruck & Melnyk, 2004 ; 69 études)** : la suggestibilité est liée assez régulièrement aux capacités langagières et à la créativité, et, du côté psychosocial, à l'image de soi, à l'attachement et à la relation parent-enfant.
- **Synthèse historique (Ceci & Bruck, 1993)** : les différences d'âge en suggestibilité sont fiables, mais même les très jeunes enfants peuvent rapporter beaucoup d'éléments forensiquement pertinents.

---

<a id="positionnement"></a>
## 6. Positionnement

### 6.1 Ce qui existe déjà (risques de redondance)

| Brique de notre simulateur | Déjà publié ? | Par qui |
|---|---|---|
| Enfant simulé + feedback sur le type de question + vérité terrain connue + conclusion | **Oui, très établi** | Avatar Training (2014–2025) |
| Classification automatique des questions pour le feedback | **Oui** (anglais, japonais) | Haginoya 2023 ; Hassan 2023 ; Røed 2023 ; Szojka 2025–2026 |
| Enfant piloté par un LLM | **Oui** (GPT-3 affiné, anglais et norvégien) | SimulaMet / OsloMet 2022–2025 |
| Architecture hybride règles + LLM pour un enfant simulé | **Oui, dans un autre domaine** (ligne d'aide) | Al Owayyed et al. 2025 |
| Score de contamination (détails erronés introduits par l'interviewer) | **Oui, sous forme de « wrong details »** | Avatar Training |
| Moteur de suggestibilité paramétré par âge **et** réalisation par LLM, avec filtre de sortie | **Non trouvé** | — |
| Classifieur de la typologie NICHD complète (invitation indicée, etc.) **en français** | **Non trouvé** | — |
| Suivi automatique des phases du protocole | **Non trouvé** | — |
| LLM open source **local** (confidentialité) | Non trouvé dans ce domaine : les travaux utilisent GPT-3/4 via API, sauf Hassan et al. (2025), qui testent des modèles ouverts norvégiens pour la génération seulement | — |
| Âges de 5–12 ans, 7 scénarios | Les avatars publiés ont 4–6 ans (Avatar Training), 6 ans (Røed) ou 8 ans (Ko) | — |

### 6.2 En quoi l'architecture hybride diffère

1. **Les avatars algorithmiques** (Pompedda, Haginoya) contrôlent finement la suggestibilité, mais leurs réponses sont des clips préenregistrés. L'expressivité est fermée et chaque scénario coûte cher à produire.
2. **Les avatars LLM** (SimulaMet) sont naturels et ouverts, mais leur comportement n'est **ni contrôlé ni vérifiable**. Deux échecs sont documentés : l'avatar ne distingue pas les questions « Do you know/remember » des invitations (Baugerud et al., 2024), et la langue est trop avancée pour l'âge (Hassan et al., 2025). Aucun mécanisme de vérité terrain ni de contamination n'est décrit.
3. **Notre approche** confie la **décision** (quoi révéler, accepter ou non une suggestion) à un moteur déterministe auditable, et la **forme** au LLM. Le filtre de sortie garantit que le LLM n'ajoute aucun fait non autorisé par le moteur. On combine ainsi la contrôlabilité de 1 et la naturalité de 2.

### 6.3 Angle de publication le plus défendable

- **Contribution principale : « fidélité comportementale vérifiable ».** Il s'agit de montrer que le simulateur reproduit les régularités empiriques, et de le comparer à une base LLM seule (même modèle, prompt seul) :
  - détails pertinents ↑ avec les questions ouvertes, détails erronés ↑ avec les questions suggestives et répétées (cibles : r ≈ 0,79 et r ≈ 0,57 dans la méga-analyse) ;
  - acquiescement aux questions fermées sans réponse possible, mais pas aux questions compréhensibles, à partir de 5 ans ;
  - baisse d'exactitude après répétition ;
  - **taux de fuite** des faits non autorisés avec et sans filtre.

  Le protocole d'évaluation pourrait réutiliser les questions types de la littérature, et un panel d'experts aveugles pourrait juger le réalisme de la langue selon l'âge (méthode de Hassan et al., 2025).
- **Contribution secondaire : classifieur NICHD en français + suivi des phases.** Il faut une validation externe : des énoncés écrits par des tiers, idéalement des transcriptions d'auditions françaises ou québécoises anonymisées ou des entretiens de formation, avec plusieurs codeurs indépendants, un κ et une sensibilité par classe. Il faut aussi comparer avec RoBERTa traduit ou un LLM sans entraînement préalable (*zero-shot*).
- **À éviter comme contribution principale** : « un avatar LLM avec feedback améliore la qualité des questions ». C'est déjà démontré (Røed 2023 ; Haginoya 2023), et ce n'est pas répliqué chez des non-spécialistes (Ko 2025).
- **Étude d'efficacité ultérieure** : un essai randomisé feedback contre sans feedback, sur le modèle d'Avatar Training, avec mesure du transfert si possible (modèle de Kask 2022).

---

<a id="parametres"></a>
## 7. Paramètres : valeurs empiriques pour la calibration

*Légende : **E** = donnée empirique sur des enfants ; **S** = choix de conception d'un simulateur publié (utile comme point de comparaison, mais ce n'est pas une mesure sur des enfants).*

| Paramètre du simulateur | Valeur trouvée | Type | Source |
|---|---|---|---|
| Part des détails obtenus par invitation (4–8 ans) | ≈ 50 %, sans différence d'âge | E | Lamb et al. (2003) |
| Part des détails obtenus par invitation indicée | 18 %, en hausse avec l'âge | E | Lamb et al. (2003) |
| Informativité d'une invitation par rapport à une question ciblée | 3 à 5 fois plus | E | Lamb et al. (2007, revue) |
| Révélation initiale suite à une question ouverte | 89 % (protocole) contre 36 % (standard), 4–12 ans | E | Sternberg et al. (2001) |
| Rendement d'une invitation (préscolaire) | ≈ 70 % (principale), ≈ 83 % (indicée) donnent une information pertinente | E | Johnson et al. (2025) |
| Productivité selon l'avancement de l'entretien | L'efficacité des invitations augmente plus tard dans l'entretien | E | Johnson et al. (2025) |
| Biais « oui », questions compréhensibles | 2 ans : fort ; 3 ans : transition ; 4–5 ans : nul | E | Fritzley & Lee (2003) ; Okanda & Itakura (2010) |
| Biais pour une question incompréhensible (4–5 ans et plus) | Biais « non » | E | Fritzley & Lee (2003) ; Fritzley et al. (2013) |
| Réponse à une question fermée sans réponse possible (5–9 ans) | **Majorité répond oui ou non** (contre « je ne sais pas » pour une question wh-) | E | Waterman et al. (2001, 2004) |
| « Je ne sais pas » selon que l'interviewer était présent ou absent de l'événement | Plus de « je ne sais pas » si l'interviewer était absent | E | Waterman et al. (2004) |
| Changement de réponse à la répétition (4–9 ans) | > 25 % des réponses changent, en général moins exactes | E | Krähenbühl et al. (2009) |
| Invention selon le nombre de répétitions (question sans réponse possible) | Augmente avec le nombre de répétitions | E | Krähenbühl et al. (2009) |
| Passage de « non » à « oui » après répétition, détail absent, 4 ans | p = 0,50 | S | Pompedda et al. (2022), description de l'algorithme |
| Détail révélé par question recommandée | p = 0,20 (4 ans) ; 0,25 (6 ans) ; 9 détails pertinents dans un ordre fixe | S | Haginoya et al. (2023) |
| Biais de récence (choix forcé à 2 options) | Préférence pour la 2ᵉ option à 3–5 ans, qui s'atténue avec l'âge (pourcentages non vérifiés) | E | Mehrani & Peterson (2015) |
| Intégration de suggestions répétées + stéréotype (3–4 ans) | ≈ 72 % de faux rapports (non vérifié dans la source primaire) ; plus faible à 5–6 ans | E | Leichtman & Ceci (1995) |
| Faux « oui » à une question « tag » suggestive | 20 % (non vérifié, source secondaire) | E | Finnilä et al. (2003), cité par Pompedda et al. (2022) |
| Désinformation préalable (parents) | Faux récits même aux questions ouvertes ; pas d'effet d'âge à ce stade ; rétractation seulement chez les plus âgés | E | Poole & Lindsay (2001) |
| Contradictions selon le type de question | 0 pour les invitations ; surreprésentées pour les questions suggestives | E | Lamb & Fauchier (2001) |
| Erreurs selon la centralité du détail | Surtout sur les détails périphériques ; viennent plutôt des questions directives et oui/non | E | Brown et al. (2013) |
| Modérateurs individuels de la suggestibilité | Langage, créativité, image de soi, attachement | E | Bruck & Melnyk (2004) |
| Non-révélation chez des victimes présumées | > 1/3 | E | Hershkowitz et al. (2005, 2007), cités par Lamb et al. (2007) |
| Registre de langue généré par un LLM | Les LLM produisent une langue **plus avancée** que l'âge cible (5 et 9 ans) | E (évaluation d'un LLM) | Hassan et al. (2025) |
| Validation du moteur (cibles de corrélation) | Questions recommandées × détails pertinents r = 0,79 ; non recommandées × détails erronés r = 0,57 ; recommandées × conclusion correcte r = 0,36 | S (validation d'un simulateur) | Pompedda et al. (2022) |

**Lacunes de calibration** : nous n'avons pas trouvé de taux chiffrés et vérifiés d'exactitude par type de question **et par tranche d'âge 7–12 ans** dans le format NICHD. Les chiffres exacts de Brown et al. (2013) seraient à extraire du texte intégral.

---

<a id="venues"></a>
## 8. Venues recommandées

### 8.1 Psychologie légale et maltraitance (contribution « fidélité comportementale » ou essai d'efficacité)

| Venue | Pourquoi | Articles similaires vérifiés |
|---|---|---|
| ***Applied Cognitive Psychology*** (Wiley) | Venue n° 1 en volume pour ce sujet entre 2017 et 2025 ; accepte les pilotes et les études qualitatives | Krause 2017 ; Brubacher 2025 ; Ko 2025 ; Pompedda 2025 |
| ***Frontiers in Psychology*** (accès ouvert) | Numéro thématique dédié ; publication rapide | Pompedda 2017 ; Haginoya 2020, 2023 ; Kask 2022 ; Røed 2023 ; éditorial Kask et al. 2024 |
| ***Child Abuse & Neglect*** | Revue de référence ; études empiriques solides | Haginoya 2021 ; Røed, Powell et al. 2023 ; Lamb 2007 |
| ***Psychology, Crime & Law*** | Avatars, LLM, livre blanc de l'EAPL | Pompedda 2015 ; Segal 2024 ; Järvilehto 2025 ; Korkman 2024 |
| ***Behavioral Sciences & the Law*** | LLM et interviewing, essais à grande échelle | Järvilehto 2025 ; Haginoya 2025 (478 policiers) |
| ***Child Maltreatment*** | Avatar LLM en conditions réelles d'usage | Baugerud et al. 2024 |
| ***Law and Human Behavior*** / ***Legal and Criminological Psychology*** | Classification automatique des questions | Szojka 2025 ; Szojka 2026 |
| ***Journal of Police and Criminal Psychology*** | Synthèses | Méga-analyse de Pompedda 2022 |
| ***Journal of Psychology and AI*** (T&F, nouvelle revue) | Positionnement explicite psychologie × IA | Järvilehto 2026 |
| *Child Protection and Practice* ; *Acta Psychologica* ; *PLOS ONE* | Venues secondaires | Haginoya 2025 ; Santtila 2025 ; Sun 2025 ; Zhang 2023 |

### 8.2 IA, TAL, interaction humain-machine et multimédia (contribution « architecture hybride contrôlable » ou « classifieur français »)

| Venue | Pourquoi | Articles similaires vérifiés |
|---|---|---|
| **ACM IVA** (Intelligent Virtual Agents) | **Meilleure adéquation pour l'architecture** : un agent enfant hybride règles + LLM pour la formation y a été publié en 2025 | Al Owayyed et al. 2025 |
| **ACL / EMNLP / NAACL (et ateliers : SICon, BEA, CL4Health)** | Simulation par LLM pour la formation ; classification de questions | Du et al. 2025 (patients standardisés, ACL) ; Siskou & Espinoza 2024 (SICon) |
| ***Scientific Reports*** / ***IEEE Access*** | Venues pluridisciplinaires déjà utilisées par SimulaMet | Hassan 2023 ; Salehi 2024 |
| **ACM MMVE / IMX / IEEE ISM / CBMI** | Systèmes multimédia et réalité virtuelle | Salehi 2024 (MMVE) ; Hassan 2022 (ISM, IMX workshop, CBMI) |
| **ACM IDC** | Enfants × IA (plutôt côté conception) | Li & Cai 2025 |
| *Nordic Machine Intelligence*, *BDCC* (MDPI) | Venues secondaires en accès ouvert | Salehi 2022, 2025 |

### 8.3 Venues francophones

- **TALN (JEP-TALN-RECITAL, actes sur ACL Anthology)**. C'est la venue naturelle pour le **classifieur NICHD en français** et le suivi des phases : ressource et évaluation en français, peu concurrencée. Nous n'avons trouvé aucun article TALN sur l'audition d'enfants ou les patients simulés. Le sujet est donc nouveau pour cette communauté, sans précédent direct à citer. Les éditions 2024–2025 comportent des ateliers médicaux sur les LLM (MLP-LLM 2025, DEFT 2024), ce qui montre qu'elle accueille les applications à fort enjeu.
- **Contexte francophone en psychologie** :
  - Cyr & Lamb (2009, *Child Abuse & Neglect*) : protocole NICHD avec des enfants francophones du Québec ;
  - Cyr (2014/2019, Dunod) : *Recueillir la parole de l'enfant témoin ou victime* ;
  - thèse de R. Job (Université de Lille, 2024) : formation et usage du protocole NICHD par les enquêteurs en France.

  Ces références légitiment le besoin d'un outil en français. La *Revue québécoise de psychologie* a publié Cyr & Dion (2006) sur le protocole NICHD (non vérifié directement).

**Stratégie suggérée**

1. Un article TALN (ou atelier ACL) sur le classifieur et les phases en français, après validation externe.
2. Un article IVA ou ACL sur l'architecture hybride et sa fidélité comportementale comparée à un LLM seul.
3. Plus tard, un essai d'efficacité dans *Applied Cognitive Psychology* ou *Child Abuse & Neglect*, idéalement avec un partenaire de terrain (gendarmerie, police, unités d'accueil pédiatriques enfants en danger).

---

<a id="biblio"></a>
## 9. Bibliographie (APA 7)

*Toutes les références ci-dessous ont été vues (métadonnées Crossref ou OpenAlex, page éditeur, PMC, arXiv ou ACL Anthology). La mention « (non vérifié) » signale qu'un chiffre précis cité dans le texte n'a pas été vu dans la source primaire.*

Al Owayyed, M., Denga, A., & Brinkman, W.-P. (2025). Controlled yet natural: A hybrid BDI-LLM conversational agent for child helpline training. In *Proceedings of the ACM International Conference on Intelligent Virtual Agents (IVA '25)*. https://doi.org/10.1145/3717511.3747075 (arXiv:2509.16784)

Ardulov, V., Kumar, M., Williams, S., Lyon, T., & Narayanan, S. (2018). *Measuring conversational productivity in child forensic interviews* (arXiv:1806.03357). https://doi.org/10.48550/arXiv.1806.03357

Baugerud, G. A., Johnson, M. S., Dianiska, R. E., Røed, R. K., Powell, M. B., Lamb, M. E., Hassan, S. Z., Sabet, S. S., Hicks, S. A., Salehi, P., Riegler, M. A., Halvorsen, P., & Quas, J. A. (2025). Using an AI-based avatar for interviewer training at Children's Advocacy Centers: Proof of concept. *Child Maltreatment, 30*(2), 242–252. https://doi.org/10.1177/10775595241263017

Brown, D. A., Lamb, M. E., Lewis, C., Pipe, M.-E., Orbach, Y., & Wolfman, M. (2013). The NICHD Investigative Interview Protocol: An analogue study. *Journal of Experimental Psychology: Applied, 19*(4), 367–382. https://doi.org/10.1037/a0035143

Brubacher, S. P., Powell, M. B., Johnson, M. S., Cano, M., Hassan, S. Z., Riegler, M. A., Halvorsen, P., & Baugerud, G. A. (2025). Experts' views on artificial intelligence-based child chatbots to train investigative interviewing skills. *Applied Cognitive Psychology, 39*(2). https://doi.org/10.1002/acp.70048

Bruck, M., & Melnyk, L. (2004). Individual differences in children's suggestibility: A review and synthesis. *Applied Cognitive Psychology, 18*(8), 947–996. https://doi.org/10.1002/acp.1070

Ceci, S. J., & Bruck, M. (1993). Suggestibility of the child witness: A historical review and synthesis. *Psychological Bulletin, 113*(3), 403–439. https://doi.org/10.1037/0033-2909.113.3.403

Chan, S., Pataranutaporn, P., Suri, A., Zulfikar, W. D., Maes, P., & Loftus, E. F. (2024). *Conversational AI powered by large language models amplifies false memories in witness interviews*. CrimRxiv / arXiv:2408.04681. https://doi.org/10.21428/cb6ab371.6ae390a8

Cyr, M. (2019). *Recueillir la parole de l'enfant témoin ou victime* (2e éd.). Dunod. https://doi.org/10.3917/dunod.cyr.2019.01

Cyr, M., & Lamb, M. E. (2009). Assessing the effectiveness of the NICHD investigative interview Protocol when interviewing French-speaking alleged victims of child sexual abuse in Quebec. *Child Abuse & Neglect, 33*(5), 257–268. https://doi.org/10.1016/j.chiabu.2008.04.002

Du, Z., Zheng, L., Hu, R., Xu, Y., Li, X., Sun, Y., Chen, W., & Wu, J. (2025). LLMs can simulate standardized patients via agent coevolution. In *Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 17278–17306). https://doi.org/10.18653/v1/2025.acl-long.846

Fritzley, V. H., & Lee, K. (2003). Do young children always say yes to yes–no questions? A metadevelopmental study of the affirmation bias. *Child Development, 74*(5), 1297–1313. https://doi.org/10.1111/1467-8624.00608

Fritzley, V. H., Lindsay, R. C. L., & Lee, K. (2013). Young children's response tendencies toward yes–no questions concerning actions. *Child Development, 84*(2), 711–725. https://doi.org/10.1111/cdev.12006

Haginoya, S., Ibe, T., Yamamoto, S., Yoshimoto, N., Mizushi, H., & Santtila, P. (2023). AI avatar tells you what happened: The first test of using AI-operated children in simulated interviews to train investigative interviewers. *Frontiers in Psychology, 14*, 1133621. https://doi.org/10.3389/fpsyg.2023.1133621

Haginoya, S., Ibe, T., Yamamoto, S., Yoshimoto, N., Mizushi, H., & Santtila, P. (2025). Scalable training for child sexual abuse interviews in Japan: Using AI-driven avatars to test multiple behavioral modeling interventions. *Child Protection and Practice, 5*, 100188. https://doi.org/10.1016/j.chipro.2025.100188

Haginoya, S., Sun, Y., & Santtila, P. (2026). Retention of training effects in police officers following scalable AI simulations of child sexual abuse interviews. *Behavioral Sciences & the Law, 44*(1), 34–46. https://doi.org/10.1002/bsl.70019 (publié en ligne en 2025)

Haginoya, S., Yamamoto, S., Pompedda, F., Naka, M., Antfolk, J., & Santtila, P. (2020). Online simulation training of child sexual abuse interviews with feedback improves interview quality in Japanese university students. *Frontiers in Psychology, 11*, 998. https://doi.org/10.3389/fpsyg.2020.00998

Haginoya, S., Yamamoto, S., & Santtila, P. (2021). The combination of feedback and modeling in online simulation training of child sexual abuse interviews improves interview quality in clinical psychologists. *Child Abuse & Neglect, 115*, 105013. https://doi.org/10.1016/j.chiabu.2021.105013

Hassan, S. Z., Halvorsen, P., Johnson, M. S., & Lison, P. (2025). *Evaluating LLMs on generating age-appropriate child-like conversations* (arXiv:2510.24250). https://doi.org/10.48550/arXiv.2510.24250

Hassan, S. Z., Sabet, S. S., Riegler, M. A., Baugerud, G. A., Ko, H., Salehi, P., Røed, R. K., Johnson, M., & Halvorsen, P. (2023). Enhancing investigative interview training using a child avatar system: A comparative study of interactive environments. *Scientific Reports, 13*, 20403. https://doi.org/10.1038/s41598-023-47368-2

Hassan, S. Z., Sabet, S. S., Salehi, P., Ko, H., Riiser, I., Johnson, M. S., Baugerud, G. A., Riegler, M. A., & Halvorsen, P. (2022). A comparative study of interactive environments for investigative interview of a virtual child avatar. In *2022 IEEE International Symposium on Multimedia (ISM)* (pp. 194–201). https://doi.org/10.1109/ISM55400.2022.00043

Hassan, S. Z., Salehi, P., Røed, R. K., Halvorsen, P., Baugerud, G. A., Johnson, M. S., Lison, P., Riegler, M. A., Lamb, M. E., Griwodz, C., & Sabet, S. S. (2022). Towards an AI-driven talking avatar in virtual reality for investigative interviews of children. In *Proceedings of the 2nd Workshop on Games Systems (GameSys '22)* (pp. 9–15). ACM. https://doi.org/10.1145/3534085.3534340

Hershkowitz, I., Lamb, M. E., & Katz, C. (2014). Allegation rates in forensic child abuse investigations: Comparing the revised and standard NICHD protocols. *Psychology, Public Policy, and Law, 20*(3), 336–344. https://doi.org/10.1037/a0037391

Järvilehto, L., Sun, Y., Aiba, N., Haginoya, S., Hällström, H. J., Korkman, J., & Santtila, P. (2026). Large language model (LLM) and human performance in child investigative interviewing question formulation tasks. *Behavioral Sciences & the Law, 44*(1), 142–163. https://doi.org/10.1002/bsl.70029 (publié en ligne en 2025)

Järvilehto, L., Sun, Y., Korkman, J., Haginoya, S., & Santtila, P. (2026). Testing large language model capability in building rapport and interviewing children about a witnessed mock event. *Journal of Psychology and AI, 2*(1). https://doi.org/10.1080/29974100.2025.2608167

Järvilehto, L., Sun, Y., Korkman, J., Pakkanen, T., Shen, C., Bader, F. M., & Santtila, P. (2025). Pre-interview hypothesis generation: Large language models (LLMs) show promise for child abuse investigations. *Psychology, Crime & Law*. Advance online publication. https://doi.org/10.1080/1068316X.2025.2531391

Job, R. (2024). *L'audition des enfants par les enquêteurs : formation et utilisation du protocole du NICHD en France* [Thèse de doctorat, Université de Lille]. https://doi.org/10.70675/9965bc78zbc3fz4c7fza316zb74789867638

Johnson, M. S., Grung, R. M., Røed, R. K., Pripp, A. H., & Baugerud, G. A. (2025). Children's elaboration of forensically relevant information in response to invitations: A national study of investigative interviews with preschool-aged abuse victims. *Child Maltreatment, 31*(1), 70–83. https://doi.org/10.1177/10775595251328933

Kask, K., Baugerud, G. A., & Volbert, R. (2024). Editorial: Technological solutions helping to train specialists' interviewing skills of possible victims and witnesses. *Frontiers in Psychology, 15*, 1406867. https://doi.org/10.3389/fpsyg.2024.1406867

Kask, K., Pompedda, F., Palu, A., Schiff, K., Mägi, M.-L., & Santtila, P. (2022). Transfer of avatar training effects to investigative field interviews of children conducted by police officers. *Frontiers in Psychology, 13*, 753111. https://doi.org/10.3389/fpsyg.2022.753111

Ko, H., Hovden, E., Köpp, U. M. S., Johnson, M. S., & Baugerud, G. A. (2025). Using an AI-driven child chatbot avatar as a training tool for information gathering skills of dental and medical professionals: A pilot study. *Applied Cognitive Psychology, 39*(1). https://doi.org/10.1002/acp.70022

Korkman, J., Otgaar, H., Geven, L. M., Bull, R., Cyr, M., Hershkowitz, I., … Volbert, R. (2024). White paper on forensic child interviewing: Research-based recommendations by the European Association of Psychology and Law. *Psychology, Crime & Law, 31*(8), 987–1030. https://doi.org/10.1080/1068316X.2024.2324098

Krähenbühl, S., Blades, M., & Eiser, C. (2009). The effect of repeated questioning on children's accuracy and consistency in eyewitness testimony. *Legal and Criminological Psychology, 14*(2), 263–278. https://doi.org/10.1348/135532508X398549

Krause, N., Pompedda, F., Antfolk, J., Zappalà, A., & Santtila, P. (2017). The effects of feedback and reflection on the questioning style of untrained interviewers in simulated child sexual abuse interviews. *Applied Cognitive Psychology, 31*(2), 187–198. https://doi.org/10.1002/acp.3316

La Rooy, D., Brubacher, S. P., Aromäki-Stratos, A., Cyr, M., Hershkowitz, I., Korkman, J., Myklebust, T., Naka, M., Peixoto, C. E., Roberts, K. P., Stewart, H., & Lamb, M. E. (2015). The NICHD protocol: A review of an internationally-used evidence-based tool for training child forensic interviewers. *Journal of Criminological Research, Policy and Practice, 1*(2), 76–89. https://doi.org/10.1108/JCRPP-01-2015-0001

Lamb, M. E., & Fauchier, A. (2001). The effects of question type on self-contradictions by children in the course of forensic interviews. *Applied Cognitive Psychology, 15*(5), 483–491. https://doi.org/10.1002/acp.726

Lamb, M. E., Hershkowitz, I., Sternberg, K. J., Esplin, P. W., Hovav, M., Manor, T., & Yudilevitch, L. (1996). Effects of investigative utterance types on Israeli children's responses. *International Journal of Behavioral Development, 19*(3), 627–637. https://doi.org/10.1177/016502549601900310

Lamb, M. E., Orbach, Y., Hershkowitz, I., Esplin, P. W., & Horowitz, D. (2007). A structured forensic interview protocol improves the quality and informativeness of investigative interviews with children: A review of research using the NICHD Investigative Interview Protocol. *Child Abuse & Neglect, 31*(11–12), 1201–1231. https://doi.org/10.1016/j.chiabu.2007.03.021

Lamb, M. E., Orbach, Y., Hershkowitz, I., Horowitz, D., & Abbott, C. B. (2007). Does the type of prompt affect the accuracy of information provided by alleged victims of abuse in forensic interviews? *Applied Cognitive Psychology, 21*(9), 1117–1130. https://doi.org/10.1002/acp.1318

Lamb, M. E., Sternberg, K. J., Orbach, Y., Esplin, P. W., Stewart, H., & Mitchell, S. (2003). Age differences in young children's responses to open-ended invitations in the course of forensic interviews. *Journal of Consulting and Clinical Psychology, 71*(5), 926–934. https://doi.org/10.1037/0022-006X.71.5.926

Leichtman, M. D., & Ceci, S. J. (1995). The effects of stereotypes and suggestions on preschoolers' reports. *Developmental Psychology, 31*(4), 568–578. https://doi.org/10.1037/0012-1649.31.4.568

Li, L., & Cai, H. (2025). Applying LLM-powered virtual humans to child interviews in child-centered design. In *Proceedings of the ACM Interaction Design and Children Conference (IDC '25)* (pp. 1140–1145). https://doi.org/10.1145/3713043.3731551

Mehrani, M. B., & Peterson, C. (2015). Recency tendency: Responses to forced-choice questions. *Applied Cognitive Psychology, 29*(3), 418–424. https://doi.org/10.1002/acp.3119

Okanda, M., & Itakura, S. (2010). When do children exhibit a "yes" bias? *Child Development, 81*(2), 568–580. https://doi.org/10.1111/j.1467-8624.2009.01416.x

Orbach, Y., Hershkowitz, I., Lamb, M. E., Sternberg, K. J., Esplin, P. W., & Horowitz, D. (2000). Assessing the value of structured protocols for forensic interviews of alleged child abuse victims. *Child Abuse & Neglect, 24*(6), 733–752. https://doi.org/10.1016/S0145-2134(00)00137-X

Pompedda, F., Antfolk, J., Zappalà, A., & Santtila, P. (2017). A combination of outcome and process feedback enhances performance in simulations of child sexual abuse interviews using avatars. *Frontiers in Psychology, 8*, 1474. https://doi.org/10.3389/fpsyg.2017.01474

Pompedda, F., Palu, A., Kask, K., Schiff, K., Soveri, A., Antfolk, J., & Santtila, P. (2020). Transfer of simulated interview training effects into interviews with children exposed to a mock event. *Nordic Psychology, 73*(1), 43–67. https://doi.org/10.1080/19012276.2020.1788417

Pompedda, F., Segal, A., Haginoya, S., Bakaitytė, A., Ustinavičiūtė-Klenauskė, L., Kaniušonytė, G., Žukauskienė, R., & Santtila, P. (2025). Experience and long-term training effects in simulated child sexual abuse interviews. *Applied Cognitive Psychology, 39*(2), e70051. https://doi.org/10.1002/acp.70051

Pompedda, F., Zappalà, A., & Santtila, P. (2015). Simulations of child sexual abuse interviews using avatars paired with feedback improves interview quality. *Psychology, Crime & Law, 21*(1), 28–52. https://doi.org/10.1080/1068316X.2014.915323

Pompedda, F., Zhang, Y., Haginoya, S., & Santtila, P. (2022). A mega-analysis of the effects of feedback on the quality of simulated child sexual abuse interviews with avatars. *Journal of Police and Criminal Psychology, 37*(3), 485–498. https://doi.org/10.1007/s11896-022-09509-7

Poole, D. A., & Lindsay, D. S. (2001). Children's eyewitness reports after exposure to misinformation from parents. *Journal of Experimental Psychology: Applied, 7*(1), 27–50. https://doi.org/10.1037/1076-898X.7.1.27

Poole, D. A., & White, L. T. (1991). Effects of question repetition on the eyewitness testimony of children and adults. *Developmental Psychology, 27*(6), 975–986. https://doi.org/10.1037/0012-1649.27.6.975

Powell, M. B., Guadagno, B., & Benson, M. (2016). Improving child investigative interviewer performance through computer-based learning activities. *Policing and Society, 26*(4), 365–374. https://doi.org/10.1080/10439463.2014.942850

Røed, R. K., Baugerud, G. A., Hassan, S. Z., Sabet, S. S., Salehi, P., Powell, M. B., Riegler, M. A., Halvorsen, P., & Johnson, M. S. (2023). Enhancing questioning skills through child avatar chatbot training with feedback. *Frontiers in Psychology, 14*, 1198235. https://doi.org/10.3389/fpsyg.2023.1198235

Røed, R. K., Powell, M. B., Riegler, M. A., & Baugerud, G. A. (2023). A field assessment of child abuse investigators' engagement with a child-avatar to develop interviewing skills. *Child Abuse & Neglect, 143*, 106324. https://doi.org/10.1016/j.chiabu.2023.106324

Salehi, P., Hassan, S. Z., Baugerud, G. A., Powell, M., Cano, M., Johnson, M. S., Røed, R. K., Johansen, D., Sabet, S. S., Riegler, M. A., & Halvorsen, P. (2024). Immersive virtual reality in child interview skills training: A comparison of 2D and 3D environments. In *Proceedings of the 16th International Workshop on Immersive Mixed and Virtual Environment Systems (MMVE '24)* (pp. 1–7). ACM. https://doi.org/10.1145/3652212.3652219

Salehi, P., Hassan, S. Z., Baugerud, G. A., Powell, M., Johnson, M. S., Johansen, D., Sabet, S. S., Riegler, M. A., & Halvorsen, P. (2024). A theoretical and empirical analysis of 2D and 3D virtual environments in training for child interview skills. *IEEE Access, 12*, 131842–131864. https://doi.org/10.1109/ACCESS.2024.3442297

Salehi, P., Hassan, S. Z., Lammerse, M., Sabet, S. S., Riiser, I., Røed, R. K., Johnson, M. S., Thambawita, V., Hicks, S. A., Powell, M., Lamb, M. E., Baugerud, G. A., Halvorsen, P., & Riegler, M. A. (2022). Synthesizing a talking child avatar to train interviewers working with maltreated children. *Big Data and Cognitive Computing, 6*(2), 62. https://doi.org/10.3390/bdcc6020062

Salehi, P., Sheshkal, S. A., Thambawita, V., Riegler, M. A., & Halvorsen, P. (2025). Multimodal integration challenges in emotionally expressive child avatars for training applications. *Nordic Machine Intelligence, 5*(1), 29–46. https://doi.org/10.5617/nmi.12537

Santtila, P., Sun, Y., Kask, K., Järvilehto, L., & Xiu, J. (2025). Large language models' knowledge of children's memory and suggestibility: Evaluating model predictions of prior experimental results. *Acta Psychologica, 258*, 105270. https://doi.org/10.1016/j.actpsy.2025.105270

Segal, A., Pompedda, F., Haginoya, S., Kaniušonytė, G., & Santtila, P. (2024). Avatars with child sexual abuse (vs. no abuse) scenarios elicit different emotional reactions. *Psychology, Crime & Law, 30*(3), 250–270. https://doi.org/10.1080/1068316X.2022.2082422

Siskou, W., & Espinoza, I. (2024). "So, are you a different person today?" Analyzing bias in questions during parole hearings. In *Proceedings of the Second Workshop on Social Influence in Conversations (SICon 2024)* (pp. 116–128). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.sicon-1.8

Sternberg, K. J., Lamb, M. E., Orbach, Y., Esplin, P. W., & Mitchell, S. (2001). Use of a structured investigative protocol enhances young children's responses to free-recall prompts in the course of forensic interviews. *Journal of Applied Psychology, 86*(5), 997–1005. https://doi.org/10.1037/0021-9010.86.5.997

Sun, Y., Pang, H., Järvilehto, L., Zhang, O., Shapiro, D., Korkman, J., Haginoya, S., & Santtila, P. (2025). Comparing the performance of a large language model and naive human interviewers in interviewing children about a witnessed mock-event. *PLOS ONE, 20*(2), e0316317. https://doi.org/10.1371/journal.pone.0316317

Szojka, Z. A., Yashraj, S., & Lyon, T. D. (2025). Automated question type coding of forensic interviews and trial testimony in child sexual abuse cases. *Law and Human Behavior, 49*(2), 163–172. https://doi.org/10.1037/lhb0000590

Szojka, Z. A., Yashraj, S., & Lyon, T. D. (2026). Expanding automated LLM coding of question type: Tags and 'do you know' questions. *Legal and Criminological Psychology*. Advance online publication. https://doi.org/10.1111/lcrp.70063

Waterman, A. H., Blades, M., & Spencer, C. (2001). Interviewing children and adults: The effect of question format on the tendency to speculate. *Applied Cognitive Psychology, 15*(5), 521–531. https://doi.org/10.1002/acp.741

Waterman, A. H., Blades, M., & Spencer, C. (2004). Indicating when you do not know the answer: The effect of question format and interviewer knowledge on children's 'don't know' responses. *British Journal of Developmental Psychology, 22*(3), 335–348. https://doi.org/10.1348/0261510041552710

Zhang, O., Li, S., Zhang, Y., Haginoya, S., & Santtila, P. (2023). Effects of combining feedback and hypothesis-testing on the quality of simulated child sexual abuse interviews with avatars among Chinese university students. *PLOS ONE, 18*(4), e0285114. https://doi.org/10.1371/journal.pone.0285114

**Cités sans vérification de la source primaire** : Finnilä et al. (2003), cité par Pompedda et al. (2022) ; Garcia (2022, thèse de Griffith, https://doi.org/10.25904/1912/4905), cité par Szojka et al. (2025) ; Hershkowitz, Horowitz & Lamb (2005, 2007), cités par Lamb et al. (2007) ; Cyr & Dion (2006), *Revue québécoise de psychologie, 27*(3), 157–175.

*Note sur les métadonnées :* les métadonnées (auteurs, volume, pages) ont été contrôlées via Crossref. Pour les articles publiés en ligne en 2025 puis en version imprimée en 2026, le texte les désigne par l'année de publication en ligne (2025) et la bibliographie donne l'année de la version imprimée.
