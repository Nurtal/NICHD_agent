# Le modèle de l'enfant face à la littérature : verdicts et pistes d'adaptation

*Date de la recherche : 19 novembre 2026. Ce document complète la [revue de littérature](revue-litterature.md), qui
couvre le positionnement, la classification des questions et la calibration de la suggestibilité. Il confronte à la
littérature les règles du moteur ajoutées depuis : dynamique de dévoilement, mensonge (ADR 0002), activation, corps et
diction (ADR 0003). C'est un **document de travail**. Les adaptations proposées sont à décider une par une, et aucune
n'est implémentée.*

**Légende des sources** : **T** = texte intégral lu ; **R** = résumé ou notice de la source primaire lus ;
**S** = chiffre lu dans une source secondaire (non vérifié dans la source primaire). Tous les DOI de la bibliographie
ont été contrôlés sur Crossref (titre, année et revue concordants).

---

## 1. Résumé

**Ce qui tient.**
- **Pas de signature non verbale du mensonge (ADR 0003).** Les adultes, professionnels compris, détectent le mensonge
  des enfants à peine mieux que le hasard : environ 54 % d'exactitude sur 45 expériences (Gongola et al., 2017 ; R, S
  pour le chiffre).
- **Le regard détourné vient de l'effort de mémoire.** Les enfants détournent le regard d'autant plus que la question est
  difficile (Doherty-Sneddon & Phelps, 2005 ; R). C'est exactement ce que fait `demeanor.py`.
- **Un enfant calme peut avoir vécu l'événement.** Les enfants maltraités montrent souvent peu d'émotion quand ils
  révèlent (Sayfan et al., 2008 ; R), et les plus âgés cachent mieux leurs émotions (Katz et al., 2012 ; R). Le style
  figé et le style par défaut selon l'âge vont dans ce sens.
- **Le soutien réduit la réticence et augmente l'informativité.** C'est établi sur le terrain (Blasbalg et al., 2018,
  2019 ; Ahern et al., 2014 ; R).
