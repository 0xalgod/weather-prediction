# EXP-20260905 — KORD annual GEFS full-member inventory

**Karar:** `ANNUAL_GEFS_INVENTORY_GATE_PASS`

365 target günün her biri için prior-day GEFS 00Z public S3 listing'i tarandı. 31 ensemble üyesi ve Chicago local-day rejimine göre gerekli dört veya beş canonical TMAX step'in hem data hem `.idx` object'i kontrol edildi.

| Metrik | Sonuç | Gate |
|---|---:|---:|
| Başarılı günlük listing | 365/365 | Geçti |
| Complete + zamanında member-day | 11.222/11.315 (%99,178) | ≥%97 — geçti |
| Fiziksel data/index çifti | 52.669/52.669 | %100 |
| Karar anında admissible pair | 52.297 | Ölçüldü |
| Terminal transport failure | 0 | 0 — geçti |
| Retry ile düzelen transient hata | 2 | Görünür tutuldu |

19 Aralık 2025, 20 Aralık 2025 ve 26 Ocak 2026 target günlerinin bütün 31 üyeleri arşivde mevcut olsa da 11:00 UTC karar zamanından sonra yayımlanmıştır. Bu günler dışlanır; alternatif cycle kullanılmaz.

NBM, GEFS ve NOAA label exclusion kümelerinin birleşimi sekiz unique target gündür. GEFS value extraction aynı coverage'ı korursa nihai join 357/365=%97,808 olacaktır ve locked ≥%97 gate'i geçecektir.

Envanter 2.190 S3 sayfasında 1.951.389 object metadata kaydını incelemiştir. Raw artifact yaklaşık 38 MB'dir ve checksum ile kilitlenmiştir.

Henüz 52.297 TMAX range indirilmedi. Bir winter-exact ve bir summer-proxy gününde gerçek index/range byte maliyeti ve gridpoint extraction doğrulanmadan yıllık bulk retrieval başlatılmayacaktır.
