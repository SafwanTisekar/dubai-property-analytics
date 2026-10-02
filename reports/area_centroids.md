# Area centroids

Generated 2026-10-02 11:52 UTC by `ingest/geocode_areas.py` (`make centroids`), 1 new Nominatim requests (the rest from the cache in `data/raw/osm/`). Centroids feed the Power BI bubble map (docs/06 §4). **Area locations © OpenStreetMap contributors (ODbL).**

**194 of 265 areas located.** Only results whose OSM address is in the emirate of Dubai (AE-DU) and inside the Dubai box are accepted. Not-found areas have no bubble; there is no fallback to a zone centroid. To fix one, type its coordinates into `dbt/seeds/seed_area.csv` with `centroid_source = manual` (never overwritten), then `make dbt`.

| Outcome | Areas |
|---|---|
| osm_nominatim | 183 |
| not found | 71 |
| osm_nominatim_approx | 6 |
| osm_nominatim_alias | 5 |

## Not found: fill in by hand (71)

Names tried, in order.

| area_id | area_name_en | zone | query |
|---|---|---|---|
| 231 | Al Mamzer | Deira | Al Mamzer |
| 235 | Eyal Nasser | Deira | Eyal Nasser |
| 236 | Burj Nahar | Deira | Burj Nahar |
| 241 | Al Qusais Old | Qusais, Nahda, Twar & Muhaisnah | Al Qusais Old |
| 243 | Al-Safiyyah | Outer Dubai & Hatta | Al Safiyyah |
| 244 | Al Murqabat | Deira | Al Murqabat |
| 245 | Al-Murar Qadeem | Deira | Al Murar Qadeem |
| 246 | Al-Murar Jadeed | Deira | Al Murar Jadeed |
| 247 | Al Khabeesi | Deira | Al Khabeesi |
| 250 | Al-Souq Al Kabeer (Deira) | Deira | Al Souq Al Kabeer (Deira) |
| 251 | Naif South | Deira | Naif South |
| 252 | Al-Riqqa East | Deira | Al Riqqa East |
| 253 | Al-Riqqa West | Deira | Al Riqqa West |
| 255 | Rega Al Buteen | Deira | Rega Al Buteen |
| 256 | Al-Tawar | Qusais, Nahda, Twar & Muhaisnah | Al Tawar |
| 258 | Muhaisna | Qusais, Nahda, Twar & Muhaisnah | Muhaisna |
| 259 | Al-Musalla (Deira) | Deira | Al Musalla (Deira) |
| 262 | Al-Zarouniyyah | Outer Dubai & Hatta | Al Zarouniyyah |
| 263 | Al-Nahdah | Qusais, Nahda, Twar & Muhaisnah | Al Nahdah |
| 264 | Nad Al Hamar | Mirdif, Mizhar, Warqa & Khawaneej | Nad Al Hamar |
| 265 | Al-Muhaisnah North | Qusais, Nahda, Twar & Muhaisnah | Al Muhaisnah North |
| 268 | Al Musalla (Dubai) | Bur Dubai & Karama | Al Musalla (Dubai) |
| 270 | Al Safaa | Jumeirah, Al Wasl & Umm Suqeim | Al Safaa |
| 272 | Al Baharna | Bur Dubai & Karama | Al Baharna |
| 273 | Al-Baloosh | Outer Dubai & Hatta | Al Baloosh |
| 274 | Shandagha East | Bur Dubai & Karama | Shandagha East |
| 275 | Shandagha West | Bur Dubai & Karama | Shandagha West |
| 276 | Al Bada | Jumeirah, Al Wasl & Umm Suqeim | Al Bada |
| 277 | Al Qoaz | Al Barsha, Al Quoz & Tecom | Al Qoaz |
| 279 | Tawaa Al Sayegh | Outer Dubai & Hatta | Tawaa Al Sayegh |
| 280 | Zareeba Duviya | Outer Dubai & Hatta | Zareeba Duviya |
| 281 | Al Asbaq | Outer Dubai & Hatta | Al Asbaq |
| 302 | Tawi Al Muraqqab | Outer Dubai & Hatta | Tawi Al Muraqqab |
| 313 | Al Saffa First | Jumeirah, Al Wasl & Umm Suqeim | Al Saffa 1; Al Saffa First; Al Saffa 1st; Al Saffa |
| 314 | Al Saffa Second | Jumeirah, Al Wasl & Umm Suqeim | Al Saffa 2; Al Saffa Second; Al Saffa 2nd; Al Saffa |
| 324 | Shandagha | Bur Dubai & Karama | Shandagha |
| 328 | Al Jafliya | Bur Dubai & Karama | Al Jafliya |
| 331 | Zaabeel First | DIFC, Trade Centre & Za'abeel | Zaabeel 1; Zaabeel First; Zaabeel 1st; Za'abeel 1; Za'abeel First; Za'abeel 1st |
| 339 | Al Mararr | Deira | Al Mararr |
| 343 | Al Warsan First | Silicon Oasis, International City & Academic City | Al Warsan 1; Al Warsan First; Al Warsan 1st; Al Warsan |
| 344 | Al Warsan Second | Silicon Oasis, International City & Academic City | Al Warsan 2; Al Warsan Second; Al Warsan 2nd; Al Warsan |
| 345 | Al Warsan Third | Silicon Oasis, International City & Academic City | Al Warsan 3; Al Warsan Third; Al Warsan 3rd; Al Warsan |
| 356 | Al Rega | Deira | Al Rega |
| 367 | Al Suq Al Kabeer | Bur Dubai & Karama | Al Suq Al Kabeer |
| 377 | Al-Nakhal | Deira | Al Nakhal |
| 379 | Al-Shumaal | Outer Dubai & Hatta | Al Shumaal |
| 385 | Muashrah Al Bahraana | Outer Dubai & Hatta | Muashrah Al Bahraana |
| 386 | Al-Raulah | MBR City, Meydan & Dubai Hills | Al Raulah |
| 387 | Al-Bastakiyah | Bur Dubai & Karama | Al Bastakiyah |
| 391 | Al Lusaily | Outer Dubai & Hatta | Al Lusaily |
| 398 | Al Aweer First | Outer Dubai & Hatta | Al Aweer 1; Al Aweer First; Al Aweer 1st; Al Aweer |
| 399 | Al Aweer Second | Outer Dubai & Hatta | Al Aweer 2; Al Aweer Second; Al Aweer 2nd; Al Aweer |
| 400 | Al Eyas | Outer Dubai & Hatta | Al Eyas |
| 411 | Palm Jabal Ali | Palm & Islands | Palm Jabal Ali; Palm Jebel Ali; Palm Jebel Ali |
| 416 | Cornich Deira | Deira | Cornich Deira |
| 417 | Sikkat Al Khail North | Deira | Sikkat Al Khail North |
| 418 | Naif North | Deira | Naif North |
| 419 | Sikkat Al Khail South | Deira | Sikkat Al Khail South |
| 421 | Al-Mustashfa West | Outer Dubai & Hatta | Al Mustashfa West |
| 423 | Al-Aweer | Outer Dubai & Hatta | Al Aweer |
| 424 | Al-Qiyadah | Outer Dubai & Hatta | Al Qiyadah |
| 425 | Al-Dzahiyyah Al-Jadeedah | Outer Dubai & Hatta | Al Dzahiyyah Al Jadeedah |
| 427 | Nad Rashid | Outer Dubai & Hatta | Nad Rashid |
| 431 | Al-Cornich | Outer Dubai & Hatta | Al Cornich |
| 448 | Al Khairan  Second | Creek Harbour, Jaddaf & Festival City | Al Khairan 2; Al Khairan Second; Al Khairan 2nd; Al Khairan |
| 470 | Al Faga'A | Outer Dubai & Hatta | Al Faga'A |
| 477 | Mena Jabal Ali | Jebel Ali, Dubai South & Waterfront | Mena Jabal Ali; Mena Jebel Ali; Mina Jebel Ali |
| 494 | Umm Addamin | Outer Dubai & Hatta | Umm Addamin |
| 500 | Um Esalay | Outer Dubai & Hatta | Um Esalay; Umm Esalay |
| 515 | Saih Aldahal | Outer Dubai & Hatta | Saih Aldahal |
| 524 | Muragab | Outer Dubai & Hatta | Muragab |

