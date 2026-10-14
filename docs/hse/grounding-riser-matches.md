# Riser and pressure incident grounding candidates

## Summary

Revision 1. Corpus current to 2026-01-08; 1,987 incident records. Accident classifications identify candidates; VIV, fatigue and overpressure causes are not established.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-14 | Riser disconnect and pressure-containment candidate identifiers were added to support incident grounding with explicit limits on confirming causes. |

## Corpus basis

Source: [BSEE Data Center](https://www.data.bsee.gov/Main/RawData.aspx).
Corpus SHA-256: `a174d467b39f74f3ceeab4c4d3e0dd01c903de253b21feec03359e818b9dd2fd`.

Identifiers below combine incident date, recorded time, lease and area block; the source has no separate incident identifier. Empty fields are preserved. No operator column is included.

## Classification limits

Riser disconnect candidates require a join to incident text that confirms the cause before citation as VIV or fatigue precedent. Weather, emergency and dropped item classifications are excluded. A missing fatigue term cannot establish absence of fatigue.

Gas and pressure releases, regulator failures, trapped well pressure and pressurized riser strings identify pressure-containment candidates. Overpressure and structural failure require corroboration. General shutdown, fire shutdown and glycol release do not qualify alone.

## riser_viv_fatigue

7 candidates (0.4% of the corpus).

- `2000-01-19|21:09|G14658|MC 822`
- `2000-02-28|14:45|G16614|MC 538`
- `2000-06-28|4:00|G15607|GC 743`
- `2001-06-30|11:00|G07998|GC 202`
- `2005-03-11|15:10|G24154|GC 157`
- `2005-03-15|11:05|G12145|EW 965`
- `2006-03-20|8:22|G17003|WR 544`

## structural_overpressure

45 candidates (2.3% of the corpus).

- `2003-12-20|16:45|G23992|MP 263`
- `2006-07-11|17:15|G18402|GC 608`
- `2007-02-28|20:14|G15610|GC 782`
- `2007-06-11|2:30|G22987|GC 680`
- `2007-09-07|6:15|G27858|VR 167`
- `2007-12-17|2:00|G04473|WD 27`
- `2008-02-14|17:30|G02925|PL 10`
- `2008-05-22|15:35|G11455|GB 128`
- `2008-05-23|2:00|G02445|VK 900`
- `2008-07-19|12:48|G01520|SS 204`
- `2009-02-13|10:12|G04240|ST 300`
- `2009-05-27|12:00|G22620|VR 122`
- `2009-07-01|13:32||GC 787`
- `2010-02-06|6:30|G02061|EC 321`
- `2010-06-26|:15|G03818|MC 280`
- `2011-09-17|13:55|G01073|WD 41`
- `2011-09-28|8:15| 00064|SS 114`
- `2013-02-01|16:10| 00680|WC 20`
- `2014-11-20|14:40||WD 105`
- `2015-05-09|17:30|G06280|EB 165`
- `2015-10-16|20:15|G21790|GC 338`
- `2016-01-30|16:00|G33735|MC 471`
- `2016-07-22|17:25|G18402|GC 608`
- `2016-11-26|14:06|G21861|WR 551`
- `2017-09-19|16:00|G11445|GB 128`
- `2017-11-03|13:50|G09743|VK 817`
- `2018-05-08|9:15||GC 787`
- `2018-09-06|20:40|G26313|GC 468`
- `2020-01-23|12:00|G31418|ST 311`
- `2020-04-27|3:00|G35292|EW 305`
- `2020-07-15|14:11|G33733|MC 437`
- `2020-08-02|19:25||MC 778`
- `2020-11-21|19:45|G06896|VK 956`
- `2020-12-09|18:06|G05868|MC 809`
- `2021-01-09|8:30| 00026|WD 30`
- `2021-01-13|23:04|G05868|MC 809`
- `2022-07-13|20:45|G16623|MC 582`
- `2022-07-29|9:00|G01084|WD 74`
- `2023-02-17|4:30|G01083|WD 73`
- `2023-03-12|16:30|G02213|MP 311`
- `2023-09-09|16:00|G02600|SM 281`
- `2023-12-15|5:20|G02280|SM 130`
- `2024-11-24|17:10|G06894|VK 915`
- `2024-12-02|8:30|G06898|VK 989`
- `2025-11-03|12:05|G01294|SP 62`
