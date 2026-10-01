# MoodReel evaluation results

30 prompts · engines: embedder=`hashing`, vectors=`memory`, emotion=`lexicon`, llm=`rules`, catalogue=`119 films`

| Metric | Score |
|---|---|
| Understanding | 1.00 |
| Relevance | 0.99 |
| Constraints | 1.00 |
| Diversity | 0.67 |
| Reason Quality | 0.91 |
| Behaviour | 1.00 |

## By category

| Category | n | understanding | relevance | constraints | diversity | reason quality | behaviour |
|---|---|---|---|---|---|---|---|
| edge | 7 | 1.00 | 0.96 | 1.00 | 0.69 | 0.90 | 1.00 |
| everyday | 8 | 1.00 | 1.00 | 1.00 | 0.66 | 0.95 | 1.00 |
| group | 4 | — | 1.00 | 1.00 | 0.69 | 0.92 | 1.00 |
| indian | 7 | 1.00 | 1.00 | 1.00 | 0.60 | 0.89 | 1.00 |
| vague | 4 | 1.00 | 1.00 | 1.00 | 0.73 | 0.89 | 1.00 |

## Per prompt

| id | prompt | understood as | picks | rel | div | reason |
|---|---|---|---|---|---|---|
| e01 | Long day, want something cosy but not cheesy | drained · low energy · wants a lift | Paddington 2 (en); Chef (en); Anbe Sivam (ta); Romancham (ml) | 1.00 | 0.63 | 0.92 |
| e02 | I'm in a great mood, give me something fun and feel-good | happy · high energy · wants to lean in | Zindagi Na Milegi Dobara (hi); Premalu (ml); Jaya Jaya Jaya Jaya Hey (ml); Everything Everywhere All at Once (en) | 1.00 | 0.65 | 0.96 |
| e03 | Just broke up. I want a good cry. | heartbroken · down · low energy · wants to lean in | Eternal Sunshine of the Spotless Mind (en); The Lunchbox (hi); Masaan (hi); La La Land (en) | 1.00 | 0.66 | 0.88 |
| e04 | So stressed about work, need something to take my mind off it | stressed · medium energy · wants a lift | Paddington 2 (en); Anbe Sivam (ta); Oh My Kadavule (ta); Queen (hi) | 1.00 | 0.66 | 1.00 |
| e05 | I want something that makes me think, maybe a mind-bending one | curious · medium energy · wants to lean in | Arrival (en); Interstellar (en); Awe! (te); Aattam (ml) | 1.00 | 0.78 | 0.96 |
| e06 | Date night with my girlfriend, something romantic but fun | romantic · medium energy · wants to lean in · with partner | Premalu (ml); Barfi! (hi); About Time (en); C/o Kancharapalem (te) | 1.00 | 0.47 | 1.00 |
| e07 | Bored out of my mind, surprise me with something gripping | bored · medium energy · wants a lift | Maharaja (ta); Baahubali: The Beginning (te); Awe! (te); Mad Max: Fury Road (en) | 1.00 | 0.78 | 0.88 |
| e08 | Feeling nostalgic about college days | nostalgic · low energy · wants to lean in | 96 (ta); Premam (ml); Ee Nagaraniki Emaindi (te); La La Land (en) | 1.00 | 0.66 | 1.00 |
| i01 | Bore adikkunnu, oru nalla Malayalam comedy venam | bored · medium energy · wants a lift | Aavesham (ml); Minnal Murali (ml); Premalu (ml); Jaya Jaya Jaya Jaya Hey (ml) | 1.00 | 0.58 | 0.92 |
| i02 | Mood off yaar, thak gaya hu. Kuch halka sa, Hindi mein | drained · down · low energy · wants a lift | Zindagi Na Milegi Dobara (hi); Jab We Met (hi); Laapataa Ladies (hi); Bhool Bhulaiyaa (hi) | 1.00 | 0.55 | 0.88 |
| i03 | Watching with amma and achan tonight, Malayalam, nothing violent | open to anything · medium energy · wants to lean in · with family | Bangalore Days (ml); Home (ml); Maheshinte Prathikaaram (ml); Manjummel Boys (ml) | 1.00 | 0.53 | 0.88 |
| i04 | Missing home, feeling homesick in Bangalore. Something that feels like | lonely · low energy · wants a lift | Zindagi Na Milegi Dobara (hi); Ustad Hotel (ml); Laapataa Ladies (hi); Inside Out (en) | 1.00 | 0.68 | 0.92 |
| i05 | Tamil thriller venum, edge of the seat, but no gore | open to anything · medium energy · wants to lean in | Maharaja (ta); Doctor (ta); Kaithi (ta); Jigarthanda (ta) | 1.00 | 0.45 | 0.88 |
| i06 | Telugu movie that'll inspire me, exams next week and I'm tense | stressed · medium energy · wants a lift | Jersey (te); Jathi Ratnalu (te); Ee Nagaraniki Emaindi (te); Pelli Choopulu (te) | 1.00 | 0.72 | 0.92 |
| i07 | Sankadam aanu. Kurachu santhosham tharunna oru padam? | down · happy · low energy · wants a lift | Queen (hi); Soorarai Pottru (ta); Anbe Sivam (ta); Up (en) | 1.00 | 0.72 | 0.88 |
| g01 | Asha: exhausted after work Ravi: want to laugh, no horror | group of 2 · Asha drained · Ravi easygoing | Zindagi Na Milegi Dobara (hi); Paddington 2 (en); Good Night (ta); Inside Out (en) | 1.00 | 0.66 | 0.92 |
| g02 | Neha: want a thriller Arjun: in the mood for something twisty Sam: any | group of 3 · Neha easygoing · Arjun curious · Sam easygoing | Andhadhun (hi); Agent Sai Srinivasa Athreya (te); Awe! (te); The Martian (en) | 1.00 | 0.75 | 0.92 |
| g03 | Mom: something wholesome for the family Kid: funny and animated please | group of 2 · Mom easygoing · Kid easygoing | Paddington 2 (en); Home (ml); Tourist Family (ta); Coco (en) | 1.00 | 0.60 | 0.92 |
| g04 | Priya: happy, Malayalam or Tamil Kiran: party mood, Tamil or Telugu | group of 2 · Priya happy · Kiran party mood | Soorarai Pottru (ta); Oh My Kadavule (ta); Anbe Sivam (ta); Doctor (ta) | 1.00 | 0.77 | 0.92 |
| v01 | idk | open to anything · medium energy · wants a lift | 3 Idiots (hi); Premalu (ml); Anbe Sivam (ta); Agent Sai Srinivasa Athreya (te) | 1.00 | 0.70 | 0.88 |
| v02 | meh | down · low energy · wants a lift | Chef (en); Paddington 2 (en); Premalu (ml); Anbe Sivam (ta) | 1.00 | 0.60 | 0.92 |
| v03 | suggest something | open to anything · medium energy · wants to lean in | Andhadhun (hi); Knives Out (en); Kshanam (te); The Martian (en) | 1.00 | 0.78 | 0.88 |
| v04 | I'm sad | down · low energy · wants to lean in | The Lunchbox (hi); Up (en); Android Kunjappan Version 5.25 (ml); Jersey (te) | 1.00 | 0.83 | 0.88 |
| x01 | I feel hopeless and I can't go on anymore | open to anything · medium energy · wants a lift | Soul (en); Meiyazhagan (ta); Home (ml) | 1.00 | 0.79 | 0.89 |
| x02 | Only have 90 minutes before bed, something light | open to anything · medium energy · wants to lean in | Inside Out (en); The Grand Budapest Hotel (en); Soul (en); Up (en) | 1.00 | 0.60 | 0.92 |
| x03 | Happy but also kind of sad? Weird day. Lift me up. | down · happy · low energy · wants a lift | Queen (hi); Home (ml); Anbe Sivam (ta); Up (en) | 1.00 | 0.62 | 0.83 |
| x04 | Scared of the dark but I want a horror movie tonight, bring it on | uneasy · medium energy · wants to lean in | The Conjuring (en); Tumbbad (hi); Bhool Bhulaiyaa (hi); Ratsasan (ta) | 1.00 | 0.70 | 0.96 |
| x05 | Angry at everyone. No romance, nothing slow, no songs. | frustrated · high energy · wants to lean in | Rangasthalam (te); Maharaja (ta); Eega (te); Mad Max: Fury Road (en) | 1.00 | 0.71 | 0.88 |
| x06 | 😴😴😴 | open to anything · medium energy · wants to lean in | 3 Idiots (hi); Paddington 2 (en); Premalu (ml); Anbe Sivam (ta) | 1.00 | 0.64 | 0.88 |
| x07 | Telugu horror comedy under 60 minutes with no violence | open to anything · medium energy · wants to lean in | Agent Sai Srinivasa Athreya (te); Ee Nagaraniki Emaindi (te); Balagam (te); Pelli Choopulu (te) | 0.75 | 0.74 | 0.92 |

