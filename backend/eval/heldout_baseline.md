# MoodReel evaluation results

15 prompts · engines: embedder=`hashing`, vectors=`memory`, emotion=`lexicon`, llm=`rules`, catalogue=`119 films`

| Metric | Score |
|---|---|
| Understanding | 0.78 |
| Relevance | 0.85 |
| Constraints | 0.92 |
| Diversity | 0.68 |
| Reason Quality | 0.91 |
| Behaviour | 0.98 |

## By category

| Category | n | understanding | relevance | constraints | diversity | reason quality | behaviour |
|---|---|---|---|---|---|---|---|
| edge | 3 | 1.00 | 0.58 | 0.58 | 0.70 | 0.89 | 0.92 |
| everyday | 5 | 0.50 | 1.00 | 1.00 | 0.72 | 0.94 | 1.00 |
| group | 2 | — | 0.75 | 1.00 | 0.66 | 0.92 | 1.00 |
| indian | 4 | 1.00 | 0.88 | 1.00 | 0.60 | 0.91 | 1.00 |
| vague | 1 | — | 1.00 | 1.00 | 0.77 | 0.83 | 1.00 |

## Per prompt

| id | prompt | understood as | picks | rel | div | reason |
|---|---|---|---|---|---|---|
| h01 | Rainy Sunday, curled up on the sofa, want something slow and soothing | calm · low energy · wants to lean in | The Lunchbox (hi); Paddington 2 (en); Wake Up Sid (hi); Ustad Hotel (ml) | 1.00 | 0.74 | 0.88 |
| h02 | Finally finished my thesis!! Celebrating tonight | party mood · high energy · wants to lean in | Aavesham (ml); Superbad (en); Hera Pheri (hi); La La Land (en) | 1.00 | 0.65 | 0.92 |
| h03 | My dog died last week. I just want something that won't make it worse. | open to anything · medium energy · wants to lean in | 3 Idiots (hi); Agent Sai Srinivasa Athreya (te); Anbe Sivam (ta); Knives Out (en) | 1.00 | 0.70 | 0.96 |
| h04 | Can't sleep, mind racing about tomorrow's interview | open to anything · medium energy · wants to lean in | 3 Idiots (hi); Agent Sai Srinivasa Athreya (te); Anbe Sivam (ta); Knives Out (en) | 1.00 | 0.70 | 1.00 |
| h05 | Want an epic I can lose myself in for three hours | open to anything · medium energy · wants to lean in | Interstellar (en); RRR (te); Anbe Sivam (ta); Inception (en) | 1.00 | 0.79 | 0.96 |
| h06 | Ente amma ude koode kaanan oru nalla family padam, Malayalam | open to anything · medium energy · wants to lean in · with family | Drishyam (ml); Maheshinte Prathikaaram (ml); Premalu (ml); Home (ml) | 0.75 | 0.66 | 0.88 |
| h07 | Office tension bahut hai, kuch comedy dikhao | stressed · medium energy · wants a lift | Paddington 2 (en); Good Night (ta); Oh My Kadavule (ta); 3 Idiots (hi) | 1.00 | 0.66 | 0.96 |
| h08 | Telugu love story, something that'll make me cry happy tears | down · happy · low energy · wants to lean in | Arjun Reddy (te); Sita Ramam (te); Pelli Choopulu (te); C/o Kancharapalem (te) | 1.00 | 0.54 | 0.92 |
| h09 | Feeling patriotic, Hindi sports film | open to anything · medium energy · wants to lean in | 3 Idiots (hi); Zindagi Na Milegi Dobara (hi); Jab We Met (hi); Andhadhun (hi) | 0.75 | 0.54 | 0.88 |
| h10 | Dev: tired, short film please Isha: romantic mood | group of 2 · Dev drained · Isha romantic | About Time (en); La La Land (en); Pelli Choopulu (te); Romancham (ml) | 1.00 | 0.66 | 0.92 |
| h11 | Ammu: Malayalam only Joe: something scary! Ria: I'm fine with horror | group of 3 · Ammu easygoing · Joe easygoing · Ria easygoing | Bangalore Days (ml); Home (ml); Romancham (ml); Manjummel Boys (ml) | 0.50 | 0.66 | 0.92 |
| h12 | hmm whatever you think | curious · medium energy · wants to lean in | Arrival (en); Interstellar (en); Awe! (te); Inception (en) | 1.00 | 0.77 | 0.83 |
| h13 | Nothing violent, nothing sad, nothing slow, nothing romantic. Go. | open to anything · medium energy · wants to lean in | 3 Idiots (hi); Paddington 2 (en); Anbe Sivam (ta); Agent Sai Srinivasa Athreya (te) | 1.00 | 0.71 | 0.88 |
| h14 | I don't want to be here anymore | open to anything · medium energy · wants to lean in | Knives Out (en); Andhadhun (hi); Agent Sai Srinivasa Athreya (te); Anbe Sivam (ta) | 0.50 | 0.68 | 0.88 |
| h15 | Need a 2-hour max thriller, English, no horror | open to anything · medium energy · wants to lean in | Knives Out (en); Inception (en); Mad Max: Fury Road (en); The Martian (en) | 0.25 | 0.70 | 0.92 |

## Sample reasons

- **h01** “Rainy Sunday, curled up on the sofa, want something slow and” → You said "rainy Sunday, want something slow and soothing" — The Lunchbox is a cosy, gentle drama about letters, loneliness and Mumbai that lets you sit with the feeling. At 1h45, it won't ask much of you.
- **h02** “Finally finished my thesis!! Celebrating tonight” → You said "finally finished my thesis!! Celebrating tonight" — Aavesham is a party-ready, funny action film about gangster, college students and Bengaluru that plays great with a crowd.
- **h03** “My dog died last week. I just want something that won't make” → You said "my dog died last week" — 3 Idiots is a feel-good, warm comedy-drama about engineering college, friendship and education system that lets you sit with the feeling.
- **h04** “Can't sleep, mind racing about tomorrow's interview” → You said "can't sleep" — 3 Idiots is a feel-good, warm comedy-drama about engineering college, friendship and education system that lets you sit with the feeling.
- **h05** “Want an epic I can lose myself in for three hours” → You said "want an epic I can lose myself in for three hours" — Interstellar is an epic sci-fi film about space and time dilation that lets you sit with the feeling.
- **h06** “Ente amma ude koode kaanan oru nalla family padam, Malayalam” → You said "ente amma ude koode kaanan oru nalla family padam" — Drishyam is a twisty, thrilling thriller about family man, cover up and police investigation that lets you sit with the feeling.
- **h07** “Office tension bahut hai, kuch comedy dikhao” → You said "office tension bahut hai, kuch comedy dikhao" — Paddington 2 is a funny, light family film about bear, pop-up book and prison that should lift you without trying too hard.
- **h08** “Telugu love story, something that'll make me cry happy tears” → You said "telugu love story" — Arjun Reddy is a romantic, melancholic romance about surgeon, addiction and heartbreak that lets you sit with the feeling.
