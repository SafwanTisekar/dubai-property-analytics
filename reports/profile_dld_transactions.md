# Profile: `bronze.dld_transactions`

Generated 2026-09-30 11:22 UTC by `quality/profile.py` (SQL-based, exact counts over the full table).

- Rows: **1,788,150**
- Columns: 52 (47 source + metadata)
- Table size on disk: 1247 MB
- Profiling time: 15 s

Blank = `NULL` or `''` (DLD quotes every field, so missing values are empty strings in bronze). Min/max are numeric when ≥95% of non-blank values are numeric, otherwise text order. Values are truncated to 40 characters; ⏎ marks a line break.

| Column | Blank % | Distinct | Min | Max | Numeric % | Top values (count) |
|---|---:|---:|---|---|---:|---|
| `actual_worth` | 0.0 | 401,811 | 1 | 13,786,936,424 | 100.0 | 750000.00 (16,665)<br>1000000.00 (15,455)<br>500000.00 (12,291)<br>2000000.00 (9,861)<br>1200000.00 (9,007) |
| `area_id` | 0.0 | 259 | 229 | 531 | 100.0 | 330 (139,196)<br>526 (117,825)<br>441 (114,440)<br>350 (99,972)<br>390 (73,834) |
| `area_name_ar` | 0.0 | 258 | أم الدمن | يراح | 0.0 | مرسى دبي (139,196)<br>الخليج التجارى (117,825)<br>البرشاء جنوب الرابعة (114,440)<br>الثنيه الخامسة (99,972)<br>برج خليفة (73,834) |
| `area_name_en` | 0.0 | 258 | AL Athbah | Zareeba Duviya | 0.0 | Marsa Dubai (139,196)<br>Business Bay (117,825)<br>Al Barsha South Fourth (114,440)<br>Al Thanyah Fifth (99,972)<br>Burj Khalifa (73,834) |
| `building_name_ar` | 28.2 | 5,028 | (C2)النبض شقق الجاده | يونيفيرسيتي فيو ايه | 0.0 | '' (505,091)<br>برج خليفة (3,601)<br>سفن سيتي جي ال تي (3,580)<br>برج الاميرة (2,980)<br>سيليكون جيت 1 (2,871) |
| `building_name_en` | 28.2 | 5,025 | 02 Residence by Ned Al Ghurair | liora | 0.0 | '' (504,589)<br>Burj Khalifa (3,601)<br>Seven City JLT (3,580)<br>PRINCESS TOWER (2,980)<br>SILICON GATES 1 (2,871) |
| `has_parking` | 0.0 | 2 | 0 | 1 | 100.0 | 1 (1,203,098)<br>0 (585,052) |
| `instance_date` | 0.0 | 6,734 | 1416-07-02 | 2026-09-25 | 0.0 | 2023-09-11 (2,850)<br>2010-03-03 (2,297)<br>2009-10-26 (2,188)<br>2025-12-29 (2,068)<br>2025-07-21 (1,870) |
| `master_project_ar` | 12.8 | 161 | 800 فيلا | وصل جيت | 0.0 | '' (228,987)<br>قرية جميرا الدائرية (114,432)<br>الخليج التجاري (105,704)<br>دبي مارينا (98,501)<br>مجمع مركز دبي للسلع المتعددة الرئيسي (83,340) |
| `master_project_en` | 12.8 | 162 | 800 Villas | Wasl Gate | 0.0 | '' (228,946)<br>Jumeirah Village Circle (114,432)<br>Business Bay (105,704)<br>Dubai Marina (98,501)<br>DMCC Master Community (83,340) |
| `meter_rent_price` | 97.9 | 30,247 | 0.01 | 11,094,156 | 100.0 | '' (1,751,218)<br>5413.24 (129)<br>7481.11 (129)<br>7472.30 (104)<br>5649.00 (97) |
| `meter_sale_price` | 0.0 | 973,463 | 0 | 81,250,000 | 100.0 | 358.80 (2,278)<br>10.76 (1,110)<br>538.19 (989)<br>10763.90 (944)<br>8070.00 (831) |
| `nearest_landmark_ar` | 20.7 | 14 | آي إم جي وورلد أدفينتشرز | وسط مدينة دبي | 0.0 | '' (370,904)<br>أكاديمية المدينة الرياضية للسباحة (368,659)<br>برج العرب (250,828)<br>وسط مدينة دبي (210,661)<br>موتور سيتي (137,803) |
| `nearest_landmark_en` | 20.7 | 14 | Al Makhtoum International Airport | Sports City Swimming Academy | 0.0 | '' (370,904)<br>Sports City Swimming Academy (368,659)<br>Burj Al Arab (250,828)<br>Downtown Dubai (210,661)<br>Motor City (137,803) |
| `nearest_mall_ar` | 32.4 | 5 | ابن بطوطة مول | مول دبي | 0.0 | '' (578,694)<br>مارينا مول (474,088)<br>مول دبي (319,345)<br>مول الإمارات (191,881)<br>سيتي سنتر مردف (136,625) |
| `nearest_mall_en` | 32.4 | 5 | City Centre Mirdif | Marina Mall | 0.0 | '' (578,694)<br>Marina Mall (474,088)<br>Dubai Mall (319,345)<br>Mall of the Emirates (191,881)<br>City Centre Mirdif (136,625) |
| `nearest_metro_ar` | 31.7 | 56 | أبراج بحيرات جميرا | نخلة جميرا | 0.0 | '' (567,723)<br>محطة مترو بوج خليفة دبي مول (130,958)<br>مدينة دبي للإنترنت (120,257)<br>محطة مترو الخليج التجاري (115,450)<br>محطة مترو النخيل (105,365) |
| `nearest_metro_en` | 31.7 | 56 | ADCB Metro Station | Union Metro Station | 0.0 | '' (567,723)<br>Buj Khalifa Dubai Mall Metro Station (130,958)<br>Dubai Internet City (120,257)<br>Business Bay Metro Station (115,450)<br>Nakheel Metro Station (105,365) |
| `no_of_parties_role_1` | 0.1 | 216 | 0 | 703 | 100.0 | 1 (1,555,195)<br>2 (198,267)<br>4 (8,216)<br>3 (8,130)<br>0 (3,910) |
| `no_of_parties_role_2` | 0.1 | 31 | 0 | 78 | 100.0 | 1 (1,472,585)<br>2 (283,931)<br>0 (12,748)<br>3 (11,360)<br>4 (3,719) |
| `no_of_parties_role_3` | 0.1 | 15 | 0 | 17 | 100.0 | 0 (1,708,311)<br>2 (57,046)<br>4 (13,844)<br>1 (7,727)<br>'' (973) |
| `procedure_area` | 0.0 | 95,044 | 0.01 | 342,103,431 | 100.0 | 1393.55 (11,406)<br>45.00 (10,739)<br>144.00 (10,125)<br>112.24 (5,461)<br>174.80 (4,397) |
| `procedure_id` | 0.0 | 52 | 4 | 861 | 100.0 | 102 (628,175)<br>11 (513,971)<br>13 (244,142)<br>41 (154,742)<br>110 (59,649) |
| `procedure_name_ar` | 0.0 | 52 | إضافة أرض بالبيع | هبه - تسجيل مبدئى | 0.0 | بيع - تسجيل مبدئى (628,175)<br>بيع (513,971)<br>تسجيل رهن (244,142)<br>بيع مبدئى (154,742)<br>تسجيل إيجارة تنتهى بالتملك (59,649) |
| `procedure_name_en` | 0.0 | 52 | Adding Land By Sell | Transfer Development Mortgage | 0.0 | Sell - Pre registration (628,175)<br>Sell (513,971)<br>Mortgage Registration (244,142)<br>Delayed Sell (154,742)<br>Lease to Own Registration (59,649) |
| `project_name_ar` | 26.3 | 3,412 | (  مايسون الاليزيه I ) | يونيفرسال تاور | 0.1 | '' (470,065)<br>رمرام (11,774)<br>سكاي كورتس (10,830)<br>جميرا بارك (7,191)<br>المدينة العالمية الإماراتية (5,074) |
| `project_name_en` | 26.3 | 3,414 | 014 TOWER | ِِAzizi Riviera 60 | 0.1 | '' (470,065)<br>REMRAAM (11,774)<br>SKY COURTS (10,830)<br>JUMEIRAH PARK (7,191)<br>INTERNATIONAL CITY EMARATI (5,074) |
| `project_number` | 26.3 | 3,420 | 2 | 4,558 | 100.0 | '' (470,065)<br>975.00 (11,774)<br>794.00 (10,830)<br>1282.00 (7,191)<br>1288.00 (5,074) |
| `property_sub_type_ar` | 19.5 | 19 | تقسيم حجمى | ورشة | 0.0 | شقه سكنيه (1,145,384)<br>'' (349,412)<br>فيلا (154,904)<br>مكتب (73,652)<br>شقة فندقية (29,763) |
| `property_sub_type_en` | 19.5 | 19 | Building | Workshop | 0.0 | Flat (1,145,384)<br>'' (349,412)<br>Villa (154,904)<br>Office (73,652)<br>Hotel Apartment (29,763) |
| `property_sub_type_id` | 19.5 | 19 | 2 | 112 | 100.0 | 60 (1,145,384)<br>'' (349,412)<br>4 (154,904)<br>42 (73,652)<br>101 (29,763) |
| `property_type_ar` | 0.0 | 4 | أرض | وحدة | 0.0 | وحدة (1,283,561)<br>فيلا (309,339)<br>أرض (158,515)<br>مبنى (36,735) |
| `property_type_en` | 0.0 | 4 | Building | Villa | 0.0 | Unit (1,283,561)<br>Villa (309,339)<br>Land (158,515)<br>Building (36,735) |
| `property_type_id` | 0.0 | 4 | 1 | 4 | 100.0 | 3 (1,283,561)<br>4 (309,339)<br>1 (158,515)<br>2 (36,735) |
| `property_usage_ar` | 0.0 | 10 | Other | مليون | 0.0 | سكني (1,489,074)<br>تجاري (189,123)<br>مليون (48,129)<br>ضيافة (44,486)<br>Other (6,322) |
| `property_usage_en` | 0.0 | 10 | Agricultural | أخرى | 0.0 | Residential (1,489,074)<br>Commercial (189,123)<br>Other (48,129)<br>Hospitality (44,486)<br>أخرى (6,322) |
| `reg_type_ar` | 0.0 | 2 | العقارات القائمة | على الخارطة | 0.0 | العقارات القائمة (1,136,422)<br>على الخارطة (651,728) |
| `reg_type_en` | 0.0 | 2 | Existing Properties | Off-Plan Properties | 0.0 | Existing Properties (1,136,422)<br>Off-Plan Properties (651,728) |
| `reg_type_id` | 0.0 | 2 | 0 | 1 | 100.0 | 1 (1,136,422)<br>0 (651,728) |
| `rent_value` | 97.9 | 15,553 | 2 | 262,080,000 | 100.0 | '' (1,751,218)<br>368100.00 (337)<br>1000000.00 (223)<br>2000000.00 (176)<br>600000.00 (156) |
| `rooms_ar` | 21.0 | 17 | GYM | مكتب | 0.0 | غرفة (489,747)<br>'' (376,176)<br>غرفتين (338,454)<br>استوديو (259,472)<br>ثلاث غرف (185,046) |
| `rooms_en` | 21.0 | 17 | 1 B/R | Studio | 0.0 | 1 B/R (489,747)<br>'' (376,176)<br>2 B/R (338,454)<br>Studio (259,472)<br>3 B/R (185,046) |
| `transaction_id` | 0.0 | 1,788,150 | 1-102-2000-2 | 3-9-2026-999 | 0.0 | 1-102-2000-2 (1)<br>1-102-2003-103 (1)<br>1-102-2003-110 (1)<br>1-102-2003-14 (1)<br>1-102-2003-2 (1) |
| `trans_group_ar` | 0.0 | 3 | رهون | هبات | 0.0 | مبايعات (1,368,630)<br>رهون (352,805)<br>هبات (66,715) |
| `trans_group_en` | 0.0 | 3 | Gifts | Sales | 0.0 | Sales (1,368,630)<br>Mortgages (352,805)<br>Gifts (66,715) |
| `trans_group_id` | 0.0 | 3 | 1 | 3 | 100.0 | 1 (1,368,630)<br>2 (352,805)<br>3 (66,715) |
| `load_timestamp` | 0.0 | 1 | 2026-09-29T06:31:10.000Z | 2026-09-29T06:31:10.000Z | 0.0 | 2026-09-29T06:31:10.000Z (1,788,150) |
| `_source_file` | 0.0 | 2 | raw/dld/transactions/transactions_2026-… | raw/dld/transactions/transactions_2026-… | 0.0 | raw/dld/transactions/transactions_2026-… (894,076)<br>raw/dld/transactions/transactions_2026-… (894,074) |
| `_source` | 0.0 | 1 | bulk | bulk | 0.0 | bulk (1,788,150) |
| `_snapshot_date` | 0.0 | 1 | 2026-09-29 | 2026-09-29 | 0.0 | 2026-09-29 (1,788,150) |
| `_ingested_at` | 0.0 | 2 | 2026-09-30 15:16:02.908749+04 | 2026-09-30 15:16:18.708849+04 | 0.0 | 2026-09-30 15:16:02.908749+04 (894,076)<br>2026-09-30 15:16:18.708849+04 (894,074) |
| `_row_hash` | 0.0 | 1,788,150 | 000000708f65dafd07689d3cd61e2253 | fffff5b08190b78b95c07cd440e8b23e | 0.0 | 000000708f65dafd07689d3cd61e2253 (1)<br>00000abba1aed32a76f33efd084a3cf9 (1)<br>000010f54b0919e9752ac6b1e039f77c (1)<br>00001779f1c10d0f9e415657ebde1673 (1)<br>00001a69a3dadefec463c8e5e92cb7b7 (1) |
