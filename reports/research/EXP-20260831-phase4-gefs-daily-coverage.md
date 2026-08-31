# GEFS 365 günlük temsilî coverage sonucu

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Data cut-off:** 2026-08-30 00Z run  
**Ölçüm zamanı:** 2026-08-31  
**Kaynak:** NOAA GEFS public operational AWS archive, `pgrb2sp25`

## Hipotez ve önceden kilitlenen gate

Operational GEFS 00Z/f024 indekslerinin historical calibration için yeterince sürekli as-issued sıcaklık alanı sunup sunmadığı sınandı. Pencere analizden önce 2025-08-31–2026-08-30 dahil 365 tamamlanmış UTC gün olarak kilitlendi. Her gün `gec00`, `gep01` ve `gep30` üyelerinde tam birer 2 m `TMP`, `TMAX` ve `TMIN` kaydı arandı.

Gate, 1.095 temsilî indeksin en az %99'unun tam olması ve üç bounded denemeden sonra terminal transport failure kalmamasıydı. Eksik tarih çıkarsa 31 üyenin tamamı ve 06/12/18Z alternatif cycle'lar otomatik araştırılacaktı.

## Sonuç

| Metrik | Sonuç |
|---|---:|
| Tam gün | 365 / 365 |
| Tam temsilî indeks | 1.095 / 1.095 |
| Coverage | %100,000 |
| Her indekste exact TMP/TMAX/TMIN | 1.095 / 1.095 |
| HTTP 200 | 1.095 / 1.095 |
| İlk denemede başarı | 1.092 |
| İkinci denemede başarı | 3 |
| Geçici transport error | 3 |
| Retry sonrası terminal transport failure | 0 |
| Eksik tarih | 0 |

Ön-kayıtlı temsilî continuity gate'i **geçti**. Eksik tarih olmadığı için full-member/alternative-cycle diagnostic dalı tetiklenmedi.

## Veri kalitesi ve yorum

- İndeks boyutları 2.491–2.841 byte aralığındaydı ve her başarılı cevap SHA-256 ile kaydedildi.
- Üç geçici bağlantı hatası ikinci denemede düzeldi. Bunlar archive missingness olarak sınıflandırılmadı; ham hata ve attempt sayıları artifact'ta korundu.
- İlk ölçüm denemesinde özetleyici, düzelmiş transient hataları yanlışlıkla terminal hata saydı. Bu çıktı `reports/data_quality/EXP-20260831-phase4-gefs-daily-coverage-365d-attempt1.json` olarak korundu; metrik kodu transient ve terminal hataları ayıracak şekilde düzeltildi ve nihai immutable artifact yeniden üretildi.
- Sonuç, üç temsilî üye için günlük sürekliliği güçlü biçimde destekler. Fakat yalnız `c00/p01/p30` incelendiğinden 365 günün her birinde 31/31 üyeyi kanıtlamaz.
- f024 alanının varlığı, Polymarket'in istasyon-yerel günlük maksimum sıcaklığının doğru forecast-step penceresinden leakage olmadan üretilebildiğini henüz kanıtlamaz.

## Karar

GEFS operational archive statüsü `CONDITIONAL_PASS` olarak kalır, ancak 365 günlük temsilî continuity alt-gate'i `PASSED` olur. Bir sonraki en küçük deney, bir DST kullanan ve bir DST kullanmayan şehir için f006/f012/f018/f024 alanlarının valid-time/window semantiğini çözerek yerel günlük MaxT dönüşüm sözleşmesini kilitlemektir.

## Yeniden üretim

```bash
PYTHONPATH=src python3 scripts/probe_noaa_gefs_daily_coverage.py \
  --start-date 2025-08-31 --days 365 --cycle 0 --step 24 --workers 8 \
  --output reports/data_quality/EXP-20260831-phase4-gefs-daily-coverage-365d.json
```

Kanıt: `reports/data_quality/EXP-20260831-phase4-gefs-daily-coverage-365d.json`.
