# KORD / NOAA LCDv2 lag-safe final archive coverage

**Experiment:** `EXP-20260830-data-source-feasibility`

**Cut-off:** 2026-08-31

**Status:** `PASSED` for final archive coverage only

## Hipotez ve cohort

Latest-365 testindeki dokuz trailing missing date publication lag kaynaklıysa, aynı KORD/LCDv2 contract'ı 40 günlük buffer'lı sabit `2025-07-23–2026-07-22` penceresinde en az %99 exact-date ve non-null daily maximum coverage sağlamalıdır.

Bu yeni cohort ilk başarısızlık görüldükten sonra ayrı olarak ön-kayıt altına alındı. İlk latest-window sonucu değiştirilmedi veya overwrite edilmedi.

## Sonuç

| Metrik | Eşik | Sonuç | Karar |
|---|---:|---:|---|
| Exact-date coverage | ≥%99 | 365/365 = %100 | `PASSED` |
| Non-null daily maximum | ≥%99 | 365/365 = %100 | `PASSED` |
| Duplicate SOD date | 0 | 0 | `PASSED` |
| Identity failure | 0 | 0 | `PASSED` |
| Terminal transport failure | 0 | 0 | `PASSED` |

Admitted daily maximum aralığı −15,0°C–35,6°C. Missing date ve imputation yoktur. KORD / GHCN `USW00094846` isim ve koordinat identity kontrolleri tam geçti.

## Publication-lag proxy

| Annual object | Observed Last-Modified | Son SOD | Calendar-day farkı |
|---|---|---|---:|
| 2025 | 2026-05-05 | 2025-12-31 | 125 |
| 2026 | 2026-08-26 | 2026-08-21 | 5 |

Bu farklar gerçek bir row-level publication timestamp veya revision history değildir. Özellikle 2025 annual object'in sonradan yeniden üretildiğini gösterir; her günün ne zaman ilk kez/final olarak yayınlandığını söylemez. 2026 için 5 gün, yalnız observed current object metadata ile son SOD arasındaki freshness proxy'sidir.

## Settlement sentinel

Event `553903` için NOAA LCDv2 27,2°C / 80,96°F, current Wunderground 27°C ve terminal `68°F or higher` bucket tutarlıdır. Sonuç `FORENSIC_CONSISTENCY_ONLY`; exact settlement-as-of label değildir.

## Karar

- KORD/LCDv2 `FINAL_ARCHIVE_COVERAGE_PASS`.
- Latest-365 publication-lag sonucu `FAILED` olarak değişmeden kalır.
- LCDv2 rolü `INDEPENDENT_FINAL_DIAGNOSTIC_ONLY`.
- Historical decision-time/freeze-time statüsü `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`.
- Phase 5 `IN_PROGRESS`; final observation coverage ile settlement-as-of reconstruction aynı gate değildir.

## Sonraki en küçük adım

Wunderground KORD için append-only prospective freeze snapshot contract'ı tasarlanacak: market local date bittikten sonra sonraki günün ilk datapoint'ı görüldüğü anda sayfa, observed timestamp, content checksum, parsed daily high ve event/rule version birlikte saklanacak. Önce fixture/replay ve idempotency testleri yapılacak; kullanıcı açıkça uzun süreli collector istemeden sürekli süreç başlatılmayacak.