- **Le temps et la fréquence sont durs pour les jeunes enfants** (`retrieval_difficulty`), et le refus de dévoiler est un
  résultat légitime : un enfant réellement victime nie souvent (Bücken et al., 2026 ; T, et sources qu'ils citent : S).

**Ce qui ne tient pas, ou pas entièrement.**
1. **La réticence ne fait que baisser dans le modèle.** Sur le terrain, elle évolue dans les deux sens. Elle répond à la
   **réaction de l'interviewer** : un « je sais pas » ou un déni accepté rend une réponse productive environ
   **7 fois plus probable** qu'un « je sais pas » rejeté (Bücken et al., 2026 ; T). Le stress et le désengagement
   physique **augmentent** au fil de l'entretien (Katz et al., 2012 ; R).
2. **Une question suggestive fait dévoiler plus vite (pression 3,0 contre 1,0), sans coût sur la réticence.** Les enfants
   qui ne révèlent pas ont reçu moins d'invitations, moins de soutien et des questions plus intrusives
   (Hershkowitz et al., 2006 ; R). Le modèle récompense la pression, la littérature l'associe au non-dévoilement.
3. **La répétition d'une question n'est pas modélisée,** alors que c'est l'un des effets les mieux documentés
   (Krähenbühl et al., 2009, déjà dans la revue).
4. **Le soutien n'agit pas sur la suggestibilité.** Une méta-analyse expérimentale montre pourtant qu'un interviewer
   soutenant réduit l'acquiescement et la suggestibilité (Saywitz et al., 2019 ; R).
5. **Les règles de base ont un effet trop fort et trop automatique.** Sur le terrain, la consigne « tu peux dire je sais
   pas » ne change pas la fréquence des « je sais pas » (Earhart et al., 2014 ; R). Les effets de laboratoire dépendent
   de la pratique et de l'âge (Brubacher et al., 2015 ; R).
6. **Le soutien calme le corps dans le modèle.** Or, sur le terrain, le soutien est associé à **plus** d'expression
   émotionnelle non verbale, qui précède les signes verbaux et accompagne l'informativité (Karni-Visel et al., 2023 ; R).

**Les 5 adaptations prioritaires** (détail en §6) :

| # | Adaptation | Pourquoi | Effort |
|---|---|---|---|
| A1 | Réaction de l'interviewer au « je sais pas » et au déni : la réticence remonte sur un rejet, baisse sur une acceptation | Bücken et al. (2026), Ahern et al. (2014), Earhart et al. (2014) | moyen |
| A2 | Répétition des questions : changement de réponse et invention qui montent avec le nombre de répétitions | Krähenbühl et al. (2009) | moyen |
| A3 | Coût de la pression : une question suggestive ou à choix sur l'événement fait monter la réticence d'un enfant réticent | Hershkowitz et al. (2006) | faible |
| A4 | Invitations par segment de temps (« raconte-moi la fin », « ce qui s'est passé avant ») | Protocole NICHD (Lamb et al., 2007), Orbach & Lamb (2007) ; corrige un défaut vu dans les démos | faible |
| A5 | Questions « Est-ce que tu sais / te souviens… ? » : un « oui » sans détail, plus fréquent chez les jeunes | Evans et al. (2014, 2017) | faible |

---

## 2. Méthode et limites

1. Chaque règle du moteur a été réécrite comme une hypothèse testable, avec son emplacement (`engine.py`,
   `parameters.yaml`, `demeanor.py`, `delivery.py`, ADR 0002 et 0003, `docs/design.md` §6).
2. Recherche sur le web (moteurs généraux, PubMed Central, dépôts institutionnels, NCAC/CALiO), sources primaires en
   priorité, puis contrôle des DOI sur Crossref.
3. Verdicts : **soutenu**, **partiel** (bonne direction, forme ou ampleur différente), **contredit**, **sans donnée**
   (choix de modélisation, aucune étude trouvée).

**Limites.**
- La plupart des articles n'ont été lus qu'en résumé (R). Deux seulement ont été lus en texte intégral (Talwar et al.,
  2004 ; Bücken et al., 2026, introduction et méthode). Les tailles d'effet exactes restent à extraire.
- La littérature de terrain porte surtout sur l'abus sexuel. Nos scénarios l'excluent. Les résultats sont repris quand
  ils portent sur la dynamique de l'entretien, pas sur le contenu. Plusieurs études portent explicitement sur la
  maltraitance physique intrafamiliale (Blasbalg et al., 2018 ; Ahern et al., 2014), ce qui correspond à nos scénarios.
- Aucune source ne donne des **probabilités par tour** directement utilisables. Les pistes donnent une direction et un
  ordre de grandeur. Les valeurs resteront `estimated`.

---

## 3. Tableau des affirmations du modèle

| # | Règle du modèle | Emplacement | Verdict | Sources |
|---|---|---|---|---|
| M1 | La réticence baisse de 0,08 par énoncé de soutien et de 0,04 par invitation de rapport | `support_reluctance_drop`, `rapport_reluctance_drop` | soutenu (direction) | Blasbalg et al. (2018, 2019) ; Ahern et al. (2014) ; Hershkowitz et al. (2014) |
| M2 | La réticence ne remonte jamais | `engine._apply_phase_effects` | **contredit** | Katz et al. (2012) ; Bücken et al. (2026) ; Hershkowitz et al. (2006) |
| M3 | Le dévoilement survient quand la pression cumulée atteint réticence × 5 ; une suggestive pèse 3, une invitation 1 | `disclosure_threshold_scale`, `disclosure_pressure` | partiel | Hershkowitz et al. (2006) ; Lyon & Ahern (2011) |
| M4 | Au-delà d'une réticence de 0,9, aucun dévoilement | `no_disclosure_reluctance` | soutenu (le non-dévoilement d'enfants victimes est fréquent) | Bücken et al. (2026) et sources citées |
| M5 | Aucune mémoire d'une séance à l'autre | `session.py` | sans donnée côté modèle ; la littérature montre que le soutien en séance 1 prépare le dévoilement en séance 2 | Hershkowitz et al. (2021) |
| M6 | Le soutien n'agit pas sur l'acquiescement | `_apply_phase_effects` | **contredit** | Saywitz et al. (2019) |
| M7 | Chaque règle de base baisse l'acquiescement de 0,12, jusqu'à 3 règles | `ground_rule_acquiescence_drop`, `max_effective_ground_rules` | partiel (trop fort sur le terrain, dépend de la pratique et de l'âge) | Earhart et al. (2014) ; Brubacher et al. (2015) |
| M8 | La pratique narrative augmente la verbosité de 0,1 par tour, jusqu'à 3 tours | `narrative_practice_verbosity_boost` | soutenu (direction) ; la pratique **épisodique** compte | Brubacher et al. (2011) ; Sternberg et al. (1997) |
| M9 | Une invitation livre les unités centrales d'abord, puis dans l'ordre chronologique | `engine._narrate` | partiel (pas de source pour « central d'abord » ; l'ordre des événements est la référence temporelle la plus fréquente, mieux tenue avec l'âge) | Orbach & Lamb (2007) |
| M10 | Une invitation indicée cible le segment d'une unité citée, pas un segment de temps | `engine._cued_invitation` | **écart au protocole** : le NICHD segmente aussi par le temps (« de X jusqu'à Y ») | Lamb et al. (2007) ; Orbach & Lamb (2007) |
| M11 | « Est-ce que tu sais… ? » est traité comme une question oui/non ordinaire | classifieur, `_yes_no` | partiel : les enfants répondent souvent « oui » sans le détail implicite | Evans et al. (2014, 2017) |
| M12 | Question à choix : récence chez les jeunes, « je sais pas » sinon | `p_recency`, `p_correct_option` | soutenu ; l'option « autre chose » n'aide presque pas | London et al. (2017) ; revue §5.2 |
| M13 | Une question répétée est traitée comme une première question | (absent) | **contredit** | Krähenbühl et al. (2009) |
| M14 | Formes du mensonge : omission, déni, feinte d'ignorance, minimisation, version de couverture | ADR 0002, `deception_load` | soutenu ; l'omission domine largement le déni actif | Talwar et al. (2004) |
| M15 | La force de la dissimulation ne dépend pas de l'âge ; la cohérence du mensonge non plus | `scenario.deception.strength` | partiel : la feinte d'ignorance et la cohérence (contrôle des fuites) progressent avec l'âge | Talwar et al. (2007) |
| M16 | Le soutien fait baisser la dissimulation ; la pression la fait monter | `support_concealment_drop`, `pressure_concealment_rise` | soutenu (direction) | Lyon & Dorado (2008) ; Lyon et al. (2008) |
| M17 | Pas d'acte « promesse de dire la vérité » | classifieur, `engine` | **manque** : la promesse réduit le mensonge sans augmenter les fausses déclarations | Talwar et al. (2004) ; Lyon & Dorado (2008) ; Lyon et al. (2008) |
| M18 | Rétractation possible sous un seuil de dissimulation (0,35), dans l'entretien | `retraction_threshold`, `p_retraction` | sans donnée dans l'entretien ; entre séances, la rétractation dépend de l'âge, de l'auteur et du soutien du parent non agresseur | Malloy et al. (2007) |
| M19 | Pas de signature non verbale ni vocale du mensonge ; poids du mensonge 0,15 dans l'hésitation | ADR 0003, `hesitation_weights` | soutenu | Gongola et al. (2017) ; revue (DePaulo et al., 2003 ; Sporer & Schwandt, 2006) |
| M20 | Le regard détourné vient de l'activation et de l'effort de mémoire | `demeanor.py` | soutenu | Doherty-Sneddon & Phelps (2005) ; Phelps et al. (2006) |
| M21 | Les jeunes bougent plus, les plus âgés montrent moins | `expression_style_default`, `demeanor_fidget_base` | soutenu (direction) | Katz et al. (2012) |
| M22 | Peu d'émotion visible possible malgré l'événement (style figé) | `expression_gains` | soutenu | Sayfan et al. (2008) |
| M23 | Le soutien baisse l'activation, donc réduit les signes visibles | `arousal_drop.support` | **contredit en partie** : le soutien va avec plus d'expression non verbale | Karni-Visel et al. (2023) |
| M24 | Le corps ne précède pas la parole : les signes suivent la réponse du tour | `demeanor.py` | partiel : les signes non verbaux sont plus fréquents que les verbaux et les précèdent | Karni-Visel et al. (2023) |
| M25 | Le désengagement ne dépend que de l'activation | `demeanor.py` | partiel : le désengagement physique est plus fréquent chez les non-révélants et augmente au fil de l'entretien | Katz et al. (2012) |
| M26 | L'activation n'influe pas sur les actes de langage | ADR 0003 | soutenu comme choix prudent : les effets du stress sur l'exactitude sont mitigés | Quas et al. (2004) ; Pipe et al. (2004, S) |
| M27 | Silence avant réponse plus long que chez l'adulte (550 à 900 ms selon l'âge) | `delivery_base_onset_ms` | soutenu (direction) : le temps de réponse des enfants est environ le double des pauses entre adultes | Rezmer et al. (2020, S pour le facteur 2) |
| M28 | L'enfant ne complète pas sa réponse si l'interviewer attend | (absent) | **manque** : une attente de 10 s après la réponse fait ajouter de l'information | Rezmer et al. (2020) |
| M29 | Pas de fatigue | ADR 0003 (reporté) | sans donnée : la fatigue est une préoccupation des guides, pas un effet mesuré | NCAC (guides de pratique) |
| M30 | Un enfant émotif est-il plus crédible ? (côté formation, pas moteur) | — | à enseigner : l'enfant triste paraît plus crédible aux jurés, à tort | Rowsell & Colloff (2022) ; Golding et al. (2003, S) |

---

## 4. Constats par axe

### 4.1 Réticence et dévoilement (M1–M5)

- **Les dynamiques diffèrent entre enfants qui révèlent et enfants qui ne révèlent pas.** Sur 50 + 50 entretiens
  NICHD d'enfants de 4 à 13 ans, avec des preuves externes de l'abus, les interviewers des non-révélants ont posé moins
  d'invitations et donné moins de soutien (Hershkowitz et al., 2006 ; R). Les études suivantes résument ce résultat
  ainsi : retrait du soutien, exploration prématurée de l'abus et questions intrusives (S).
- **Le soutien réduit la réticence, qui elle-même explique en partie l'informativité.** Ce résultat vient de 200 entretiens
  d'enfants de 6 à 14 ans victimes présumées de maltraitance physique intrafamiliale (Blasbalg et al., 2018 ; R). Il se
  retrouve sur 254 entretiens, protocole révisé contre standard (Blasbalg et al., 2019 ; R).
- **La réticence est suivie tour par tour.** Sur 199 entretiens d'enfants de 3 à 13 ans, le protocole révisé donne plus de
  soutien. Les interviewers ne répondent pourtant pas spécifiquement à la réticence par du soutien. Quand ils le font,
  la coopération est immédiate (Ahern et al., 2014 ; R).
- **La réaction de l'interviewer à « je sais pas » et au déni compte** (Bücken et al., 2026 ; T, 68 entretiens
  néerlandais).
  - Les interviewers rejettent 63 % des énoncés d'évitement et 49 % des dénis, formés au NICHD ou non.
  - Un enfant dont la réticence est acceptée donne une réponse productive **environ 7 fois plus souvent** qu'un enfant
    dont la réticence est rejetée.
  - Après un rejet, 76 à 81 % des enfants finissent par répondre (Grung et al., 2024 ; Earhart et al., 2014 ; S, cités
    dans Bücken et al.), avec un risque de réponse de complaisance.
  - Le non-dévoilement est fréquent chez des enfants réellement victimes. Lyon (2007) rapporte 58 % de dénis chez des
    enfants porteurs d'une infection sexuellement transmissible. Les taux de déni vont de 4 à 76 %, avec une moyenne de
    36 % (London et al., 2005, 2008). Eisen et al. (2021) trouvent 44 % de dénis faux en cas d'abus physique avéré.
    Ces trois chiffres sont des S.
