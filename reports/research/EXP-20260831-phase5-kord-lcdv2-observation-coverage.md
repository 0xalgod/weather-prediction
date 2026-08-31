# KORD / NOAA LCDv2 observation coverage

**Experiment:** `EXP-20260830-data-source-feasibility`

**Cut-off:** 2026-08-31

**Status:** `FAILED` for the locked latest-365-day coverage gate

## Soru

NOAA NCEI Local Climatological Data v2 (LCDv2), Chicago O'Hare/KORD için kilitlenen 2025-08-31–2026-08-30 aralığında en az %99 daily-maximum coverage, exact station identity ve açık revision sınırlaması sağlayabiliyor mu?

LCDv2, NOAA'nın airport observation sistemlerinden ürettiği resmî hourly/daily üründür. Ancak Polymarket event 553903'ün declared settlement kaynağı Wunderground KORD'dur. Bu nedenle NOAA sonucu yalnız bağımsız forensic diagnostic olarak değerlendirilmiştir.

## Kaynak ve provenance

- Dataset: NOAA NCEI Local Climatological Data v2
- Documentation: `https://www.ncei.noaa.gov/products/land-based-station/local-climatological-data`
- Station: GHCN `USW00094846`, KORD / Chicago O'Hare, WBAN 94846
- Files: `LCD_USW00094846_2025.csv`, `LCD_USW00094846_2026.csv`
- Field: `DailyMaximumDryBulbTemperature`, `REPORT_TYPE=SOD`, °C
- Local immutable raw run: `data/raw/noaa_lcdv2/run=20260831T-phase5-kord-lcdv2-v2`

URL, retrieval timestamp, Last-Modified, ETag, byte count and SHA-256 final JSON artifact'ta saklanmıştır. Raw files source control'e alınmamıştır.

## Ön-kayıtlı gate ve sonuç

| Metrik | Eşik | Sonuç | Karar |
|---|---:|---:|---|
| Beklenen local date | 365 | 365 | — |
| Temsil edilen date | ≥%99 | 356 / 365 = %97,53 | `FAILED` |
| Non-null daily maximum | ≥%99 | 356 / 365 = %97,53 | `FAILED` |
| Duplicate SOD date | 0 | 0 | `PASSED` |
| Identity failure | 0 | 0 | `PASSED` |
| Terminal transport failure | 0 | 0 | `PASSED` |

Eksik tarihler ardışık dokuz gündür: `2026-08-22`–`2026-08-30`. 2026 objesinin observed `Last-Modified` zamanı 2026-08-26 21:03:31 GMT olmasına rağmen son SOD tarihi 2026-08-21'dir. Bu nedenle eksiklik parser veya tekil gün anomalisi değil, current annual product publication lag'iyle tutarlıdır.

Admitted daily maximum aralığı −15,0°C ile 35,6°C'dir. İmputation yapılmadı.

## Settlement sentinel

Event `553903`, Chicago 2026-06-05:

- terminal Polymarket winner: `68°F or higher`;
- current Wunderground high: 27°C;
- NOAA LCDv2 SOD maximum: 27,2°C = 80,96°F;
- NOAA value terminal bucket ile tutarlı.

Bu yalnız `FORENSIC_CONSISTENCY_ONLY` sonucudur. Tek event, NOAA'nın Wunderground freeze-time değerini yeniden ürettiğini veya historical exact-temperature label sağladığını kanıtlamaz.

## Revision ve label kararı

- Annual object Last-Modified, yalnız bugün gözlenen object version'ını gösterir.
- Settlement anındaki Wunderground sayfasının veya NOAA annual file'ın o tarihteki sürümü geri kurulamadı.
- LCDv2 daily-window/finalization semantiğinin Wunderground local-calendar-day ve next-day-first-datapoint freeze kuralıyla birebir eşitliği kanıtlanmadı.
- Sonuç sınıfı: `INDEPENDENT_FINAL_DIAGNOSTIC_ONLY`.
- Historical freeze statüsü: `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`.
- Exact-temperature training/backtest label statüsü verilmedi.

## Deney hafızası

İlk artifact, ön-kayıtlı terminal transport failure metriğini açık alan olarak içermediği için `-attempt1.json` adıyla korunmuştur. Ölçüm sonucu değişmedi; final artifact bu metriği `0` olarak açıkça taşır.

## Karar ve sonraki adım

Latest-365 LCDv2 coverage gate `FAILED`; Phase 5 `IN_PROGRESS` kalır. NOAA LCDv2 KORD için yüksek kaliteli final diagnostic olmaya devam eder, ancak yakın günlerdeki publication lag nedeniyle karar-zamanlı outcome collector değildir.

Sonraki en küçük deney, sonuç seçmeden önce lag-safe bir historical window ve publication-lag ölçümünü ön-kaydetmektir: aynı 365 günlük aralık en az 30 günlük as-of buffer ile yeniden ölçülecek; ayrıca annual-object Last-Modified ile son SOD tarihi arasındaki lag raporlanacaktır. Bu test yalnız final research-label coverage'ı değerlendirir, freeze-as-of sorununu çözmüş saymaz.
