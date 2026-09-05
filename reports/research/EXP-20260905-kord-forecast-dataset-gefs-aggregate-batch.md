# EXP-20260905 — Annual KORD GEFS aggregate feature batch

**Karar:** `ANNUAL_GEFS_AGGREGATE_GATE_PASS`

362 publication-admissible KORD target günü için `geavg` ve `gespr` canonical TMAX mesajları compact range ile indirildi ve nearest gridpoint'te decode edildi.

| Metrik | Sonuç | Gate |
|---|---:|---:|
| Aggregate message | 3.374/3.374 | ≥%99 — geçti |
| Complete target day | 362/362 | ≥%97 — geçti |
| Exact / proxy gün | 122 / 240 | Ayrı saklandı |
| Finite/plausible | %100 | Geçti |
| Duplicate target date | 0 | Geçti |
| Recovered transient transport | 46 | Atomic retry ile düzeldi |
| Terminal transport failure | 0 | Geçti |
| Gerçek range transfer | 1.600.972.976 byte (1,490 GiB) | Projected 1,462 GiB'e yakın |

Her gün overlap/interior mean maximum, peak-step spread, maximum block spread, exact/proxy ve outside-local seconds alanlarını taşır. Summer/DST proxy değerleri resolution-equivalent olarak etiketlenmez.

NBM, GEFS ve NOAA label tarih kümelerinin exact kesişimi 357/365=%97,808'dir. Sekiz dışlanan gün source publication veya label publication eksikliğinden gelir; imputation uygulanmadı.

Sonraki adım bu üç kaynağı exact 357 satırlık model-ready tabloda birleştirip schema ve checksum ile dondurmaktır. Temporal split ve model seçimi ancak bu final data gate sonrasında önceden kaydedilecektir.