- **Le stress et le désengagement physique montent au fil de l'entretien, et les émotions positives baissent**
  (Katz et al., 2012 ; R, 40 entretiens).
- **Deux séances.** Sur 204 enfants restés réticents en séance 1, 104 révèlent en séance 2, quelques jours plus tard. Le
  soutien de la séance 1 prédit la coopération en séance 2, qui prédit des allégations spontanées (Hershkowitz et al.,
  2021 ; R).
- **Les questions directes ont une place.** Il est difficile d'obtenir certains dévoilements sans question directe. Les
  oui/non directs donnent cependant des réponses ambiguës, surtout chez les plus jeunes (Lyon & Ahern, 2011 ; R).

**Verdicts.**
- M1 est soutenu.
- M2 est contredit : la réticence doit pouvoir remonter, sous l'effet du rejet, de la pression et de l'avancée dans
  l'entretien.
- M3 est partiel. Que la pression focalisée obtienne parfois un dévoilement est plausible. Mais le modèle ne lui fait payer
  aucun coût sur la réticence, et il en fait le chemin le plus rapide.
- M5 relève d'une extension future, des sessions en plusieurs séances.

### 4.2 Phases préparatoires (M6–M8)

- **Règles de base.**
  - Les études expérimentales montrent que la consigne augmente les « je sais pas » appropriés (Brubacher et al.,
    2015 ; R, synthèse).
  - Sur le terrain, la consigne ne change pas leur fréquence. Les interviewers rejettent près de 30 % des « je sais
    pas », puis posent des questions plus risquées (Earhart et al., 2014 ; R, 76 entretiens).
  - Les 4 à 6 ans réussissent moins bien les règles « je sais pas » et « corrige-moi » que les plus âgés. Même à 4 ans,
    ils répondent correctement aux questions d'entraînement plus de 80 % du temps (Dickinson et al., 2015 ; S).
