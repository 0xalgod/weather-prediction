# Polymarket Weather Quant Research — Living Roadmap

**Proje tipi:** Quant araştırma projesi ve küçük sermayeli niche strategy  
**Plan versiyonu:** 0.4.0
**Son güncelleme:** 2026-08-30
**Mevcut faz:** Phase 0 — Research charter  
**Genel durum:** `IN_PROGRESS`  
**Canlı sermaye yetkisi:** Yok

## 1. North-star ve araştırma sorusu

Amaç, seçilmiş günlük hava durumu marketlerinde aşağıdaki koşulu sağlayan tekrarlanabilir segmentler bulmaktır:

\[
EV_{net}=q-p_{exec}-fee-slippage-latency\ cost-resolution\ risk > 0
\]

Burada:

- \(q\): karar anındaki bilgiyle tahmin edilen kalibre outcome olasılığı,
- \(p_{exec}\): gerçekte erişilebilir bid/ask ve depth üzerinden fill fiyatı,
- diğer terimler: fee, slippage, gecikme/fill ve çözüm belirsizliği maliyetleridir.

Ana soru:

> Hangi şehir/istasyon, lead time, weather regime ve execution koşullarında tahminimiz executable piyasa fiyatından maliyetler sonrası anlamlı biçimde daha iyidir?

### Başarı tanımı

Araştırma başarısı iki olası çıktıdan biridir:

1. Önceden tanımlanmış gate'leri geçen, kapasitesi ölçülmüş küçük bir canlı pilot; veya
2. Edge'in yetersiz/istikrarsız olduğunu gösteren yeniden üretilebilir bir no-go raporu.

## 2. Scope

### İlk kapsam

- Market türü: günlük maksimum sıcaklık bucket marketleri
- Başlangıç evreni: veri ve resolution kalitesi doğrulandıktan sonra 3–5 istasyon
- Strateji ufku: market açılışından çözümlemeye kadar; lead-time segmentleri ayrı
- Execution: önce snapshot araştırması, sonra paper trading; canlı aşamada maker-first
- Sermaye yaklaşımı: küçük, kaybı tolere edilebilir araştırma bütçesi

### Başlangıçta kapsam dışı

- Yağış, kasırga, kar miktarı ve uzun vadeli iklim marketleri
- Copy trading veya trader sinyali takip etme
- Manipülasyona dayalı herhangi bir yaklaşım
- Full Kelly veya yüksek kaldıraç
- Kanıtlanmamış modelle otomatik canlı işlem
- Hava tahmini dışındaki Polymarket kategorileri

Scope ancak Decision Log'a veri temelli gerekçe eklenerek değiştirilebilir.

## 3. Primary hipotezler

| ID | Hipotez | Ölçüm | Başlangıç kabul kriteri | Durum |
|---|---|---|---|---|
| H1 | İstasyona özel kalibre ensemble, ham ensemble'dan daha iyi olasılık üretir | OOS log loss, Brier, calibration | Log loss/Brier iyileşmesi ve daha iyi calibration; cluster bootstrap ile istikrarlı | `NOT_STARTED` |
| H2 | Kalibre model, executable market fiyatına incremental bilgi ekler | Market-price benchmark'a karşı OOS log loss ve net EV | Maliyet sonrası pozitif net EV; yalnızca tek segmente bağımlı değil | `NOT_STARTED` |
| H3 | Yeni forecast run'larından sonra kısa süreli repricing gecikmesi vardır | Run sonrası edge decay ve fill simülasyonu | Latency/fill sonrası pozitif ve tekrarlanabilir | `NOT_STARTED` |
| H4 | Maker-first execution taker'a göre ekonomik sonucu belirgin iyileştirir | Net P&L, fill rate, adverse selection | Gerçekçi fill altında daha yüksek risk-adjusted net EV | `NOT_STARTED` |
| H5 | Bazı şehir/lead-time segmentleri diğerlerinden kalıcı olarak daha verimlidir | Segment bazlı OOS EV ve stability | En az iki ayrı OOS dönemde aynı yönlü net sonuç | `NOT_STARTED` |
| H6 | Bucket fiyatlarında zaman zaman cross-outcome incoherence oluşur | Executable fiyat toplamı ve eşzamanlı fill | Tüm maliyet/partial-fill stresinden sonra pozitif | `NOT_STARTED` |

Hipotezler sonuç görüldükten sonra sessizce değiştirilemez. Yeni hipotez yeni ID alır.

