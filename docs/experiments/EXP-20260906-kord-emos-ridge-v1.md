# EXP-20260906 — KORD EMOS-style ridge v1

**Durum:** `FAILED`

Amaç, ham NBM Gaussian'a incremental değer sağlayan küçük ve regularized bir probabilistik model geliştirmektir. Mean modeli NBM mean, GEFS−NBM disagreement, mevsim, provider version ve GEFS pencere kalitesini kullanır. Gaussian spread, inner validation'da seçilen NBM spread katsayısıdır.

Her dış OOS gününde yalnız geçmiş kullanılır. Ridge lambda ve spread scale, geçmiş train'in son 30 günündeki blocked inner validation ile seçilir; ardından model tüm geçmişte yeniden fit edilir. Outer dönem önceki deneylerle aynı 178 development OOS gündür.

Promotion için ham NBM'e karşı ≥%3 relative log-loss improvement, Brier farkı ≤0 ve paired-date bootstrap %95 CI üst sınırı <0 zorunludur. Bu dönem consumed olduğundan başarı yalnız modeli 2026-09-01 sonrası prospektif challenger olarak dondurur; final-test veya EV iddiası oluşturmaz.

## Sonuç

Nested walk-forward 178/178 OOS günde tamamlandı. Ham NBM/EMOS ridge log loss 2.0608/2.1090; relative improvement −%2.339 ve Brier farkı +0.01113 oldu. EMOS-minus-raw paired-date %95 CI [−0.1069,+0.2092] sıfırı kesmektedir.

Model Ocak ve Şubat'ta raw NBM'i iyileştirdi, fakat Mart–Haziran aylarının tamamında kötüleştirdi. Ridge/spread seçimi inner validation kullanmasına rağmen kısa geçmiş ve provider/mevsim driftine dayanıklı genelleme sağlamadı.

Promotion gate başarısızdır; model v1 reddedildi. Raw NBM Gaussian forecast champion olarak dondurulacak, yeni karmaşık model araması ek veri gelene kadar durdurulacaktır.
