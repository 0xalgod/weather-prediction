# EXP-20260906 — Chicago Gaussian Paper Day 2

**Durum:** `CAPTURE_ELIGIBLE_PENDING_OUTCOME`

## Kilitli tasarım

Event 968537, Chicago/KORD 7 Eylül 2026 için 6 Eylül 10:45–11:15 UTC penceresinde `RAW_NBM_GAUSSIAN_V1` kullanıldı. Her bucket için $10 ask-depth VWAP, live taker fee, 2 puan resolution haircut ve minimum 3 puan adjusted edge uygulandı. Yalnız Gaussian paper kolu aktiftir; emir gönderimi yasaktır.

## Capture sonucu

- NBM v5.0 07Z f41 mean: 79°F
- NBM standard deviation: 2°F
- 11/11 bucket executable
- Forecast-to-last-book skew: 0.874 saniye
- Request/identity/fee/probability hatası: 0

En yüksek adjusted edge `76–77°F` bucket'ındadır:

- Model olasılığı: %18.657
- $10 VWAP / best ask: 0.09
- Hypothetical shares: 111.111
- Taker fee: $0.455
- Gross edge: +9.657 yüzde puan
- Fee sonrası edge: +9.247 yüzde puan
- 2 puan haircut sonrası edge: +7.247 yüzde puan
- Frozen karar: `PAPER_TRADE`
- `order_sent=false`

Outcome ve P&L henüz bilinmiyor. Bu tek sinyal edge kanıtı değildir; settlement sonrası frozen karar değiştirilmeden skorlanacaktır.
