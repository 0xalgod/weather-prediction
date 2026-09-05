# EXP-20260905 — KORD NBM Gaussian calibration v1

**Durum:** `PREREGISTERED`

## Hipotez

Her hedef günde yalnız daha önce gerçekleşmiş KORD hatalarıyla seçilen sabit bias ve spread scale, raw NBM Gaussian'a karşı en az %2 OOS log-loss iyileşmesi sağlar ve Brier skorunu kötüleştirmez.

## Tasarım

- Frozen annual dataset ve önceki baseline ile aynı 178 development OOS günü
- İlk 120 uygun gözlem başlangıç train'i; expanding window, günlük refit
- Bias grid: −5°F…+5°F, 0.25°F adım
- Spread scale: 0.5×…3.0×, 0.25 adım
- Seçim yalnız geçmiş ortalama multiclass log loss ile
- Deterministic tie-break: en küçük mutlak bias, sonra 1'e en yakın scale
- Primary karşılaştırma calibrated-minus-raw paired-date bootstrap

## Kabul eşiği

Practical pass için relative log-loss improvement ≥%2 ve Brier farkı ≤0. Strong evidence için ayrıca %95 bootstrap CI üst sınırı <0 olmalıdır. Temmuz–Ağustos selection'a kapalıdır; prospektif final test henüz yoktur.
