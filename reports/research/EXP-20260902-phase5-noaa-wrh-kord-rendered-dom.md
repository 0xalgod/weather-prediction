# NOAA WRH KORD rendered-DOM diagnostic

**Deney:** `EXP-20260830-data-source-feasibility`  
**Run:** `EXP-20260902-phase5-noaa-wrh-kord-rendered-dom`  
**Veri cut-off:** 2026-09-02 13:49:37 UTC  
**Karar:** `BROWSER_RENDERED_DIAGNOSTIC_PASS`

## Soru ve ön-kayıtlı eşik

Sabit NOAA WRH KORD URL'si, sayfanın istemci tarafı render edildikten sonra credential çıkarmadan iki bounded gözlemde aynı kimlik, °F kolonları ve en az 24 timestamp'li sıcaklık satırı üretiyor mu? İki gözlemde duplicate timestamp sıfır ve normalize kolon şeması aynı olmalıydı. Sep 1→Sep 2 seçimi yalnız trigger algoritması testi olarak kaydedildi; geçmiş freeze kanıtı olarak değil.

## Ölçülen sonuç

| Metrik | Render 1 | Render 2 | Eşik |
|---|---:|---:|---:|
| Gözlem zamanı (UTC) | 13:47:49 | 13:49:37 | iki bounded render |
| Timestamp'li satır | 85 | 85 | ≥24 |
| Sayısal °F sıcaklık | 85 | 85 | satırların tamamı |
| Duplicate timestamp | 0 | 0 | 0 |
| Normalize kolon sayısı | 21 | 21 | aynı şema |
| Body-text SHA-256 | `2f61cd…e6b1` | `2f61cd…e6b1` | fark izinli, kaydedilmeli |

Başlık iki renderda da `Chicago, Chicago-O'Hare International Airport` idi. Satırlar 30 Ağustos 08:51–2 Eylül 07:51 yerel zaman aralığını kapsadı. Gün sayıları 30 Ağustos: 16, 31 Ağustos: 37, 1 Eylül: 24 ve 2 Eylül: 8 oldu.

Deterministik `following local date içindeki minimum timestamp` algoritması iki renderda da **2 Eylül 00:51, 81°F** satırını seçti. Bu, parserın kuraldaki “ertesi günün ilk datapoint'i” ifadesini uygulayabildiğini gösterir.

## Veri kalitesi ve sınırlar

- Sayfanın `Date/Time (L)` alanı yerel zamanı gösteriyor; satır metninde UTC offset veya yıl yok. `America/Chicago` eşlemesi KORD istasyon kimliği ve local-time semantiğine, 2026 yılı ise gözlem anı/chart bağlamına dayanıyor. DST fold/gap için ayrıca contract test gerekir.
- Sayfada verilerin preliminary olduğu ve quality-control adjustment görebileceği uyarısı görünür durumda.
- Bu ölçüm trigger saatinden yaklaşık 8 saat sonra yapıldı. Dolayısıyla 00:51'de görünen içeriğin birebir aynısını kanıtlamaz.
- Daha önceki kaynak keşfi resmî-origin bir machine endpoint bulamadı. Rendered DOM okunabilir olsa da browser bağımlılığı otomasyon, latency ve uptime riski yaratıyor.
- Credential, cookie, local storage, network token, raw DOM veya screenshot kaydedilmedi.

## Quant kararı

Ön-kayıtlı DOM gate'i geçti. Sonuç yalnız `BROWSER_RENDERED_DIAGNOSTIC_PASS`: current NOAA-primary Chicago rejimi, **prospective ve bounded browser capture araştırması** için teknik olarak açık kalıyor.

Bu sonuç settlement label üretmeye, geçmiş backtesti doldurmaya veya canlı trading'e yetmez. `AUTOMATED_API_ACCESS`, `HISTORICAL_FREEZE_AS_OF`, gerçek trigger anında capture ve settlement sonrası reconciliation hâlâ çözülmedi. Bu yüzden Phase 5 `IN_PROGRESS`, canlı sermaye yetkisi yok.

## Sonraki en küçük deney

Outcome görülmeden tek bir observed-future KORD event'i kilitle; rule hash ve bucket/token kimliklerini kaydet. Ertesi yerel gün ilk satır oluştuğunda yalnız bir bounded browser capture al, append-only snapshot sözleşmesine yaz ve settlement sonrası terminal bucket ile reconcile et. Uzun süre çalışan collector başlatma; capture zamanı ayrıca kullanıcı tarafından tetiklenebilir veya ayrı açık izinle zamanlanabilir.

Makine-okunur ölçümler: `reports/data_quality/EXP-20260902-phase5-noaa-wrh-kord-rendered-dom.json`.
