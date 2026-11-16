# Criblage TTS — résultats bruts

| Variante | WER phrases | WER fragments (≤ 3 mots) | CER | F0 médiane | Débit 0,75 (attendu 1,33) | Hallucinations | Synthèse / segment | RTF |
|---|---|---|---|---|---|---|---|---|
| chatterbox-default | 18.9% | 215.8% | 62.8% | 150 Hz | 1.33 | 14 / 60 | 3.66 s | 0.91 |
| chatterbox-default-child | 17.9% | 215.8% | 61.0% | 192 Hz | 1.33 | 15 / 60 | 5.62 s | 1.43 |
| chatterbox-clone-kchild | 5.8% | 15.8% | 4.0% | 236 Hz | 1.33 | 1 / 60 | 5.06 s | 1.60 |
| kokoro-siwis | 3.8% | 10.5% | 3.3% | 215 Hz | 1.36 | 1 / 60 | 0.09 s | 0.03 |
| kokoro-siwis-child | 5.4% | 36.8% | 6.6% | 266 Hz | 1.31 | 0 / 60 | 0.10 s | 0.03 |

| Moteur | Chargement | Mémoire GPU (pic) | Déterministe (seed fixée) | Fréquence |
|---|---|---|---|---|
| chatterbox | 13.1 s | 4.39 Go | non | 24000 Hz |
| kokoro | 2.0 s | 0.98 Go | oui | 24000 Hz |

## Segments signalés et « euh »

- `chatterbox-default` c01 « J'avais » → « J'avais halein békaï djaït clash. » (3.7 s)
- `chatterbox-default` c03 « D'accord. » → « D'accord. » (4.7 s)
- `chatterbox-default` c04 « Non. » → « Non. Non. » (1.5 s)
- `chatterbox-default` c05 « était là. » → « Et de là, Antfor, maître Pals, was fard, with head N, and uttered to the town Pals, with head N, and othered to the religions. » (8.8 s)
- `chatterbox-default` c07 « Je suis tombée » → « Je suis tombé. Je suis... » (3.4 s)
- `chatterbox-default` c13 « La télé était allumée. » → « La télé était à l'aimé. Un d'eux, un d'eux entrant. Alors, il y a eu comme un d'eux hors d'off date. » (10.3 s)
- `chatterbox-default` c18 « Oui. C'était mardi après l'école, vers cinq heures. » → « Oui, c'est une idée à peu de code vers 5K. » (3.8 s)
- `chatterbox-default` c26 « Oui. C'était dimanche soir. » → « Oui, c'était dimanche soir. My old poor, un HSTM, comment ça? » (4.5 s)
- `chatterbox-default` c32 « Oui. C'était un mercredi, il y avait pas école. » → « Oui, c'était un mercredi, il n'y avait pas d'école. Des fois, et des fois, moi je me tenais comme un homme, c'était un mercredi. » (5.3 s)
- `chatterbox-default` c35 « Jade a pleuré très fort. » → « J'ai déploré Treffor. » (3.8 s)
- `chatterbox-default` c46 « Après on a mangé une pizza avec l'équipe. » → « Appelez-en à manger une pizza avec l'équipe. » (2.8 s)
- `chatterbox-default` c48 « Hein ? Je comprends pas. » → « Je ne comprends pas. Bye. » (2.1 s)
- `chatterbox-default` c49 « un bleu sur le bras. » → « Un bleu sur le bras. Un ventre, un tropif, un despair. Un bleu sur le bras. » (4.9 s)
- `chatterbox-default` c58 « Je leur ai donné les dix euros de la cantine. » → « Je leur ai donné les 10 euros de la cantine, chaque fois il y avait un, chaque fois un, chaque fois être gestion et docteur est donné les 10 euros de la cantine. » (7.2 s)
- `chatterbox-default` « euh… » : 5.16 s, entendu « Estabring and them all. And cool, cool. »
- `chatterbox-default-child` c01 « J'avais » → « J'avais, Halem Bekai, Jade Clash. » (3.7 s)
- `chatterbox-default-child` c03 « D'accord. » → « D'accord. » (4.7 s)
- `chatterbox-default-child` c04 « Non. » → « Non, non. » (1.5 s)
- `chatterbox-default-child` c05 « était là. » → « Etena, entre 4 matri-paules, was fard, with head N, and uttered to the town-paules, with head N, and othered to the religions. » (8.8 s)
- `chatterbox-default-child` c07 « Je suis tombée » → « Je suis tombé. Je suis... » (3.4 s)
- `chatterbox-default-child` c09 « Au début j'avais le trac. » → « Oh, des buts à faire attaquer ! » (1.6 s)
- `chatterbox-default-child` c13 « La télé était allumée. » → « La télé est un ennemi, un dice, un dice entrant, un diocum, un dice horde of dates. » (10.3 s)
- `chatterbox-default-child` c18 « Oui. C'était mardi après l'école, vers cinq heures. » → « Oui, c'est un mardi après l'école vers 5h. » (3.8 s)
- `chatterbox-default-child` c20 « C'était un mercredi, il y avait pas école. Je faisais du toboggan. » → « C'était un mercredi. Il n'y allait pas à l'école. Je faisais du toboggan. Oui, Joe et Pam. » (5.5 s)
- `chatterbox-default-child` c26 « Oui. C'était dimanche soir. » → « Oui, c'était dimanche soir. My old poor, un HSTM, comment ça? » (4.5 s)
- `chatterbox-default-child` c32 « Oui. C'était un mercredi, il y avait pas école. » → « Oui, c'était un mercredi, il n'y avait pas d'école. Des fours et des porcs, moi je me tenais comme un homme, c'était un mercredi. » (5.3 s)
- `chatterbox-default-child` c35 « Jade a pleuré très fort. » → « J'ai de pleuré trefours. » (3.8 s)
- `chatterbox-default-child` c48 « Hein ? Je comprends pas. » → « Je ne comprends pas. » (2.1 s)
- `chatterbox-default-child` c49 « un bleu sur le bras. » → « Un bleu sur le bras. Un peintre en tropif et en despair. Un bleu sur le bras. » (4.9 s)
- `chatterbox-default-child` c58 « Je leur ai donné les dix euros de la cantine. » → « Je leur ai donné les 10 euros de la cantine. Chapeau à Yéven. Chapeau à Anne. Chapeau à être gestion. Et docteur, j'ai donné les 10 euros de la cantine. » (7.2 s)
- `chatterbox-default-child` « euh… » : 5.16 s, entendu « S to bring in them all. And cool, cool. »
- `chatterbox-clone-kchild` c05 « était là. » → « était là. » (3.5 s)
- `chatterbox-clone-kchild` « euh… » : 1.06 s, entendu « Euh... »
- `kokoro-siwis` c48 « Hein ? Je comprends pas. » → « Je ne comprends pas. » (1.9 s)
- `kokoro-siwis` « euh… » : 0.75 s, entendu « Heu... »
- `kokoro-siwis-child` « euh… » : 0.76 s, entendu « Zut. »
