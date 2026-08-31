# Wunderground current-page / Polymarket settlement audit

**Experiment:** `EXP-20260830-data-source-feasibility`

**Cut-off:** 2026-08-31

**Artifact:** `reports/data_quality/EXP-20260831-phase5-wunderground-settlement-audit.json`

## Soru ve ön-kayıtlı gate

Hipotez: Önceden kilitlenmiş Phase 1 örnekleminde, parse edilebilir Wunderground daily high ile terminal Polymarket winner bucket en az 10 event ve en az 3 şehirde tutarlı olacak; tüm ayrışmalar karantinaya alınacak ve çözümsüz eligible kayıt kalmayacak.

Primary cohort, sonuçlar görülmeden önce seçilmiş 20-event stratified sample'dır. Toronto event `249630`, ayrı bir anomaly araştırmasında keşfedildiği için yalnız sensitivity sentinel olarak eklenmiştir; population divergence tahminine dahil edilmez.

## Sonuç

| Cohort | Kayıt | Eligible | Match | Divergence | Ineligible | Match şehir | Divergence oranı | Wilson %95 CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed sample — primary | 20 | 14 | 12 | 2 | 6 | 12 | %14,29 | %4,01–%39,94 |
| Fixed + anomaly sentinel — sensitivity | 21 | 15 | 12 | 3 | 6 | 12 | %20,00 | %7,05–%45,19 |

Unresolved eligible kayıt 0 ve bütün divergence kayıtları `HISTORICAL_PAGE_DIVERGED_FROM_SETTLEMENT` olarak karantinaya alındı. Bu nedenle **ön-kayıtlı sample observation/settlement subgate `PASSED`**.

Bu, Phase 5'in tamamının geçtiği anlamına gelmez. Üçüncü şehrin uzun dönem observation/revision semantiği ve exact freeze-time temperature label hâlâ çözülmemiştir.

## Ayrışan eventler

| Cohort | Event | Şehir / istasyon | Current WU high | Terminal winner | Disposition |
|---|---:|---|---:|---|---|
| Fixed | 493659 | Dallas / KDAL | 30°C (~86°F) | `73°F or below` | `NO_TRAIN_NO_BACKTEST` |
| Fixed | 493666 | Munich / EDDM | 19°C | `11°C or below` | `NO_TRAIN_NO_BACKTEST` |
| Sentinel | 249630 | Toronto / CYYZ | 9°C | `10°C or higher` | `NO_TRAIN_NO_BACKTEST` |

## İki farklı label hedefi

1. **Terminal market bucket outcome:** Identifier'ı doğrulanmış terminal eventlerde kazanan bucket doğrudan Polymarket settlement'tan alınabilir. Current Wunderground sayfasının ayrışması bu terminal market etiketini geçersiz kılmaz. Fixed sample eligible eventlerin 14/14'ünde, sentinel dahil 15/15'inde terminal label mevcuttur.
2. **Exact temperature outcome:** Bugün çekilen historical page'in freeze anında görülen exact sıcaklık olduğunu bir bucket match kanıtlamaz. Bu nedenle exact temperature label eligibility fixed sample'da 0/14, sentinel dahil 0/15'tir.

Sonuç olarak Wunderground current historical page, evrensel exact-temperature ground truth olarak **FAILED**. Terminal Polymarket bucket etiketi ise market-outcome modellemesi için ayrı bir hedef olarak kullanılabilir.

## Ekonomik ve istatistiksel yorum

- Fixed-sample divergence %14,3 küçümsenemez; fakat 14 eligible kayıt nedeniyle güven aralığı geniştir. Bu oran population estimate veya gelecekteki hata oranı olarak kullanılmamalıdır.
- Sentinel-inclusive %20 oranı anomaly-selected olduğu için yalnız sensitivity ölçümüdür.
- 12 bucket match, Wunderground değerinin settlement sırasında aynı kaldığını veya exact sıcaklığın doğru olduğunu ispatlamaz; yalnız bugünkü sayının kazanan bucket içine düştüğünü gösterir.
- Exact-temperature supervised model/backtest, korunmuş freeze-time snapshot veya açık version history olmadan kurulmayacaktır.
- Bucket-outcome modeli, Polymarket terminal winner label'ını kullanabilir; ancak geçmişte karar anında erişilebilir forecast ve executable fiyat verisi ayrıca sağlanmalıdır.

## Deney hafızası

- `-attempt1.json`: `training_eligible` kavramını bucket ve exact-temperature hedefleri arasında ayırmadığı için superseded.
- `-attempt2.json`: Current-page divergence'ını yanlış biçimde terminal market label'ının yokluğu gibi yorumladığı için superseded.
- Final artifact iki hedefi ayırır: `market_terminal_label_available` ve `temperature_label_eligible`.

## Karar ve sonraki en küçük adım

Sample settlement-consistency subgate geçti; Phase 5 `IN_PROGRESS` kalır. Sonraki deney, üçüncü şehir olarak KORD/Chicago için exact resolution rule, 365 günlük official station observation coverage, revision/final semantiği ve terminal settlement join'ini analizden önce sabitlemektir. Bu çalışma Wunderground current page'i exact-temperature truth olarak varsaymayacaktır.
