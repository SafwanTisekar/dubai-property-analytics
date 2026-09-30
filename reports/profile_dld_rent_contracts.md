# Profile: `bronze.dld_rent_contracts`

Generated 2026-09-30 11:25 UTC by `quality/profile.py` (SQL-based, exact counts over the full table).

- Rows: **10,538,926**
- Columns: 46 (41 source + metadata)
- Table size on disk: 5912 MB
- Profiling time: 183 s

Blank = `NULL` or `''` (DLD quotes every field, so missing values are empty strings in bronze). Min/max are numeric when ≥95% of non-blank values are numeric, otherwise text order. Values are truncated to 40 characters; ⏎ marks a line break.

| Column | Blank % | Distinct | Min | Max | Numeric % | Top values (count) |
|---|---:|---:|---|---|---:|---|
| `actual_area` | 12.6 | 62,281 | 0 | 930,091,045 | 100.0 | '' (1,324,496)<br>1.00 (200,339)<br>30.00 (94,367)<br>45.00 (82,063)<br>20.00 (61,525) |
| `annual_amount` | 0.0 | 379,632 | 0.01 | 3,300,037,950 | 100.0 | 15000.00 (270,573)<br>20000.00 (270,174)<br>60000.00 (201,076)<br>50000.00 (196,825)<br>40000.00 (190,498) |
| `area_id` | 0.0 | 215 | 229 | 531 | 100.0 | 395 (390,651)<br>343 (379,779)<br>360 (336,219)<br>445 (333,518)<br>526 (300,209) |
| `area_name_ar` | 0.0 | 215 | أم الدمن | يراح | 0.0 | جبل على الصناعية الأولى (390,651)<br>ورسان الاولى (379,779)<br>محيصنه الثانيه (336,219)<br>جبل علي الأولى (333,518)<br>الخليج التجارى (300,209) |
| `area_name_en` | 0.0 | 215 | AL Athbah | Zareeba Duviya | 0.0 | Jabal Ali Industrial First (390,651)<br>Al Warsan First (379,779)<br>Muhaisanah Second (336,219)<br>Jabal Ali First (333,518)<br>Business Bay (300,209) |
| `contract_amount` | 0.0 | 299,944 | 0.01 | 4,200,000,003 | 100.0 | 15000.00 (273,694)<br>20000.00 (272,786)<br>60000.00 (200,987)<br>50000.00 (200,578)<br>40000.00 (194,855) |
| `contract_end_date` | 0.0 | 8,260 | 2002-02-15 | 5013-05-28 | 0.0 | 2018-12-31 (63,969)<br>2019-12-31 (63,102)<br>2017-12-31 (61,488)<br>2025-12-31 (60,389)<br>2015-12-31 (59,382) |
| `contract_id` | 0.0 | 8,795,059 | CNT10000 | CRT997996666 | 0.0 | CNT655748705 (788)<br>CNT919700037 (788)<br>CNT2129189989 (661)<br>CNT484478147 (660)<br>CRT1410311676 (636) |
| `contract_reg_type_ar` | 0.0 | 2 | تجديد | جديد | 0.0 | جديد (5,477,398)<br>تجديد (5,061,528) |
| `contract_reg_type_en` | 0.0 | 2 | New | Renew | 0.0 | New (5,477,398)<br>Renew (5,061,528) |
| `contract_reg_type_id` | 0.0 | 2 | 1 | 2 | 100.0 | 1 (5,477,398)<br>2 (5,061,528) |
| `contract_start_date` | 0.0 | 6,454 | 2001-02-15 | 2205-07-16 | 0.0 | 2018-01-01 (59,481)<br>2017-01-01 (58,371)<br>2019-01-01 (58,201)<br>2015-01-01 (57,937)<br>2025-01-01 (57,377) |
| `ejari_bus_property_type_ar` | 0.0 | 5 | أرض | وحدة افتراضية | 0.0 | وحدة (8,550,706)<br>وحدة افتراضية (1,230,265)<br>فيلا (686,652)<br>أرض (63,773)<br>مبنى (3,955) |
| `ejari_bus_property_type_en` | 0.0 | 5 | Building | Virtual Unit | 0.0 | Unit (8,550,706)<br>Virtual Unit (1,230,265)<br>Villa (686,652)<br>Land (63,773)<br>Building (3,955) |
| `ejari_bus_property_type_id` | 0.0 | 5 | 0 | 5 | 100.0 | 2 (8,550,706)<br>5 (1,230,265)<br>4 (686,652)<br>0 (63,773)<br>1 (3,955) |
| `ejari_property_sub_type_ar` | 0.7 | 84 | 11 غرف نوم + صالة | ي | 0.0 | غرفة و صالة (2,147,551)<br>غرفتين و صالة (1,975,347)<br>مكتب (1,572,782)<br>أستوديو (1,097,518)<br>غرفه سكن عمال (1,063,202) |
| `ejari_property_sub_type_en` | 0.7 | 85 | 10 bed rooms+hall | swimming pool | 0.0 | 1bed room+Hall (2,147,551)<br>2 bed rooms+hall (1,975,347)<br>Office (1,572,782)<br>Studio (1,097,518)<br>Room in labor Camp (1,063,202) |
| `ejari_property_sub_type_id` | 0.7 | 88 | 0 | 2,117,935,896 | 100.0 | 1 (2,147,551)<br>2 (1,975,347)<br>422 (1,572,782)<br>11 (1,097,518)<br>12 (1,063,202) |
| `ejari_property_type_ar` | 0.7 | 71 | أرض فضاء | ورشه | 0.0 | شقه (5,484,343)<br>مكتب (1,587,277)<br>سكن عمال (1,216,854)<br>محل (928,540)<br>فيلا (619,272) |
| `ejari_property_type_en` | 0.7 | 71 | ATM | swimming pool | 0.0 | Flat (5,484,343)<br>Office (1,587,277)<br>Labor Camps (1,216,854)<br>Shop (928,540)<br>Villa (619,272) |
| `ejari_property_type_id` | 0.6 | 73 | 0 | 2,117,944,026 | 100.0 | 842 (5,484,343)<br>2 (1,587,277)<br>4 (1,216,854)<br>1 (928,540)<br>841 (619,272) |
| `is_free_hold` | 0.0 | 2 | 0 | 1 | 100.0 | 0 (6,516,920)<br>1 (4,018,431)<br>'' (3,575) |
| `line_number` | 0.0 | 788 | 1 | 788 | 100.0 | 1 (8,795,059)<br>2 (248,173)<br>3 (129,947)<br>4 (93,613)<br>5 (72,423) |
| `master_project_ar` | 66.7 | 144 | 800 فيلا | وصل جيت | 0.0 | '' (7,033,769)<br>المدينة العالمية - المرحلة الاولى (371,151)<br>واحة السيليكون (203,948)<br>الخليج التجاري (201,600)<br>قرية جميرا الدائرية (191,174) |
| `master_project_en` | 66.7 | 145 | 800 Villas | Wasl Gate | 0.0 | '' (7,033,736)<br>International City Phase 1 (371,151)<br>Silicon Oasis (203,948)<br>Business Bay (201,600)<br>Jumeirah Village Circle (191,174) |
| `nearest_landmark_ar` | 7.0 | 14 | آي إم جي وورلد أدفينتشرز | وسط مدينة دبي | 0.0 | مطار دبي الدولي (4,216,532)<br>برج العرب (1,246,702)<br>برج خليفة (1,075,702)<br>أكاديمية المدينة الرياضية للسباحة (824,886)<br>وسط مدينة دبي (809,990) |
| `nearest_landmark_en` | 7.0 | 14 | Al Makhtoum International Airport | Sports City Swimming Academy | 0.0 | Dubai International Airport (4,216,532)<br>Burj Al Arab (1,246,702)<br>Burj Khalifa (1,075,702)<br>Sports City Swimming Academy (824,886)<br>Downtown Dubai (809,990) |
| `nearest_mall_ar` | 12.0 | 5 | ابن بطوطة مول | مول دبي | 0.0 | مول دبي (3,604,658)<br>سيتي سنتر مردف (2,614,143)<br>مول الإمارات (1,272,756)<br>'' (1,264,930)<br>مارينا مول (904,220) |
| `nearest_mall_en` | 12.0 | 5 | City Centre Mirdif | Marina Mall | 0.0 | Dubai Mall (3,604,658)<br>City Centre Mirdif (2,614,143)<br>Mall of the Emirates (1,272,756)<br>'' (1,264,930)<br>Marina Mall (904,220) |
| `nearest_metro_ar` | 11.1 | 56 | أبراج بحيرات جميرا | نخلة جميرا | 0.0 | '' (1,169,042)<br>محطة مترو الراشدية (856,106)<br>محطة مترو نور بنك (585,582)<br>محطة مترو الدانوب (427,057)<br>محطة مترو اتصالات (418,523) |
| `nearest_metro_en` | 11.1 | 56 | ADCB Metro Station | Union Metro Station | 0.0 | '' (1,169,042)<br>Rashidiya Metro Station (856,106)<br>Noor Bank Metro Station (585,582)<br>DANUBE Metro Station (427,057)<br>Etisalat Metro Station (418,523) |
| `no_of_prop` | 0.0 | 357 | 0 | 788 | 100.0 | 1 (8,557,763)<br>2 (225,724)<br>3 (109,104)<br>4 (84,578)<br>5 (70,188) |
| `project_name_ar` | 84.5 | 1,660 | (2) داماك لاجونز - سانتوريني | يونيستيت برايم تاور | 0.1 | '' (8,902,564)<br>رمرام (30,440)<br>سكاي كورتس (22,869)<br>ليكسايد (18,072)<br>المدينة العالمية الإماراتية (16,152) |
| `project_name_en` | 84.5 | 1,659 | 014 TOWER | joya verde residences dubai | 0.1 | '' (8,902,564)<br>REMRAAM (30,440)<br>SKY COURTS (22,869)<br>LAKESIDE (18,072)<br>INTERNATIONAL CITY EMARATI (16,152) |
| `project_number` | 84.5 | 1,663 | 2 | 4,000 | 100.0 | '' (8,902,564)<br>975.00 (30,440)<br>794.00 (22,869)<br>436.00 (18,072)<br>1288.00 (16,152) |
| `property_usage_ar` | 0.1 | 12 | تجاري | منشأه صحيه | 0.0 | سكني (7,452,713)<br>تجاري (2,953,007)<br>صناعي (64,190)<br>متعدد الاستخدامات (21,677)<br>صناعي / تجاري (16,883) |
| `property_usage_en` | 0.1 | 12 | Agriculture | Tourist origin | 0.0 | Residential (7,452,713)<br>Commercial (2,953,007)<br>Industrial (64,190)<br>Multi Usage (21,677)<br>Industrial / Commercial (16,883) |
| `tenant_type_ar` | 40.1 | 2 | جهة | شخص | 0.0 | '' (4,226,244)<br>شخص (3,271,365)<br>جهة (3,041,317) |
| `tenant_type_en` | 40.1 | 2 | Authority | Person | 0.0 | '' (4,226,244)<br>Person (3,271,365)<br>Authority (3,041,317) |
| `tenant_type_id` | 40.1 | 2 | 0 | 1 | 100.0 | '' (4,226,244)<br>0 (3,271,365)<br>1 (3,041,317) |
| `load_timestamp` | 0.0 | 1 | 2026-09-30T00:34:47.000Z | 2026-09-30T00:34:47.000Z | 0.0 | 2026-09-30T00:34:47.000Z (10,538,926) |
| `_source_file` | 0.0 | 11 | raw/dld/rents/rent_contracts_2026-09-30… | raw/dld/rents/rent_contracts_2026-09-30… | 0.0 | raw/dld/rents/rent_contracts_2026-09-30… (958,085)<br>raw/dld/rents/rent_contracts_2026-09-30… (958,085)<br>raw/dld/rents/rent_contracts_2026-09-30… (958,085)<br>raw/dld/rents/rent_contracts_2026-09-30… (958,085)<br>raw/dld/rents/rent_contracts_2026-09-30… (958,085) |
| `_source` | 0.0 | 1 | bulk | bulk | 0.0 | bulk (10,538,926) |
| `_snapshot_date` | 0.0 | 1 | 2026-09-30 | 2026-09-30 | 0.0 | 2026-09-30 (10,538,926) |
| `_ingested_at` | 0.0 | 11 | 2026-09-30 15:16:38.028982+04 | 2026-09-30 15:19:15.66679+04 | 0.0 | 2026-09-30 15:16:38.028982+04 (958,085)<br>2026-09-30 15:16:54.525646+04 (958,085)<br>2026-09-30 15:17:09.139313+04 (958,085)<br>2026-09-30 15:18:26.9571+04 (958,085)<br>2026-09-30 15:18:59.929682+04 (958,085) |
| `_row_hash` | 0.0 | 10,538,926 | 0000022789fc9b2a5aae78cfc53b5b0b | ffffff88302e06f8f0910242766fba28 | 0.0 | 0000022789fc9b2a5aae78cfc53b5b0b (1)<br>0000027b09c1dba6e6fa46f239a95c5c (1)<br>00000597a1537da4a4e96226b968d608 (1)<br>0000074d3ba03007f59744106c71171d (1)<br>000008098d49f314b888e343b04f3b6c (1) |
