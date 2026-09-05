# EXP-20260905 — KORD GEFS extraction pilot

**Durum:** `IN_PROGRESS`  
**Ön kayıt tarihi:** 2026-09-05

## Hipotez

15 Ocak 2026 exact-winter ve 15 Temmuz 2026 proxy-summer günlerinde gerekli 279 GEFS TMAX mesajının tamamı index-directed byte range ile indirilebilir, GRIB bütünlüğü korunabilir ve KORD'a en yakın gridpoint sıcaklığı finite/plausible biçimde çözülebilir. Pilot maliyeti yıllığa ölçeklendiğinde ≤25 GiB range transfer ve ≤60.000 range GET olmalıdır.

## Kilitli kapsam

- Winter exact: run 2026-01-14 00Z, step 36/42/48/54, 31 member = 124 mesaj
- Summer proxy: run 2026-07-14 00Z, step 30/36/42/48/54, 31 member = 155 mesaj
- Toplam: 279 mesaj
- Station: KORD / `USW00094846`, 41.96019, −87.93162
- Parametre: yalnız 2 m `TMAX`
- Alternatif cycle yok

## Gate

- Exact 279/279 index → TMAX range → HTTP 206 → GRIB/7777 → decode
- Publication leakage 0
- Non-finite değer 0; sıcaklık −80°F ile 140°F arasında
- Nearest grid koordinat farkı öklidyen derece cinsinden ≤0,2
- Yıllık projected transfer ≤25 GiB
- Yıllık projected range GET ≤60.000

Her range için URL, offset/end, index checksum, object ETag/Last-Modified, byte count ve message checksum saklanır. Summer gün interior ve overlap maksimumları ayrı tutulur; exact label iddiası yapılmaz.

## Sınır

Bu pilot yalnız extraction doğruluğu ve operasyonel maliyeti ölçer. Model loss, calibration, Polymarket fiyatı ve EV hesaplanmaz.

## Sıradaki adım

Pilot runner'ı exact 279 mesaj için implementasyon commit'inden sonra bir kez çalıştır; integrity/decode/byte projection sonucunu immutable artifact'a yaz.

## Uygulama durumu

- ecCodes `>=2.48,<2.49` reproducible runtime dependency olarak eklendi.
- Nearest-grid coordinate normalization ve Kelvin→Fahrenheit dönüşüm testleri eklendi.
- Runner her object için exact TMAX index row, canonical 6h window, publication time, HTTP 206, GRIB boundaries, single-message decode ve KORD grid mesafesini fail-closed doğruluyor.
