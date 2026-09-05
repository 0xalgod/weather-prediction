# EXP-20260906 — KORD EMOS-style ridge v1

**Durum:** `PREREGISTERED`

Amaç, ham NBM Gaussian'a incremental değer sağlayan küçük ve regularized bir probabilistik model geliştirmektir. Mean modeli NBM mean, GEFS−NBM disagreement, mevsim, provider version ve GEFS pencere kalitesini kullanır. Gaussian spread, inner validation'da seçilen NBM spread katsayısıdır.

Her dış OOS gününde yalnız geçmiş kullanılır. Ridge lambda ve spread scale, geçmiş train'in son 30 günündeki blocked inner validation ile seçilir; ardından model tüm geçmişte yeniden fit edilir. Outer dönem önceki deneylerle aynı 178 development OOS gündür.

Promotion için ham NBM'e karşı ≥%3 relative log-loss improvement, Brier farkı ≤0 ve paired-date bootstrap %95 CI üst sınırı <0 zorunludur. Bu dönem consumed olduğundan başarı yalnız modeli 2026-09-01 sonrası prospektif challenger olarak dondurur; final-test veya EV iddiası oluşturmaz.
