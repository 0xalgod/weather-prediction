# EXP-20260906 — Multi-city weather inventory v1

**Durum:** `PASSED`

## Sonuç

8.222 closed highest-temperature event, immutable Gamma envanterinden normalize edildi. Exactly-one resolved YES winner, resolution source, temperature unit, target date ve tüm bucket market/condition/token kimlikleri zorunlu tutuldu.

- Eligible event: 7.573 / 8.222 = %92,107
- Eligible şehir: 52
- En az 30 eventli araştırma şehri: 48
- Araştırma evreni: 7.512 event
- Admitted bucket: 82.407
- Duplicate event: 0
- Tarih aralığı: 2025-12-30–2026-08-29
- Celsius/Fahrenheit: 5.655 / 1.918 event

Rule açıklamalarındaki unit-toggle metni iki birimi birlikte içerdiğinden attempt 1 yalnız 262 event kabul etti. Post-hoc corrective v2, bütün bucket label'larının oybirliğiyle taşıdığı birimi kullandı. Eksik `eventDate` bulunan 449 admitted eski eventte `endDate` UTC calendar date açık provenance ile fallback oldu. Numeric gate'ler değiştirilmedi.

639 missing-source, 10 terminal-winner-count anomaly ve 2 incomplete-identity reason kaydı dışarıda kaldı; reason'lar çakışabilir.

## Karar

Multi-city inventory gate geçti. Sonraki deney tüm 7.512 eventi körlemesine indirmeden önce şehir/tarih stratified pilot üzerinde 6/12/18/24/36 saat historical price coverage'ını ölçecektir. Bu sonuç forecast edge, executable fill veya P&L kanıtı değildir.