- **Pratique narrative.** La pratique **épisodique** (« raconte-moi ce qui s'est passé quand… ») amène un langage plus
  épisodique dans la phase substantive que la pratique générique (Brubacher et al., 2011 ; R).
- **Soutien et suggestibilité.** Le soutien non conditionnel améliore l'exactitude, la résistance aux questions
  suggestives et réduit l'acquiescement. L'effet est modéré, sur une quinzaine d'études (Saywitz et al., 2019 ; R).
- **Rapport renforcé.** Mettre l'accent sur le rapport change la dynamique sans rendre les questions plus risquées
  (Hershkowitz et al., 2015 ; R).

**Verdicts.**
- M6 est contredit : le soutien devrait aussi baisser l'acquiescement.
- M7 est partiel : effet plus faible sur le terrain, conditionné à une question d'entraînement et à l'âge.
- M8 est soutenu, avec une nuance : seule la pratique épisodique devrait compter.

### 4.3 Organisation du récit (M9–M11)

- **Le temps.** Sur 250 entretiens NICHD d'enfants de 4 à 10 ans, les références temporelles augmentent avec l'âge
  (Orbach & Lamb, 2007 ; R).
  - L'ordre des événements est le type de référence temporelle le plus fréquent (S).
  - Les questions de rappel en obtiennent plus que les questions de reconnaissance.
  - Les plus jeunes utilisent surtout des repères de court terme.
  - Le protocole NICHD découpe le récit en segments (« raconte-moi tout depuis X jusqu'à Y ») ; c'est le principe des
    invitations indicées par le temps (Lamb et al., 2007).
- **Questions en « quoi » et « comment ».** Les questions sur les actions sont les plus productives, en rapport comme en
  phase substantive (Ahern et al., 2018 ; R). Les questions de causalité, dont les « pourquoi », sont productives au
  tribunal (Andrews et al., 2016 ; S).
- **« Est-ce que tu sais / te souviens… ? »** En expérience, les enfants répondent « oui » sans le détail implicite 14 à
  18 % du temps, et cette erreur diminue avec l'âge (Evans et al., 2014 ; S). Dans des transcriptions de tribunal
  (4 à 9 ans), ils le font 46 % du temps (Evans & Lyon, 2012 ; S). Il suffit de poser ensuite la question implicite
  (Evans et al., 2017 ; R).

**Verdicts.**
- M9 est partiel. L'ordre chronologique est réaliste, mais « central d'abord » n'est pas sourcé. Chez les plus jeunes,
  un récit partiellement désordonné serait plus fidèle (S).
- M10 est un écart au protocole. C'est la cause du défaut des démos : « Raconte-moi la fin » donnait le début.
- M11 est partiel.
- « Ben non » en réponse à un « pourquoi » n'est pas un phénomène documenté. C'est un défaut de notre chaîne : une
  question ouverte causale ne doit jamais recevoir un oui/non.

### 4.4 Suggestibilité : compléments (M12, M13)

- **L'option « autre chose ».** Chez les 3 à 5 ans, elle ne change pas l'exactitude globale. Elle la fait passer de 15 à
  31 % seulement quand aucune option n'est juste, et les enfants spéculent toujours face à une question sans réponse
  possible (London et al., 2017 ; R).
- **Répétition.** Plus d'un quart des réponses changent à la répétition, en général vers moins d'exactitude. Face à une
  question sans réponse possible, l'invention augmente avec le nombre de répétitions (Krähenbühl et al., 2009 ; voir la
  revue §5.3).
- **Inversion développementale.** Les plus âgés peuvent être plus suggestibles quand la suggestion s'appuie sur des
  connaissances de script (Otgaar et al., 2017 ; S, cités par Bücken et al., 2026). C'est à garder en tête pour les
  10 à 12 ans, pas à implémenter maintenant.

**Verdicts.** M12 est soutenu. M13 est contredit : c'est un manque.

### 4.5 Mensonge et dissimulation (M14–M19)

- **Taux et formes** (Talwar et al., 2004 ; T). Un parent casse un jouet et demande à l'enfant de ne rien dire (enfants
  de 3 à 11 ans).
  - Au premier entretien, 48 à 54 % des enfants **ne nomment pas** le parent à « Qu'est-ce qui s'est passé ? ». Seuls 20
    à 33 % **nient** activement quand on leur demande si le parent l'a cassé.
  - La présence du parent ne change pas significativement les taux.
  - Un enfant qui ne risque pas d'être blâmé ment davantage (78 % ne nomment pas le parent, 49 % nient).
  - Après la promesse de dire la vérité (examen de compétence), le mensonge chute (de 48 à 15 % d'omissions, de 20 à 11 %
    de dénis, parent absent).
  - Pas d'effet de l'âge sur les questions critiques. Dans l'expérience 2, les 5 ans et moins acceptent plus souvent
    qu'« un autre » l'ait cassé.
- **Promesse et réassurance.** Chez des enfants maltraités de 4 à 7 ans, la promesse de dire la vérité augmente les
  révélations vraies sans augmenter les fausses (Lyon & Dorado, 2008 ; Lyon et al., 2008 ; R).
- **Cohérence du mensonge** (Talwar et al., 2007 ; R). La feinte d'ignorance stratégique et la capacité à ne pas se
  trahir dans les questions de suite (« contrôle des fuites sémantiques ») progressent avec la compréhension des
  croyances de second ordre, donc avec l'âge, pendant l'école primaire.
- **Rétractation entre séances.** Sur 257 cas, 23,1 % des enfants se rétractent (Malloy et al., 2007 ; R). La
  rétractation est plus probable chez les moins de 10 ans, quand l'auteur est une figure parentale ou vit au foyer, et
  quand le parent non agresseur ne soutient pas l'enfant.
- **Détection.** Environ 54 % d'exactitude (Gongola et al., 2017 ; R, S pour le chiffre). La détection est meilleure sur
  les vérités que sur les mensonges et sur les plus jeunes. Les professionnels ne font qu'à peine mieux que les profanes.

**Verdicts.**
- M14 est soutenu, mais la répartition doit favoriser l'omission.
- M15 est partiel : l'âge devrait jouer sur la cohérence, pas sur la volonté de cacher.
- M16 est soutenu.
- M17 est un manque.
- M18 n'a pas de donnée dans l'entretien.
- M19 est soutenu.

### 4.6 Corps et émotion (M20–M26)

- **Les signes non verbaux ne disent pas si l'enfant a révélé, mais renseignent sur la réticence** (Katz et al., 2012 ;
  R, 40 entretiens, la moitié révèlent).
  - Les non-révélants montrent plus de **désengagement physique** que les révélants, en introduction comme en phase
    substantive.
  - Le stress augmente au fil de l'entretien.
  - Les plus âgés cachent mieux leurs émotions.
  - Les auteurs déconseillent d'évaluer l'enfant sur son seul comportement non verbal.
- **Le soutien libère l'expression non verbale** (Karni-Visel et al., 2023 ; R, 100 entretiens). Les signes non verbaux
  d'émotion sont plus fréquents que les signes verbaux et les précèdent. Le soutien de l'interviewer est associé à plus
  d'expressivité, et l'émotion non verbale explique en partie le lien entre soutien et informativité.
- **Au dévoilement, l'affect est souvent neutre** (Sayfan et al., 2008 ; R).
- **Le regard sert à penser.** Des enfants de 8 ans détournent le regard d'autant plus que la question est difficile, en
  face à face comme en vidéo (Doherty-Sneddon & Phelps, 2005 ; R). Des enfants de 5 ans entraînés à détourner le regard
  répondent mieux (72,5 % contre 55,9 % de bonnes réponses ; Phelps et al., 2006 ; S pour les chiffres).
- **Stress et mémoire.** Les effets sur l'exactitude sont mitigés. La réactivité physiologique va avec une meilleure
  exactitude quand l'entretien est soutenant, et une moins bonne quand il ne l'est pas (Quas et al., 2004 ; R).

**Verdicts.**
- M20, M21, M22 et M26 sont soutenus.
- M23 est contredit en partie. Le modèle confond deux choses : l'**activation** (l'état intérieur, que le soutien peut
  apaiser) et l'**expressivité** (ce que l'enfant ose montrer, que le soutien augmente).
- M24 et M25 sont partiels.

### 4.7 Diction (M27, M28)