## 4. Ana metrikler

### Forecast metrikleri

- Multiclass log loss — primary forecast metriği
- Brier score ve Brier decomposition
- Reliability diagram / expected calibration error
- Ranked probability score — sıralı sıcaklık bucket'ları için
- CRPS — sürekli maksimum sıcaklık dağılımı mevcutsa
- Sharpness, calibration sağlandıktan sonra

### Trading metrikleri

- Token başına ve deployed capital başına net EV
- Gerçekleşen net P&L ve ROI
- Maker/taker ayrımlı fee ve rebate
- Fill rate, time-to-fill ve partial fill oranı
- Slippage ve order-book impact
- Turnover ve sermaye kullanım süresi
- Maximum drawdown ve drawdown süresi
- Profit factor; fakat tek başına karar metriği değildir
- Closing-line value
- Capacity: edge korunarak deploy edilebilen tahmini sermaye

### Güvenilirlik metrikleri

- Cluster-bootstrap %95 güven aralığı
- Şehir, sezon, lead time ve fiyat bucket'ı stabilitesi
- En iyi günlerin/top marketlerin toplam P&L içindeki payı
- Veri eksikliği, stale snapshot ve kural parse hata oranı
- Model/provider drift göstergeleri

## 5. Gate özeti

| Gate | Geçiş koşulu | Başarısızlık sonucu |
|---|---|---|
| G0 — Feasibility | Veri kaynakları, yasal/erişim kısıtları ve maliyetler belgeli | Scope değiştir veya durdur |
| G1 — Data integrity | Timestamp, market rules, sonuç ve order book eşleşmeleri güvenilir | Modellemeye geçme |
| G2 — Forecast value | Kalibre model baseline'ları OOS geçiyor | Feature/model revizyonu veya no-go |
| G3 — Economic value | Executable, cost-adjusted backtest pozitif ve dayanıklı | Paper trading'e geçme |
| G4 — Paper execution | Gerçek zamanlı fill/latency sonucu backtestle uyumlu | Execution modelini düzelt |
| G5 — Live readiness | Hukuk/erişim, risk ve operasyon checklist'i tamam | Canlı işlem yok |
| G6 — Pilot scale | Küçük canlı pilot beklenen aralıkta ve risk limitlerinde | Scale etme; durdur/incele |

## 6. Fazlar

## Phase 0 — Research charter ve operasyonel temel

**Durum:** `IN_PROGRESS`  
**Amaç:** Araştırmayı sonuç yanlılığından koruyacak scope, kayıt ve yeniden üretilebilirlik temelini kurmak.

### İşler

- [x] Proje amacını ve canlı sermaye sınırını tanımla.
- [x] Agent araştırma kurallarını oluştur.
- [x] İlk hipotezleri ve gate'leri pre-register et.
- [x] Experiment planlama ve proje-hafızası protokolünü oluştur.
- [ ] Repository'yi başlat; `.gitignore`, README ve lisans kararını ekle. (`README.md` ve `.gitignore` tamamlandı; lisans kararı bekliyor.)
- [x] Python environment ve dependency lock yaklaşımını seç. (`pyproject.toml`; bootstrap runtime dependency yok, dev dependency aralıkları tanımlı.)
- [x] Klasör yapısını ve config standardını oluştur.
- [x] Experiment registry şemasını oluştur.
- [x] Data manifest ve data dictionary şablonlarını oluştur.
- [x] Reproducibility smoke test ekle.

### Çıktılar

- `AGENTS.md`
- `PROJECT_PLAN.md`
- `docs/agents.md`
- `README.md`, `pyproject.toml`, `.gitignore`
- `configs/base.json`
- `experiments/registry.schema.json`
- `docs/data/manifest-template.md`, `docs/data/data-dictionary-template.md`
- `src/weather_quant/`, `tests/`, `data/`, `notebooks/`, `reports/`

### Exit kriteri — G0'ın araştırma altyapısı kısmı

- Temiz ortamda test komutu çalışıyor.
- Tek bir config ile dummy ingestion → feature → evaluation akışı yeniden üretilebiliyor.
- Deney ve veri provenance formatı tanımlı.

---

## Phase 1 — Market, resolution ve veri fizibilitesi

**Durum:** `NOT_STARTED`  
**Amaç:** Model kurmadan önce gerçekten trade edilebilir veri evrenini ve resolution hedefini belirlemek.

