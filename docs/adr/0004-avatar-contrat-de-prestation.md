# ADR 0004 — Avatar : un contrat de prestation entre le moteur et le corps

- **Statut** : accepté
- **Date** : 2026-11-17
- **Prolonge** : [ADR 0002](0002-mensonge-diction-voix.md), [ADR 0003](0003-activation-comportement-non-verbal.md)

## Contexte

L'objectif final du projet est un **avatar d'enfant qu'on interroge en réalité virtuelle**. À chaque tour, le
moteur produit déjà tout ce qu'il faut pour animer un corps :
- les mots ;
- un plan d'élocution minuté (silences, « euh », faux départs) et, facultativement, l'audio Kokoro ;
- la diction (volume, débit, voix tremblante) ;
- le comportement non verbal (signes, intensités, activation, style).

Le choix du moteur de rendu VR (WebXR, Unity, Unreal) est lointain et le restera tant que le comportement
évolue. Il faut donc pouvoir changer de corps sans toucher au cerveau.

## Décision

1. **Un contrat de prestation versionné** (`src/nichd_sim/performance.py`, `PERFORMANCE_FORMAT = 1`).
   - Pour chaque tour, il donne :
     - la question entendue et la réponse ;
     - l'acte de langage et la didascalie ;
     - une **chronologie** de segments parlés et de silences, en millisecondes ;
     - la voix (volume, débit, tremblement, faux départs) ;
     - le corps (activation, style, signes avec leur famille et leur intensité) ;
     - le nom du fichier audio, s'il existe.
   - La chronologie est **mesurée sur l'audio** quand il est rendu. Sinon, elle est **estimée** : silences
     exacts, parole à environ 65 ms par caractère divisés par le débit.
   - Le schéma JSON est exporté (`json_schema()`), pour des corps écrits dans d'autres langages.
2. **Le contrat ne porte aucune cause**, ni aucun élément interne du moteur : pas de charge d'hésitation,
   pas de mensonge, pas de règle. Un corps montre l'enfant, il ne l'explique pas. Sinon, un corps pourrait
   « montrer » un mensonge, ce que les ADR 0002 et 0003 interdisent.
3. **Premier corps : three.js dans le navigateur** (`avatar/`), sans étape de build, avec three.js en version
   épinglée.
   - Le navigateur passe par le tunnel SSH, comme l'interface Streamlit.
   - **WebXR** permettra d'aller en VR (navigateur du casque) sans changer de pile.
4. **Les comportements fins sont des marqueurs de couleur et de mouvement simples**, assumés comme
   provisoires. Exemples : un halo coloré pour l'activation, la tête et les yeux tournés pour le regard, un
   membre qui oscille et jaunit pour l'agitation, une figure désaturée pour le figement. Une **légende**
   affiche toujours les signes actifs : sans elle, le marqueur n'est pas lisible.
5. **Premier jalon : le rejeu de journaux** (`nichd-sim export-avatar`, puis `nichd-sim avatar`).
   C'est déterministe, sans LLM, et idéal pour caler le contrat et les démos.
6. **Même dépôt pour l'instant**, dans un dossier `avatar/` qui ne contient aucune logique métier.
   - On séparera le jour où un moteur VR natif sera choisi : le contrat sera alors la seule interface.
   - Le client n'interprète que le contrat.

## Ajout : carte du système en arrière-plan (canal de débogage)

Pour les démonstrations et le débogage, `export-avatar --debug-map` produit à côté du contrat (`debug/`) la
carte du système de chaque tour, en 3 étapes : classification, décision, fin. L'avatar peut l'afficher derrière
l'enfant (bouton « Carte », `?map=1`).

Ces fichiers montrent les rouages du moteur, mensonges compris. Ils **ne font pas partie du contrat** : le
`performance.json` est identique avec ou sans cette option, et un corps de formation ne les reçoit pas.

## Jalons suivants

1. **Direct** : un serveur WebSocket autour de `Session.turn(on_step=…)` ; l'avatar répond pendant qu'on lui
   parle.
2. **WebXR** : la même scène dans un casque, avec l'interviewer face à l'enfant.
3. **Un vrai modèle 3D** (rig, morphologies faciales) à la place des marqueurs ; le contrat ne change pas.
4. Peut-être un horodatage plus fin des signes à l'intérieur d'un tour, s'il s'avère nécessaire (le contrat
   passerait alors en format 2).

## Conséquences

- Positives : le cerveau et le corps évoluent séparément. Le rejeu est exact. Aucun corps ne peut devenir un
  détecteur de mensonge.
- Négatives : les signes ne sont décidés qu'une fois par tour, et non à l'intérieur de la réponse. Les
  marqueurs de couleur ne remplacent pas une étude de plausibilité, qui reste à faire avec un vrai modèle.
