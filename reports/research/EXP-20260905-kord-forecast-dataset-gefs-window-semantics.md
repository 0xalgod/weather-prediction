# EXP-20260905 — KORD GEFS local-day window semantics

**Karar:** `GEFS_TMAX_MIXED_EXACT_AND_PROXY`

GEFS canonical 6-hour TMAX blokları, target-minus-one-day 00Z run'a göre 365 KORD hedef gününün `America/Chicago` yerel gün pencereleriyle karşılaştırıldı.

| Rejim | Gün | Hedef kapsama | Dışarıdan süre | Exact partition |
|---|---:|---:|---:|---|
| Yaz saati normal gün | 238 | %100 | 6 saat | Hayır |
| DST bitiş günü | 1 | %100 | 5 saat | Hayır |
| Kış saati normal gün | 125 | %100 | 0 saat | Evet |
| DST başlangıç günü | 1 | %100 | 1 saat | Hayır |

Tüm hedef günler kapsanır fakat yalnız 125 gün exact local-day partition sağlar. Diğer 240 günün TMAX blokları hedef gün dışından süre içerir.

Bu nedenle GEFS feature politikası model skoru görülmeden güncellendi:

- Exact 125 günde dört bloktan exact local-day ensemble maximum kullanılabilir.
- Diğer günlerde yalnız tamamen içeride kalan blokların `interior lower-feature` değeri ve hedefe dokunan blokların `overlap upper-feature` değeri birlikte saklanır.
- `outside_local_seconds` zorunlu feature/quality alanıdır.
- Non-exact değerler resolution-equivalent günlük MaxT olarak sunulmaz.
- Model sonuçları exact/non-exact rejimde ayrı ve non-exact günleri dışlayan sensitivity testiyle raporlanır.

Henüz GEFS member dosyaları indirilmedi veya model skoru hesaplanmadı.