### 1A. Polymarket market universe

- Gamma/CLOB API'lerinden weather market discovery yöntemini doğrula.
- En az 60–90 gün boyunca market metadata ve order-book snapshot toplamayı planla.
- Market başına outcome/token mapping, tick size, fee schedule, negative-risk özelliği ve rewards alanlarını kaydet.
- Fiyat geçmişinin gerçek bid/ask geçmişi yerine geçip geçmediğini dokümante et.
- WebSocket ile REST snapshot kapsamı ve olası veri kaybını ölç.

### 1B. Resolution registry

Her market için makinece okunabilir registry oluştur:

- şehir ve canonical station ID,
- çözüm kaynağı ve URL,
- local timezone ve DST,
- ölçüm periyodu,
- birim dönüşümü,
- bucket sınırları,
- inclusive/exclusive kuralları,
- yuvarlama ve tie kuralları,
- source revision ve rule hash,
- ambiguity/anomaly bayrakları.

Manuel olarak rastgele örneklenen marketlerin parse sonucu çift kontrol edilmelidir.

### 1C. Weather data feasibility

Aday kaynakları availability, geçmiş arşiv ve lisans açısından değerlendir:

- NOAA/NBM QMD ve core ürünleri
- GEFS/GFS
- HRRR — ABD ve kısa lead time
- ECMWF ENS — erişim/lisans/maliyet doğrulanarak
- yerel meteoroloji servisleri
- METAR/SYNOP/nihai günlük iklim gözlemleri
- resolution'da kullanılan kaynak

Forecast arşivinde **historical forecasts as issued** bulunduğu doğrulanmalıdır. Reanalysis, geçmiş forecast yerine kullanılmaz.

### 1D. Şehir seçme skoru

Her aday şehir için 0–5 puanla:

- resolution netliği,
- sonuç gözlemi güvenilirliği,
- historical forecast erişimi,
- order-book likiditesi/depth,
- spread,
- market sıklığı,
- istasyon-grid temsil edilebilirliği,
- anomaly/manipülasyon riski,
- veri sağlayıcı maliyeti.

İlk 3–5 şehir skorla seçilir; tanıdıklık veya sezgiyle değil.

### G0 geçiş kriteri

- En az 3 aday şehirde forecast, observation, rules ve market verisi birleştirilebilir.
- Fee ve executable price semantiği test işlemi olmadan dokümandan/API'den doğrulanmıştır.
- Kullanım şartları, coğrafi erişim, Türkiye'deki hukuk/vergi araştırması için profesyonel kontrol ihtiyacı kaydedilmiştir.
- Tahmini veri maliyeti ve operasyon bütçesi çıkarılmıştır.

---

## Phase 2 — Timestamp-doğru veri platformu

**Durum:** `NOT_STARTED`  
**Amaç:** Look-ahead bias içermeyen birleşik araştırma dataset'i üretmek.

### Veri tabloları

Minimum mantıksal tablolar:

- `markets`
- `outcomes`
- `resolution_rules`
- `orderbook_snapshots`
- `trades`
- `forecast_runs`
- `forecast_members_or_quantiles`
- `station_observations`
- `settlements`
- `data_quality_flags`

### Zorunlu timestamp'ler

- event/valid time
- provider model run time
- provider publication/availability time
- local ingestion time
- market snapshot exchange time
- local receipt time
- settlement proposal/final time

### Kalite kontrolleri

- Outcome bucket'ları boşluk/overlap içeriyor mu?
- Olasılık bucket'ları exhaustive mi?
- Station ID tarih içinde değişmiş mi?
- Celsius/Fahrenheit dönüşümleri exact mı?
- Local-day → UTC dönüşümü DST günlerinde doğru mu?
- Snapshot sırası monoton mu; duplicate/stale oranı ne?
- Forecast veri dosyası model run'dan önce görünmüş gibi mi?
- Nihai sonuç resolution kaynağıyla eşleşiyor mu?

### G1 geçiş kriteri

- Bir market, ham kaynaklardan model-ready satıra uçtan uca izlenebiliyor.
- Kritik timestamp/rule alanlarında hedeflenen kapsama göre en az %99 bütünlük; kalanlar bayraklı.
- Seçilmiş market örneğinde manuel reconciliation geçiyor.
- Veri leakage testleri geçiyor.
- Dataset ve schema versioned.

---

## Phase 3 — Baseline probabilistic forecasting

