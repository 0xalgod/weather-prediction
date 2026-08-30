# EXP-20260830 — GEFS operasyonel archive ilk fizibilite ölçümü

**Tarih:** 2026-08-30

**Durum:** `CONDITIONAL_PASS`

**Data cut-off:** 2026-08-30 00Z, forecast hour 24

## Hipotez ve pre-registered gate

NOAA'nın operasyonel GEFS public archive'ı global şehirler için geçmişte gerçekten yayımlanmış,
en az 365 gün geriye giden ensemble sıcaklık girdisi sağlar.

Gate analizden önce şöyle kilitlendi:

- güncel ve ≥365 gün eski operasyonel run;
- control `c00` + perturbed `p01–p30`, yani 31/31 üye;
- her üyede 2 metre `TMP`, `TMAX`, `TMIN` tam birer kez;
- `c00`, `p01`, `p30` için gerçek byte-range download;
- subset başına 3 geçerli GRIB mesajı, HTTP 206 ve SHA-256;
- reforecast/replay verisi operasyonel geçmiş sayılmaz.

## Ölçülen sonuç

| Run | Yaş | Tam üye | Availability aralığı | Full f024 obje toplamı | Seçili 3 alan toplamı |
|---|---:|---:|---:|---:|---:|
| 2026-08-30 00Z | 0 gün | 31/31 | 3,91–4,12 saat | 577,68 MB | 54,31 MB |
| 2025-08-30 00Z | 365 gün | 31/31 | 3,91–3,94 saat | 545,34 MB | 60,46 MB |
| 2020-09-24 00Z | 2.166 gün | 31/31 | 4,44–4,45 saat | 464,69 MB | 65,18 MB |

Her tarihte 31 indexin tamamı HTTP 200 döndü. Toplam 93 indexte her üye için `TMP`, `TMAX`
ve `TMIN` birer kez bulundu. Her tarihte control, ilk perturbed ve son perturbed üyeden gerçek
range'ler indirildi: 9 subset, 27 GRIB mesajı; tüm range cevapları HTTP 206 ve her mesajın
`GRIB...7777` bütünlüğü geçerliydi. Checksum ve obje `Last-Modified` değerleri evidence JSON'unda
saklandı.

## Ekonomik/operasyonel yorum

- ECMWF Open Data'nın yaklaşık üç günlük retention probleminin aksine, GEFS operasyonel bucket
  gerçek as-issued geçmiş için güçlü adaydır.
- Sadece tek forecast hour'da üç sıcaklık alanının 31 üye toplamı 54–65 MB'dir. Full objeler
  aynı örneklerde 465–578 MB; range retrieval yaklaşık %88–91 transfer tasarrufu sağlar.
- Günlük maksimum sıcaklığı istasyonun yerel takvim gününe çevirmek için tek `f024` yeterli
  değildir. İlgili 6 saatlik TMAX pencereleri, şehir timezone'u ve karar anında available run'lar
  birlikte seçilmelidir.
- `Last-Modified` ile ölçülen full-member availability yaklaşık run+3,9–4,45 saattir. Her market
  snapshot join'i member setinin tamamının available olduğu muhafazakâr maksimum timestamp'i
  kullanmalıdır.

## Karar

GEFS ilk source gate'inde `CONDITIONAL_PASS`:

- alan, üye, gerçek download, provenance ve ≥365 günlük retention koşulları geçti;
- yalnız üç tarih ölçüldüğü için kesintisiz günlük coverage henüz kanıtlanmadı;
- local-day MaxT step aggregation ve model-version boundary henüz çözülmedi;
- reforecast veya replay operational as-issued history yerine kullanılmayacak.

## Sonraki en küçük adım

Kilitli son 365 tamamlanmış gün için 00Z `f024` control/p01/p30 index coverage'ını ölç; eksik
günleri tüm 31 üye ve alternatif cycle açısından araştır. Aynı deneyde f006/f012/f018/f024
TMAX window semantiğini en az bir DST'li ve bir DST'siz şehir için doğrula.

## Artifact'lar

- `reports/data_quality/EXP-20260830-phase4-gefs-operational-archive-probe.json`
- local raw: `data/raw/gefs/run=20260830T-phase4-gefs-v1/` (Git dışında)
- `src/weather_quant/ingestion/noaa_gefs.py`
- `scripts/probe_noaa_gefs_archive.py`

## Birincil kaynaklar

- <https://registry.opendata.aws/noaa-gefs/>
- <https://www.nco.ncep.noaa.gov/pmb/products/gens/>
