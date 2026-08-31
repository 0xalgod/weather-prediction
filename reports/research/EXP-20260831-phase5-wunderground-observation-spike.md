# CYYZ/WMKK Wunderground observation spike

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Ölçüm:** 2026-08-31  
**Evidence class:** Current/final historical page; market-freeze-as-of değildir

## Ön-kayıtlı soru

Polymarket'in exact resolution source'u olan Wunderground daily-history sayfalarının CYYZ ve WMKK için 365 günlük observation dataset'ine ölçeklenmeden önce station/date/high/observation sözleşmesini sabit bir 24 sayfalık örnekte geçip geçmediği ölçüldü.

Her istasyonun reconciled market tarihinden geriye `0,1,7,30,60,90,120,150,180,240,300,364` gün seçildi. Gate, 24 sayfanın tamamında HTTP 200, exact station code/name/timezone/requested date, Celsius daily high, non-empty observation table, deterministic normalized parse ve terminal transport failure 0 idi.

## Sonuç

| Kontrol | Sonuç |
|---|---:|
| Tam sayfa | 24 / 24 |
| HTTP 200 | 24 / 24 |
| Station code/name/timezone | 24 / 24 |
| Requested date identity | 24 / 24 |
| Celsius daily high | 24 / 24 |
| Observation table | 24 / 24 |
| Normalized repeatability | 24 / 24 |
| İlk attempt'te başarı | 24 / 24 |
| Terminal transport failure | 0 |
| Daily high = max observation temperature | 24 / 24 |

CYYZ sayfalarında gün başına 24–41, WMKK sayfalarında 41–50 sıcaklık gözlemi vardı. Toplam 1.344.540 byte source HTML çekildi ve her response için SHA-256 ile retrieval timestamp kaydedildi.

## Karar

Spike gate `PASSED`. Ön-kayıtlı scaling rule uyarınca iki istasyon için 365'er günlük full current/final coverage ölçümüne izin verildi.

Bu sonuç historical settlement-as-of değerini kanıtlamaz. Polymarket kuralı revizyonları ertesi gün ilk veri noktasında donduruyor; bugün çekilen Wunderground sayfası sonradan değişmiş olabilir. Bu nedenle:

- forecast calibration için current/final observation label olarak değerlendirilebilir;
- exact historical settlement reconciliation için korunmuş freeze-time snapshot veya prospective next-day capture gereklidir;
- iki evidence class aynı kolon/statü altında sessizce birleştirilemez.

## Artifact

`reports/data_quality/EXP-20260831-phase5-wunderground-observation-spike.json`
