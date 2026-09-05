# EXP-20260906 — KORD champion ve Paper Day 1 reconciliation

**Durum:** `PASSED`

`RAW_NBM_GAUSSIAN_V1`, prior-day NBM 07Z f41 MaxT mean ve en az 1°F standart sapmalı Gaussian dağılım olarak donduruldu. Development log loss'u 2.0608'dir; modelin specification evidence checksum'ı config içinde sabittir.

Paper Day 1 için resmi `api.weather.gov` KORD sorgusu 314 sıcaklık gözlemi döndürdü. Her değer Fahrenheit'a çevrilip kaynağın whole-degree kuralına göre yuvarlandığında günlük maksimum 93°F oldu. Bu `92–93°F` bucket'ına düştü. Terminal Gamma kaydında da exactly one YES winner aynı market/bucket'tır.

Frozen Gaussian kararı `NO_TRADE` idi ve paper P&L $0 kaldı. Daha sonra calibration testinde reddedilen quantile model `86–87°F` için $10 paper buy seçmişti; $0 payout ve $0.445 fee ile paper P&L −$10.445 oldu.

Bu n=1 sonuç Gaussian edge kanıtı değildir. Yalnız settlement pipeline'ını doğrular ve calibration hatasının ekonomik önemini gösterir. Quantile kolu kapatıldı; sonraki paper capture yalnız Gaussian champion ile yapılacaktır.