- Le temps de réponse des enfants est environ le double des pauses entre adultes (S, cité par Rezmer et al., 2020).
- **Une attente d'au moins 10 s après la réponse**, avant la question suivante, permet souvent aux enfants d'ajouter de
  l'information (Rezmer et al., 2020 ; R). C'est la seule étude sur le temps d'attente en entretien forensique selon une
  revue de 2024 (S).
- **Pas de source** reliant la latence à la réticence (recherche infructueuse). Les « je sais pas » ne signalent pas la
  réticence dans l'étude d'Earhart et al. (2014 ; R).

**Verdicts.**
- M27 est soutenu en direction.
- M28 est un manque, exploitable en mode vocal, puisque le moteur reçoit déjà la chronologie de l'apprenant.
- Les poids d'hésitation autres que le mensonge restent sans donnée.

### 4.8 Durée et fatigue (M29)

Les guides de pratique demandent de surveiller la fatigue et de faire des pauses (NCAC). Aucune étude trouvée ne mesure
l'effet de la durée sur la productivité. La revue existante cite en revanche une efficacité des invitations **croissante**
au fil de l'entretien (Johnson et al., 2025). **Verdict** : rester reporté. Le désengagement progressif (§4.6) est mieux
documenté que la fatigue.

### 4.9 Ce que la formation peut enseigner (M30)

Les jurés jugent plus crédible un enfant qui paraît triste (revue systématique, 8 études, 2 148 participants ; Rowsell
& Colloff, 2022 ; R). Les pleurs seuls ont des effets moins constants (Golding et al., 2003 ; Cooper et al., 2014 ; S).
Ce n'est pas une règle du moteur, mais un message pour le bilan : un enfant calme n'est pas moins crédible.

---

## 5. Pistes d'adaptation : vue d'ensemble

Classement par rapport bénéfice/effort. « Garde-fous » renvoie aux ADR 0001 (le LLM ne décide pas), 0002 (paires
contrôlées mensonge/vérité, flux aléatoires séparés), 0003 (pas de signature non verbale du mensonge) et 0004 (pas de
fuite dans le suivi). Toute piste qui touche aux décisions doit **rejouer à l'identique les journaux du MVP** quand
elle n'est pas déclenchée, ou être isolée derrière un paramètre.

| Priorité | Piste | Preuve | Effort | Touche |
|---|---|---|---|---|
| 1 | A1 Réaction au « je sais pas » et au déni | terrain, séquentiel | moyen | `engine` (réticence, acquiescement) |
| 1 | A2 Répétition des questions | expérimental | moyen | `engine` (mémoire des questions) |
| 1 | A3 Coût de la pression sur la réticence | terrain | faible | `engine._apply_phase_effects`, `parameters.yaml` |
| 1 | A4 Invitations par segment de temps | protocole, terrain | faible | classifieur (indice de segment), `engine._cued_invitation` |
| 1 | A5 « Est-ce que tu sais / te souviens… ? » | expérimental et tribunal | faible | classifieur (sous-type), `engine._yes_no` |
| 2 | A6 Le soutien baisse aussi l'acquiescement | méta-analyse expérimentale | faible | `parameters.yaml` |
| 2 | A7 Règles de base conditionnées à l'entraînement et à l'âge | terrain + synthèse | faible | `parameters.yaml`, indice de phase |
| 2 | A8 Promesse de dire la vérité | expérimental | faible | classifieur (règle de base « promesse »), `concealment` |
| 2 | A9 Omission avant déni ; cohérence du mensonge selon l'âge | expérimental | moyen | `engine` (choix de la forme), `parameters.yaml` par bande |
| 2 | A10 Séparer activation et expressivité ; désengagement lié à la réticence | terrain | moyen | `demeanor.py`, ADR 0003 (avenant) |
| 3 | A11 Signes non verbaux en avance sur le dévoilement | terrain | moyen | `demeanor.py` |
| 3 | A12 Temps d'attente : l'enfant complète après un silence | expérimental | moyen | `session.py` (mode vocal) |
| 3 | A13 Pratique narrative épisodique seulement | expérimental | faible | classifieur (indice), `parameters.yaml` |
| 3 | A14 Plusieurs séances et rétractation | terrain | fort | `session.py`, scénario (soutien du parent) |
| — | A15 Aucune réponse oui/non à une question ouverte causale | défaut de la chaîne | faible | `engine`, tests |

---

## 6. Fiches

### A1. Réaction de l'interviewer au « je sais pas » et au déni

- **Constat.**
  - Accepter la réticence rend une réponse productive environ 7 fois plus probable que la rejeter (Bücken et al., 2026).
  - Un soutien après une réticence donne une coopération immédiate (Ahern et al., 2014).
  - Les rejets sont fréquents (30 à 63 %). Après un rejet, la plupart des enfants répondent quand même, avec un risque de
    complaisance (Earhart et al., 2014 ; Grung et al., 2024).
- **Proposition.** Le moteur mémorise le dernier acte de l'enfant. Si c'était `dont_know`, `reluctant` ou un déni :
  - **acceptation**, c'est-à-dire soutien, facilitateur ou passage à un autre sujet : la réticence baisse
    (`acceptance_reluctance_drop`) ;
  - **rejet**, c'est-à-dire même cible reposée, en particulier en question fermée ou suggestive : la réticence monte
    (`rejection_reluctance_rise`), et l'acquiescement monte aussi pour ce tour (`rejection_acquiescence_boost`). C'est ce
    qui produit la réponse de complaisance.
  - La détection « même cible » se calcule dans le moteur (cible du tour précédent), sans LLM.
- **Suivi (coaching).** Une alerte « rejet d'un je sais pas » ne dépend que de ce que l'apprenant a dit et du tour
  précédent. Elle ne révèle rien du scénario (ADR 0004).
- **Test.** Paires contrôlées sur la même seed : un « je sais pas » suivi d'une acceptation, puis d'une invitation, doit
  donner plus d'unités vraies qu'un « je sais pas » suivi d'un rejet. Le rejet doit augmenter le taux d'acquiescement à
  la suggestive suivante. Les journaux du MVP sans ces séquences se rejouent à l'identique.

### A2. Répétition des questions

- **Constat.** Plus d'un quart des réponses changent à la répétition, vers moins d'exactitude. L'invention augmente avec
  le nombre de répétitions d'une question sans réponse possible (Krähenbühl et al., 2009).
- **Proposition.** Compteur par (cible, forme fermée) dans l'état. À partir de la 2ᵉ occurrence :
  - `p_change_on_repeat` : l'enfant abandonne sa réponse précédente ;
  - `p_confabulation` multiplié par un facteur qui croît avec le compteur, pour une cible hors scénario ;
  - un fait vrai déjà dit reste stable plus souvent qu'une réponse devinée.
  - Lien avec A1 : une répétition après « je sais pas » est un rejet.