**Durum:** `NOT_STARTED`  
**Amaç:** Karmaşık modele geçmeden gerçek tahmin zorluğunu ve minimum benchmark'ı ölçmek.

### Modeller

1. İstasyon/mevsim climatology
2. Persistence ve son gözlem baseline
3. Resmî point forecast çevresinde historical error distribution
4. Ham ensemble member frequency
5. Varsa NBM/QMD probabilistik baseline
6. Basit bias-corrected Gaussian distribution

### Değerlendirme tasarımı

- Rolling/expanding-window walk-forward
- Şehir ve lead time bazlı sonuç
- Model-provider upgrade tarihlerinde ayrı regime analizi
- Bucket probability üretirken resolution yuvarlamasının birebir simülasyonu
- Calibration curve ve PIT/rank histogram

### Önceden tanımlanacak split

Veri kapsamı belli olduktan sonra train/validation/final test tarihleri sonuçlara bakmadan Decision Log'a yazılacaktır. Final test, model seçimi bitene kadar kilitli tutulacaktır.

### G2 geçiş kriteri

- En az bir kalibre model, naive ve ham ensemble baseline'ına karşı OOS improvement gösteriyor.
- Calibration ekonomik olarak önemli fiyat bölgelerinde kabul edilebilir.
- İyileşme yalnızca tek ekstrem olay veya tek şehre bağlı değil.
- Final test açılmadan model ailesi ve hyperparameter protokolü dondurulmuş.

---

## Phase 4 — Station-specific calibration ve model geliştirme

**Durum:** `NOT_STARTED`  
**Amaç:** Hava tahmininden kalibre edilmiş outcome dağılımına geçmek.

### Sıralı model geliştirme

1. EMOS/NGR: ensemble mean ve spread
2. Rolling station bias ve lead-time error
3. Multi-model weighted ensemble
4. Rejim feature'ları:
   - cloud cover,
   - wind direction/speed,
   - humidity/dew point,
   - precipitation,
   - boundary-layer göstergeleri,
   - önceki run değişimi,
   - gün içi gerçekleşen maksimum ve kalan ısınma potansiyeli
5. Gerekirse distributional boosting veya mixture model

Her model, bir önceki basit modele karşı incremental test edilir. Karmaşıklık otomatik olarak ilerleme sayılmaz.

### Model belirsizliği

- Probability point estimate yanında güven/credible interval
- Forecast-provider disagreement
- Out-of-distribution ve extreme-weather bayrağı
- Conservative trade probability: `q_lower` veya shrinkage-to-market/climatology

### Çıkış koşulu

- Baseline'a incremental OOS forecast value
- Calibration'ın segmentlerde kabul edilebilir olması
- Feature leakage ve data snooping incelemesinin geçmesi

---

## Phase 5 — Market benchmark ve edge discovery

**Durum:** `NOT_STARTED`  
**Amaç:** İyi hava tahmininin gerçekten trade edilebilir alpha olup olmadığını sınamak.

### Market karşılaştırması

Her karar timestamp'inde:

- model probability \(q\),
- executable ask/bid ve depth,
- market-implied probability,
- fee schedule,
- beklenen slippage,
- kalan settlement süresi,
- model freshness,
- resolution risk score

birleştirilir.

### Aday sinyaller

- `q_lower > effective_ask + margin`
- `q_upper < effective_bid - margin`
- Yeni forecast run sonrası repricing gecikmesi
- Gün içi gözlemle artık imkânsız/çok düşük ihtimalli bucket'lar
- Cross-outcome probability incoherence
- Maker quote: model fair value çevresinde inventory-aware spread

Her sinyal ayrı strateji ID'si alır; sonradan en iyisini seçme etkisi raporlanır.

### Edge decay analizi

- Market açılışına göre
- Forecast run yayınından sonraki dakika/saatlere göre
- Yerel günün aşamasına göre
- Likidite/spread rejimine göre
- Model disagreement'a göre

### Sinyal kabul kriteri

- Tahmini brüt edge işlem maliyetinden belirgin büyük.
- Edge calibration bucket'larında realized return monoton veya açıklanabilir.
- Aynı sinyal en az iki OOS zaman bloğunda çalışıyor.
- Capacity sıfıra yakın değil.

---

## Phase 6 — Event-driven backtest ve execution simulator

**Durum:** `NOT_STARTED`  
**Amaç:** Teorik probability edge'i uygulanabilir P&L'e çevirmek.