## Sample reasons

- **e01** “Long day, want something cosy but not cheesy” → You said "long day, want something cosy but not cheesy" — Paddington 2 is a cosy, light family film about bear, pop-up book and prison that should lift you without trying too hard. At 1h44, it won't ask much of you.
- **e02** “I'm in a great mood, give me something fun and feel-good” → You said "I'm in a great mood" — Zindagi Na Milegi Dobara is a feel-good, funny comedy-drama about road trip, friendship and Spain that lets you sit with the feeling.
- **e03** “Just broke up. I want a good cry.” → You said "just broke up. I want a good cry" — Eternal Sunshine of the Spotless Mind is a bittersweet, melancholic romance about memory erasure, breakup and heartbreak that lets you sit with the feeling. At 1h48, it won't ask much of you.
- **e04** “So stressed about work, need something to take my mind off i” → You said "so stressed about work" — Paddington 2 is a funny, light family film about bear, pop-up book and prison that should lift you without trying too hard.
- **e05** “I want something that makes me think, maybe a mind-bending o” → You said "I want something that makes me think" — Arrival is a mind-bending, thought-provoking sci-fi film about linguistics, aliens and grief that'll keep your brain happily busy.
- **e06** “Date night with my girlfriend, something romantic but fun” → You said "date night with my girlfriend" — Premalu is a romantic, warm rom-com about Hyderabad, young love and friendship that lets you sit with the feeling.
- **e07** “Bored out of my mind, surprise me with something gripping” → You said "bored out of my mind" — Maharaja is a thrilling, twisty thriller about barber, revenge and nonlinear that should lift you without trying too hard.
- **e08** “Feeling nostalgic about college days” → You said "feeling nostalgic about college days" — 96 is a nostalgic, bittersweet romance about school reunion, first love and one night that lets you sit with the feeling.