- **Garde-fous.** Le compteur ne s'applique qu'aux formes fermées. Une invitation répétée (« et quoi d'autre ? ») est
  normale.
- **Test.** Courbe du taux d'invention selon le nombre de répétitions, croissante et du même ordre que Krähenbühl et al.
  (2009).

### A3. Coût de la pression sur la réticence

- **Constat.** Moins d'invitations, moins de soutien et des questions intrusives caractérisent les entretiens sans
  dévoilement (Hershkowitz et al., 2006). Le stress monte au fil de l'entretien (Katz et al., 2012).
- **Proposition.** Une question suggestive ou à choix sur l'événement cible, **avant le dévoilement**, augmente la
  réticence (`pressure_reluctance_rise`, proportionnel à la réticence courante). La pression cumulée continue de compter :
  un enfant peu réticent peut dévoiler sous la pression, un enfant très réticent se ferme. Les pressions de
  `disclosure_pressure` sont à recalibrer pour que l'invitation reste, en moyenne, le chemin le plus sûr vers le
  dévoilement.
- **Test.** Sur les scénarios réticents, le dévoilement par invitations et soutien doit être plus probable que par
  suggestives répétées (simulation sur 100 seeds).

### A4. Invitations par segment de temps

- **Constat.** Le NICHD segmente le récit par le temps (Lamb et al., 2007). Les références à l'ordre des événements sont
  les plus fréquentes (Orbach & Lamb, 2007). Dans les démos, « Raconte-moi la fin » donnait le début.
- **Proposition.** Le classifieur ajoute un indice de segment (`before` / `during` / `after`) aux invitations indicées par
  le temps : « la fin », « ce qui s'est passé après », « avant que… ». `_cued_invitation` prend alors le segment de
  l'indice. Les scénarios ont déjà ces segments (`scenario.py`).
- **Test.** Jeu de test du classifieur (10 à 20 énoncés), puis un test moteur : « Raconte-moi la fin » ne livre que des
  unités `after`.

### A5. « Est-ce que tu sais / te souviens… ? »

- **Constat.** Les enfants répondent « oui » sans le détail implicite : 14 à 18 % en expérience, 46 % dans des
  transcriptions de tribunal chez les 4 à 9 ans. L'erreur diminue avec l'âge (Evans et al., 2014, 2017 ; Evans & Lyon,
  2012).
- **Proposition.** Sous-type `knowledge_question` dans le classifieur (oui/non qui demande implicitement une
  information). Le moteur répond par l'acte « oui » sans unité, avec `p_unelaborated_yes` par bande d'âge, sinon comme
  une directive. Le bilan conseille de poser directement la question implicite.
- **Test.** Taux de « oui » sans détail par bande sur 100 seeds, décroissant avec l'âge.

### A6. Le soutien baisse aussi l'acquiescement

- **Constat.** Méta-analyse expérimentale : moins d'acquiescement et plus de résistance aux suggestions avec un
  interviewer soutenant (Saywitz et al., 2019).
- **Proposition.** `support_acquiescence_drop` (petit, avec un plafond comme les règles de base).
- **Test.** Après deux énoncés de soutien, le taux d'acquiescement à une suggestive baisse par rapport à aucun soutien.

### A7. Règles de base conditionnées à l'entraînement et à l'âge

- **Constat.** Sur le terrain, la consigne seule ne change pas la fréquence des « je sais pas » (Earhart et al., 2014).
  Les jeunes réussissent moins bien les règles, et la pratique compte (Brubacher et al., 2015).
- **Proposition.** Effet réduit pour une règle simplement énoncée. Effet plein quand elle est suivie d'une question
  d'entraînement (indice de phase `ground_rules` + question d'essai). Facteur d'âge sur l'effet (`ground_rule_age_factor`).
- **Test.** Paires : règle énoncée seule contre règle pratiquée, puis même question sans réponse possible.

### A8. Promesse de dire la vérité

- **Constat.** La promesse réduit le mensonge sur la faute d'un parent (Talwar et al., 2004 : omissions de 48 à 15 %,
  parent absent). Elle augmente les révélations vraies sans augmenter les fausses chez de jeunes enfants maltraités
  (Lyon & Dorado, 2008 ; Lyon et al., 2008).
- **Proposition.** Une règle de base « promesse » reconnue par le classifieur fait baisser `concealment`
  (`promise_concealment_drop`). Elle n'a aucun effet sur la confabulation.
- **Garde-fous.** Paires contrôlées mensonge/vérité inchangées (ADR 0002). La promesse agit sur la décision, jamais sur la
  diction.
- **Test.** Sur s08, la part des faits protégés révélés est plus élevée avec la promesse que sans, à seed égale.

### A9. Omission avant déni ; cohérence du mensonge selon l'âge

- **Constat.** L'omission (ne pas nommer) est bien plus fréquente que le déni actif (Talwar et al., 2004). La feinte
  d'ignorance cohérente et le contrôle des fuites progressent avec l'âge (Talwar et al., 2007).
- **Proposition.**
  - Une invitation ne produit qu'une omission. Le déni n'arrive que sur une question focalisée : c'est déjà le cas dans
    `_narrate` et `_lie_to_focused`, à vérifier sur les taux simulés.
  - Ajouter `p_leak` par bande d'âge : sur une question de suite à propos d'un fait protégé, un jeune enfant laisse
    échapper un détail qui contredit son mensonge.
- **Garde-fous.** La fuite est un contenu verbal décidé par le moteur, pas un signe du corps (ADR 0003).
- **Test.** Taux de fuite décroissant avec l'âge ; répartition omission/déni du même ordre que Talwar et al. (2004).

### A10. Séparer activation et expressivité ; désengagement lié à la réticence

- **Constat.** Le soutien va avec plus d'expression non verbale (Karni-Visel et al., 2023). Les non-révélants montrent
  plus de désengagement physique (Katz et al., 2012).
- **Proposition.**
  - Une variable `expressivity` (0 à 1), relevée par le soutien et le rapport, multiplie le gain moteur des signes
    d'émotion (pleurs, tremblement, crispation).
  - Le désengagement (repli, regard fuyant) suit la réticence en plus de l'activation.
  - Avenant à l'ADR 0003.
- **Garde-fous.** Aucune des deux variables ne dépend du mensonge.
- **Test.** Après du soutien, à activation égale, plus de signes d'émotion. Chez un enfant réticent, plus de repli.

### A11. Signes non verbaux en avance sur le dévoilement

