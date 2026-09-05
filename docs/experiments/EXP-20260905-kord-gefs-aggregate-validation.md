# EXP-20260905 — GEFS aggregate-product corrective validation

**Durum:** `IN_PROGRESS`  
**Tasarım:** Full-member extraction pilotu sonrasında, aggregate değerler görülmeden pre-registered corrective deney.

## Hipotez

NOAA `geavg` ve `gespr` 2 m TMAX ürünleri, iki pilot gündeki tam 31-member hücrelerin empirical population mean ve standard deviation değerlerini düşük hatayla yeniden üretir. Aggregate ürün kullanımı yıllık transferi ≤3 GiB ve range GET sayısını ≤4.000 seviyesine indirir.

## Karşılaştırma kümesi

Full-member pilotunda altı case-step hücre 31/31 üyeye sahiptir:

- Winter: f036, f042, f048
- Summer: f030, f048, f054

Eksik üye taşıyan winter f054 ile summer f036/f042 yalnız diagnostic olarak raporlanır; primary gate'e alınmaz.

Her dokuz hücre için `geavg` ve `gespr` olmak üzere 18 aggregate GRIB mesajı beklenir. Empirical spread `ddof=0` population standard deviation ile hesaplanır.

## Önceden kilitli gate

- Aggregate retrieval/index/range/decode: 18/18
- Publication leakage: 0
- Primary complete cell: exact 6
- Mean product: MAE ≤0,25°F ve max absolute error ≤0,75°F
- Spread product: MAE ≤0,25°F ve max absolute error ≤0,75°F
- Annual projected transfer ≤3 GiB
- Annual projected range GET ≤4.000

Bir aggregate ürün adı mevcut değilse, field semantiği farklıysa veya eşikler geçilmezse annual summary feature olarak kabul edilmez. Eşikler sonuçtan sonra değiştirilmez.

## Sınır

Bu deney GEFS summary feature'ın veri/maliyet doğrulamasıdır. Forecast model loss'u, calibration veya EV ölçmez.

## Sıradaki adım

Aggregate product URL/index desteğini ve decoder semantiğini implement et; testlerden sonra 18-message deneyi bir kez çalıştır.
