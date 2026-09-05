# EXP-20260905 — KORD GEFS extraction pilot result

**Karar:** `GEFS_FULL_MEMBER_EXTRACTION_PILOT_FAIL`

İki pre-registered target günde 279 GEFS TMAX mesajı için index-directed range ve KORD nearest-grid decode denendi.

| Metrik | Sonuç | Gate |
|---|---:|---:|
| Başarılı message | 275/279 (%98,57) | %100 — fail |
| Non-finite/plausibility hatası | 0 | 0 — geçti |
| Uzak gridpoint | 0 | 0 — geçti |
| KORD nearest grid | 42.0°, 272.0° | Delta 0,079° — geçti |
| Pilot range transfer | 156.264.912 byte | Ölçüldü |
| Annual projected transfer | 27,28 GiB | ≤25 GiB — fail |
| Annual projected GET | 52.297 | ≤60.000 — geçti |

Dört mesaj transport 503/reset sonrasında başarısız oldu. Teşhis, range streaming sırasında yarım destination bırakılması ve retry'ın immutable-file kontrolüne takılmasıdır. Source object'ler envanterde mevcuttur; bu data missingness değildir. Downloader atomic temporary-file yaklaşımıyla düzeltilmelidir.

Ancak dört retry düzeltilse bile yıllık projected transfer 27,28 GiB ile maliyet gate'ini aşmaktadır. Bu nedenle 31 üyeli yıllık bulk retrieval başlatılmayacaktır.

## Düzeltici yön

NOAA'nın `geavg` ve `gespr` ensemble mean/spread ürünleri, pilotte başarıyla çözülen 275 member değerin empirical mean/spread'iyle iki gün/step bazında karşılaştırılacak. Aggregate ürünler yeterince eşleşirse aynı dağılım bilgisini yaklaşık 2/31 ürün ve çok daha düşük transferle feature olarak kullanabiliriz.

Bu karar model skoruna veya trading sonucuna dayanmaz; yalnız extraction bütünlüğü ve önceden kilitli operasyon maliyetine dayanır.
