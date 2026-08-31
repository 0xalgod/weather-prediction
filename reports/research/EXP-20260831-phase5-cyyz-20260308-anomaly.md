# CYYZ 2026-03-08 observation ve settlement anomalisi

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Tarih:** 2026-08-31  
**İstasyon:** CYYZ / Toronto Pearson

## Neden araştırıldı?

365 günlük Wunderground coverage koşusunda 2026-03-08 CYYZ sayfası yalnız iki observation ve 9°C daily high gösterdi. Komşu günlerde 44 ve 24 satır vardı. Tarih Toronto'nun spring-forward DST günüdür; civil gün 23 saat olsa da iki kayıt açıklanamaz.

## Kaynaklar

- Exact resolution page: Wunderground CYYZ daily history immutable snapshot.
- Bağımsız resmî kaynak: Environment and Climate Change Canada `climate-hourly` OGC API, `TORONTO INTL A`, climate identifier `6158731`.
- Settlement: korunmuş 8.222-event Polymarket closed inventory, event `249630`.
- ECCC, hourly station dataset'ini saatlik yüzey gözlemleri olarak tanımlar: <https://open.canada.ca/data/en/dataset/df2e6e1a-6057-4c4d-a509-94aa57705a8c>.
- Resmî teknik doküman hourly ve daily/climatological time semantics'inin ayrımını açıklar: <https://www.canada.ca/en/environment-climate-change/services/climate-change/canadian-centre-climate-services/display-download/technical-documentation-hourly-data.html>.

## v1 failure

İlk diagnostic ECCC `LOCAL_DATE` alanını civil DST günü sandı. Bu alan 0–23 şeklinde 24 satır üretti ve ön-kayıtlı 23-saat gate'i başarısız oldu. v1 artifact silinmedi. Corrective v2 yalnız zaman filtresini değiştirdi: kaynak `UTC_DATE`, event-effective `America/Toronto` IANA `[00:00,next 00:00)` aralığına dönüştürüldü.

## Corrective v2 sonucu

| Kanıt | Sonuç |
|---|---:|
| Civil local-day saat sayısı | 23/23 |
| Eksik civil saat | 02:00 (beklenen DST skip) |
| Non-null ECCC temperature | 23/23 |
| ECCC station | TORONTO INTL A / 6158731 |
| Verified CYYZ koordinatına mesafe | <1 km |
| ECCC maksimum | 12.1°C |
| Half-up whole-degree maksimum | 12°C |
| Wunderground mevcut daily high | 9°C |
| Wunderground observation | 2 |
| Polymarket exact event | 249630 |
| Terminal winner | `10°C or higher` |
| ECCC maksimum → winner | `MATCH` |
| Wunderground 9°C → winner | `MISMATCH` |

Corrective forensic diagnostic `PASSED`: bug, Wunderground değerini doğrulamak yerine historical page divergence'ını kanıtladı.

## Karar

`CYYZ 2026-03-08` etiketi `HISTORICAL_PAGE_DIVERGED_FROM_SETTLEMENT` ve `NO_TRAIN_NO_BACKTEST` olarak karantinaya alınır. Bugün görünen Wunderground historical page, geçmişte settlement sırasında görünen değerin güvenilir kopyası değildir.

Bu bulgu şu ayrımı zorunlu kılar:

1. **Page availability:** 365/365 sayfa erişilebilir — önceki gate hâlâ teknik olarak doğru.
2. **Outcome-label validity:** settlement ile kontrol edilmeden bilinmez; CYYZ'de en az 1/365 yanlışlanmış gün vardır.
3. **Settlement-as-of:** korunmuş event-time snapshot veya terminal bucket reconciliation gerektirir.

CYYZ için şimdilik kullanılabilir current-page label üst sınırı 364/365 (%99,726) olur. WMKK'nin 365 sayfasında bu spesifik anomaly görülmedi, ancak settlement-audit yapılmadığı için 365'inin de doğru olduğu iddia edilemez.

## Sonraki adım

Önceden sabitlenmiş settlement örneklemindeki en az 10 event ve en az 3 şehir, mevcut Wunderground daily high ile terminal winner bucket açısından yeniden denetlenecek. Divergence oranı, station/date ve page observation-count ile birlikte raporlanacak. Başarısız kayıtlar outcome eğitiminden çıkarılacak; current page label settlement yerine kullanılmayacak.

## Artifact'lar

- `reports/data_quality/EXP-20260831-phase5-cyyz-20260308-anomaly.json`
- `reports/data_quality/EXP-20260831-phase5-cyyz-20260308-anomaly-attempt1.json`
