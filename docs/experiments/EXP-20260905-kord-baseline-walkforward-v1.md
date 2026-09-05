# EXP-20260905 — KORD annual baseline walk-forward v1

**Durum:** `PASSED_DATA_GATE_BASELINES_SCORED`

## Hipotez ve tasarım

Frozen 357-row KORD dataset üzerinde ilk 120 uygun gün başlangıç train'i, 2026-06-30'a kadar expanding one-step-ahead OOS değerlendirme için kullanıldı. Temmuz–Ağustos daha önce tüketilmiş diagnostic dönemdir; 2026-09-01 sonrası veri gerçek prospektif final test olarak ayrılmıştır.

Outcome, −50…50 arası exhaustive integer Celsius sınıflarıdır. Primary metrik multiclass log loss; Brier ve RPS ikincildir. Dört ön-kayıtlı baseline seasonal climatology Gaussian, raw NBM Gaussian, raw NBM quantile CDF ve raw GEFS Gaussian'dır.

## Sonuç

178 OOS günde probability kalite gate'i geçti. Ortalama log loss:

| Model | Log loss | Brier | RPS |
|---|---:|---:|---:|
| Raw NBM Gaussian | 2.0608 | 0.8324 | 0.01110 |
| Seasonal climatology Gaussian | 3.4633 | 0.9649 | 0.04460 |
| Raw NBM quantile | 3.9851 | 0.8530 | 0.01136 |
| Raw GEFS Gaussian | 3.9866 | 0.9521 | 0.01607 |

NBM Gaussian eksi climatology paired-date bootstrap farkı −1.4025, %95 CI [−1.5545, −1.2396]. NBM Gaussian bu development OOS örnekleminde açık reference baseline'dır.

NBM quantile 15, GEFS Gaussian 7 günde log loss >20 üretti. Median performansları daha iyi olsa da tail dışına gerçek outcome düştüğünde aşırı cezalandılar; calibration olmadan güvenilir probabilistik baseline değiller.

NBM v5.0 slice'ında Gaussian 1.701 ve quantile 1.750 log loss verdi; v4.3 slice'ında 2.218 ve 4.958. Provider version tarih/mevsim ile çakıştığı için bu nedensel model-upgrade kanıtı değildir.

## Karar

Raw NBM Gaussian, sonraki bias/spread calibration deneyinin karşılaştırma baseline'ı olacaktır. Sonraki deney yalnız geçmiş residual kullanacak ve parametre/eşikler sonuçtan önce kilitlenecektir. Bu sonuç market fiyatına karşı edge, maliyet sonrası EV veya trading izni değildir.