### Simulator özellikleri

- Bid/ask depth walk
- Limit order queue/fill yaklaşımı
- Partial fills
- Emir iptal/değişim gecikmesi
- Forecast ingest ve strategy compute latency
- Güncel per-market fee schedule
- Maker rebate için muhafazakâr senaryolar
- Inventory ve correlated exposure
- Settlement gecikmesi ve sermaye kilidi
- Stale snapshot filtresi

### Senaryolar

- Optimistic — yalnızca üst sınır, karar için kullanılmaz
- Base — ölçülmüş latency/fill tahmini
- Conservative — düşük fill, yüksek adverse selection
- Stress — fee/slippage 2×, gecikme yüksek, rebate 0

### Risk sizing araştırması

- Sabit çok küçük stake
- Volatility/uncertainty scaling
- 0.10–0.25 fractional Kelly tavanlı
- Şehir/gün/weather-system cluster exposure limitleri

### G3 geçiş kriteri

Final eşikler veri hacmi görüldüğünde pre-register edilecek; başlangıç hedefleri:

- En az 2.000 OOS market/sinyal fırsatı veya eşdeğer etkili örnek büyüklüğü
- Base senaryoda tüm maliyetlerden sonra pozitif net EV
- Cluster-bootstrap %95 CI alt sınırı tercihen > 0; değilse açık "inconclusive"
- Stress testte ekonomik tezin tamamen tersine dönmemesi
- Tek şehir/gün/mevsim toplam P&L'in baskın kaynağı olmaması
- Drawdown küçük sermaye risk bütçesiyle uyumlu
- Capacity ve sermaye dönüş hızı ölçülmüş

---

## Phase 7 — Shadow mode ve paper trading

**Durum:** `NOT_STARTED`  
**Amaç:** Gerçek zamanlı data, latency ve fill varsayımlarını sermaye riske etmeden doğrulamak.

### Aşamalar

1. Shadow signal: emir üretmeden timestamp'li sinyal kaydı
2. Touch-fill paper: fiyat dokununca fill varsayımı
3. Queue-aware paper: muhafazakâr fill modeli
4. Operational rehearsal: restart, stale data, API outage ve alert testleri

### İzlenecek farklar

- Historical backtest ile canlı shadow calibration farkı
- Beklenen ve gerçekleşebilir spread/depth farkı
- Sinyal üretim gecikmesi
- Limit fill ve adverse selection
- Provider/API outage oranı
- Model drift

### G4 geçiş kriteri

- En az 6–8 hafta veya yeterli market rejimi kapsayan paper period
- Veri pipeline uptime hedefi sağlanmış
- Paper sonuçları backtest güven aralığıyla uyumlu
- Fill model hatası ölçülmüş ve simulator güncellenmiş
- Fail-safe ve `NO_TRADE` koşulları test edilmiş

---

## Phase 8 — Live readiness ve küçük sermayeli pilot

**Durum:** `NOT_STARTED`  
**Amaç:** Edge'i kanıtlamak değil, araştırma varsayımlarının gerçek execution altında korunup korunmadığını minimum riskle ölçmek.

### G5 zorunlu checklist

- [ ] Kullanıcı açık biçimde canlı pilotu yetkilendirdi.
- [ ] Platformun ilgili kullanıcı ve coğrafya için erişim/uygunluk durumu doğrulandı.
- [ ] Türkiye hukuk, vergi ve raporlama yükümlülükleri profesyonel olarak değerlendirildi.
- [ ] Kullanım şartları ve veri lisansları incelendi.
- [ ] Ayrı cüzdan ve kaybı tolere edilebilir pilot bütçesi belirlendi.
- [ ] Secret management ve withdrawal güvenliği kuruldu.
- [ ] Günlük/haftalık zarar, exposure ve kill-switch limitleri config'te.
- [ ] Manuel emergency stop test edildi.
- [ ] Monitoring ve reconciliation raporu hazır.

### Başlangıç risk taslağı

Bu değerler kullanıcı onayı ve backtest sonucu olmadan aktive edilmez:

- İşlem başına bankroll: en fazla %0.25
- Market başına toplam: en fazla %0.50
- Aynı şehir/gün cluster: en fazla %1.0
- Toplam açık risk: en fazla %3–5
- Günlük stop: %1 bankroll
- Haftalık stop: %3 bankroll
- Sizing: en fazla 0.10 Kelly; belirsizlik shrinkage sonrası
- İlk pilot: maker-first; taker yalnızca ayrı kanıtlı sinyalde