- **Constat.** Les signes non verbaux précèdent les signes verbaux (Karni-Visel et al., 2023).
- **Proposition.** Quand la pression approche le seuil de dévoilement sans l'atteindre, l'activation monte un peu : le
  corps « annonce » ce qui vient.
- **Garde-fous.** Ce n'est pas un indice de vérité. Le même mécanisme vaut pour un fait vrai ou caché, et l'apprenant ne
  voit pas la cause.
- **Test.** À la seed fixée, la courbe d'activation monte dans les tours qui précèdent le dévoilement.

### A12. Temps d'attente

- **Constat.** Une attente de 10 s après la réponse fait souvent ajouter de l'information (Rezmer et al., 2020).
- **Proposition.** En mode vocal, si l'apprenant laisse un silence au-delà d'un seuil après la réponse, le moteur produit
  un tour « suite » (comme un facilitateur) sans question. En texte, un bouton « attendre ».
- **Test.** À seed égale, un silence long rapporte des unités en plus.

### A13. Pratique narrative épisodique

- **Constat.** C'est la pratique épisodique qui transfère (Brubacher et al., 2011).
- **Proposition.** Le gain de verbosité ne s'applique qu'aux invitations de pratique sur un événement précis.
- **Test.** Jeu de test du classifieur avec des pratiques génériques (« qu'est-ce que tu fais d'habitude ») et épisodiques.

### A14. Plusieurs séances et rétractation

- **Constat.**
  - Le soutien en séance 1 prépare le dévoilement en séance 2 (Hershkowitz et al., 2021).
  - 23 % de rétractations entre séances, plus probables chez les moins de 10 ans, avec un auteur parent, et sans le
    soutien du parent non agresseur (Malloy et al., 2007).
- **Proposition.** Persister l'état de l'enfant entre séances. Ajouter au scénario un trait « soutien du parent non
  agresseur ».
- **Garde-fous.** Ce chantier est gros et touche le format des journaux. À traiter seulement si la formation vise les
  entretiens répétés.

### A15. Pas de oui/non à une question ouverte causale

- **Constat.** C'est un défaut de la chaîne, pas un phénomène documenté : « Ben non » répondait à un « pourquoi ».
- **Proposition.** Tracer la classification de ce tour. Le moteur ne doit pas émettre d'acte oui/non quand la question
  n'est pas fermée.
- **Test.** Ajouter le cas au jeu de test du classifieur, plus un test moteur qui l'interdit.

---

## 7. Ce que nous n'avons pas trouvé

- Des probabilités par tour (dévoilement, changement de réponse, fuite) dans le format NICHD, par tranche d'âge.
- Une source reliant la **latence** ou les « euh » à la réticence.
- Des données sur la fatigue et la longueur de l'entretien.
- Une base empirique pour « central d'abord » dans le récit libre, et pour les poids de diction autres que le mensonge.
- Une signature non verbale fiable de quoi que ce soit : c'est en soi un résultat qui protège la règle de l'ADR 0003.

À faire ensuite :
1. Lire en texte intégral Katz et al. (2012), Karni-Visel et al. (2023), Bücken et al. (2026, résultats) et Saywitz et
   al. (2019), pour les tailles d'effet.
2. Faire valider les pistes A1, A3 et A10 par un formateur NICHD.

---

## 8. Bibliographie (APA 7)

