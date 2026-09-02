# Upcoming exact-rule KORD event discovery

**Experiment:** `EXP-20260830-data-source-feasibility`

**Observed:** 2026-09-02 12:04 UTC

**Result:** `NOT_AVAILABLE` for Wunderground-primary KORD cohort

## Ön-kayıtlı soru

Complete public Gamma `highest-temperature`, `closed=false` inventory'sinde observed-future, active/not-closed, exact Wunderground `/KORD` primary source ve next-day-first-datapoint rule taşıyan fully identified bir Chicago event var mı?

Varsa en erken endDate/event ID seçilecekti. Yoksa başka şehir veya geçmiş event ikame edilmeyecekti.

## Inventory sonucu

| Metrik | Sonuç |
|---|---:|
| Keyset page | 2 |
| Source event | 150 |
| Duplicate event | 0 |
| Unique city | 51 |
| Chicago event | 3 |
| Observed-future Chicago event | 2 |
| Identity-complete Chicago event | 3 |
| Wunderground-primary KORD event | 0 |
| Fully qualified event | 0 |

## Chicago rule audit

| Event | Tarih/end | Observed-future | Primary source | KORD/trigger/identity | Qualified |
|---:|---|---|---|---|---|
| 940517 | 2026-09-02 12:00Z | Hayır | NOAA WRH KORD | Geçti | Hayır |
| 946566 | 2026-09-03 12:00Z | Evet | NOAA WRH KORD | Geçti | Hayır |
| 952456 | 2026-09-04 12:00Z | Evet | NOAA WRH KORD | Geçti | Hayır |

Üç event de active/not-closed ve nested market/token identity açısından tamdır. Fakat `resolutionSource` üçünde de `https://www.weather.gov/wrh/timeseries?site=kord`; Wunderground yalnız fallback metninde yer alır. Ön-kayıtlı primary-source gate bu nedenle 0/3'tür.

## Bulguların anlamı

- Wunderground freeze snapshot yazılımı geçerli bir storage primitive olarak kalır, fakat mevcut Chicago cohort'una primary settlement evidence olarak uygulanamaz.
- Chicago rule/provider rejimi historical Wunderground-primary event 553903'ten current NOAA-primary eventlere değişmiştir.
- Historical ve current Chicago eventleri aynı provider rejimiymiş gibi tek model/backtest segmentine karıştırılmamalıdır.
- Wunderground fallback'in devreye girme koşulu ayrıca versioned rule field olmalıdır; primary NOAA mevcutken fallback page çekimi settlement label değildir.
- Sonuç, market availability değil exact preregistered cohort availability açısından `NOT_AVAILABLE`dır.

## Güvenlik ve provenance

Yalnız public Gamma GET/keyset çağrısı kullanıldı. Raw iki envelope checksum/timestamp ile ignored immutable run `data/raw/polymarket_gamma-kord-discovery/run=20260902T120408Z` altında saklandı. Wallet, credential, order veya background collector kullanılmadı.

## Karar ve sonraki adım

Wunderground-primary KORD live cohort seçilmedi. Phase 5 `IN_PROGRESS`. Sonraki adım, mevcut NOAA WRH KORD primary source'un veri yüzeyi, timestamp/timezone/unit, hourly row, next-day trigger ve revision semantiğini read-only incelemek ve sonuç görmeden NOAA-primary prospective contract gate'ini tanımlamaktır.