### G6 pilot değerlendirmesi

- Live fill, slippage ve fee simülasyona yakın mı?
- Gerçekleşen calibration bozulmuş mu?
- P&L beklenen güven aralığında mı?
- Adverse selection veya sistematik operasyon hatası var mı?
- Scale için yeterli örnek var mı, yoksa yalnızca süre mi geçti?

Scale kararı otomatik verilmez. Yeni Decision Log girdisi ve kullanıcı onayı gerekir.

---

## Phase 9 — Sürekli araştırma ve kontrollü ölçekleme

**Durum:** `NOT_STARTED`

- Haftalık data-quality ve execution review
- Aylık calibration/drift raporu
- Model/provider değişikliklerinde yeniden validation
- Quarterly strategy retirement review
- Yeni şehir eklemeden önce Phase 1 skorlaması
- Risk artışından önce yeni capacity backtest
- Edge yarı ömrü ve rakip davranışı takibi
- P&L attribution: forecast, timing, maker rebate, incoherence

Bir strateji aşağıdaki durumlarda otomatik olarak `REVIEW/NO_TRADE` durumuna alınmalıdır:

- calibration drift eşiği aşılırsa,
- veri kaynağı/rules değişirse,
- üç ardışık değerlendirme penceresinde net EV negatife dönerse,
- slippage/fill beklenen aralığın dışına çıkarsa,
- resolution veya istasyon kalite anomalisi oluşursa.

## 7. İlk 30 günlük çalışma planı

Takvim süre değil, sıra önerisidir; veri engelleri planı değiştirebilir.

### Hafta 1 — Temel ve fizibilite

- Repo/environment iskeleti
- Polymarket API ve fee/rules spike
- Weather source ve archive matrisi
- 10–15 şehirlik aday listesi
- Resolution registry prototipi
- İlk G0 risk ve maliyet notu

### Hafta 2 — Veri toplama MVP

- Market discovery collector
- Order-book snapshot/WebSocket collector
- Forecast run collector — önce tek sağlayıcı
- Observation/settlement collector
- Raw manifest, schema ve timezone testleri

### Hafta 3 — İlk birleşik dataset

- 2–3 örnek marketi uçtan uca reconcile et
- Bucket mapping ve rounding testleri
- Baseline climatology ve ensemble probability notebook'u
- Veri boşluğu ve leakage raporu
- Şehir skorlamasını güncelle

### Hafta 4 — İlk evidence review

- Walk-forward tasarımını veri kapsamına göre pre-register et
- İlk calibration baseline'larını karşılaştır
- Market snapshot kalitesini ve uygulanabilir backtest ufkunu değerlendir
- G0/G1 için `PASS`, `BLOCKED` veya `FAIL` kararı
- Sonraki 30 günü kanıta göre yeniden planla

## 8. İlk backlog

Öncelik sırası:

1. `README.md` ve repository/environment bootstrap
2. Data-source feasibility matrix
3. Polymarket market schema keşfi
4. Resolution-rule registry schema
5. City/station scoring rubric'in veriye uygulanması
6. Order-book recorder MVP
7. Forecast archive proof-of-concept
8. Observation/settlement reconciliation
9. Data-quality dashboard/report
10. Baseline walk-forward experiment

## 9. Risk register