- Ahern, E. C., Andrews, S. J., Stolzenberg, S. N., & Lyon, T. D. (2018). The productivity of wh- prompts in child forensic interviews. *Journal of Interpersonal Violence, 33*(13), 2007–2015. https://doi.org/10.1177/0886260515621084
- Ahern, E. C., Hershkowitz, I., Lamb, M. E., Blasbalg, U., & Winstanley, A. (2014). Support and reluctance in the pre-substantive phase of alleged child abuse victim investigative interviews: Revised versus standard NICHD protocols. *Behavioral Sciences & the Law, 32*(6), 762–774. https://doi.org/10.1002/bsl.2149
- Blasbalg, U., Hershkowitz, I., & Karni-Visel, Y. (2018). Support, reluctance, and production in child abuse investigative interviews. *Psychology, Public Policy, and Law, 24*(4), 518–527. https://doi.org/10.1037/law0000183
- Blasbalg, U., Hershkowitz, I., Lamb, M. E., Karni-Visel, Y., & Ahern, E. C. (2019). Is interviewer support associated with the reduced reluctance and enhanced informativeness of alleged child abuse victims? *Law and Human Behavior, 43*(2), 156–165. https://doi.org/10.1037/lhb0000303
- Brubacher, S. P., Poole, D. A., & Dickinson, J. J. (2015). The use of ground rules in investigative interviews with children: A synthesis and call for research. *Developmental Review, 36*, 15–33. https://doi.org/10.1016/j.dr.2015.01.001
- Brubacher, S. P., Roberts, K. P., & Powell, M. (2011). Effects of practicing episodic versus scripted recall on children's subsequent narratives of a repeated event. *Psychology, Public Policy, and Law, 17*(2), 286–314. https://doi.org/10.1037/a0022793
- Bücken, C. A., Erens, B., de Ruiter, C., Raymaekers, L., & Otgaar, H. (2026). Navigating reluctance in Dutch child forensic interviews: Interviewers tend to reject avoidant and denial statements regardless of NICHD protocol training. *Psychology, Public Policy, and Law, 32*(3), 342–356. https://doi.org/10.1037/law0000484
- Doherty-Sneddon, G., & Phelps, F. G. (2005). Gaze aversion: A response to cognitive or social difficulty? *Memory & Cognition, 33*(4), 727–733. https://doi.org/10.3758/BF03195338
- Earhart, B., La Rooy, D. J., Brubacher, S. P., & Lamb, M. E. (2014). An examination of "don't know" responses in forensic interviews with children. *Behavioral Sciences & the Law, 32*(6), 746–761. https://doi.org/10.1002/bsl.2141
- Evans, A. D., Stolzenberg, S. N., & Lyon, T. D. (2017). Pragmatic failure and referential ambiguity when attorneys ask child witnesses "do you know/remember" questions. *Psychology, Public Policy, and Law, 23*(2), 191–199. https://doi.org/10.1037/law0000116
- Gongola, J., Scurich, N., & Quas, J. A. (2017). Detecting deception in children: A meta-analysis. *Law and Human Behavior, 41*(1), 44–54. https://doi.org/10.1037/lhb0000211
- Hershkowitz, I., Lamb, M. E., Blasbalg, U., & Karni-Visel, Y. (2021). The dynamics of two-session interviews with suspected victims of abuse who are reluctant to make allegations. *Development and Psychopathology, 33*(2), 739–747. https://doi.org/10.1017/S0954579420001820
- Hershkowitz, I., Lamb, M. E., & Katz, C. (2014). Allegation rates in forensic child abuse investigations: Comparing the revised and standard NICHD protocols. *Psychology, Public Policy, and Law, 20*(3), 336–344. https://doi.org/10.1037/a0037391
- Hershkowitz, I., Lamb, M. E., Katz, C., & Malloy, L. C. (2015). Does enhanced rapport-building alter the dynamics of investigative interviews with suspected victims of intra-familial abuse? *Journal of Police and Criminal Psychology, 30*(1), 6–14. https://doi.org/10.1007/s11896-013-9136-8
- Hershkowitz, I., Orbach, Y., Lamb, M. E., Sternberg, K. J., & Horowitz, D. (2006). Dynamics of forensic interviews with suspected abuse victims who do not disclose abuse. *Child Abuse & Neglect, 30*(7), 753–769. https://doi.org/10.1016/j.chiabu.2005.10.016
- Karni-Visel, Y., Hershkowitz, I., Lamb, M. E., & Blasbalg, U. (2023). Nonverbal emotions while disclosing child abuse: The role of interviewer support. *Child Maltreatment, 28*(1), 66–75. https://doi.org/10.1177/10775595211063497
- Katz, C., Hershkowitz, I., Malloy, L. C., Lamb, M. E., Atabaki, A., & Spindler, S. (2012). Non-verbal behavior of children who disclose or do not disclose child abuse in investigative interviews. *Child Abuse & Neglect, 36*(1), 12–20. https://doi.org/10.1016/j.chiabu.2011.08.006
- Lamb, M. E., Orbach, Y., Hershkowitz, I., Esplin, P. W., & Horowitz, D. (2007). A structured forensic interview protocol improves the quality and informativeness of investigative interviews with children: A review of research using the NICHD Investigative Interview Protocol. *Child Abuse & Neglect, 31*(11–12), 1201–1231. https://doi.org/10.1016/j.chiabu.2007.03.021
- London, K., Bruck, M., Ceci, S. J., & Shuman, D. W. (2005). Disclosure of child sexual abuse: What does the research tell us about the ways that children tell? *Psychology, Public Policy, and Law, 11*(1), 194–226. https://doi.org/10.1037/1076-8971.11.1.194
- London, K., Hall, A. K., & Lytle, N. E. (2017). Does it help, hurt, or something else? The effect of a something else response alternative on children's performance on forced-choice questions. *Psychology, Public Policy, and Law, 23*(3), 281–289. https://doi.org/10.1037/law0000129
- Lyon, T. D., & Ahern, E. C. (2011). Disclosure of child sexual abuse. In J. E. B. Myers (Ed.), *The APSAC handbook on child maltreatment* (3rd ed., pp. 233–252). Sage.
- Lyon, T. D., & Dorado, J. S. (2008). Truth induction in young maltreated children: The effects of oath-taking and reassurance on true and false disclosures. *Child Abuse & Neglect, 32*(7), 738–748. (déjà dans `parameters.yaml`)
- Lyon, T. D., Malloy, L. C., Quas, J. A., & Talwar, V. A. (2008). Coaching, truth induction, and young maltreated children's false allegations and false denials. *Child Development, 79*(4), 914–929. https://doi.org/10.1111/j.1467-8624.2008.01167.x
- Malloy, L. C., Lyon, T. D., & Quas, J. A. (2007). Filial dependency and recantation of child sexual abuse allegations. *Journal of the American Academy of Child & Adolescent Psychiatry, 46*(2), 162–170. https://doi.org/10.1097/01.chi.0000246067.77953.f7
- Orbach, Y., & Lamb, M. E. (2007). Young children's references to temporal attributes of allegedly experienced events in the course of forensic interviews. *Child Development, 78*(4), 1100–1120. https://doi.org/10.1111/j.1467-8624.2007.01055.x
- Phelps, F. G., Doherty-Sneddon, G., & Warnock, H. (2006). Helping children think: Gaze aversion and teaching. *British Journal of Developmental Psychology, 24*(3), 577–588. https://doi.org/10.1348/026151005X49872
- Quas, J. A., Bauer, A., & Boyce, W. T. (2004). Physiological reactivity, social support, and memory in early childhood. *Child Development, 75*(3), 797–814. https://doi.org/10.1111/j.1467-8624.2004.00707.x
- Rezmer, B. E., Trager, L. A., Catlin, M., & Poole, D. A. (2020). Pause for effect: A 10-s interviewer wait time gives children time to respond to open-ended prompts. *Journal of Experimental Child Psychology, 194*, 104824. https://doi.org/10.1016/j.jecp.2020.104824
- Rowsell, A. C., & Colloff, M. F. (2022). Are sad children more believable? A systematic review of the relationship between emotional presentation and credibility of child victims. *Psychology, Crime & Law, 28*(10), 943–966. https://doi.org/10.1080/1068316X.2021.1972109
- Sayfan, L., Mitchell, E. B., Goodman, G. S., Eisen, M. L., & Qin, J. (2008). Children's expressed emotions when disclosing maltreatment. *Child Abuse & Neglect, 32*(11), 1026–1036. https://doi.org/10.1016/j.chiabu.2008.03.004
- Saywitz, K. J., Wells, C. R., Larson, R. P., & Hobbs, S. D. (2019). Effects of interviewer support on children's memory and suggestibility: Systematic review and meta-analyses of experimental research. *Trauma, Violence, & Abuse, 20*(1), 22–39. https://doi.org/10.1177/1524838016683457
- Talwar, V., Gordon, H. M., & Lee, K. (2007). Lying in the elementary school years: Verbal deception and its relation to second-order belief understanding. *Developmental Psychology, 43*(3), 804–810. https://doi.org/10.1037/0012-1649.43.3.804
- Talwar, V., Lee, K., Bala, N., & Lindsay, R. C. L. (2004). Children's lie-telling to conceal a parent's transgression: Legal implications. *Law and Human Behavior, 28*(4), 411–435. https://doi.org/10.1023/B:LAHU.0000039333.51399.f6

**Cités par une source secondaire seulement (S)** : Andrews et al. (2016) ; Cooper, Quas & Cleveland (2014) ;
Dickinson, Brubacher & Poole (2015) ; Eisen et al. (2021) ; Evans et al. (2014) ; Evans & Lyon (2012) ; Golding et al.
(2003) ; Grung et al. (2024) ; London et al. (2008) ; Lyon (2007) ; Otgaar et al. (2017) ; Pipe et al. (2004).
Krähenbühl, Blades & Eiser (2009) et Johnson et al. (2025) sont référencés dans la [revue existante](revue-litterature.md).