## Approximate: parent community only, please review (6)

Found only without the sub-area suffix, so sub-areas share one point.

| area_id | area_name_en | zone | query | osm_name | latitude | longitude |
|---|---|---|---|---|---|---|
| 336 | Nad Al Shiba Second | MBR City, Meydan & Dubai Hills | Nad Al Sheba | Nad Al Sheba | 25.145630 | 55.364275 |
| 337 | Nad Al Shiba Third | MBR City, Meydan & Dubai Hills | Nad Al Sheba | Nad Al Sheba | 25.145630 | 55.364275 |
| 406 | Nad Al Shiba Fourth | MBR City, Meydan & Dubai Hills | Nad Al Sheba | Nad Al Sheba | 25.145630 | 55.364275 |
| 436 | Festival City First | Creek Harbour, Jaddaf & Festival City | Festival City | Al Badia Hillside Village | 25.220404 | 55.362942 |
| 528 | Al Yufrah 3 | Dubailand | Al Yufrah | Al Yufrah 1 | 25.003250 | 55.439521 |
| 529 | Al Yufrah 4 | Dubailand | Al Yufrah | Al Yufrah 1 | 25.003250 | 55.439521 |

## Found under an alias, please review (5)

Located under the better-known name in `ALIASES`.

| area_id | area_name_en | zone | query | osm_name | latitude | longitude |
|---|---|---|---|---|---|---|
| 330 | Marsa Dubai | Marina, JBR & JLT | Dubai Marina | Dubai Marina | 25.078641 | 55.135252 |
| 333 | Madinat Dubai Almelaheyah | Bur Dubai & Karama | Port Rashid | Port Rashid | 25.271108 | 55.265932 |
| 412 | Al Merkadh | MBR City, Meydan & Dubai Hills | Al Merkad | MBR- Al Merkad | 25.169213 | 55.292473 |
| 447 | Al Khairan First | Creek Harbour, Jaddaf & Festival City | Dubai Creek Harbour | Dubai Creek Harbour | 25.197978 | 55.360380 |
| 527 | Island 2 (Jumeira Bay) | Palm & Islands | Island 2 | Jumeirah Island 2 | 25.197624 | 55.225824 |