| ID | Risk | Olasılık | Etki | Erken sinyal | Mitigasyon |
|---|---|---:|---:|---|---|
| R1 | Historical order-book verisi yetersiz | Yüksek | Yüksek | Yalnızca trades/midpoint bulunması | Şimdi snapshot toplamaya başla; conservative simulator |
| R2 | Historical forecast-as-issued yok | Orta/Yüksek | Yüksek | Reanalysis veya sonradan revize veri | Kaynak değiştir, scope daralt, canlı-forward araştırma |
| R3 | Resolution rule/istasyon değişikliği | Orta | Yüksek | Rule hash veya station ID farkı | Versioned registry ve regime split |
| R4 | Model leakage/look-ahead | Orta | Çok yüksek | Olağandışı yüksek backtest | Availability timestamps ve leakage tests |
| R5 | Edge spread/fee ile yok oluyor | Yüksek | Yüksek | Midpoint pozitif, executable negatif | Maker-first; erken ekonomik benchmark |
| R6 | Fill modeli fazla iyimser | Yüksek | Yüksek | Paper fill düşük | Queue-aware paper ve stress test |
| R7 | Multiple testing/data snooping | Yüksek | Yüksek | Çok sayıda segment/model | Pre-registration, locked test, correction |
| R8 | P&L tek rejime yoğunlaşmış | Orta | Yüksek | Top gün/şehir payı yüksek | Segment stability ve risk cap |
| R9 | Provider/model version drift | Yüksek | Orta/Yüksek | Error distribution kırılması | Version flags, rolling recalibration |
| R10 | API outage/stale data | Orta | Yüksek | Timestamp lag | Stale guard, no-trade, monitoring |
| R11 | Hukuk/erişim/vergi engeli | Belirsiz | Çok yüksek | Terms/geofence belirsizliği | Canlıdan önce profesyonel doğrulama |
| R12 | Küçük capacity | Yüksek | Orta | Edge yalnızca çok küçük depth'te | Capacity metriğini north-star'a dahil et |
| R13 | Manipülasyon/sensör anomalisi | Düşük/Orta | Yüksek | Fizik dışı gözlem spike'ı | QC, source cross-check, no-trade |

## 10. Evidence ve artifact standardı

Her milestone aşağıdakilerden en az birini üretmelidir:

- `reports/data_quality/...`
- `reports/research/...`
- `reports/backtests/...`
- `experiments/<experiment_id>/`
- versioned dataset manifest
- test çıktısı/CI kaydı

Her raporun başında:

- data cut-off,
- code/config version,
- dataset version,
- kapsanan market/şehir,
- bilinen sınırlamalar

yer almalıdır.

## 11. Plan güncelleme protokolü

Her anlamlı çalışma sonunda bu dosyada dört değişiklik yapılır:

1. İlgili checkbox/durum güncellenir.
2. Ölçülen metrik veya veri problemi ilgili faza eklenir.
3. `Decision Log` bölümüne yeni kayıt eklenir.
4. `Next Action` tek ve uygulanabilir biçimde güncellenir.

Sonuçlar planı desteklemiyorsa hipotez veya scope revize edilir. Başarısız deney silinmez.

## 12. Decision Log

### D-0001 — 2026-08-29 — Proje charter'ı

- **Durum:** `ACTIVE`
- **Karar:** Proje, garantili gelir sistemi değil; quant araştırma ve küçük sermayeli niche strategy fizibilitesi olarak yürütülecek.
- **Kanıt:** Weather marketlerde teorik probability edge imkânı bulunmakla birlikte fee, spread, resolution ve timestamp-doğru geçmiş veri olmadan ekonomik avantaj gösterilemez.
- **Sonuç:** Canlı işlem Phase 8'e ve açık kullanıcı onayına kadar yasak. İlk odak veri integrity ve executable-price backtest.
- **Etkilenen hipotezler:** H1–H6 oluşturuldu.

### D-0002 — 2026-08-29 — İlk market kapsamı

- **Durum:** `ACTIVE`
- **Karar:** İlk araştırma günlük maksimum sıcaklık bucket marketleri ve veriyle seçilecek 3–5 istasyonla sınırlandırıldı.
- **Gerekçe:** Dar scope, station-specific bias ve resolution kurallarının doğru modellenmesini; yeterli örnek biriktirmeyi ve veri kalite sorunlarını görünür kılmayı kolaylaştırır.
- **Yeniden değerlendirme:** Phase 1 şehir skoru ve veri erişimi tamamlandığında.

### D-0003 — 2026-08-29 — Experiment hafızası ve commit protokolü

- **Durum:** `ACTIVE`
- **Karar:** Her material araştırma deneyi, `docs/experiments/EXP-YYYYMMDD-short-slug/PLAN.md` altında pre-register edilecek; aşamalara bölünecek ve her aşama sonunda status, evidence, decision ve next action güncellenerek ayrı bir Git commit oluşturulacak.
- **Gerekçe:** Başarılı ve başarısız denemelerin, veri/code lineage'ın ve post-hoc değişikliklerin kalıcı biçimde izlenmesi; proje hafızasının terminal çıktısına veya insan belleğine bağlı kalmaması.
- **Artifact:** `docs/agents.md`
- **Sonuç:** İlk gerçek deney oluşturulduğunda `docs/experiments/README.md` index'i de başlatılacak. Experiment-level ayrıntılar kendi planında, project-level kararlar bu dosyanın Decision Log'unda tutulacak.

