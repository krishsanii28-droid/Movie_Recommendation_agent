# MoodReel evaluation results

15 prompts · engines: embedder=`hashing`, vectors=`memory`, emotion=`lexicon`, llm=`rules`, catalogue=`119 films`

| Metric | Score |
|---|---|
| Understanding | 1.00 |
| Relevance | 0.93 |
| Constraints | 1.00 |
| Diversity | 0.68 |
| Reason Quality | 0.91 |
| Behaviour | 1.00 |

## By category

| Category | n | understanding | relevance | constraints | diversity | reason quality | behaviour |
|---|---|---|---|---|---|---|---|
| edge | 3 | 1.00 | 0.92 | 1.00 | 0.78 | 0.88 | 1.00 |
| everyday | 5 | 1.00 | 1.00 | 1.00 | 0.76 | 0.94 | 1.00 |
| group | 2 | — | 0.75 | 1.00 | 0.58 | 0.92 | 1.00 |
| indian | 4 | 1.00 | 0.94 | 1.00 | 0.54 | 0.91 | 1.00 |
| vague | 1 | — | 1.00 | 1.00 | 0.78 | 0.83 | 1.00 |

## Per prompt

| id | prompt | understood as | picks | rel | div | reason |
|---|---|---|---|---|---|---|
| h01 | Rainy Sunday, curled up on the sofa, want something slow and soothing | calm · low energy · wants to lean in | Maheshinte Prathikaaram (ml); Wake Up Sid (hi); Kadaisi Vivasayi (ta); Soul (en) | 1.00 | 0.78 | 0.88 |
| h02 | Finally finished my thesis!! Celebrating tonight | party mood · high energy · wants to lean in | Aavesham (ml); Superbad (en); Hera Pheri (hi); La La Land (en) | 1.00 | 0.65 | 0.92 |
| h03 | My dog died last week. I just want something that won't make it worse. | down · low energy · wants a lift | Queen (hi); The Shawshank Redemption (en); Anbe Sivam (ta); Up (en) | 1.00 | 0.72 | 0.92 |
| h04 | Can't sleep, mind racing about tomorrow's interview | anxious · medium energy · wants a lift | Soul (en); Meiyazhagan (ta); Good Night (ta); Thondimuthalum Driksakshiyum (ml) | 1.00 | 0.80 | 1.00 |
| h05 | Want an epic I can lose myself in for three hours | open to anything · medium energy · wants to lean in | Interstellar (en); RRR (te); Tumbbad (hi); Inception (en) | 1.00 | 0.84 | 1.00 |
| h06 | Ente amma ude koode kaanan oru nalla family padam, Malayalam | open to anything · medium energy · wants to lean in · with family | Drishyam (ml); Maheshinte Prathikaaram (ml); Premalu (ml); Home (ml) | 0.75 | 0.66 | 0.88 |
| h07 | Office tension bahut hai, kuch comedy dikhao | stressed · medium energy · wants a lift | Paddington 2 (en); Good Night (ta); Oh My Kadavule (ta); 3 Idiots (hi) | 1.00 | 0.66 | 0.96 |
| h08 | Telugu love story, something that'll make me cry happy tears | down · happy · low energy · wants to lean in | Sita Ramam (te); Arjun Reddy (te); Hi Nanna (te); C/o Kancharapalem (te) | 1.00 | 0.43 | 0.92 |
| h09 | Feeling patriotic, Hindi sports film | open to anything · medium energy · wants to lean in | 3 Idiots (hi); Queen (hi); Bajrangi Bhaijaan (hi); Swades (hi) | 1.00 | 0.41 | 0.88 |
| h10 | Dev: tired, short film please Isha: romantic mood | group of 2 · Dev drained · Isha romantic | About Time (en); La La Land (en); Crazy Rich Asians (en); Pelli Choopulu (te) | 1.00 | 0.45 | 0.92 |
| h11 | Ammu: Malayalam only Joe: something scary! Ria: I'm fine with horror | group of 3 · Ammu easygoing · Joe easygoing · Ria easygoing | Bramayugam (ml); Home (ml); Premalu (ml); Romancham (ml) | 0.50 | 0.72 | 0.92 |
| h12 | hmm whatever you think | curious · medium energy · wants to lean in | Arrival (en); Interstellar (en); Awe! (te); Aattam (ml) | 1.00 | 0.78 | 0.83 |
| h13 | Nothing violent, nothing sad, nothing slow, nothing romantic. Go. | open to anything · medium energy · wants to lean in | 3 Idiots (hi); Paddington 2 (en); Anbe Sivam (ta); Agent Sai Srinivasa Athreya (te) | 1.00 | 0.71 | 0.88 |
| h14 | I don't want to be here anymore | open to anything · medium energy · wants a lift | Soul (en); Meiyazhagan (ta); Home (ml) | 1.00 | 0.79 | 0.89 |
| h15 | Need a 2-hour max thriller, English, no horror | open to anything · medium energy · wants to lean in | Mad Max: Fury Road (en); Whiplash (en); Crazy Rich Asians (en); Arrival (en) | 0.75 | 0.84 | 0.88 |

## Sample reasons

- **h01** “Rainy Sunday, curled up on the sofa, want something slow and” → You said "rainy Sunday, want something slow and soothing" — Maheshinte Prathikaaram is a gentle, warm comedy-drama about revenge vow, photographer and village life that lets you sit with the feeling. At 2h00, it won't ask much of you.
- **h02** “Finally finished my thesis!! Celebrating tonight” → You said "finally finished my thesis!! Celebrating tonight" — Aavesham is a party-ready, funny action film about gangster, college students and Bengaluru that plays great with a crowd.
- **h03** “My dog died last week. I just want something that won't make” → You said "my dog died last week" — Queen is an uplifting, funny comedy-drama about solo travel, self-discovery and jilted bride that should lift you without trying too hard.
- **h04** “Can't sleep, mind racing about tomorrow's interview” → You said "can't sleep" — Soul is a comforting, gentle animated film about jazz, purpose and afterlife that should lift you without trying too hard.
- **h05** “Want an epic I can lose myself in for three hours” → You said "want an epic I can lose myself in for three hours" — Interstellar is an epic sci-fi film about space and time dilation that lets you sit with the feeling.
- **h06** “Ente amma ude koode kaanan oru nalla family padam, Malayalam” → You said "ente amma ude koode kaanan oru nalla family padam" — Drishyam is a twisty, thrilling thriller about family man, cover up and police investigation that lets you sit with the feeling.
- **h07** “Office tension bahut hai, kuch comedy dikhao” → You said "office tension bahut hai, kuch comedy dikhao" — Paddington 2 is a funny, light family film about bear, pop-up book and prison that should lift you without trying too hard.
- **h08** “Telugu love story, something that'll make me cry happy tears” → You said "telugu love story" — Sita Ramam is a romantic, bittersweet romance about letters, soldier and Kashmir that lets you sit with the feeling.
