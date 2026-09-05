# EXP-20260905 — KORD annual dataset label coverage

**Karar:** `LABEL_COVERAGE_PASS_WITH_PUBLICATION_LAG`  
**Ölçüm zamanı:** 2026-09-05 13:12 UTC

## Sonuç

NOAA LCDv2 yıllık dosyaları yeniden indirildi ve KORD/`USW00094846` için 2025-09-01–2026-08-31 arasındaki tam 365 günlük hedef pencere ölçüldü.

| Metrik | Sonuç | Gate |
|---|---:|---:|
| Günlük maksimum etiketi | 362/365 | ≥%99 |
| Coverage | %99,178 | ≥%99 — geçti |
| Duplicate tarih | 0 | 0 — geçti |
| İstasyon identity hatası | 0 | 0 — geçti |
| Terminal transport hatası | 0 | 0 — geçti |

Eksik tarihler 2026-08-29, 2026-08-30 ve 2026-08-31. Kaynağın 2026 dosyası en son 2026-09-01'de güncellenmiş ve son SOD kaydı 2026-08-28'dir. Bu nedenle eksiklik provider publication lag olarak sınıflandırıldı; değerler doldurulmadı veya başka kaynaktan sessizce taşınmadı.

## Karar

Ön-kayıtlı `%99` label coverage gate'i geçti. Şimdilik yalnız 362 gözlenen gün dataset'e alınabilir. Son üç gün daha sonraki immutable refresh'te eklenebilir; mevcut source checksum'ları korunur.

Bu NOAA etiketi forecast modelinin öğrenme hedefidir. Polymarket'in historical frozen settlement değerini kanıtlamaz; ekonomik testte resolution kaynağı ayrı bağlanacaktır.

## Sıradaki adım

Aynı 365 hedef gün için prior-day NBM 07Z source availability/publication envanterini ölç. Feature değerlerini veya model skorlarını henüz hesaplama.