### D-0004 — 2026-08-30 — Phase 0 repository bootstrap standardı

- **Durum:** `ACTIVE`
- **Karar:** Proje `src/weather_quant/` package layout, standard-library ile çalışan `configs/base.json`, `pyproject.toml`, immutable veri katmanları, machine-readable experiment registry şeması ve durable report/data-documentation dizinleriyle başlatıldı.
- **Kanıt:** `PYTHONPATH=src python3 -m unittest discover -s tests -v` ile config → normalize → feature → evaluation smoke akışındaki 2 test geçti. `configs/base.json` ve `experiments/registry.schema.json` JSON parse kontrolünden geçti. İlk koşu Python 3.9'da `tomllib/tomli` bulunmadığını gösterdi; ek bootstrap dependency gerektirmemek için config formatı JSON'a çevrildi ve yeniden test başarılı oldu.
- **Sınırlama:** Lisans kararı henüz verilmedi. Smoke akışı altyapı doğrulamasıdır; forecast veya trading edge kanıtı değildir.
- **Branch:** `feat/project-bootstrap`
- **Sonuç:** Phase 0'ın veri/provenance ve test altyapısı hazır. Sonraki araştırma çalışması ayrı experiment planıyla pre-register edilecek.

### D-0005 — 2026-08-30 — İlk veri fizibilite deneyi pre-registration

- **Durum:** `ACTIVE`
- **Karar:** `EXP-20260830-data-source-feasibility` deneyi `READY` olarak kaydedildi. En az üç şehirde market/outcome metadata, versioned resolution rule ve istasyon, prospective executable L2 order book, historical forecast-as-issued, exact station observation ve settlement bileşenleri birleşmeden forecast/backtest geliştirmesi araştırma kanıtı olarak kabul edilmeyecek.
- **Pre-registered gate:** `PASS` için en az 3 complete city, kritik identifier/rule bütünlüğünde %100, 24 saatlik collector koşusunda ≥%99 uptime ve ≥%95 beklenen interval coverage, final şehir başına tercihen ≥365 günlük forecast-as-issued ve observation geçmişi gerekir. 180–364 gün veya yalnız prospective L2 durumunda ancak açık koşullu `CONDITIONAL_PASS` verilebilir.
- **Kanıt:** Resmî Polymarket dokümantasyonu public current book, market WebSocket ve price-history yüzeylerini; NOAA NBM dokümantasyonu NOMADS/AWS dağıtımını; ECMWF Open Data dokümantasyonu rolling archive yapısını gösteriyor. Endpoint-level gerçek coverage henüz ölçülmedi.
- **Artifact:** `docs/experiments/EXP-20260830-data-source-feasibility/PLAN.md`
- **Sonuç:** Yalnız Phase 1 read-only Polymarket market discovery spike'ı yetkilidir. Profitability claim, model eğitimi sonucu ve canlı emir kapsam dışıdır.

## 13. Open Questions

- Polymarket historical L2/order-book verisi ne kadar geriye ve hangi çözünürlükte erişilebilir?
- Mevcut weather marketlerin her biri hangi istasyon ve resolution source'u kullanıyor?
- Forecast-as-issued arşivlerinde NBM/GEFS/HRRR/ECMWF için maliyet ve retention nedir?
- Polymarket weather fee/rebate schedule market metadata ile tarihsel olarak versioned alınabilir mi?
- Negative-risk marketlerde tüm bucket'ları kapsayan gerçek execution mekaniği nedir?
- Türkiye'den kullanım, fonlama, vergi ve raporlama açısından hangi profesyonel doğrulamalar gerekir?
- İlk veri toplama döneminde yeterli market sıklığı ve depth var mı?

## 14. Next Action

**Tek sonraki adım:** `EXP-20260830-data-source-feasibility` Phase 1 kapsamında public Gamma/CLOB yüzeylerinden daily maximum-temperature market discovery ve event/market/outcome/token/condition identifier reconciliation spike'ını uygulamak.

Beklenen artifact'lar:

- `src/weather_quant/ingestion/polymarket_markets.py`
- sanitized API fixtures ve identifier contract testleri
- `reports/data_quality/EXP-20260830-phase1-market-discovery.md`

Phase 1 sonunda experiment planı, experiment index ve project Decision Log ölçülen coverage/missingness sonuçlarıyla güncellenecek ve ayrı experiment commit'i oluşturulacaktır. Phase 0'ın kalan idari işi lisans seçimidir.
