# Glossaire

Le code et les commentaires sont en anglais. Le contenu métier (prompts, skill, scénarios, interface, feedback) est en français. Ce glossaire fixe la correspondance entre les deux. Tout nouveau terme métier y est ajouté **avant** d'apparaître dans le code.

Voir aussi : [docs/design.md](docs/design.md).

## Acteurs et artefacts

| Français | Identifiant | Définition |
|---|---|---|
| Interviewer / apprenant | `interviewer`, `learner` | Personne en formation qui mène l'entretien. `interviewer` désigne son rôle dans le dialogue, `learner` son rôle pédagogique. |
| Enfant simulé | `child` | Personnage joué par le système. |
| Formateur | `trainer` | Expert NICHD qui valide scénarios et exemples. Il utilise le mode formateur. |
| Codeur humain | `human_coder` | Annotateur humain de l'étude d'accord. |
| Session | `session` | Un entretien complet, de l'ouverture à la fin. |
| Tour | `turn` | Un énoncé de l'interviewer et la réponse de l'enfant. |
| Énoncé | `utterance` | Une prise de parole, de l'interviewer ou de l'enfant. |
| Fiche de scénario | `scenario` | Fichier versionné : profil de l'enfant, faits de référence, événement neutre. |
| Journal de session | `session_log` | JSON autonome par session ; source de vérité, permet le rejeu. |
| Rejeu | `replay` | Reconstitution exacte d'une session à partir de son journal. |
| Seed | `seed` | Graine aléatoire qui rend le moteur déterministe. |

## Scénario

| Français | Identifiant | Définition |
|---|---|---|
| Profil de l'enfant | `child_profile` | Âge, réticence, compétences verbales, suggestibilité. |
| Bande d'âge | `age_band` | `4_6`, `7_9`, `10_12`. Fixe les paramètres par défaut et le registre linguistique. |
| Faits de référence | `ground_truth` | Ensemble des faits réels de l'événement. |
| Segment | `segment` | Partie chronologique de l'événement : `before`, `during`, `after`. |
| Unité d'information | `info_unit` | Plus petit fait vérifiable : `id`, `category`, `centrality`, `value`, `anchors`. |
| Catégorie | `category` | `who` (qui), `what` (quoi), `where` (où), `when` (quand), `frequency` (fréquence). |
| Centralité | `centrality` | `central` ou `peripheral` (périphérique). |
| Ancre | `anchor` | Mot ou expression rattaché à une unité. Sert aux invitations indicées et au contrôle de fuite. |
| Événement neutre | `neutral_event` | Mini-scénario non sensible (anniversaire, sortie) utilisé pendant la pratique narrative. |
| Événement cible | `target_event` | L'événement qui fait l'objet de l'audition. |

## Typologie des énoncés de l'interviewer

D'après Lamb et al.

