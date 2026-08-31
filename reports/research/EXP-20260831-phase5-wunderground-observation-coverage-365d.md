# CYYZ/WMKK Wunderground 365 günlük observation coverage

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Ölçüm:** 2026-08-31  
**Evidence class:** `CURRENT_OR_FINAL_HISTORICAL_PAGE_NOT_AS_OF_MARKET_FREEZE`

## Ön-kayıtlı kapsam

- CYYZ: 2025-07-24–2026-07-23, 365 yerel tarih
- WMKK: 2025-06-23–2026-06-22, 365 yerel tarih
- Toplam: 730 exact Wunderground daily-history sayfası

Gate, istasyon başına en az %99 complete-page coverage, retry sonrası terminal transport failure 0, HTTP-available sayfalarda %100 station/date/timezone identity ve 365/365 `daily_high == max(observation temperature)` idi.

## Sonuç

| Metrik | CYYZ | WMKK |
|---|---:|---:|
| Complete page | 365/365 | 365/365 |
| Coverage | %100 | %100 |
| HTTP available | 365 | 365 |
| Station/date/timezone identity | 365/365 | 365/365 |
| Daily high = observation max | 365/365 | 365/365 |
| Terminal transport failure | 0 | 0 |
| İlk attempt'te başarı | 363 | 361 |
| İkinci attempt'te başarı | 2 | 4 |
| Daily high aralığı | −13–36°C | 25–36°C |
| Observation/gün aralığı | 2–60 | 40–54 |

Gate `PASSED`. Toplam 41.178.264 byte HTML çekildi. Her response için URL, retrieval timestamps, attempt/error bilgisi, byte count ve SHA-256; her observation dizisi için ayrı normalized checksum saklandı.

## Veri kalitesi anomalisi

CYYZ 2026-03-08 sayfasında yalnız iki observation bulunuyor; komşu günlerde 44 ve 24 kayıt var. Bu tarih Toronto'nun DST başlangıç günüdür, ancak 23 saatlik gün tek başına 2 kaydı açıklamaz. Sayfanın daily high değeri 9°C ve iki satırın maksimumu da 9°C olduğu için ön-kayıtlı gate teknik olarak geçer.

Yine de bu gün `SUBDAILY_INCOMPLETE_SUSPECTED` olarak işaretlenmelidir:

- Wunderground'ın görünen daily high değeri current/final label olarak korunabilir;
- yalnız iki satırdan daily maximum yeniden üretildiği iddia edilemez;
- feature/outcome karşılaştırmasında bu gün sensitivity exclusion olarak ayrıca raporlanmalıdır;
- bağımsız CYYZ kaynağıyla ve varsa market settlement'iyle araştırılmalıdır.

`observation_count >= 20` burada post-hoc gate değildir; anomalinin büyüklüğünü görünür kılan diagnostic eşiğidir. Bu eşiğe göre CYYZ 364/365 ve WMKK 365/365 sub-daily-complete görünür.

## Kanıtın sınırı

Bu çalışma bugün görünen historical page'i ölçer. Polymarket kuralı revizyonları ertesi gün ilk veri noktası geldiğinde dondurduğu için, bugün görünen değer historical freeze-time değerinden farklı olabilir. Dolayısıyla:

- forecast calibration için current/final daily outcome coverage alt-gate'i geçmiştir;
- historical settlement-as-of kanıtı geçmemiştir;
- exact EV backtest'te settlement join için korunmuş snapshot/prospective capture gereklidir.

## Sonraki adım

CYYZ 2026-03-08 anomalisi bağımsız station kaynağı ve varsa Polymarket settlement ile araştırılacak; ardından üçüncü bir reconciled şehir eklenerek Phase 5'in en az 10 event/3 city observation-settlement gate'i uygulanacaktır.

## Artifact

`reports/data_quality/EXP-20260831-phase5-wunderground-observation-coverage-365d.json`
