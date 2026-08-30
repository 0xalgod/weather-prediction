# EXP-20260830 — ECMWF Open Data gerçek dosya ve retention ölçümü

**Tarih:** 2026-08-30

**Durum:** `CONDITIONAL_PASS` (prospective), `FAILED` (historical backtest source)

**Data cut-off:** 2026-08-30T00Z run, step 24

**Client:** `ecmwf-opendata==0.3.34`

## Hipotez ve önceden yazılan gate

ECMWF Open Data, uluslararası şehirler için sıcaklık olasılığı üretecek gerçek
deterministic/ensemble alanlarını sağlar ve doğrudan en az 365 günlük as-issued retention taşır.

Koşudan önce gereken alanlar `2t`, `mx2t3`, `mn2t3`; deterministic için alan başına 1,
perturbed ensemble için alan başına 50 ve tam 1–50 member seti olarak kilitlendi. İndirilen
GRIB subsetlerinin beklenen mesaj sayısı 3/150/3 (deterministic/perturbed/control), geçerli GRIB
başlangıç/sonu ve SHA-256 taşıması; historical gate için 365 günlük obje erişimi gerekiyordu.

## Ölçülen sonuç

| Ölçüm | Sonuç |
|---|---:|
| Deterministic index | 184 row, 40.210 byte |
| Deterministic sıcaklık inventory | 3 row: her alan 1 |
| Deterministic gerçek subset | 3 GRIB mesajı, 1.941.310 byte |
| Ensemble index | 8.500 row, 2.004.334 byte |
| Perturbed sıcaklık inventory | 150 row: her alan 50 |
| Perturbed member seti | tam 1–50 |
| Perturbed gerçek subset | 150 GRIB mesajı, 97.501.524 byte |
| Control (`cf`) | bu run/step indexinde eşleşme yok |
| Retention HTTP 200 | run tarihi −0, −1, −2 gün |
| Retention HTTP 404 | −3, −4, −7, −30, −365 gün |

Her iki indirilen GRIB subseti `GRIB` ile başlayıp `7777` ile bitti; checksum'lar evidence
JSON'unda kayıtlıdır. Ensemble indexi tam 50 perturbed üye içerdi. Client dokümantasyonu
`cf` control tipini tarif etmesine karşın gerçek `enfo` indexi yalnız `pf` satırları içerdi ve
bu alan/step için control retrieval eşleşmedi. Control varmış gibi doldurulmayacaktır.

## Karar

- **Current/prospective kullanım:** Koşullu geçti. IFS deterministic ile 50-member ensemble,
  global şehirler için gereken yüzey sıcaklığı ve 3 saatlik max/min alanlarını taşıyor.
- **Historical backtest:** Başarısız. Ölçülen açık yüzey yalnız üç run tarihini kapsıyor;
  365 günlük as-issued geçmiş üretilemez.
- **Look-ahead kuralı:** Reanalysis veya bugün indirilen tahmin, eski karar anındaki as-issued
  tahminin yerine geçirilemez.
- **Operasyonel sınır:** Tek step/tek run/üç alanın perturbed subseti yaklaşık 97,5 MB. Kalıcı
  prospective toplamada şehir çevresi spatial subset, gerekli step seçimi ve retention bütçesi
  tasarlanmalıdır.
- **Lisans:** Resmî dağıtım ve client mesajı veriyi CC BY 4.0 altında tanımlar; attribution ve
  exact source/run provenance korunmalıdır.

## Sonraki en küçük adım

Tarihsel global ensemble ihtiyacı için açık ve gerçek archive erişimi olan GEFS'i aynı standartla
ölç: as-issued object erişimi, temperature/max-min değişkenleri, member yapısı, run availability,
en az 365 günlük retention ve tahmini indirme/depolama maliyeti.

## Artifact'lar

- `reports/data_quality/EXP-20260830-phase4-ecmwf-open-data-probe.json`
- local immutable raw: `data/raw/ecmwf_open/run=20260830T00Z-step24-v1/` (Git dışında)
- probe: `scripts/probe_ecmwf_open_data.py`
- ingestion contract: `src/weather_quant/ingestion/ecmwf_open_data.py`

## Birincil kaynaklar

- <https://www.ecmwf.int/en/forecasts/datasets/open-data>
- <https://github.com/ecmwf/ecmwf-opendata>
- <https://www.ecmwf.int/sites/default/files/ECMWF_Standard_Licence.pdf>