| Français | Identifiant | Définition |
|---|---|---|
| Invitation | `invitation` | Question ouverte de rappel libre (« Dis-moi tout sur… »). |
| Invitation indicée | `cued_invitation` | Invitation qui reprend un détail déjà mentionné par l'enfant (« Tu as parlé de X, dis-m'en plus »). |
| Question directive | `directive` | Question en qui, quoi, où, quand, comment, portant sur un détail déjà mentionné. |
| Question à choix | `option_posing` | Question fermée ou à options (« C'était le jour ou la nuit ? »), ou oui/non sur un détail non mentionné. |
| Question suggestive | `suggestive` | Question qui présuppose ou induit une information non fournie par l'enfant. |
| Facilitateur | `facilitator` | Relance non suggestive (« hmm », « d'accord », « et après ? »). |
| Énoncé de règle | `ground_rule` | Énoncé d'une règle de base (« tu peux dire je ne sais pas »). |
| Énoncé de soutien | `support` | Énoncé de rapport ou de soutien non suggestif. |
| Question composée | `compound` | Plusieurs questions en un seul énoncé. Elle est classée selon son élément le plus directif et signalée. |
| Autre | `other` | Énoncé hors typologie, y compris les tentatives de détournement. |
| Cible | `target` | Unité visée par une question, ou `out_of_scenario` (hors scénario). |
| Proposition suggérée | `suggested_proposition` | Contenu introduit par l'interviewer dans une question suggestive ou à choix. |

## Phases de l'entretien

| Français | Identifiant |
|---|---|
| Rapport | `rapport` |
| Règles de base | `ground_rules` |
| Pratique narrative | `narrative_practice` |
| Transition | `transition` |
| Phase substantive | `substantive` |
| Clôture | `closure` |
| Violation de phase | `phase_violation` |
| Incitation de transition | `transition_prompt` |

## Moteur de comportement

| Français | Identifiant | Définition |
|---|---|---|
| Moteur de comportement | `behavior_engine` | Machine à états qui décide de chaque réponse. |
| Suivi des phases | `phase_tracker` | Machine à états qui infère la phase courante. |
| Réticence | `reluctance` | Variable d'état qui freine le dévoilement. |
| Verbosité | `verbosity` | Variable d'état qui module la quantité d'unités livrées par invitation. |
| Acquiescement | `acquiescence` | Propension à accepter une proposition suggérée. |
| Suggestibilité | `suggestibility` | Trait du profil qui influence l'acquiescement et l'intégration. |
| Seuil de dévoilement | `disclosure_threshold` | Niveau d'incitation de transition requis avant le premier dévoilement. |
| Dévoilement | `disclosure` | Première mention de l'événement cible par l'enfant. |
| Révéler une unité | `reveal` | Autoriser une unité vraie dans la réponse. |
| Contamination | `contamination` | Intégration durable d'un faux détail suggéré. |
| Unité contaminée | `contaminated_unit` | Faux détail intégré, rattaché à son tour d'origine (`source_turn`). |
| Confabulation | `confabulation` | Réponse inventée à une question hors scénario. |
| Suggestion tombée juste | `lucky_suggestion` | Question suggestive ou fermée dont la proposition s'avère vraie : pas de contamination, mais faute de technique. |
| Intégration | `integrated` | Un faux détail intégré peut réapparaître spontanément plus tard. |
| Type effectif | `effective_type` | Type de question auquel le moteur a appliqué ses règles (l'élément le plus directif d'une question composée). |
| Biais de récence | `recency_bias` | Tendance à choisir la dernière option proposée. |
| Acte de langage | `speech_act` | Ce que l'enfant fait dans le tour : `answer`, `dont_know`, `acquiesce`, `deny`, `confabulate` (inventer une réponse), `acknowledge` (accuser réception d'une règle ou d'un soutien), `confusion`, `silence`. |
| Décision | `decision` | Acte de langage et unités autorisées pour le tour. |
| Unités autorisées | `allowed_units` | Seules unités transmises au LLM pour le tour. |
| Paramètres | `parameters` | Probabilités et effets, chacun avec sa source. `estimated` si la valeur est extrapolée. |

## LLM et contrôle du contenu

| Français | Identifiant | Définition |
|---|---|---|
| Classifieur | `classifier` | Étiquette chaque énoncé de l'interviewer (type, cible, proposition). |
| Skill NICHD | `nichd_skill` | Répertoire versionné : spécification, exemples few-shot, schéma, jeu de test. |
| Réalisation linguistique | `realizer` | Transforme une décision en énoncé d'enfant. |
| Filtre de sortie | `output_filter` | Lexique interdit et contrôle de fuite. |
| Contrôle de fuite | `leak_check` | Vérifie qu'aucune ancre d'unité non autorisée n'apparaît dans la réponse. |
| Réponse type | `fallback_response` | Réponse prédéfinie par acte de langage, utilisée si le filtre échoue deux fois. |

## Évaluation et feedback

| Français | Identifiant | Définition |
|---|---|---|
| Proportion de questions ouvertes | `open_question_ratio` | (invitations + invitations indicées) / questions, en phase substantive. |
| Informations exactes recueillies | `accurate_info_recall` | Unités vraies révélées / total, avec les parts centrale et périphérique. |
| Score de contamination | `contamination_score` | Unités contaminées / (vraies révélées + contaminées). |
| Synthèse de l'apprenant | `learner_summary` | Récit rédigé par l'apprenant en fin de session (optionnel). |
| Retour structuré | `feedback_report` | Écran de fin de session : métriques, frise des phases, transcription annotée, reformulations. |
| Reformulation proposée | `suggested_rephrasing` | Version ouverte d'une question fermée, générée par le LLM. |
| Mode formateur | `trainer_mode` | Affichage en direct de la classification et de l'état du moteur. |
| Export pour codeurs | `coder_export` | CSV de transcription vierge pour l'étude d'accord. |
