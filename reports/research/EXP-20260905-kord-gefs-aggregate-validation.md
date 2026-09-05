# EXP-20260905 — GEFS aggregate-product validation result

**Karar:** `GEFS_AGGREGATE_VALIDATION_PASS`

`geavg` ve `gespr` TMAX ürünleri, checksum-locked full-member pilotundaki altı eksiksiz 31/31 case-step hücreyle karşılaştırıldı.

| Metrik | Sonuç | Gate |
|---|---:|---:|
| Aggregate message | 18/18 | %100 — geçti |
| Primary complete cell | 6 | Exact 6 — geçti |
| Mean MAE | 0,0333°F | ≤0,25°F — geçti |
| Mean max absolute error | 0,1179°F | ≤0,75°F — geçti |
| Spread MAE | 0,0658°F | ≤0,25°F — geçti |
| Spread max absolute error | 0,1514°F | ≤0,75°F — geçti |
| Annual projected transfer | 1,462 GiB | ≤3 GiB — geçti |
| Annual projected range GET | 3.374 | ≤4.000 — geçti |

NOAA aggregate ürünleri pilot kapsamındaki empirical mean ve population spread'i önceden kilitlenen toleransların çok içinde yeniden üretti. Bu nedenle yıllık 31-member bulk retrieval yerine `geavg`/`gespr` compact ingestion kullanılmasına izin verildi.

Bu karar yaklaşık 27,28 GiB ve 52.297 GET öngören full-member tasarımını yaklaşık 1,46 GiB ve 3.374 GET seviyesine indirir. Individual ensemble frequency kaybolur; modelde mean/spread tabanlı parametrik dağılım veya regularized feature olarak kullanılacaktır.

Doğrulama yalnız bir winter ve bir summer gündeki altı complete hücreyi kapsar. Forecast skill, calibration veya trading edge kanıtı değildir. Yıllık ingestion exact/proxy window rejimini ve publication gates'i korumalıdır.
