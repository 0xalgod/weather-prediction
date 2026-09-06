# Polymarket Weather Quant Research — Living Roadmap

**Proje tipi:** Quant araştırma projesi ve küçük sermayeli niche strategy  
**Plan versiyonu:** 1.4.0
**Son güncelleme:** 2026-09-05
**Mevcut faz:** Forecast-first temporal split ve baseline model ön kaydı; settlement reconciliation parallel/deferred
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
| H7 | Bir yıllık KORD as-issued NBM+GEFS verisi leakage olmadan günlük maksimum etiketiyle kurulabilir | Coverage, timestamp ve schema gate'leri | Joined ≥%97, label ≥%99, temporal leakage 0 | `IN_PROGRESS` |

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

**Durum:** `IN_PROGRESS`
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

**Durum:** `IN_PROGRESS`
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

**Durum:** `IN_PROGRESS`
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

### D-0006 — 2026-08-30 — Polymarket MaxT discovery yüzeyi

- **Durum:** `ACTIVE`
- **Karar:** Daily maximum-temperature discovery için primary surface `highest-temperature` tag slug/ID `104596` ve cursor-based keyset pagination olacak. Broad Weather tag ID `84` coverage cross-check olarak kalacak; generic temperature tag ID `104615` primary filter olmayacak.
- **Ölçülen kanıt:** Narrow tag ilk keyset sayfası 100/100 yapısal olarak eşleşen event ve non-null cursor döndürdü. Broad Weather ilk sayfada 36 MaxT event, 33 şehir etiketi ve 396 nested binary market gözlendi. Bunların 44'ünde condition/token identifier eksikti. `active=true,closed=false` Mayıs'ta bitmiş stale eventleri de içerdi.
- **Artifact:** `reports/data_quality/EXP-20260830-phase1-schema-recon.md`
- **Sonuç:** Experiment `IN_PROGRESS`. Tag membership/lifecycle flag tek başına yeterli değil; production client date relevance, identifier completeness, nested JSON array integrity, negative-risk ve fee metadata sınıflandırması yapacak.

### D-0007 — 2026-08-30 — Point-in-time Gamma discovery contract

- **Durum:** `ACTIVE`
- **Karar:** Phase 1 discovery client public HTTPS/keyset, opaque cursor, immutable checksummed raw envelope ve strict normalization contract kullanacak. Stale lifecycle, eksik condition/token, outcome-token mismatch, non-binary market ve disabled book durumları sessizce drop edilmeyecek; reason code ile ayrılacak.
- **Kanıt:** `src/weather_quant/ingestion/polymarket_markets.py` ve sanitized fixture üzerinde pagination/cursor-loop, checksum/timestamps, overwrite protection, JSON-array parsing, identifier mapping ve exclusion davranışını kapsayan 7 contract testi; bootstrap ile toplam 9 test başarılı.
- **Sonuç:** Implementation contract hazır, fakat full live inventory ölçülmeden Phase 1 gate değerlendirilemez. Sıradaki adım tüm active/not-closed keyset sayfalarını raw envelope ile çekip coverage raporu üretmektir.

### D-0008 — 2026-08-30 — Active MaxT inventory kapsamı

- **Durum:** `ACTIVE`
- **Karar:** Full active/not-closed Gamma inventory keyset ile iki sayfada tamamlandı; lifecycle/date/identifier reason-code sınıflandırması downstream collector evreninin zorunlu parçası olacak.
- **Ölçülen kanıt:** Run `20260829T214842Z`: 136 event, 51 şehir etiketi, 1.496 nested market, 0 duplicate event. 100 temporally relevant event içindeki 1.100 market eligibility contract'ını geçti; 396 geçmiş market elendi ve 44'ünde condition/token eksikliği de vardı. İki raw envelope 6.6 MB.
- **Artifact:** `reports/data_quality/EXP-20260830-phase1-active-inventory.md`
- **Sonuç:** Active inventory substep geçti; Phase 1 henüz geçmedi. Closed/resolved coverage ve ≥20 manual reconciliation sıradaki zorunlu kanıtlardır.

### D-0009 — 2026-08-30 — Historical identity ve current eligibility ayrımı

- **Durum:** `ACTIVE`
- **Karar:** Closed/historical marketlerde outcome-token mapping `identifier_complete` ile korunacak; `eligible_for_book_collection` yalnız current prospective collection uygunluğunu gösterecek. Bu iki durum tek filtrede birleştirilmeyecek.
- **Ölçülen kanıt:** İlk closed run 83 sayfa, 8.222 event, 54 şehir, 89.536 market, 0 duplicate ve 370 MB raw veri üretti. İncelenen resolved kayıtta valid condition/token/outcome price olmasına rağmen eski normalizer current eligibility false olduğu için `outcome_count=0` üretti.
- **Invalidation:** İlk closed run'ın page/event/market/city/date/storage ölçümleri geçerli; historical outcome ve identifier-complete sayıları geçersizdir.
- **Artifact:** `reports/data_quality/EXP-20260830-phase1-closed-inventory-attempt.md`
- **Sonuç:** Contract ayrıştırıldı ve regression test eklendi. Closed history yeni immutable run ile yeniden ölçülecek.

### D-0010 — 2026-08-30 — Closed history identifier ve settlement kapsamı

- **Durum:** `ACTIVE`
- **Karar:** Gamma closed history, event/market identity registry için kullanılabilir aday olarak tutulacak; ancak eksik resolution/status cohortları sınıflandırılmadan Phase 1 geçmeyecek. Full-snapshot storage için scheduled collector öncesi dedup/compression retention kararı zorunlu.
- **Ölçülen kanıt:** Corrected run `20260829T215446Z` önceki 83 sayfa/8.222 event/89.536 market/0 duplicate ölçümünü yeniden üretti. 89.514 market identifier-complete (%99,9754) ve 179.028 historical outcome satırı oluştu. Event resolution source %92,2282; automatic resolution %98,5892; closedTime %99,3067; UMA-resolved market %99,9107. Tek raw run yaklaşık 370 MB.
- **Eksik cohortlar:** 639 no-source event, 116 non-automatic event, 57 no-close-time event, 22 identity-incomplete market, 80 non-UMA-resolved market; overlap henüz çözülmedi.
- **Artifact:** `reports/data_quality/EXP-20260830-phase1-closed-inventory.md`
- **Sonuç:** Closed inventory substep geçti; Phase 1 `IN_PROGRESS`. Sıradaki adım anomaly cohort extraction ve stratified 20-event manual reconciliation sample'dır.

### D-0011 — 2026-08-30 — Anomaly cohortları ve deterministik reconciliation örneklemi

- **Durum:** `ACTIVE`
- **Karar:** Closed-history kalite bayrakları event ve market seviyesinde ayrı raporlanacak; 20-event manuel kontrol kuyruğu sabit seed ve hash sırasıyla seçildi. Örnek seçimi tamamlandı, fakat manuel reconciliation tamamlanmış sayılmayacak.
- **Ölçülen kanıt:** 8.222 eventin 7.470'i temiz, 752'si en az bir anomaly bayrağı taşıyor. 639 no-source, 116 non-automatic, 57 no-close-time event var. Önceki 22 identity-incomplete ve 80 non-UMA-resolved sayıları market düzeyinde; bunlar sırasıyla yalnız 2 ve 19 eventte yoğunlaşıyor. Cohortlar örtüşüyor.
- **Örneklem:** Sabit `EXP-20260830-phase1-manual-reconciliation-v1` seed'iyle 20 benzersiz event seçildi; beş anomaly sınıfının tamamı ve temiz kontroller kapsandı. Identifier-incomplete popülasyon yalnız iki event olduğu için ikisi de örneğe girdi.
- **Artifact:** `reports/data_quality/EXP-20260830-phase1-closed-anomaly-cohorts.md`, `reports/data_quality/EXP-20260830-phase1-closed-audit-sample.json`
- **Sonuç:** Cohort extraction/sample-selection substep geçti; Phase 1 `IN_PROGRESS`. Sıradaki adım seçilmiş 20 eventin kaynak, station, identifier ve terminal outcome alanlarını manuel reconcile etmektir.

### D-0012 — 2026-08-30 — Market discovery/identifier reconciliation gate sonucu

- **Durum:** `ACTIVE`
- **Karar:** Experiment Phase 1 market-discovery gate'i geçti; yalnız `RECONCILED` disposition alan eventler future label registry'ye girebilir. Missing-source, non-terminal/cancelled ve source/outcome mismatch kayıtları hard `NO_TRADE`/exclude durumudur.
- **Ölçülen kanıt:** Sabit 20-event örneklemde 12 event identifier + station/rule + terminal bucket + Wunderground displayed high zincirini geçti; 3 missing-source, 3 non-terminal/cancelled ve 2 source/outcome mismatch bulundu. Fetch error 0; retained 12 kayıt 12 şehir kapsıyor ve ön kayıtlı ≥10 event/≥3 şehir eşiğini geçiyor.
- **Kritik bulgu:** Exact terminal Gamma outcome her zaman gerçekleşen hava etiketi değildir. Dallas 19 Mayıs terminal `73°F or below` iken linked source 30°C; Munich 19 Mayıs terminal `11°C or below` iken source 19°C gösterdi.
- **Artifact:** `reports/data_quality/EXP-20260830-phase1-manual-reconciliation.md`, `reports/data_quality/EXP-20260830-phase1-manual-reconciliation-v2.json`
- **Sonuç:** Üst seviye veri fizibilitesi Phase 1 hâlâ `IN_PROGRESS`; market identity alt gate'i geçti. Sıradaki adım versioned resolution-rule/station registry şemasıdır.

### D-0013 — 2026-08-30 — Resolution registry veri sözleşmesi

- **Durum:** `ACTIVE`
- **Karar:** Research label'a alınacak her event; versioned event/station/rule/bucket/provenance kaydıyla ve `RECONCILED` disposition ile temsil edilecek. Kritik alanı eksik kayıtlar uydurularak doldurulmayacak; reason-code içeren hard `NO_TRADE` kaydı olarak korunacak.
- **Zorunlu semantik:** IANA timezone, explicit local calendar day, unit/precision/rounding, exact rule SHA-256, inclusive sayısal bucket sınırları, event-market-condition-token zinciri ve source snapshot checksumları.
- **Kanıt:** Sanitized fixture üzerinde valid record, gap/overlap, rule hash revision, invalid timezone ve missing-source `NO_TRADE` davranışını kapsayan 5 yeni test; repository toplam 23 test geçti.
- **Artifact:** `schemas/resolution_registry.schema.json`, `src/weather_quant/normalization/resolution_rules.py`, `reports/data_quality/EXP-20260830-phase2-resolution-registry-contract.md`
- **Sonuç:** Phase 2 contract substep geçti; Phase 2 `IN_PROGRESS`. Sıradaki adım parser ile sabit 20-event örneklem için candidate registry üretmektir.

### D-0014 — 2026-08-30 — Candidate resolution registry population

- **Durum:** `ACTIVE`
- **Karar:** Phase 1'de eşleşen 12 kayıt station/timezone metadata bağımsız doğrulanana kadar final `RECONCILED` değil, `CANDIDATE_STATION_UNVERIFIED` olarak tutulacak. Candidate statüsü structural validation'dan geçse bile backtest/trading label'ı olamaz.
- **Ölçülen kanıt:** Sabit örneklemden deterministik olarak 20 registry kaydı, 161 bucket ve 20 ayrı rule hash üretildi. 12 candidate kayıtta 128 bucket tam contract'ı geçti; 8 hard `NO_TRADE` disposition değişmeden korundu. İkinci koşu byte-for-byte aynı sonucu verdi; 26 test geçti.
- **Artifact:** `reports/data_quality/EXP-20260830-phase2-resolution-registry-candidate.jsonl`, `reports/data_quality/EXP-20260830-phase2-resolution-registry-population.md`
- **Sonuç:** Parser/population substep geçti; Phase 2 `IN_PROGRESS`. Sıradaki adım 12 candidate station/timezone eşleşmesini authoritative metadata ile doğrulamaktır.

### D-0015 — 2026-08-30 — Station identity ve timezone promotion sonucu

- **Durum:** `ACTIVE`
- **Karar:** Candidate yalnız current AviationWeather ICAO metadata, coordinate-to-IANA 2026c boundary eşleşmesi ve rule-name/source-code semantik kontrolünün tamamını geçerse final `RECONCILED` olur.
- **Ölçülen kanıt:** AviationWeather 12/12 ICAO kodunu döndürdü; timezone boundary ve release equivalence mapping ile 12/12 timezone doğrulandı. 11/12 station identity geçti. Karachi kuralındaki `Masroor Airbase` adı, source ICAO `OPKC` için resmî `Karachi/Jinnah Intl` metadata'sıyla çelişti.
- **Sonuç:** 11 kayıt final `RECONCILED`, toplam 9 kayıt hard `NO_TRADE`; 117 bucket retained. Phase 2 minimum ≥3 şehir mapping eşiğini aşıyor ancak city-family revision ve DST testleri tamamlanmadan Phase 2 kapanmıyor.
- **Artifact:** `reports/data_quality/EXP-20260830-phase2-station-timezone-verification.md`, `reports/data_quality/EXP-20260830-phase2-resolution-registry-verified.jsonl`
- **Sıradaki adım:** Tekrarlanan şehirlerde rule/station değişimini ölçmek ve DST/local-date boundary testlerini eklemek.

### D-0016 — 2026-08-30 — Phase 2 rule revision/DST gate sonucu

- **Durum:** `ACTIVE`
- **Karar:** Phase 2 pre-registered gate geçti; yalnız verified registry kapsamı için. Şehir bazında sabit station/rule varsayımı yasak: event-effective station ve exact rule hash kullanılacak.
- **Ölçülen kanıt:** 8.222 event/54 şehirde corrected analiz 7.321 complete parse (%89,0416), 901 incomplete parse, 2 gerçek station transition (Denver `KDEN→KBKF`, Paris `LFPG→LFPB`), 0 unit transition ve 52 multi-template şehir buldu. DST testleri Toronto için 23/25 saat, Kuala Lumpur için 24 saat local-day window doğruladı.
- **Invalidation:** İlk koşudaki 46 multi-station sonucu NWS `?site=` URL parse hatası nedeniyle geçersizdi; regression test sonrası corrected count 2.
- **Gate:** 11 final kayıt/11 şehir, retained critical completeness %100; ≥3 şehir eşiği geçti. 901 incomplete historical event kesinlikle label değildir.
- **Artifact:** `reports/data_quality/EXP-20260830-phase2-rule-family-dst.md`, `reports/data_quality/EXP-20260830-phase2-rule-family-revisions.json`
- **Sonuç:** Experiment Phase 2 `PASSED`; Phase 3 executable order-book feasibility `IN_PROGRESS`.

### D-0017 — 2026-08-30 — Public REST executable-book contract sonucu

- **Durum:** `ACTIVE`
- **Karar:** Point-in-time book snapshot; exchange timestamp, request/receipt UTC, raw checksum, book hash, asset identity, current dynamic tick ve iki tarafın tüm seviyelerini taşıyacak. One-sided/empty book'ta spread veya midpoint üretilmeyecek.
- **Ölçülen kanıt:** Panama City, Mexico City ve Toronto'daki 66 Yes/No token için 66/66 public `/book` ve tick-size snapshot başarılı. 48 two-sided, 18 one-sided, 0 empty/crossed; 1.914 bid + 1.914 ask seviye doğrulandı. Median REST latency 147,9 ms; two-sided median spread 0,020.
- **Invalidation:** İlk koşudaki 190 tick violation Gamma statik tick'i current değer sanan yanlış contract'tan kaynaklandı. Dynamic `/tick-size/{token_id}` ile v2'de ihlal 0; 8/66 token Gamma metadata'dan farklı current tick taşıdı.
- **Artifact:** `reports/data_quality/EXP-20260830-phase3-rest-orderbook-contract.md`, `reports/data_quality/EXP-20260830-phase3-rest-book-coverage.json`
- **Sonuç:** REST substep geçti; Phase 3 `IN_PROGRESS`. WebSocket/reconnect ve 24 saat stability gate'i henüz geçmedi.

### D-0018 — 2026-08-30 — Public WebSocket forced-reconnect sonucu

- **Durum:** `ACTIVE`
- **Karar:** Her bağlantı kendi authoritative full-book başlangıcını almak zorunda; önceki bağlantının state'i yeni bağlantıda kullanılamaz. Asset full book gelmeden görülen delta uygulanmayacak ve kalite ihlali olarak sayılacak.
- **Önceden yazılan eşik:** İki token için her iki bağlantıda full book; reconnect ≤15 saniye; reconnect'te base öncesi delta 0; fresh REST ile aynı hash veya aynı executable best bid/ask.
- **Ölçülen kanıt:** Aynı Mexico City marketinin Yes/No token'ları connection-1'de 0,416 saniye, forced reconnect sonrasında connection-2'de 0,341 saniyede full book aldı. Base öncesi delta 0; REST/WebSocket hash ve top-of-book eşleşmesi 2/2.
- **Sınır:** Kısa koşuda yalnız initial `book` görüldü; canlı `price_change`/`tick_size_change`, heartbeat ve uzun süreli gap/stale davranışı henüz kanıtlanmadı.
- **Artifact:** `reports/data_quality/EXP-20260830-phase3-websocket-recovery.md`, `reports/data_quality/EXP-20260830-phase3-websocket-recovery.json`
- **Sonuç:** Forced-reconnect substep geçti; Phase 3 `IN_PROGRESS`. Delta replay shakeout ve 24 saat stability gate'i bekliyor.

### D-0019 — 2026-08-30 — WebSocket heartbeat/delta shakeout sonucu

- **Durum:** `ACTIVE`
- **Karar:** Prospective state modeli full book + sıralı price delta + dynamic tick state olacak. Bir event içindeki değişiklikler atomik uygulanıp event-advertised best bid/ask sonrasında kontrol edilecek; size `0` seviyesi silinecek.
- **Önceden yazılan eşik:** 35 saniye/12 two-sided token; full-book %100; ≥3 PING, ≥2 PONG, ≥1 applied change; base öncesi delta ve advertised-top mismatch 0; REST hash-or-top match ≥%90.
- **Ölçülen kanıt:** 12/12 full book, 3/3 heartbeat/PONG, 39 price-change event ve 78 applied level change. Base öncesi delta 0, advertised-top mismatch 0; final REST hash ve top-of-book eşleşmesi 12/12. 43 raw frame checksum'u doğrulandı; median/maksimum inter-frame gap 0,0435/4,9662 saniye.
- **Sınır:** 35 saniye uptime/retention kanıtı değildir; tick-size-change gözlenmedi. 24 saat runner reconnect/backoff, periodic REST anchor, stale/gap ve storage metriklerini ölçmeli.
- **Artifact:** `reports/data_quality/EXP-20260830-phase3-websocket-shakeout.md`, `reports/data_quality/EXP-20260830-phase3-websocket-shakeout-v1.json`
- **Sonuç:** Bounded shakeout geçti; Phase 3 `IN_PROGRESS`. 24 saat stability gate'i bekliyor.

### D-0020 — 2026-08-30 — Stability runner readiness sonucu

- **Durum:** `ACTIVE`
- **Karar:** 24 saat gate metrikleri kilitlendi: useful uptime = tüm asset base'leri hazır saniye/wall time; coverage = tüm asset'lerin hazır olduğu 60 saniyelik checkpoint oranı. Gate sırasıyla ≥%99 ve ≥%95; minimum süre 86.400 saniye değişmez.
- **Ölçülen kanıt:** 25 saniyelik smoke'ta 12/12 base, 36 delta event/72 change, 2 PING/PONG, 4/4 ready checkpoint ve 24/24 REST anchor match; sıfır contract/connection error. Ayrı koşu process ortasında kesilip aynı start/end ile connection-2 üzerinden 12 fresh base alarak resume edildi.
- **Sınır:** Hard termination son checkpoint'ten sonraki aggregate sayaçları kaybedebilir; 60 saniyelik production checkpoint ile kayıp üst sınırı yaklaşık bir intervaldir. Flush edilmiş raw frameler korunur.
- **Artifact:** `reports/data_quality/EXP-20260830-phase3-stability-runner-smoke.md`
- **Sonuç:** Runner readiness geçti; Phase 3 `IN_PROGRESS`. Sıradaki adım production 24 saat capture'ı başlatmaktır.

### D-0021 — 2026-08-30 — Production 24 saat stability capture başlatıldı

- **Durum:** `ACTIVE`
- **Karar:** `run=20260830T1145Z-phase3-stability-24h-v1`, 12 asset, 86.400 saniye, 60 saniye checkpoint, 300 saniye REST anchor, 15 saniye base timeout ve maksimum 30 saniye exponential backoff ile başlatıldı. Gate koşu tamamlanmadan değerlendirilmeyecek.
- **İlk checkpoint:** Start `2026-08-30T11:44:58Z`, target end `2026-08-31T11:44:58Z`. İlk 60 saniyede useful uptime %99,4699, ready checkpoint 1/1, 82 price-change event/164 applied change, 5 PING/PONG, 0 reconnect/error/base/top ihlali.
- **Henüz bilinmeyen:** İlk REST anchor 300. saniyede; 24 saat uptime, coverage, gap, storage ve final anchor oranı henüz ölçülmedi.
- **Local artifact:** `data/raw/polymarket_ws/run=20260830T1145Z-phase3-stability-24h-v1`, `data/interim/polymarket_ws/stability-24h-v1.json` (git-ignore; raw veri commitlenmeyecek).
- **Sonuç:** Capture `RUNNING`; Phase 3 `IN_PROGRESS` ve gate sonucu bekleniyor.

### D-0022 — 2026-08-30 — NBM/KORD ilk as-issued archive sonucu

- **Durum:** `ACTIVE`
- **Karar:** NBM yalnız verified KORD/Chicago için aday baseline; cycle dataset anahtarının zorunlu parçası. `model_run_time`, object `Last-Modified`, historical unknown `first_seen_at` ve local ingestion zamanı ayrı tutulacak.
- **Önceden yazılan eşik:** Güncel ve ≥365 gün eski gerçek dosya indirilecek; KORD bloğunda mean/SD ve 10/25/50/75/90 QMD MaxT-MinT marker'ları, checksum ve run identity doğrulanacak.
- **Ölçülen kanıt:** 2026-08-30 ve 2023-08-31 01Z NBP dosyaları (1.095 gün aralık) HTTP 200 ile 34.724.488/34.806.674 byte indirildi; SHA-256 yeniden doğrulandı. KORD blokları NBM v5.0/v4.1 ve gerekli yedi marker'ın tamamını birer kez içeriyor.
- **Invalidation:** İlk 00Z karşılaştırmasında 2023 KORD sıcaklık marker'ı yoktu; bu archive yokluğu değil cycle-availability farkıydı. Matched 01Z karşılaştırması iki tarihte de geçti.
- **Sınır:** İki tarih continuous daily coverage, earliest retention veya historical first-publication kanıtı değildir; NBM mevcut retained evrende yalnız Chicago'ya doğrudan uygulanır.
- **Artifact:** `reports/research/EXP-20260830-phase4-nbm-initial-feasibility.md`, `reports/data_quality/EXP-20260830-phase4-nbm-archive-probe-cycle01-v2-analysis.json`
- **Sonuç:** NBM initial spike `CONDITIONAL_PASS`; experiment Phase 4 `IN_PROGRESS`.

### D-0023 — 2026-08-30 — NBM sampled coverage ve KORD parser sonucu

- **Durum:** `ACTIVE`
- **Karar:** NBM KORD records `run_date+cycle+product+version` ile key edilecek; MaxT valid time run+forecast-hour olarak üretilecek. Alternatif cycle sessizce doldurulmayacak ve kendi availability zamanıyla flag'lenecek.
- **Ölçülen kanıt:** 2023-08–2026-08 arası 37 month-start + 12 model-boundary olmak üzere 49 unique 01Z obje kontrolünde 48 HTTP 200 (%97,959), boundary 12/12. Tek eksik `2026-06-01 01Z`; aynı gün 00/07/13/19Z ve komşu 01Z objeleri mevcut.
- **Parser sonucu:** İki checksum'lı KORD dosyasından 9+9 MaxT record, 0 missing value; run, FHR 23–215, valid UTC, mean/SD ve monotonic 10/25/50/75/90 percentilleri provenance ile üretildi. 43 test geçti.
- **Maliyet:** Ortalama full bulletin 34.796.159 byte; tek 01Z full raw/gün yaklaşık 12,70 GB/yıl.
- **Sınır:** %97,959 sampled coverage günlük coverage değildir; valid UTC henüz Chicago contract local-date/window semantiğiyle reconcile edilmedi.
- **Artifact:** `reports/research/EXP-20260830-phase4-nbm-coverage-parser.md`, `reports/data_quality/EXP-20260830-phase4-nbm-monthly-boundary-coverage.json`, `reports/data_quality/EXP-20260830-phase4-nbm-kord-parsed-sample.json`
- **Sonuç:** Sampled coverage/parser substep geçti; NBM source `CONDITIONAL_PASS`, Phase 4 `IN_PROGRESS`.

### D-0024 — 2026-08-30 — NBM 365 günlük coverage ve KORD run policy

- **Durum:** `ACTIVE`
- **Karar:** KORD canonical cycle policy `01Z → 07Z → 13Z → 19Z`; fallback ayrı information set'tir, gerçek run/availability timestamp'i korunur ve yalnız market snapshot'tan önce available ise kullanılabilir. Daha sonraki fallback ile eski karar zamanı doldurulamaz.
- **Önceden yazılan gate:** Locked 365 gün; primary ≥%99, cascade policy %100, transient failure 0; kullanılan fallback gerçek dosya download/checksum/KORD parse geçmeli.
- **Ölçülen kanıt:** 2025-08-30–2026-08-29: primary 364/365 (%99,726), fallback 1, unavailable 0, policy %100, transient failure 0. `2026-06-01 07Z` 34.712.943 byte indirildi, SHA-256 doğrulandı ve 9 KORD MaxT record/0 missing üretti.
- **Look-ahead sınırı:** Fallback object Last-Modified `08:15:34Z`; bu run daha erken market snapshot'larında kullanılamaz. Primary/fallback skorları ayrı raporlanacak.
- **Artifact:** `reports/research/EXP-20260830-phase4-nbm-daily-policy.md`, `reports/data_quality/EXP-20260830-phase4-nbm-daily-coverage-365d.json`, `reports/data_quality/EXP-20260830-phase4-nbm-fallback-kord-parsed.json`
- **Sonuç:** 365 günlük policy substep geçti; NBM/KORD `CONDITIONAL_PASS`, Phase 4 `IN_PROGRESS`.

### D-0025 — 2026-08-30 — ECMWF Open Data gerçek ensemble ve retention sonucu

- **Durum:** `ACTIVE`
- **Karar:** ECMWF Open Data global prospective forecast kaynağı olarak `CONDITIONAL_PASS`, doğrudan historical backtest kaynağı olarak `FAILED`. Reanalysis veya bugünkü forecast eski as-issued run yerine kullanılmayacak.
- **Önceden yazılan gate:** `2t/mx2t3/mn2t3`; deterministic 1'er, perturbed ensemble 50'şer ve tam member 1–50; GRIB bütünlüğü; historical kullanım için ≥365 gün retention.
- **Ölçülen kanıt:** 2026-08-30 00Z step-24 deterministic subset 3 mesaj/1.941.310 byte, perturbed subset 150 mesaj/97.501.524 byte; tam 1–50 member ve geçerli checksum/GRIB sınırları. Control `cf` gerçek indexte yok. −0/−1/−2 gün HTTP 200; −3/−4/−7/−30/−365 gün HTTP 404.
- **Gate:** Current fields/member yapısı geçti; control ve 365 günlük retention geçmedi. Açık yüzeyden retrospective ECMWF dataset kurulamaz.
- **Artifact:** `reports/research/EXP-20260830-phase4-ecmwf-open-data.md`, `reports/data_quality/EXP-20260830-phase4-ecmwf-open-data-probe.json`
- **Sonuç:** Phase 4 `IN_PROGRESS`; global historical ensemble için sıradaki kaynak GEFS archive ölçümüdür.

### D-0026 — 2026-08-30 — GEFS operasyonel archive ilk fizibilite sonucu

- **Durum:** `ACTIVE`
- **Karar:** GEFS operational public archive, global historical as-issued ensemble kaynağı olarak `CONDITIONAL_PASS`; reforecast/replay operasyonel geçmiş yerine kullanılmayacak.
- **Önceden yazılan gate:** Güncel ve ≥365 gün eski run; 31/31 control+perturbed üye; her üyede 2 m `TMP/TMAX/TMIN`; temsilî gerçek range download, GRIB bütünlüğü ve checksum.
- **Ölçülen kanıt:** 2026-08-30, 2025-08-30 ve 2020-09-24 00Z f024 run'larının her birinde 31/31 tam üye ve üç alan bulundu. c00/p01/p30 için 9 gerçek subset/27 GRIB mesajı HTTP 206 ve bütünlük kontrolünden geçti. En eski örnek 2.166 gün; full-member availability run+3,91–4,45 saat.
- **Hacim:** Tek f024 üç-alan range toplamı run başına 54,31–65,18 MB; full objeler 464,69–577,68 MB.
- **Sınır:** Üç tarih continuous daily coverage değildir; local-day TMAX çoklu-step sözleşmesi ve version boundary henüz doğrulanmadı.
- **Artifact:** `reports/research/EXP-20260830-phase4-gefs-initial-feasibility.md`, `reports/data_quality/EXP-20260830-phase4-gefs-operational-archive-probe.json`
- **Sonuç:** Phase 4 `IN_PROGRESS`; sıradaki gate kilitli 365 günlük GEFS coverage ve local-day step semantiğidir.

### D-0027 — 2026-08-31 — Phase 3 host-sleep kontaminasyonu ve raw replay

- **Durum:** `ACTIVE`
- **Karar:** İlk 24 saat koşusu stability gate'e uygun değildir; `HOST_SLEEP_CONTAMINATED_INTERRUPTED` olarak korunur ve yalnız failure diagnosis için kullanılır.
- **Ölçülen kanıt:** 37.015 saniyede useful uptime `%82,14`; macOS power log çoklu gerçek sleep aralığı doğruladı. Raw replay 27 connection/69.461 frame ve 16.936 advertised-top mismatch buldu; Toronto 11.394, Panama City 5.542, Mexico City 0.
- **Ayrım:** Host sleep uptime/reconnect'i açıklar fakat mismatch'i tamamen açıklamaz. REST anchor match `%99,789`; event-level protocol/state veya gap handling ayrıca düzeltilmeli. Son reconnect'lerde yalnız 6/12 full book, fixed asset lifecycle riskini gösterdi.
- **Metrik hatası:** Ready-checkpoint oranı kaçırılan wall-clock slotlarını paydaya eklemediği için yukarı yönlü yanlıdır.
- **Artifact:** `reports/data_quality/EXP-20260830-phase3-stability-host-sleep-analysis.md`, `reports/data_quality/EXP-20260830-phase3-stability-host-sleep-analysis.json`
- **Sonuç:** Phase 3 `IN_PROGRESS`; collector düzeltmesi → 15 dakika regression → 1 saat caffeinated soak → yeni 24 saat gate sırası kilitlendi.

### D-0028 — 2026-08-31 — Collector remediation 15 dakika regression sonucu

- **Durum:** `ACTIVE`
- **Karar:** Wall-clock checkpoint, lifecycle horizon, non-blocking anchor ve fail-closed desync düzeltmeleri 15 dakika v3 regression gate'ini geçti; Phase 3 henüz geçmedi.
- **Invalidation:** İlk v2 sonucu 900 saniyede final boundary slotunu saymadığı için 14 checkpoint üretti; post-hoc kabul edilmedi. Final slot düzeltildikten sonra v3 sıfırdan çalıştırıldı.
- **Ölçülen kanıt:** v3 elapsed 900,068 sn; useful uptime `%99,9592`; 15/15 ready slot, 0 missed; 12/12 full book; 785 price event/1.570 change; 0 reconnect/error/delta-before-book/mismatch; 24/24 REST anchor; 89/89 heartbeat/PONG.
- **Artifact:** `reports/data_quality/EXP-20260831-phase3-collector-regression-15m.md`; local raw/interim run `run=20260830T2224Z-phase3-regression-15m-v3`.
- **Sonuç:** Regression `PASSED`; sıradaki gate aynı kodla 1 saatlik `caffeinate` soak.

### D-0029 — 2026-08-31 — Remediated collector 1 saat soak sonucu

- **Durum:** `ACTIVE`
- **Karar:** 1 saat transport/state soak `PASSED_WITH_ACTIVITY_LIMITATION`; 15 dakika aktif-delta regression ile birlikte replacement 24 saat gate başlatılabilir. Phase 3 henüz geçmedi.
- **Ölçülen kanıt:** 3.600,069 sn; useful uptime `%99,9915`; 60/60 ready, 0 missed; 1 connection, 0 error/reconnect; 12/12 full book; 132/132 REST anchor; 359/359 heartbeat/PONG; 0 base/mismatch.
- **Faaliyet sınırı:** Soak boyunca 0 price-change gözlendi. Delta replay kanıtı önceki v3 regression'daki 785 event/1.570 applied change ve 24/24 anchor sonucundan gelir; iki koşu birlikte yorumlanır.
- **Artifact:** `reports/data_quality/EXP-20260831-phase3-collector-soak-1h.md`; local raw/interim `run=20260831T0045Z-phase3-soak-1h-v1`.
- **Sonuç:** Soak subgate geçti; sıradaki adım remediated 24 saat `caffeinate` capture.

### D-0030 — 2026-08-31 — Remediated replacement 24 saat capture başlatıldı

- **Durum:** `ACTIVE`
- **Karar:** `run=20260831T0820Z-phase3-stability-24h-v2`, 12 lifecycle-safe asset, 86.400 saniye, 60 saniye wall-clock slot, 300 saniye non-blocking REST anchor ve fail-closed desync ile `caffeinate` altında başlatıldı.
- **Horizon:** Start `2026-08-31T08:15:51Z`, target end `2026-09-01T08:15:51Z`; seçili market end `2026-09-01T12:00:00Z`, dolayısıyla target'tan 3 saat 44 dakika sonra.
- **İlk kanıt:** 360 saniyede useful uptime `%99,9057`; 6/6 ready, 0 missed; 12/12 full base; 1 REST anchor/12 asset ve 12/12 match; 0 error/reconnect/base/mismatch.
- **Faaliyet:** İlk 6 dakikada price-change yok; activity final raporda ayrı gate/limitation olarak gösterilecek.
- **Local artifact:** `data/raw/polymarket_ws/run=20260831T0820Z-phase3-stability-24h-v2`, `data/interim/polymarket_ws/stability-24h-v2.json`.
- **Sonuç:** Capture `RUNNING`; Phase 3 `IN_PROGRESS`, final gate target end'den önce değerlendirilmeyecek.

### D-0031 — 2026-08-31 — Replacement v2 internet kesintisi sonucu

- **Durum:** `ACTIVE`
- **Karar:** v2 `NETWORK_OUTAGE_CONTAMINATED_INTERRUPTED`; stability gate'e dahil edilmeyecek. 117 reconnect storm nedeniyle gereksiz endpoint yükünü önlemek için kontrollü durduruldu.
- **Ölçülen kanıt:** 11.463 sn; useful uptime `%91,4008`; 174/190 ready, 13 missed; 117 attempt/116 error/117 reconnect; 160 mismatch. Error log `gaierror` ile yerel DNS/internet kesintisini doğruladı. REST anchor 408/408 kaldı.
- **Yeni failure mode:** Bağlantı kurulunca backoff hemen 1 saniyeye resetlendiği için kısa ömürlü desync bağlantıları reconnect storm yarattı. Network ve protocol-desync sayaçları ayrılmalı, stable-grace/circuit-breaker eklenmeli.
- **Artifact:** `reports/data_quality/EXP-20260831-phase3-network-outage-v2.md`; local raw/interim `run=20260831T0820Z-phase3-stability-24h-v2`.
- **Sonuç:** Phase 3 `IN_PROGRESS`; yeni 24 saatten önce recovery/backoff remediation ve forced-disconnect regression gerekir.

### D-0032 — 2026-08-31 — 24 saat gate managed host'a ertelendi

- **Durum:** `ACTIVE`
- **Karar:** Registered 24 saat Phase 3 kriteri silinmedi, gevşetilmedi ve geçmiş kısa koşularla `PASSED` sayılmadı; ev laptopu/internetinden bağımsız always-on managed host veya VPS aşamasına `DEFERRED_UNTIL_MANAGED_HOST` olarak ertelendi.
- **Gerekçe:** İki uzun deneme collector'dan bağımsız host sleep ve yerel network outage ile kontamine oldu. 15 dakika aktif-delta regression ve 1 saat persistence soak kısa sözleşmeleri geçti; tekrar ev ortamında 24 saat çalıştırmanın incremental bilgi değeri düşüktür.
- **Sınır:** Phase 3 `IN_PROGRESS`; historical executable L2/backtest veya live readiness iddiası yok. Recovery/backoff düzeltmesi kısa deterministic testlerle daha sonra devam eder.
- **Sonuç:** Ana araştırma hattı Phase 4 GEFS coverage'a döner; 24 saat gate paper/live altyapıdan önce managed host'ta zorunludur.

### D-0033 — 2026-08-31 — GEFS 365 günlük temsilî continuity gate geçti

- **Durum:** `ACTIVE`
- **Karar:** GEFS 365 günlük representative-member continuity alt-gate'i `PASSED`; provider genel statüsü local-day ve full-member sınırları nedeniyle `CONDITIONAL_PASS` kalır.
- **Önceden yazılan gate:** 2025-08-31–2026-08-30, 00Z f024, c00/p01/p30; 1.095 indeksin ≥%99'u exact 2 m TMP/TMAX/TMIN ve retry sonrası terminal transport failure 0.
- **Ölçülen kanıt:** 365/365 tam gün, 1.095/1.095 tam indeks (%100), tümü HTTP 200 ve exact 1/1/1 alan. 1.092 ilk denemede, 3 ikinci denemede geçti; transient error 3, terminal failure 0, missing date 0.
- **Sınır:** Üç temsilî üye 31/31 günlük tamlığı kanıtlamaz; f024 varlığı yerel-gün MaxT step semantiğini çözmez.
- **Artifact:** `reports/research/EXP-20260831-phase4-gefs-daily-coverage.md`, `reports/data_quality/EXP-20260831-phase4-gefs-daily-coverage-365d.json`
- **Sonuç:** Phase 4 `IN_PROGRESS`; sıradaki gate DST ve non-DST şehirlerde leakage-safe local-day step sözleşmesidir.

### D-0034 — 2026-08-31 — GEFS local-day semantik gate ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** GEFS 2 m TMAX index metadata'sı ardışık 3 saatlik UTC pencereleri doğru tanımlar; bu pencereler Toronto/CYYZ ve Kuala Lumpur/WMKK yerel günleri için dış saat eklemeden tam bir günlük MaxT feature'ına çevrilebilir.
- **Kilitli örnekler:** Toronto 2026-07-23 (`America/Toronto`, DST aktif) ve Kuala Lumpur 2026-06-22 (`Asia/Kuala_Lumpur`, DST yok); ikisi de Phase 2 `RECONCILED` registry kaydıdır.
- **Veri:** İlgili önceki/güncel 00Z control run'ların f003 adımlarıyla en az f048'e kadar gerçek index satırları; seçilen TMAX range'lerinde HTTP 206/GRIB bütünlüğü.
- **Gate A:** Kontrol edilen her f003 adımında exact bir 2 m TMAX ve metadata penceresi `(step-3)-step hour max fcst`; gap/overlap 0.
- **Gate B:** Her yerel gün için seçilen UTC pencerelerinin birleşimi local `[00:00, 24:00)` aralığına tam eşit; uncovered ve outside-local süre 0. DST günlerinde gerçek 23/25 saat korunur.
- **Fail-closed:** Gate B geçmezse interval TMAX label-equivalent günlük MaxT sayılmaz; sınır kontaminasyonu feature olarak açıkça işaretlenir ve exact-local-day alternatif sözleşmesi ayrıca sınanır.
- **Artifact hedefi:** `reports/data_quality/EXP-20260831-phase4-gefs-local-day-semantics.json` ve eşlik eden research raporu.

### D-0035 — 2026-08-31 — GEFS TMAX exact local-day gate başarısız

- **Durum:** `ACTIVE`
- **Karar:** GEFS interval TMAX resolution-equivalent günlük MaxT/label olarak kullanılamaz. Canonical 6h pencereler yalnız açık boundary-contamination taşıyan forecast feature'ları olabilir ve outcome kalibrasyonu geçmeden probability/EV girdisi sayılmaz.
- **Gate A:** `FAILED`. Gerçek metadata dönüşümlüdür: f003=`0-3h`, f006=`0-6h`, f009=`6-9h`, f012=`6-12h`; her f003 step bağımsız `(step-3)-step` değildir.
- **Düzeltici bulgu:** `f006,f012,...` canonical 6h serisi gap/overlap 0 ile ardışıktır.
- **Gate B:** `FAILED`. Toronto 04Z–04Z ve Kuala Lumpur 16Z–16Z local-day aralıkları 5'er 6h blokla tam kapsandı fakat her birinde 6 saat outside-local contamination oluştu.
- **Bütünlük:** 10/10 gerçek TMAX range, toplam 4.259.526 byte; HTTP 206, tek mesaj, GRIB/7777 sınırları geçti.
- **İzinli feature sözleşmesi:** Tamamen içerideki üç bloktan 18h interior feature ve dokunan beş bloktan contamination-tagged overlap feature; run/publish/interval provenance zorunlu.
- **Artifact:** `reports/research/EXP-20260831-phase4-gefs-local-day-semantics.md`, `reports/data_quality/EXP-20260831-phase4-gefs-local-day-semantics.json` ve superseded `-attempt1.json`.
- **Sonuç:** GEFS `CONDITIONAL_PASS`, Phase 4 `IN_PROGRESS`; sıradaki düzeltici deney CYYZ/WMKK observation feasibility ve bu feature politikalarının outcome calibration testidir.

### D-0036 — 2026-08-31 — Wunderground observation spike ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Polymarket'in exact resolution source'u olan Wunderground daily sayfaları CYYZ ve WMKK için en az 365 gün geriye parse edilebilir station/date/high ve saatlik observation kanıtı sunar.
- **Kilitli spike:** Her istasyonun reconciled market tarihinden geriye `0,1,7,30,60,90,120,150,180,240,300,364` gün; toplam 24 sayfa.
- **Gate:** 24/24 HTTP 200; station code/name, requested date, daily high ve en az bir observation satırı parse oranı %100; ikinci parse deterministik. Transport failure retry sonrası 0.
- **Scale policy:** Spike tam geçmeden 730 sayfalık 365×2 koşu yapılmaz. Eksik sayfa/alanlar archive missingness, parser drift ve transport olarak ayrılır.
- **Revision sınırı:** Bugün çekilen historical sayfa current/final görünümü kanıtlar, marketin next-day freeze anındaki değeri kanıtlamaz. Exact settlement-as-of için korunmuş historical snapshot veya prospective next-day capture gerekir.
- **Artifact hedefi:** `reports/data_quality/EXP-20260831-phase5-wunderground-observation-spike.json` ve research raporu.

### D-0037 — 2026-08-31 — Wunderground 24-date observation spike geçti

- **Durum:** `ACTIVE`
- **Karar:** CYYZ/WMKK Wunderground current/final observation yüzeyi 365×2 coverage ölçümüne ilerler; historical market-freeze-as-of statüsü ayrı ve çözülmemiş kalır.
- **Ölçülen kanıt:** 24/24 complete page, HTTP/identity/date/timezone/high/unit/observations/repeatability kontrollerinin tamamı 24/24, terminal failure 0 ve tümü ilk attempt'te başarı.
- **İç tutarlılık:** 24/24 daily high, parse edilen observation sıcaklık maksimumuna eşitti. CYYZ 24–41, WMKK 41–50 observation/gün; toplam HTML 1.344.540 byte.
- **Artifact:** `reports/research/EXP-20260831-phase5-wunderground-observation-spike.md`, `reports/data_quality/EXP-20260831-phase5-wunderground-observation-spike.json`; local raw `run=20260831T-phase5-spike-v1`.
- **Sonuç:** Phase 5 `IN_PROGRESS`; sıradaki gate kilitli iki 365 günlük current/final coverage ölçümüdür.

### D-0038 — 2026-08-31 — CYYZ/WMKK 365 günlük current/final observation gate geçti

- **Durum:** `SUPERSEDED_BY_D0041`
- **Karar:** Wunderground current/final daily outcome coverage CYYZ ve WMKK için `PASSED`; historical market-freeze-as-of settlement kanıtı hâlâ çözülmemiştir.
- **Ölçülen kanıt:** Her istasyonda 365/365 complete page (%100), identity 365/365, daily-high/observation-max 365/365, terminal failure 0. Altı transient istek ikinci attempt'te düzeldi.
- **Hacim:** 730 sayfa, toplam 41.178.264 byte. CYYZ daily high −13–36°C ve 2–60 observation/gün; WMKK 25–36°C ve 40–54 observation/gün.
- **Anomali:** CYYZ 2026-03-08 yalnız 2 observation içeriyor; daily high 9°C yine parsed max ile eşit. Ön-kayıtlı gate değişmeden geçti, fakat post-hoc diagnostic ile `SUBDAILY_INCOMPLETE_SUSPECTED`; CYYZ sub-daily diagnostic 364/365.
- **Artifact:** `reports/research/EXP-20260831-phase5-wunderground-observation-coverage-365d.md`, `reports/data_quality/EXP-20260831-phase5-wunderground-observation-coverage-365d.json`; local raw `run=20260831T-phase5-coverage-365d-v1`.
- **Sonuç:** Phase 5 `IN_PROGRESS`; CYYZ anomalisi ve üçüncü şehir/settlement join'i sıradadır.

### D-0039 — 2026-08-31 — CYYZ 2026-03-08 anomaly diagnostic ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Wunderground'ın iki satırlı CYYZ sayfası sub-daily eksiktir fakat 9°C daily high, exact Toronto Pearson istasyonunun resmî ECCC local-calendar-day saatlik maksimumuyla tutarlıdır.
- **Kaynak:** ECCC `climate-hourly` OGC API, `TORONTO INTL A`, climate identifier `6158731`; Wunderground immutable raw page; 8.222-event Polymarket closed raw inventory.
- **Gate:** Local date 2026-03-08 için DST nedeniyle exact 23 unique hourly row, 23 non-null TEMP, station/coordinate identity, raw maximumun half-up whole °C değeri 9 ve Wunderground daily high ile eşleşme.
- **Settlement kontrolü:** Exact Toronto/date event count raporlanır. Event yoksa settlement `NOT_APPLICABLE`, başarı diye sayılmaz.
- **Zaman sözleşmesi:** ECCC daily aggregate kullanılmaz; resmî climatological-day boundary local calendar day ile farklı olabileceğinden yalnız hourly `LOCAL_DATE` filtrelenir.
- **Artifact hedefi:** `reports/data_quality/EXP-20260831-phase5-cyyz-20260308-anomaly.json` ve research raporu.

### D-0040 — 2026-08-31 — CYYZ anomaly diagnostic v1 başarısız ve settlement bulundu

- **Durum:** `ACTIVE`
- **Sonuç:** Ön-kayıtlı diagnostic `FAILED`: ECCC `LOCAL_DATE` 24 sıra ve 0–23 saat üretti, beklenen civil-DST 23 saatini vermedi; max 12,1°C ve half-up değeri Wunderground 9°C ile eşleşmedi.
- **Settlement bulgusu:** Önceki text araması yanlıştı; structured 8.222-event taraması exact event `249630` buldu. Terminal winner `10°C or higher`; dolayısıyla bugünkü Wunderground 9°C sayfasıyla settlement çelişiyor.
- **Yorum:** ECCC `LOCAL_DATE` alanı civil IANA DST günü varsayımıyla kullanılamaz. Corrective v2, UTC_DATE değerlerini `America/Toronto` civil `[00:00,next 00:00)` sınırlarıyla filtreleyecek ve winner bucket'ı artifact'a çıkaracak.
- **Gate değişikliği yok:** v1 `FAILED` olarak korunur. v2 yeni bir forensic correction'dır; ilk gate'i geçmiş saymaz.
- **Artifact:** `reports/data_quality/EXP-20260831-phase5-cyyz-20260308-anomaly-attempt1.json`.
- **Sonuç:** D-0038'in “current/final calibration label” yorumu bu tarih için yanlışlandı; corrective v2 sonrasında CYYZ label policy daraltılacaktır.

### D-0041 — 2026-08-31 — Wunderground historical page settlement'tan ayrıştı

- **Durum:** `ACTIVE`
- **Karar:** Wunderground current historical page availability outcome-label validity değildir. Settlement bucket ile doğrulanmamış Wunderground daily high, training/backtest label olarak kullanılamaz.
- **Corrective kanıt:** IANA civil window ile ECCC 23/23 saat ve max 12,1°C; exact CYYZ kimliği/koordinatı geçti. Event 249630 terminal winner `10°C or higher` ECCC ile `MATCH`, bugünkü Wunderground 9°C ile `MISMATCH`.
- **Karantina:** `CYYZ 2026-03-08 = HISTORICAL_PAGE_DIVERGED_FROM_SETTLEMENT / NO_TRAIN_NO_BACKTEST`.
- **D-0038 düzeltmesi:** 365/365 page availability değişmez; CYYZ usable-label üst sınırı 364/365 (%99,726). WMKK label validity settlement audit yapılmadan bilinmez.
- **Artifact:** `reports/research/EXP-20260831-phase5-cyyz-20260308-anomaly.md`, final ve `-attempt1` JSON artifact'ları; local raw ECCC `run=20260831T-cyyz-anomaly-v2`.
- **Sonuç:** Phase 5 `IN_PROGRESS`; fixed ≥10 event/≥3 city settlement divergence audit zorunludur.

### D-0042 — 2026-08-31 — Fixed settlement-divergence audit ön-kaydı

- **Durum:** `ACTIVE`
- **Cohort:** Önceden kilitli 20-event Phase 1 stratified sample + CYYZ event 249630 anomaly sentinel; yeni sonuç-seçilmiş örnek yok.
- **Eligibility:** Exact terminal winner, identity match ve parse edilmiş Wunderground daily high birlikte zorunlu. Diğer kayıtlar denominator'a eklenmez, `INELIGIBLE` nedeni ile korunur.
- **Metrikler:** Eligible/match/diverged/ineligible event ve unique-city sayıları, divergence oranı + Wilson %95 CI, event-level evidence class ve quarantine disposition.
- **Gate:** Sample observation-settlement subgate için ≥10 `MATCH`, ≥3 şehir ve tüm divergence'larda explicit `NO_TRAIN_NO_BACKTEST`; unresolved eligible record 0.
- **Sınır:** MATCH current-page/bucket consistency gösterir, freeze-time snapshot kanıtı değildir. DIVERGED kayıt label olarak kullanılamaz.
- **Artifact hedefi:** `reports/data_quality/EXP-20260831-phase5-wunderground-settlement-audit.json` ve research raporu.

### D-0043 — 2026-08-31 — Fixed settlement audit geçti; exact-temperature label geçmedi

- **Durum:** `ACTIVE`
- **Primary sonuç:** Fixed 20-event sample'da 14 eligible event; 12 `MATCH`/12 şehir, 2 `MISMATCH`/2 şehir, 6 `INELIGIBLE`, unresolved eligible 0. Divergence 2/14 = %14,29; Wilson %95 CI %4,01–%39,94.
- **Sensitivity:** Anomaly-selected CYYZ sentinel dahil 3/15 divergence = %20,00; Wilson %95 CI %7,05–%45,19. Bu population estimate değildir.
- **Gate:** Ön-kayıtlı sample observation-settlement subgate `PASSED`; Dallas 493659, Munich 493666 ve sentinel Toronto 249630 ayrışmaları `NO_TRAIN_NO_BACKTEST` olarak karantinada.
- **Label ayrımı:** Eligible fixed sample eventlerin 14/14'ünde terminal Polymarket bucket label var. Preserved freeze-time snapshot bulunmadığı için exact-temperature label eligibility 0/14; sentinel dahil 0/15.
- **Karar:** Wunderground current historical page'in universal exact-temperature label kullanımı `FAILED`. Terminal Polymarket winner bucket, identifier/terminal durum doğrulandığında ayrı market-outcome hedefi olarak kullanılabilir.
- **Artifact:** Final audit JSON, iki superseded attempt JSON'u ve `reports/research/EXP-20260831-phase5-wunderground-settlement-audit.md`.
- **Sonuç:** Phase 5 `IN_PROGRESS`; sample alt-gate geçti fakat üçüncü şehir 365 günlük observation/revision kanıtı ve freeze-time exact-temperature semantiği çözülmedi.

### D-0044 — 2026-08-31 — KORD/LCDv2 365 günlük observation paketi ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** NOAA NCEI LCDv2, KORD ile aynı O'Hare istasyonunu temsil eden `USW00094846` kaydında 2025-08-31–2026-08-30 arasındaki 365 tamamlanmış Chicago local date için bağımsız daily maximum observation coverage sağlayabilir ve event 553903 terminal bucket'ıyla yönsel bir forensic kontrol üretir.
- **Primary kaynak:** NOAA NCEI LCDv2 yıllık CSV'leri `LCD_USW00094846_<YYYY>.csv`; station identity KORD/O'Hare, WBAN 94846, koordinat ve isimle doğrulanacak. Kaynak URL, response Last-Modified/ETag, retrieval time, byte count ve SHA-256 saklanacak.
- **Resolution contract:** Event 553903'ün gerçek settlement kaynağı Wunderground KORD, `America/Chicago` local calendar day, whole °F ve ilk sonraki-gün datapoint freeze kuralıdır. LCDv2 bağımsız diagnostic kaynaktır; Wunderground yerine geçirilmez.
- **Coverage gate:** Kilitli 365 tarihin tamamı temsil edilmeli; exact date coverage ≥%99, non-null daily maximum ≥%99, duplicate daily summary 0, station/name/coordinate identity %100 ve terminal transport failure 0. Missing/duplicate/flagged değerler ayrı raporlanacak, impute edilmeyecek.
- **Semantik gate:** LCDv2 daily-summary alanı, birimi, report type ve source documentation kaydedilecek. NOAA'nın günlük pencere/finalization semantiği Wunderground freeze kuralıyla eşit kanıtlanamazsa `INDEPENDENT_FINAL_DIAGNOSTIC_ONLY`; exact settlement label statüsü verilmeyecek.
- **Settlement kontrolü:** Exact event 553903, date 2026-06-05 ve terminal winner `68°F or higher` sabit sentinel'dir. LCDv2 maximum, Wunderground current high ve terminal bucket ayrı saklanacak. Tek event Phase 5 sample gate'ini tekrar geçirmez.
- **Revision gate:** Historical as-of version reconstruction, yalnız annual object Last-Modified ile kanıtlanmış sayılmaz. Immutable eski snapshot/version history yoksa `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`; prospective snapshot gerekecek.
- **Artifact hedefi:** `reports/data_quality/EXP-20260831-phase5-kord-lcdv2-observation-coverage.json` ve `reports/research/EXP-20260831-phase5-kord-lcdv2-observation-coverage.md`.

### D-0045 — 2026-08-31 — KORD/LCDv2 latest-365 coverage publication lag nedeniyle başarısız

- **Durum:** `ACTIVE`
- **Gate sonucu:** `FAILED`; 2025-08-31–2026-08-30 aralığında 356/365 date ve non-null daily maximum = %97,534; ön-kayıtlı ≥%99 eşiğinin altında. Duplicate 0, identity failure 0, terminal transport failure 0.
- **Missingness:** Dokuz ardışık tarih `2026-08-22`–`2026-08-30`. 2026 annual object Last-Modified 2026-08-26 iken son SOD 2026-08-21; current product publication lag'iyle tutarlı.
- **Sentinel:** Event 553903 için LCDv2 27,2°C = 80,96°F, current WU 27°C ve terminal `68°F or higher` bucket yönsel olarak tutarlı; statü yalnız `FORENSIC_CONSISTENCY_ONLY`.
- **Semantik karar:** LCDv2 `INDEPENDENT_FINAL_DIAGNOSTIC_ONLY`; Wunderground yerine settlement label değildir. Annual-object Last-Modified historical version kanıtı olmadığından `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`.
- **Kalite:** KORD/GHCN `USW00094846` identity %100; admitted 356 daily maximum −15,0–35,6°C; imputation yok. 69 test geçti.
- **Artifact:** Final ve `-attempt1` JSON, research raporu; raw v2 `data/raw/noaa_lcdv2/run=20260831T-phase5-kord-lcdv2-v2`.
- **Sonuç:** Phase 5 `IN_PROGRESS`; third-city current/final diagnostic bulundu fakat locked latest-365 gate geçmedi ve freeze-as-of çözülmedi.

### D-0046 — 2026-08-31 — KORD/LCDv2 lag-safe final archive ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Latest-window failure trailing publication lag'den kaynaklanıyorsa, aynı KORD/LCDv2 contract'ı 40 günlük as-of buffer'lı sabit 2025-07-23–2026-07-22 penceresinde ≥%99 exact-date ve non-null daily maximum coverage sağlamalıdır.
- **Cohort:** 365 tarih; sonuç görüldükten sonra replacement date yok. Aynı `USW00094846`, SOD ve `DailyMaximumDryBulbTemperature` parser/identity contract'ı kullanılacak.
- **Gate:** Date coverage ≥%99, non-null maximum ≥%99, duplicate date 0, identity failure 0, terminal transport failure 0. İmputation ve provider mixing yok.
- **Publication-lag metriği:** Her annual object için observed Last-Modified ve dosyadaki son SOD tarihi saklanacak; 2026 object için calendar-day farkı bir publication-lag proxy olarak raporlanacak. Bu revision history değildir.
- **Interpretation:** Pass yalnız `FINAL_ARCHIVE_COVERAGE_PASS`; historical decision-time availability ve Wunderground freeze-as-of statüsü yine `UNRESOLVED`. Fail, LCDv2'nin final research label coverage'ını da zayıflatır.
- **Artifact hedefi:** `reports/data_quality/EXP-20260831-phase5-kord-lcdv2-lag-safe-coverage.json` ve research raporu.

### D-0047 — 2026-08-31 — KORD/LCDv2 lag-safe final archive coverage geçti

- **Durum:** `ACTIVE`
- **Gate sonucu:** `PASSED` yalnız final archive coverage için; 2025-07-23–2026-07-22 aralığında 365/365 exact date ve non-null daily maximum, duplicate 0, identity failure 0, terminal transport failure 0.
- **Değer aralığı:** −15,0–35,6°C; missing ve imputation yok.
- **Lag proxy:** Observed 2026 annual object Last-Modified 2026-08-26, son SOD 2026-08-21, fark 5 calendar day. 2025 annual object farkı 125 gün; bunlar per-row publication/revision timestamp değildir.
- **Karar:** KORD/LCDv2 `FINAL_ARCHIVE_COVERAGE_PASS` ve `INDEPENDENT_FINAL_DIAGNOSTIC_ONLY`. D-0045 latest-365 `FAILED` sonucu değişmez.
- **Sınır:** `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`; final archive pass, settlement veya karar anında erişilebilirlik kanıtı değildir.
- **Kalite:** 69 test ve Ruff geçti; artifact ile local immutable raw `run=20260831T-phase5-kord-lcdv2-lag-safe-v1` saklandı.
- **Sonuç:** Phase 5 `IN_PROGRESS`; third-city final observation coverage var, prospective freeze snapshot contract'ı yok.

### D-0048 — 2026-09-02 — Prospective Wunderground freeze snapshot contract ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** KORD için target-date sayfası ve following-date sayfasının ilk non-empty observation durumu aynı capture içinde saklanırsa, freeze eligibility sonradan deterministik replay edilebilir; duplicate capture overwrite yaratmaz ve değişmiş içerik yeni immutable version olur.
- **Fixture scope:** Sentetik KORD target `2026-09-01`, following date `2026-09-02`, `America/Chicago`, whole °F ve versioned rule/event kimliği. Bu fixture gerçek settlement kanıtı değildir.
- **Qualification:** Target ve trigger HTTP 200/raw mevcut; iki sayfada KORD/name/timezone/date identity exact; target daily high + expected F unit mevcut; following page observation count ≥1; capture zamanı following local midnight'dan önce değil; raw SHA-256 ve rule hash mevcut. Herhangi biri yoksa fail closed `NOT_FREEZE_ELIGIBLE`.
- **Append-only contract:** Raw target/trigger bytes content-addressed saklanacak; manifest canonical capture ID, requested/received timestamps, event/date/rule version, parser version, checks, parsed values ve iki checksum taşıyacak. Mevcut dosya farklı byte ile overwrite edilemez.
- **Idempotency/revision:** Aynı canonical payload ikinci kez yazıldığında yeni kayıt üretmeden aynı snapshot kimliği dönmeli. Farklı checksum aynı event/date için yeni revision olarak eklenmeli; önceki revision silinmemeli.
- **Test gate:** Valid fixture qualify; pre-midnight, missing trigger observation, identity/date/unit/rule-hash mismatch fail closed; byte tamper checksum verification'ı bozmalı; replay aynı normalized manifest'i üretmeli; duplicate idempotent ve changed-content append testleri geçmeli. Ruff + tüm test suite zorunlu.
- **Sınır:** Fixture gate'i collector uptime veya canlı Wunderground davranışını kanıtlamaz. Persistent collector bu adımda başlatılmayacak.
- **Artifact hedefi:** `reports/data_quality/EXP-20260902-phase5-wunderground-freeze-snapshot-contract.json` ve research raporu.

### D-0049 — 2026-09-02 — Prospective freeze snapshot fixture contract geçti

- **Durum:** `ACTIVE`
- **Gate sonucu:** `PASSED`; 12/12 fixture/replay/idempotency/fail-closed case geçti. Geçerli target+trigger bundle qualify; pre-midnight, empty trigger, station/unit/rule hash mismatch fail closed.
- **Immutable davranış:** İlk write append, duplicate aynı snapshot ID ile idempotent, değişmiş target content ikinci revision, byte tamper checksum failure üretti.
- **Evidence:** Target/trigger raw SHA-256, event/date/rule/parser versions, requested/received/capture timestamps, parsed identity/high/observation ve qualification checks canonical manifest'te.
- **Kalite:** Ruff ve 76 test geçti. Artifact `reports/data_quality/EXP-20260902-phase5-wunderground-freeze-snapshot-contract.json`; research raporu kaydedildi.
- **Sınır:** Fixture synthetic; live Wunderground davranışı, uptime veya geçmiş settlement kanıtı değildir. Persistent collector başlatılmadı.
- **Sonuç:** Phase 5 `IN_PROGRESS`; storage contract hazır, ilk uygun canlı KORD event/capture cohort'u seçilmedi.

### D-0050 — 2026-09-02 — Upcoming exact-rule KORD event discovery ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Public Gamma `highest-temperature`, `closed=false` keyset inventory'sinde observed-at anından sonra biten, active/not-closed, Chicago title'lı ve exact Wunderground `/KORD` next-day-first-datapoint rule taşıyan en az bir event bulunabilir.
- **Universe:** Tek complete keyset traversal; raw response envelope'ları checksum ve requested/received timestamp ile immutable local raw run'da saklanacak. Broad weather tag veya closed inventory outcome-seçimli ikame değildir.
- **Candidate gate:** Event title exact Chicago family; `active=true`, `closed=false`, endDate ≥ discovery observed-at; resolution/rule text Wunderground KORD station/source ve following-date first datapoint freeze semantiği içermeli; event ID, endDate ve tüm nested bucketlarda market/condition/two CLOB token identity complete olmalı.
- **Selection:** Birden çok qualified event varsa en erken endDate, sonra numeric event ID; sonuçlara bakarak seçim yok. Hiç yoksa `NOT_AVAILABLE`, gate başarısız sayılmaz ve başka şehir sessizce ikame edilmez.
- **Metrikler:** Page/source/duplicate/event/city sayıları; Chicago raw, temporally relevant, exact-rule ve fully qualified sayıları; exclusion reasons; selected event/rule hash/date/tokens.
- **Güvenlik:** Public GET dışında çağrı yok; wallet/credential/order yok. Bu adım collector başlatmaz.
- **Artifact hedefi:** `reports/data_quality/EXP-20260902-phase5-kord-upcoming-event-discovery.json`, research raporu ve ignored immutable raw run.

### D-0051 — 2026-09-02 — Wunderground-primary KORD live cohort yok; NOAA-primary regime bulundu

- **Durum:** `ACTIVE`
- **Inventory:** 2 keyset page, 150 source event, 0 duplicate, 51 şehir. Chicago event 3; observed-future 2; identity-complete 3.
- **Gate sonucu:** Exact Wunderground-primary KORD qualified event 0; `availability_status=NOT_AVAILABLE`. Deterministic selection uygulanamadı, şehir/event ikamesi yapılmadı.
- **Rule drift:** Event 940517/946566/952456 primary source olarak NOAA WRH `timeseries?site=kord` kullanıyor; historical event 553903 Wunderground-primary idi. Wunderground current rule'da yalnız fallback.
- **Karar:** Chicago provider rejimleri versioned ayrılacak; Wunderground freeze contract current NOAA-primary eventlere primary evidence olarak uygulanmayacak.
- **Kalite/güvenlik:** 79 test ve yeni modüllerde Ruff geçti; public GET dışında işlem, credential veya background collector yok.
- **Artifact:** Discovery JSON, research raporu; raw `data/raw/polymarket_gamma-kord-discovery/run=20260902T120408Z`.
- **Sonuç:** Phase 5 `IN_PROGRESS`; current NOAA-primary KORD observation/freeze semantiği henüz doğrulanmadı.

### D-0052 — 2026-09-02 — NOAA WRH KORD source-surface discovery ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Event 946566/952456'nın declared primary URL'si `weather.gov/wrh/timeseries?site=kord`, exact KORD identity ile observation timestamp, temperature value/unit ve hourly/table records sağlayan resmî, read-only ve makinece parse edilebilir bir surface veya aynı resmî sayfanın çağırdığı documented data endpoint'ine sahiptir.
- **Scope:** Yalnız `weather.gov`/resmî NOAA-NWS origin ve sayfanın kendi first-party asset/data çağrıları; üçüncü taraf weather aggregator yok. GET/HEAD dışında işlem yok.
- **Discovery artifact:** URL, requested/received UTC, HTTP status/headers, byte count, SHA-256, content type; HTML/script/network referansları; bulunan candidate endpoint ve örnek şema alanları. Credential gereksinimi ve erişim koşulu açık raporlanacak.
- **Semantic gate:** Exact `KORD` identity; en az bir timezone-aware veya timezone semantiği belgelenmiş observation timestamp; temperature value + açık unit; en az bir hourly observation; timestamp'i `America/Chicago` local date'e deterministik çevirebilme. Hepsi birlikte yoksa source `NOT_MACHINE_RECONCILABLE`.
- **Trigger gate:** Following local date'e ait ilk observation, timestamp'li kayıtlardan deterministik seçilebilmeli. Sayfanın yalnız görüntülenmesi trigger kanıtı değildir.
- **Revision sınırı:** Current response historical first-seen/freeze version değildir. Version/revision endpoint bulunmazsa `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`; prospective raw capture gerekir.
- **Stability:** Aynı endpoint iki bounded ardışık retrieval'da HTTP/schema/identity açısından tutarlı olmalı; dynamic record/checksum farkı hata değildir ve timestamp ile saklanır. Persistent polling yok.
- **Gate sonucu:** `PASSED`, `CONDITIONAL_PASS` veya `FAILED`; sonuçtan sonra alan/eşik değiştirilmeyecek. Artifact hedefi `reports/data_quality/EXP-20260902-phase5-noaa-wrh-kord-source-discovery.json` ve research raporu.

### D-0053 — 2026-09-02 — NOAA WRH official-origin machine reconciliation başarısız

- **Durum:** `ACTIVE`
- **Stability:** İki page retrieval HTTP 200, content type aynı, 64.758 byte ve SHA-256 aynı; static page observation payload içermiyor.
- **Dependency:** First-party `obs.js`, `STID`, °F ve `obtimezone=local` semantiğini kuruyor fakat actual timeseries origin `api.synopticdata.com`; credential helper referansı var. Credential değeri persist/output edilmedi.
- **Gate:** Official-origin machine endpoint 0; exact KORD payload, timestamped temperature rows ve following-local-date trigger selection `FAILED`. Karar `FAILED_NOT_MACHINE_RECONCILABLE_WITHIN_OFFICIAL_ORIGIN_SCOPE`.
- **Revision:** Sayfa veriyi preliminary/QC adjustment'a açık tanımlıyor; download feature unavailable. `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`.
- **Güvenlik:** Third-party endpoint çağrılmadı; token değeri raw/log/artifact/repository'ye yazılmadı; polling yok.
- **Kalite:** 81 test ve scoped Ruff geçti. Artifact, rapor ve ignored raw page/client script run'ı kaydedildi.
- **Sonuç:** Phase 5 `IN_PROGRESS`; Chicago NOAA-primary automated exact-temperature source gate başarısız, browser-rendered declared-source evidence son sınırlı seçenek.

### D-0054 — 2026-09-02 — NOAA WRH browser-rendered DOM diagnostic ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Declared URL `weather.gov/wrh/timeseries?site=kord&hours=72&units=english_k&hourly=true` browser'da render edildiğinde credential çıkarmadan exact KORD/name, °F Temp header ve timestamp+temperature içeren hourly table rows deterministik parse edilebilir; Sep 1→Sep 2 ilk-local-row trigger algoritması canlı DOM üzerinde gösterilebilir.
- **Cohort:** İki bounded render/reload; sabit KORD, 72 saat, `english_k`, `hourly=true`. Sep 1 target ve Sep 2 following date yalnız parser/trigger diagnostic'tir; historical freeze-time capture veya outcome label değildir.
- **Gate:** Her iki render ≤30 saniyede load; exact KORD/O'Hare identity; °F temperature header; her render ≥24 timestamped non-null temperature row; parse edilen timestamp'ler timezone semantiğiyle `America/Chicago` local date'e çevrilebilir; duplicate timestamp 0; column schema iki renderda aynı.
- **Trigger diagnostic:** Sep 2 local date'e ait ilk timestamp deterministik ve Sep 1 satırlarından sonra seçilmeli. Capture'ın trigger anında yapılmış olması gerekmez ve iddia edilmeyecek.
- **Artifact/provenance:** URL, navigation/reload observed time, DOM table schema, row count/date range, first-following row, visible warning text ve rendered DOM/body checksum; credential/cookie/local storage/network token kaydı yok. Screenshot/raw DOM yalnız ignored local artifact olabilir.
- **Karar:** Gate geçerse `BROWSER_RENDERED_DIAGNOSTIC_PASS`, fakat automated/API ve freeze-as-of unresolved kalır. Gate kalırsa current Chicago NOAA-primary exact-temperature pipeline `NO_GO`.
- **Güvenlik:** Browser navigation/DOM read-only; form submission, download, credential extraction, order veya persistent polling yok.
- **Artifact hedefi:** `reports/data_quality/EXP-20260902-phase5-noaa-wrh-kord-rendered-dom.json` ve research raporu.

### D-0055 — 2026-09-02 — NOAA WRH rendered DOM gate geçti, settlement gate geçmedi

- **Durum:** `ACTIVE`
- **Ölçüm:** İki bounded render 13:47:49Z ve 13:49:37Z'de exact O'Hare title, aynı normalize 21 kolon ve 85/85 timestamp+numeric °F row verdi; duplicate timestamp 0, body-text SHA-256 aynı.
- **Trigger diagnostic:** Sep 2 local date minimum timestamp iki renderda da `00:51`, sıcaklık `81°F`. Bu seçim trigger saatinden sonra yapıldığı için historical freeze snapshot değildir.
- **Gate:** Ön-kayıtlı eşikler post-hoc değişiklik olmadan geçti: `BROWSER_RENDERED_DIAGNOSTIC_PASS`.
- **Sınır:** Satırda explicit UTC offset/yıl yok; local timezone KORD/`(L)` semantiğinden, yıl page/chart context'inden türetiliyor. Preliminary/QC revision uyarısı var. Automated API, historical freeze-as-of ve prospective trigger capture unresolved.
- **Güvenlik:** Yalnız read-only navigation/DOM; credential, cookie, local storage, network token, raw DOM veya screenshot kaydı yok.
- **Karar:** Chicago exact-temperature hattı `NO_GO` yapılmadı; yalnız tek-event prospective bounded browser capture araştırmasına conditional olarak açık. Phase 5 `IN_PROGRESS`, training/backtest/live sermaye kapalı.

### D-0056 — 2026-09-02 — İlk NOAA-primary prospective KORD cohort kilitlendi

- **Durum:** `ACTIVE`
- **Hipotez:** Trigger penceresindeki bounded browser session, event 946566 için Sep 3 target rows + ilk Sep 4 local row'u outcome kullanılmadan immutable kanıt olarak saklayabilir.
- **Selection:** Checksum-locked discovery'deki iki observed-future NOAA-primary KORD event arasından outcome bağımsız `earliest end_at` ile event `946566` seçildi. Rule hash, 11 market/condition ve 22 token identity source checksum/JSON pointer ile kilitli.
- **Zaman:** `America/Chicago`; not-before `2026-09-04T05:00Z`, preferred `05:45Z`, hard stop `06:30Z`; ≤45 dakika, ≤10 render, araları ≥240 saniye. Persistent/background collector ve automatic schedule yok.
- **Gate:** Exact identity/°F; target-date ≥20 numeric row; following-date ≥1 row; duplicate 0; min following timestamp seçimi; source-lock, payload/manifest checksum ve append-only replay pass.
- **Karar sınıfları:** Başarı `PROSPECTIVE_TRIGGER_CAPTURE_PASS_PENDING_SETTLEMENT`; capture failure current Chicago NOAA-primary pipeline `NO_GO`; tek settlement match edge kanıtı değildir.
- **Güvenlik:** Read-only browser; order/wallet/credential/token inspection/outcome lookup yok.

### D-0057 — 2026-09-02 — NOAA rendered-table snapshot adapter ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Pure/deterministic bir adapter, browser'dan gelen sanitized table payload'ını locked event contract ile validate edip content-addressed append-only manifest'e dönüştürebilir; invalid zaman/identity/schema/unit/coverage/duplicate/source-lock girdileri fail-closed olur.
- **Fixture:** Synthetic Sep 3 target + Sep 4 trigger KORD payload; gerçek event 946566'nın public identity/rule/source checksum kilidi, fakat gerçek weather outcome kullanılmaz.
- **Gate:** Valid fixture qualify; pre-midnight, wrong identity/unit/schema/source checksum, target <20, following 0, duplicate timestamp ve tamper fail; first-following=min timestamp; identical replay idempotent; changed payload new revision. En az 12 contract assertion ve full test suite pass.
- **Artifact:** `reports/data_quality/EXP-20260902-phase5-noaa-wrh-snapshot-adapter.json` ve research raporu.
- **Sınır:** Adapter pass canlı capture/uptime/settlement kanıtı değildir; gerçek pencere ve D-0056 eşikleri değişmez.

### D-0058 — 2026-09-02 — NOAA snapshot adapter contract gate geçti

- **Durum:** `ACTIVE`
- **Sonuç:** `SNAPSHOT_ADAPTER_CONTRACT_PASS`; focused 13/13, full suite 94/94, scoped Ruff 0 error.
- **Kanıt:** Valid synthetic fixture qualify; min following timestamp seçimi ve Chicago DST conversion doğru. Wrong identity/unit/schema/URL, target coverage, following row, duplicate, numeric parse, pre-midnight ve source tamper fail-closed.
- **Immutability:** Identical replay idempotent; changed payload yeni revision; payload tamperi ve manifest/payload mismatch reddediliyor; build deterministic.
- **Sınır:** Live NOAA payload, browser uptime, gerçek trigger timing ve settlement test edilmedi. Edge/P&L kanıtı değildir.
- **Karar:** Event 946566 capture sözleşmesi uygulamaya hazır; D-0056 pencere/eşikleri değişmedi.

### D-0059 — 2026-09-03 — Quant vertical slice settlement beklemeden başlatıldı

- **Durum:** `ACTIVE`
- **Kullanıcı kararı:** Uzayan fizibilite ana hattı bloke etmeyecek; Sep 4 capture paralel label-quality kontrolü olarak devam edecek.
- **Cohort:** Event 946566 / KORD / Sep 3; locked rule/source/11 bucket identity. Experiment-specific forecast, price veya outcome değeri görülmeden yeni plan kaydedildi.
- **Forecast:** Latest-available NOAA NBM probabilistic text, exact KORD target record; Gaussian mean/std baseline + 0.5°F integer continuity correction. Açıkça uncalibrated diagnostic.
- **Execution:** 11 YES book; bucket başına $10 ask-depth VWAP; midpoint/imputation yok; forecast→last-book ≤15 dakika; executable coverage ≥9/11.
- **Cost:** Verified primary fee formula varsa net EV; yoksa fee/net EV `UNKNOWN`. Gross edge ve 1pp/2pp resolution-risk sensitivity ayrı.
- **Gate:** Exact identity, 11 exhaustive/non-overlap bucket, probability sum 1±1e-9, immutable provenance, temporal skew ve coverage koşulları birlikte `VERTICAL_SLICE_MECHANICS_PASS` için zorunlu.
- **Sınır:** Tek event edge/calibration/P&L kanıtı değildir; paper/live signal ve outcome lookup yasak.

### D-0060 — 2026-09-03 — Vertical slice quant core gate geçti

- **Durum:** `ACTIVE`
- **Sonuç:** `VERTICAL_SLICE_CORE_PASS`; focused 10/10, full suite 104/104, scoped Ruff 0.
- **Probability:** Gaussian CDF, half-degree bucket mass, exhaustive probability sum ve partition gap/overlap fail-closed test edildi.
- **Execution:** Fixed-$ ask-depth VWAP best-first; single/multi-level fill, explicit insufficient depth ve invalid price/size rejection test edildi. Midpoint girdisi yok.
- **Sınır:** Live NBM/event/book/fee, calibration, settlement ve P&L henüz ölçülmedi.
- **Karar:** Pure core hazır; aynı preregistration altında tek immutable live read-only slice çalıştırılabilir.

### D-0061 — 2026-09-03 — Immutable live vertical-slice runner hazır

- **Durum:** `ACTIVE`
- **Akış:** Availability-only latest NBM ≤6-cycle search → exact KORD target record → locked Gamma identities → 11 concurrent YES book/tick/fee public GET → probability/VWAP/fee table.
- **Fee:** Official formula `C × rate × p × (1-p)` implement edildi; per-token `/fee-rate` bps değeri Gamma `feeSchedule.rate` ile eşleşmeden net EV üretilmiyor.
- **Provenance:** Yeni raw run path zorunlu, overwrite yasak; NBM/Gamma/book/tick/fee checksum ve timestamps saklanıyor.
- **Kalite:** Full suite 105/105, scoped Ruff 0. Outcome/order/wallet/credential endpoint'i yok.
- **Karar:** Runner aynı preregistration altında tek live run için hazır.

### D-0062 — 2026-09-03 — Vertical slice attempt 1 fee gate'te fail-closed

- **Durum:** `ACTIVE`
- **Passed:** Exact event/rule, one KORD forecast, 11 bucket, probability sum 1.0, 11/11 `$10` executable ask-depth, 0 request error, forecast→last-book 0.913s.
- **Forecast:** NBM 07Z, f17, target-valid 00Z; mean 90°F, sd 4°F; quantiles 86/87/89/94/95°F.
- **Failed:** Legacy `/fee-rate base_fee=1000 bps` ile Gamma `feeSchedule.rate=0.05` eşit değil; net EV doğru şekilde üretilmedi. Karar `VERTICAL_SLICE_INCOMPLETE`.
- **Diagnostic only:** Gross edge aralığı +8.72pp (`86-87°F`) ile −38.38pp (`94-95°F`); uncalibrated tek event, signal değil.
- **Safety:** Outcome/order/wallet/credential yok; raw NBM/Gamma/11 book/tick/fee immutable ignored run'da.

### D-0063 — 2026-09-03 — V2 condition-level fee corrective ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Official `/clob-markets/{condition_id}` `fd={r,e,to}` alanı Gamma `feeSchedule` ile 11/11 reconcile olur ve documented `C×r×p×(1-p)` formula net EV üretir.
- **Gate:** Exact condition/token identity; `fd.r=Gamma rate`, `fd.e=Gamma exponent=1`, `fd.to=Gamma takerOnly=true` for 11/11; immutable response checksum; diğer vertical-slice eşikleri değişmez.
- **Failure:** Herhangi fee mismatch veya missing field net EV'yi tekrar `UNKNOWN` ve slice'ı `INCOMPLETE` bırakır. Legacy `base_fee/tbf` rate olarak kullanılmaz.
- **Karar:** Runner düzeltmesi ve yeni immutable attempt; attempt 1 overwrite edilmez.

### D-0064 — 2026-09-03 — V2 fee corrective implement edildi

- **Durum:** `ACTIVE`
- **Değişiklik:** Runner condition-level `/clob-markets/{condition_id}` `fd.r/e/to`, token membership ve Gamma schedule equality kullanıyor; legacy `/fee-rate` kaldırıldı, `tbf` yalnız provenance.
- **Değişmeyenler:** Event, NBM selection, Gaussian baseline, $10 VWAP, 15-minute skew, ≥9/11 coverage ve no-signal sınırı aynı.
- **Kalite:** Full 105/105 ve scoped Ruff pass.
- **Karar:** Attempt 2 yeni immutable path ile çalıştırılabilir.

### D-0065 — 2026-09-03 — İlk live quant vertical slice mechanics gate geçti

- **Durum:** `ACTIVE`
- **Karar:** `VERTICAL_SLICE_MECHANICS_PASS`; exact identity, 11 bucket, probability sum 1.0, NBM-before-book, 1.413s skew, 11/11 $10 ask-depth, fee 11/11 ve 0 error.
- **Forecast:** NBM 07Z KORD f17; mean/sd 90/4°F, reported quantiles 86/87/89/94/95°F.
- **Market disagreement:** En yüksek diagnostic net edge/share `88-89°F` +10.68pp; `94-95°F` −39.63pp. 2pp haircut sonrası 5/11 pozitif.
- **Model risk:** Gaussian implied quantiles yaklaşık 84.87/87.30/90.00/92.70/95.13°F ve NBM reported quantiles ile uyuşmuyor. Tail/dollar EV güvenilir calibration değildir.
- **Sınır:** Tek event, yakın-resolution snapshot, outcome yok. Signal/paper/live trade yok; pozitif edge iddiası yapılmaz.
- **Sonuç:** Quant mechanics artık çalışıyor; Phase 6 conditional `IN_PROGRESS`. Sonraki kanıt fixed-lead prospective paper cohort olmalı.

### D-0066 — 2026-09-03 — Chicago fixed-time prospective paper pilot ön-kaydı

- **Durum:** `ACTIVE`
- **Cohort:** 14 daily schedule, 2026-09-03–16 UTC at 12:00±15m; target local Sep 4–17; minimum eligible 10. Missing date substitute/backfill yok.
- **Primary model:** Published p10/p25/p50/p75/p90 üzerinden locked piecewise-linear quantile CDF + slope-extended finite tails; outcome tuning yok. Gaussian benchmark olarak kalır.
- **Paper rule:** Model başına günde ≤1; en yüksek `q−VWAP−fee−2pp`, minimum adjusted edge 3pp; `$10` ask-depth; yetersiz kalite/depth `NO_TRADE`. Emir yok.
- **Pilot data gate:** ≥10/14; bucket executable ≥90%; identity/provider mix ve leakage 0; explicit rejection reasons.
- **Continue gate:** Data pass, semantic defect yok, adjusted P&L deployed capital'ın −30%'undan iyi, tek positive-gross gün payı ≤50%, eligible settlement labels. Sonuç yalnız `CONTINUE_DATA_COLLECTION` veya `STOP_OR_REDESIGN`.
- **Edge sınırı:** ≥30 eligible date ve future preregistered positive cluster-CI gate öncesi edge claim yok.
- **Operasyon:** Günde bir kısa foreground run; automatic schedule/always-on collector yetkisi yok.

### D-0067 — 2026-09-03 — Quantile-preserving baseline contract geçti

- **Durum:** `ACTIVE`
- **Sonuç:** `QUANTILE_BASELINE_CONTRACT_PASS`; focused 17/17, full 111/111, scoped Ruff 0.
- **Contract:** Tail slope extension, exact quantile anchors, repeated-value right-continuous jump, half-degree exhaustive mass, monotonic rejection ve aligned TV doğrulandı.
- **Outcome-free replay:** Probability sum 1.0; Gaussian vs quantile TV `0.273812`. Model seçimi apparent edge'i materyal değiştiriyor.
- **Karar:** Primary quantile ve Gaussian benchmark her daily record'da ayrı korunacak; outcome'a göre model seçilmeyecek. Pass doğruluk/calibration kanıtı değildir.

### D-0068 — 2026-09-03 — Paper cohort saati pre-data 11:00 UTC'ye alındı

- **Durum:** `ACTIVE`
- **Değişiklik:** Kullanıcı kolaylığı için daily time 12:00 UTC'den 11:00 UTC / 14:00 Europe/Istanbul'a, aynı ±15m toleransla alındı.
- **Timing integrity:** Değişiklik snapshot 1 ve cohort-specific forecast/price gözleminden önce yapıldı; post-result selection değildir.
- **Değişmeyenler:** 14 date/≥10 eligible, models, $10 VWAP, fee+2pp, minimum 3pp, metrics ve bütün gates aynı.
- **Kural:** Cohort boyunca 11:00 UTC sabit; sonraki timing değişikliği mixed cohort değil yeni version gerektirir.

### D-0070 — 2026-09-03 — Paper Day 1 attempt 1 variable-shadow gate failure

- **Durum:** `ACTIVE`
- **Observed:** 10:54–10:55Z; exact event/buckets, dual probability sum, fee, 11/11 execution, ordering/skew ve requests geçti; gerçek target NBM record count 1.
- **Failure:** `candidates` değişkeni paper-selection aşamasında shadow edildi; final `target_nbm_record` check yanlış false oldu. Run `INCOMPLETE`, provisional decisions cohort'a alınmadı.
- **Provisional only:** Gaussian `NO_TRADE` +2.20pp adjusted; quantile `PAPER_TRADE` +12.15pp, ikisi de 86-87°F. Order yok.
- **Corrective pre-registration:** Yalnız değişkeni `paper_candidates` olarak ayır, target-count regression test ekle; model/data/threshold/time değişmeden aynı pencere içinde yeni immutable attempt çalıştır.

### D-0071 — 2026-09-03 — Paper Day 1 snapshot kabul edildi, outcome pending

- **Durum:** `ACTIVE`
- **Timing/quality:** Completed 10:57:52Z inside 11:00±15m; all mechanics checks pass, 11/11 executable, 10 two-sided/1 one-sided, 0 errors, skew 0.944s.
- **Forecast:** NBM 07Z f41; mean/sd 89/4°F, quantiles 85/86/88/93/95°F; target Sep 4 contract, product valid Sep 5 00Z.
- **Model difference:** Gaussian/quantile TV `0.267234`.
- **Paper decisions:** Gaussian best 86-87°F adjusted +2.81pp <3pp → `NO_TRADE`; quantile 86-87°F q=26.25%, VWAP=11¢, fee $0.445/$10, adjusted +12.76pp → `PAPER_TRADE`.
- **Safety:** 90.909 hypothetical shares only; `order_sent=false`, outcome/P&L null.
- **Boundary:** `CAPTURE_ELIGIBLE_PENDING_OUTCOME`; one day edge evidence değil, NBM valid-time→target-local-day semantic check tracked dependency.

### D-0072 — 2026-09-03 — Hızlı tarihsel Chicago fiyat-kapsam deneyi ön-kaydı

- **Durum:** `ACTIVE`
- **Amaç:** Prospective cohort devam ederken beklemeden tarihsel model araştırmasını açmak; önce backtest girdisinin gerçekten mevcut olup olmadığını ölçmek.
- **Locked sample:** Frozen corrected Gamma inventory'den deterministic latest 30 eligible closed Chicago event; minimum 20; tüm YES bucket token'ları.
- **Primary gates:** event/token any-history ≥80%, request error ≤2%, window dışı point 0%, covered token başına ≥2 point.
- **Endpoint:** Public CLOB `/prices-history`, explicit creation→close window, `interval=all`, 1-minute fidelity; responses append-only ve checksum'lı.
- **Boundary:** Endpoint geçmiş L2 bid/ask/depth sağlamaz. Pass yalnız indicative-price/forecast research iznidir; executable P&L veya edge kanıtı değildir.

### D-0073 — 2026-09-03 — Historical coverage attempt 1 pre-network timestamp parse failure

- **Durum:** `ACTIVE`
- **Failure:** Gamma `creationDate` içindeki 5-digit fractional seconds Python 3.9 `fromisoformat` tarafından reddedildi.
- **Integrity:** Run directory ve CLOB request oluşmadan durdu; price/history sonucu gözlenmedi.
- **Corrective lock:** Yalnız 1–5 fractional digit'i 6 haneye pad et ve regression test ekle. Sample, endpoint, query windows, metrics ve thresholds değişmez; yeni immutable attempt zorunlu.

### D-0074 — 2026-09-03 — Chicago historical price coverage geçti, execution kanıtı değil

- **Durum:** `ACTIVE`
- **Sample:** Latest deterministic 30 eligible event, 2026-07-30–08-28; event başına 11, toplam 330 YES token.
- **Coverage:** event 30/30, token 330/330, request error 0, window dışı point 0; locked gate'lerin tümü geçti.
- **Resolution:** 1,303 point; token başına min/median/max 3/4/4. Duplicate/conflict/non-strict response 0.
- **Karar:** `HISTORICAL_PRICE_COVERAGE_PASS`; tarihsel indicative-price ve forecast calibration araştırması başlayabilir.
- **Boundary:** 3–4 point/token seyrek seridir; historical bid/ask, depth, spread, side, size veya fill yok. Executable backtest/net EV/edge kanıtı sayılmaz.

### D-0075 — 2026-09-03 — Chicago historical forecast/outcome join ön-kaydı

- **Durum:** `ACTIVE`
- **Identity lock:** Önceki coverage deneyinin checksum-locked aynı 30 event'i; replacement/backfill yok.
- **Decision time:** Target−1 calendar day 11:00 UTC; NBM target−1 07Z, fallback yok; HTTP Last-Modified decision time'ı aşamaz.
- **Forecast mapping:** KORD MaxT valid target+1 00Z; exact tek record. Mapping semantic bağımsız doğrulamaya kadar provisional.
- **Outcome:** Frozen Gamma'da exact tek `[1,0]` YES winner ve diğer tüm bucket'larda `[0,1]`; exhaustive whole°F partition.
- **Primary gates:** identities/winner/partition 100%; object ve final join ≥29/30; retrieved parse/target record 100%; publication leakage 0.
- **Boundary:** Pass model dataset'i açar; trained model, executable P&L veya edge kanıtı değildir.

### D-0076 — 2026-09-04 — Historical join attempt 1 transport nedeniyle gate fail

- **Durum:** `ACTIVE`
- **Passed components:** Identity/winner/partition 30/30; NBM download+parse+exact target 23/23; publication-proxy leakage 0.
- **Failure:** 5 read timeout + 2 connection reset; observed object/join 23/30 = %76.67, locked ≥29/30 gate başarısız. Raw decision `HISTORICAL_JOIN_FAIL` korunur.
- **Diagnosis:** Hatalar HTTP missing değil transport exception; archive missingness kanıtı değildir. Partial raw files kabul edilmez.
- **Corrective lock:** 23 complete file'ı checksum ile doğrula/reuse et; yalnız aynı 7 object'i yeni immutable run'da 2 worker/300s timeout ile retry et. Identity, cycle, mapping, outcome, metrics, thresholds değişmez.

### D-0077 — 2026-09-04 — Chicago historical forecast/outcome join gate geçti

- **Durum:** `ACTIVE`
- **Retry integrity:** Önceki 23 complete object checksum-verified; yalnız aynı 7 transport failure yeniden indirildi.
- **Coverage:** Identity/object/parse/exact f41 target/winner/partition/final join 30/30; publication-proxy leakage 0.
- **Data:** 2026-07-30–08-28, NBM v5.0 07Z/f41, accepted source 1,041,734,375 byte.
- **Karar:** `HISTORICAL_JOIN_PASS`; preliminary Gaussian/quantile/indicative-market scoring dataset'i açıldı.
- **Boundary:** 30 summer date edge/model-training için küçük; price executable değil; NBM local-day semantics provisional.

### D-0078 — 2026-09-04 — Chicago baseline scoring ön-kaydı

- **Durum:** `ACTIVE`
- **Split:** Exact 30 date ascending; first 20 validation, last 10 single-use test; fitting/tuning yok.
- **Models:** Uniform, locked NBM Gaussian, locked quantile-preserving CDF.
- **Metrics:** Primary multiclass log loss; Brier/RPS/winner probability secondary; paired date bootstrap 10,000, seed 20260904.
- **Market rule:** Her YES token için decision time'da/öncesinde latest point; future yasak, max 18h stale, all tokens, normalized cross-bucket score. Test coverage <8 ise market comparison yok.
- **Claims:** Testte uniform'u geçen model yalnız preliminary baseline olabilir; model-vs-market/EV/trade claim ayrı coverage ve execution gate gerektirir.

### D-0079 — 2026-09-04 — İlk Chicago baseline skorları geçti, market comparison unavailable

- **Durum:** `ACTIVE`
- **Quality:** 30/30 finite; 20 validation/10 test; max probability-sum error `2.22e-16`; exact winners 30/30.
- **Log loss validation:** uniform 2.398, Gaussian 1.575, quantile 1.556.
- **Log loss test:** uniform 2.398, Gaussian 1.171, quantile 1.085. İki NBM model de preliminary uniform baseline'ı geçti.
- **Model uncertainty:** Gaussian−quantile paired 95% CI validation `[-0.124,+0.187]`, test `[-0.096,+0.267]`; zero içeriyor, quantile superiority claim yok.
- **Market gate:** 0/30 complete event decision time 11:00Z öncesi historical price içeriyor; `INSUFFICIENT_POINT_IN_TIME_COVERAGE`. Future price taşınmadı; model-vs-market/EV/P&L yok.
- **Karar:** Forecast sample genişletmeye değer; model eğitmeden önce NBM local-day semantic mapping doğrulanmalı. Execution kanıtı prospective L2'den gelecek.

### D-0080 — 2026-09-04 — Paper Day 2 missed, backfill yasak

- **Durum:** `ACTIVE`
- **Observed:** İlk kontrol 17:01 UTC; locked 10:45–11:15 UTC penceresi geçmişti.
- **Karar:** Day 2 `MISSED_NO_CAPTURE`; later snapshot/substitute/backfill yok. Schedule coverage şu an 1/2; cohort gate ≥10/14 değişmedi.

### D-0081 — 2026-09-04 — NBM f41 resolution-equivalent değil, proxy feature

- **Durum:** `ACTIVE`
- **Official semantic:** NOAA NBM MaxT 12Z current→06Z next 18h window, following 00Z'de raporlanır; NBP TXNMN/TXNP aynı max convention'ı kullanır.
- **Chicago CDT market day:** 05Z target→05Z next, 24h. NBM ile overlap 17h; market başlangıcından 7h eksik, market sonrasından 1h fazla.
- **Karar:** f41/TXN `PROXY_18H_MAX`, resolution-equivalent label değil. 30-date scoring predictive-proxy sonucu olarak kalır; exact meteorological target iddiası yok.
- **Path:** NBM proxy outcome'a karşı walk-forward calibrate edilebilir; gerçek label frozen settlement source'dan gelir ve iki window açıkça saklanır.

### D-0082 — 2026-09-04 — 114-date Chicago walk-forward calibration ön-kaydı

- **Durum:** `ACTIVE`
- **Universe:** Frozen Gamma, exact 114 resolved Chicago date, 2026-05-06–08-28, 11°F buckets, NBM v5.0 regime.
- **Forecast:** Prior-day 07Z f41 `PROXY_18H_MAX`; publication proxy ≤11Z; fallback/replacement yok.
- **Walk-forward:** First 60 initial train; expected next 54 OOS; expanding refit every event, future outcome yok.
- **Calibration:** Shift −5..+5°F step 0.5 × spread {0.75,1,1.25}; train log loss selection, deterministic raw-nearest tie-break.
- **Gate:** Eligible ≥99%, OOS ≥53; practical improve ≥2% log loss + Brier non-worse; strong evidence paired CI upper <0.
- **Boundary:** Forecast calibration only; market/EV/fill/order yok, one-city/season/version external-validity limiti var.

### D-0083 — 2026-09-04 — Expanded dataset retrieval policy kilitlendi

- **Durum:** `ACTIVE`
- **Reuse:** Accepted 30-date join result ve her NBM source checksum doğrulanacak.
- **Pending:** Yalnız kalan 84 prior-day 07Z object; 4 worker, 300s timeout, transport error için max 3 attempt.
- **Integrity:** Attempt dosyaları benzersiz/immutable; partial dosya parse/kabul edilmez. HTTP missing/semantic failure için cycle/date replacement yok.
- **Thresholds:** 114-universe, ≥99% eligible ve ≥53 OOS dahil tüm D-0082 gate'leri değişmedi.

### D-0084 — 2026-09-04 — Calibration dataset attempt 1 pre-download duplicate gate düzeltmesi

- **Durum:** `ACTIVE`
- **Observed:** Selector May 19 archived duplicate event 493662'yi strict event gate öncesi aldı; record `arch-` slug ve missing `closedTime`/`automaticallyResolved` taşıyor. Canonical 503629 complete.
- **Integrity:** Duplicate check NOAA download ve forecast value gözleminden önce durdu; run path oluşmadı.
- **Universe clarification:** Strict eligible set 114 unique date; 2026-06-18 eksik, bu nedenle “consecutive” ifadesi kaldırıldı. Count/date bounds değişmedi.
- **Correction:** Duplicate validation öncesi pre-registered closed + automatically-resolved + closed-time + all UMA-resolved contract uygula. Model/threshold/retrieval değişmez.

### D-0085 — 2026-09-04 — 114-date calibration dataset gate FAILED, training yapılmadı

- **Durum:** `ACTIVE`
- **Transport:** 30 checksum reuse + 84 download = 114/114 object; terminal download failure 0; accepted 3,958,130,429 byte.
- **Exclusions:** Target May 6 source NBM v4.3 (v5 lock mismatch); target May 8 source Last-Modified 13:16Z >11:00Z decision.
- **Gate:** Eligible 112/114=%98.25 <99%; OOS 52 <53; publication leakage 1 >0. `CALIBRATION_DATASET_FAIL`.
- **Integrity:** Alternate cycle/date, later source, imputation ve threshold change yok; calibration training/scoring çalıştırılmadı.
- **Corrective path:** Yeni ve açıkça post-hoc v2 deney, v5 başlangıcını May 7'ye daraltabilir; May 8 missing kalır; 60 train + 52 OOS için yeni gate önceden yazılmalıdır.

### D-0086 — 2026-09-04 — Post-hoc corrective calibration v2 ön-kaydı

- **Durum:** `ACTIVE`
- **Timing:** Dataset quality facts görüldü, fakat expanded-sample calibration fit/OOS score henüz hesaplanmadı.
- **Sample:** Target ≥May 7 ve source eligible; exact 112. May 8 late-publication ve Jun 18 absent kalır.
- **Walk-forward:** First 60 eligible train, next 52 OOS, expanding daily refit.
- **Unchanged:** Gaussian/quantile dönüşümleri, −5..+5 step0.5 × {0.75,1,1.25} grid, metrics/bootstrap ve ≥2%+Brier/CI gates.
- **Boundary:** Explicit post-hoc evidential weakness; market/EV/fill/order yok.

### D-0087 — 2026-09-05 — Walk-forward calibration başarısız, raw quantile korunuyor

- **Durum:** `ACTIVE`
- **Contract:** 112 eligible, first 60 train, next 52 expanding OOS; train size 60→111; finite/probability checks geçti.
- **Gaussian:** Raw/cal log loss 1.4628/1.4528, yalnız %0.69 improve; Brier +0.0232 worse; paired CI `[-0.128,+0.125]`. Practical/strong fail.
- **Quantile:** Raw/cal log loss 1.4102/1.4668, %4.02 worse; Brier +0.0261; CI `[-0.0469,+0.1625]`. Practical/strong fail.
- **Karar:** `NO_STRONG_CALIBRATION_EVIDENCE`; shift/spread calibrated modeller kullanılmaz. Raw quantile best tested forecast baseline olarak korunur.
- **Boundary:** Bu weather forecast sonucu market mispricing/EV/P&L değildir; aynı 52 OOS üzerinde yeni model seçimi yapılmaz.

### D-0088 — 2026-09-05 — Forecast-first bir yıllık KORD dataset fazı ön-kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** 2025-09-01–2026-08-31 arasındaki 365 KORD hedef gününde prior-day NBM 07Z ve GEFS 00Z özellikleri NOAA yerel-gün MaxT etiketiyle joined ≥%97 ve leakage 0 olarak kurulabilir.
- **Features:** NBM probabilistic MaxT `PROXY_18H_MAX`; GEFS control+30 member local-day TMAX; calendar/DST. Exact timestamp ve provider version saklanır.
- **Label:** NOAA LCDv2 günlük maksimumu forecast-training outcome'dur; frozen Polymarket settlement kanıtı değildir.
- **Gates:** NBM fields ≥%99, GEFS completeness ≥%97, label ≥%99, joined ≥%97; duplicate/non-finite/leakage 0.
- **Evaluation firewall:** Önceki 52 OOS gün model selection için tüketildi. Yeni temporal split yalnız dataset gate sonrasında ve model skorlarından önce kilitlenecek; random split yok.
- **Boundary:** Dataset gate geçmeden model tuning yok; bu faz market/EV/order içermez.

### D-0089 — 2026-09-05 — KORD bir yıllık label coverage gate geçti

- **Durum:** `ACTIVE`
- **Source refresh:** NOAA LCDv2 2025 ve 2026 yıllık KORD dosyaları immutable run'a yeniden indirildi; result/source checksum'ları kaydedildi.
- **Coverage:** 2025-09-01–2026-08-31 hedefinde 362/365=%99.178 non-null günlük maksimum; locked ≥%99 gate geçti.
- **Quality:** Duplicate 0, station identity failure 0, terminal transport failure 0.
- **Missingness:** 2026-08-29–31 source dosyasında henüz yok; publication lag olarak işaretlendi, imputation/backfill yapılmadı.
- **Boundary:** NOAA label forecast eğitimi içindir; frozen historical Polymarket settlement-as-of kanıtı değildir.

### D-0090 — 2026-09-05 — Bir yıllık NBM 07Z source inventory gate geçti

- **Durum:** `ACTIVE`
- **Availability:** Prior-day 07Z probabilistic text object 365/365 mevcut; terminal transport failure 0.
- **Publication:** 362/365=%99.178 object 11:00 UTC decision time öncesi; Jan 25, Feb 21 ve May 7 source run'ları geç yayımlandı ve dışlanacak.
- **Storage:** Full object bulk download yaklaşık 11.83 GiB; compact KORD extraction doğrulanmadan yapılmayacak.
- **Pending:** Required field/station parse coverage henüz ölçülmedi; model/feature score hesaplanmadı.
- **Integrity:** Alternatif cycle, imputation veya late object admission yok.

### D-0091 — 2026-09-05 — Compact KORD NBM range extraction doğrulandı

- **Durum:** `ACTIVE`
- **Validation:** 2026-07-07 07Z bounded 1,000,001-byte range içinden çıkarılan KORD block, checksum-locked 34,724,473-byte full object block'uyla exact byte match.
- **Parse:** NBM v5.0, 9 MaxT record ve exact 1 f41 target record; gate geçti.
- **Efficiency:** Yıllık tahmin yaklaşık 348 MiB transfer + 1.28 MiB station storage; full-object storage 11.83 GiB.
- **Boundary:** Tek v5.0 vaka; annual batch her object'te range/station/marker/f41/version drift için fail-closed olacak.
- **Modeling:** Feature dataset/model score henüz üretilmedi.

### D-0092 — 2026-09-05 — Annual compact NBM batch runner hazır

- **Durum:** `ACTIVE`
- **Selection:** Checksum-locked 365-object inventory; exact 362 publication-admissible ve 3 late exclusion zorunlu.
- **Retrieval:** Gözlenen NBM schema-offset rejimleri için iki bounded range; station bulunmazsa sessiz fallback/admission değil fail-closed kayıt.
- **Per-day contract:** Exact KORD block, required MaxT alanları non-null, exact 1 f41, provider version/checksum/ETag/timestamps.
- **Gate:** Admissible günlerde required-field complete rate ≥%99; leakage 0. Batch sonuçları implementasyon commit'inden sonra ilk kez görülecek.
- **Boundary:** Runner yalnız NBM forecast feature üretir; label join/model score/EV yok.

### D-0093 — 2026-09-05 — Annual compact NBM feature gate geçti

- **Durum:** `ACTIVE`
- **Result:** 362/362 publication-admissible source compact retrieve+parse; required fields/exact f41 %100, retrieval failure ve leakage 0.
- **Efficiency:** 362,000,362 network range byte; 1,363,866 station-block byte; run yaklaşık 2.1 MiB disk.
- **Regimes:** NBM v4.3=246, v5.0=116. Upgrade model değerlendirmesinde explicit regime boundary olacak.
- **Range integrity:** v4.3 için 246 first-range schema miss kaydedildi; locked second range 246/246 başarı. Sessiz failure yok.
- **Preliminary join:** NBM∩label 359/365=%98.356; ≥%97 overall gate provisional pass, GEFS/final join bekliyor.
- **Boundary:** Split/model score/EV yok.

### D-0094 — 2026-09-05 — KORD GEFS TMAX exact/proxy rejimleri ayrıldı

- **Durum:** `ACTIVE`
- **365-day semantics:** Target coverage %100; exact partition 125 kış-saati günü, non-exact 240 gün.
- **Contamination:** 238 normal DST gününde 6h, DST bitişinde 5h, DST başlangıcında 1h outside-local süre.
- **Policy update:** Exact dates dört-block local-day max; diğerleri interior-18h lower + overlap upper + explicit outside seconds. Resolution-equivalent claim yok.
- **Robustness:** Model performansı window regime bazında ve non-exact exclusion sensitivity ile raporlanacak.
- **Timing:** Bu semantic düzeltme GEFS bulk retrieval ve model score öncesinde yapıldı; performance-driven değildir.

### D-0095 — 2026-09-05 — Annual GEFS full-member inventory runner hazır

- **Durum:** `ACTIVE`
- **Efficient inventory:** Her member/step'e ayrı HEAD yerine günlük paginated NOAA S3 listing; XML page checksum ve URL provenance saklanır.
- **Contract:** 365 target × 31 member × rejime göre 4–5 TMAX step; data ve `.idx` object birlikte zorunlu.
- **Timing:** Object ve index Last-Modified, run-date 11:00 UTC decision time'ı aşamaz.
- **Gate:** Complete+publication-admissible member-day ≥%97; terminal listing failure 0.
- **Boundary:** Inventory feature değerini indirmez ve model skoru hesaplamaz; sonuç implementasyon commit'inden sonra görülecek.

### D-0096 — 2026-09-05 — Annual GEFS full-member inventory gate geçti

- **Durum:** `ACTIVE`
- **Coverage:** 365/365 listing; complete+timely member-day 11,222/11,315=%99.178; locked ≥%97 geçti.
- **Objects:** Gerekli data+index pair 52,669/52,669 fiziksel mevcut; timely pair 52,297.
- **Exclusions:** Target Dec 19, Dec 20 ve Jan 26 tüm 31 member'da late-publication; alternate cycle yok.
- **Transport:** 2 transient retry ile düzeldi; terminal failure 0. Raw 2,190 page/1,951,389 metadata object.
- **Preliminary join:** NBM+GEFS+label unique exclusion 8 gün; expected 357/365=%97.808, locked ≥%97 provisional pass.
- **Boundary:** GEFS values henüz indirilmedi; model/split/score yok.

### D-0097 — 2026-09-05 — İki-rejim GEFS extraction pilotu ön-kaydı

- **Durum:** `ACTIVE`
- **Cases:** Target 2026-01-15 exact-winter (31×4=124) ve 2026-07-15 proxy-summer (31×5=155); toplam exact 279 TMAX message.
- **Integrity gate:** 279/279 index/range HTTP206/GRIB/decode; leakage ve non-finite 0; KORD nearest-grid distance ≤0.2°; −80..140°F.
- **Cost gate:** Ölçülen message byte'ı 52,297 annual pair'e ölçeklendiğinde ≤25 GiB; range GET ≤60,000.
- **Dependency:** Sayısal GRIB decode için ecCodes runtime reproducible dependency olarak eklenecek; mevcut environment'ta decoder yok.
- **Boundary:** Pilot model loss/feature selection/market/EV içermez.

### D-0098 — 2026-09-05 — GEFS GRIB decoder ve extraction pilot runner hazır

- **Durum:** `ACTIVE`
- **Runtime:** ecCodes `>=2.48,<2.49` project dependency; local isolated `.venv` kuruldu.
- **Decoder:** Tek-message, 2m TMAX/Kelvin identity; nearest KORD grid coordinate/distance; Fahrenheit conversion.
- **Runner:** Exact 279 görev; index row/canonical 6h/publication/HTTP206/GRIB/single-message/finite/range provenance fail-closed.
- **Projection:** Pilot mean message byte × locked 52,297 annual pair; ≤25 GiB ve ≤60,000 GET gate.
- **Boundary:** Gerçek pilot sonucu implementasyon commit'inden sonra ilk kez görülecek; model score yok.

### D-0099 — 2026-09-05 — Full-member GEFS extraction pilotu maliyet ve integrity gate'inde kaldı

- **Durum:** `ACTIVE`
- **Result:** 275/279=%98.57 decode; locked %100 fail. Finite/plausibility/grid/leakage kontrolleri geçti.
- **Bug:** 4 transport 503/reset, partial destination bıraktı; retry immutable-file check'e takıldı. Source missing değil; atomic temp write gerekli.
- **Cost:** 156,264,912 pilot byte → annual 27.28 GiB; locked ≤25 GiB fail. GET projection 52,297 ≤60,000 geçti.
- **Karar:** 31-member annual bulk retrieval yapılmaz; retry fix tek başına cost fail'i çözmez.
- **Corrective hypothesis:** Resmî `geavg`/`gespr` TMAX ürünlerini 275 empirical member değeriyle karşılaştır; yeterli eşleşirse low-cost summary feature olarak kullan.
- **Boundary:** Model score/EV/order yok.

### D-0100 — 2026-09-05 — GEFS range download atomic retry güvenliği düzeltildi

- **Durum:** `ACTIVE`
- **Fix:** Range bytes önce aynı dizinde unique `.part` dosyasına yazılır; tüm message integrity kontrolleri geçince hard-link ile immutable destination publish edilir.
- **Failure behavior:** Transport/content/commit exception'ında temporary file `finally` ile silinir; retry önünde yarım destination kalmaz.
- **Contract test:** Forced connection reset sonrası destination yok ve temp directory boş.
- **Boundary:** Bu fix FAILED pilot sonucunu veya 27.28 GiB cost kararını değiştirmez; full-member annual bulk hâlâ reddedildi.

### D-0101 — 2026-09-05 — GEFS aggregate-product corrective deney ön-kaydı

- **Durum:** `ACTIVE`
- **Source:** Checksum-locked 275-message full-member pilot; primary comparator yalnız exact 6 adet 31/31 case-step cell.
- **Candidates:** NOAA `geavg` TMAX vs empirical mean; `gespr` TMAX vs empirical population std (`ddof=0`). Toplam 18 aggregate message.
- **Accuracy gates:** Her ürün için MAE ≤0.25°F ve max absolute error ≤0.75°F; aggregate retrieve/decode %100; leakage 0.
- **Cost gates:** Annual projected transfer ≤3 GiB, range GET ≤4,000.
- **Integrity:** Üç incomplete-member cell diagnostic-only; eksik değerle primary threshold hesaplanmaz.
- **Boundary:** Model score/calibration/market/EV yok; eşikler aggregate değer görülmeden kilitlendi.

### D-0102 — 2026-09-05 — GEFS aggregate validation runner hazır

- **Durum:** `ACTIVE`
- **Contracts:** `geavg`/`gespr` object URL; exact index semantic `ens mean`/`ens std dev`; canonical 6h TMAX.
- **Units:** Mean absolute Kelvin→°F; spread Kelvin delta→°F delta yalnız ×9/5.
- **Comparator:** Checksum-locked pilot; empirical arithmetic mean ve population std; yalnız 6 adet 31/31 cell primary.
- **Output:** 18 aggregate message provenance, cell errors ve annual byte/GET projection.
- **Boundary:** Sonuç implementasyon commit'inden sonra görülecek; model loss/EV yok.

### D-0103 — 2026-09-05 — Aggregate attempt 1 veri öncesi config hatasında durdu

- **Durum:** `ACTIVE`
- **Failure:** Runner task submission öncesi machine config'te `station` bloğu olmadığı için `KeyError`; aggregate HTTP request/value 0, output directory boş.
- **Correction:** Human planında önceden kilitli KORD identity/41.96019/−87.93162 machine config'e eklendi.
- **Unchanged:** Dates/products/18 messages/comparator/accuracy/cost thresholds aynen korundu.
- **Retry:** İlk gerçek veri koşusu yeni immutable `run=20260905T-gefs-aggregate-validation-v2` path'inde yapılacak.

### D-0104 — 2026-09-05 — GEFS aggregate mean/spread validation tüm gate'leri geçti

- **Durum:** `ACTIVE`
- **Integrity:** 18/18 `geavg`/`gespr` TMAX index-range-decode; primary exact 6 adet 31/31 cell.
- **Accuracy:** Mean MAE/max 0.0333/0.1179°F; spread MAE/max 0.0658/0.1514°F. Locked 0.25/0.75°F gate'ler geçti.
- **Cost:** Annual projected 1.462 GiB ve 3,374 GET; locked ≤3 GiB/≤4,000 geçti.
- **Karar:** 31-member annual bulk yerine validated aggregate summary ingestion; individual-member frequency kaybı explicit limitation.
- **Boundary:** Aggregate equivalence forecast skill/calibration/EV değildir; yalnız feature fidelity ve cost kanıtıdır.

### D-0105 — 2026-09-05 — Annual GEFS aggregate ingestion runner hazır

- **Durum:** `ACTIVE`
- **Scope:** 362 timely date, exact 3,374 `geavg`/`gespr` message; 3 late date explicit exclusion.
- **Gates:** Message success ≥%99, complete-day ≥%97, leakage 0, finite/plausible mean/spread.
- **Features:** Overlap/interior mean-max ve peak spread, max block spread, exact/proxy, outside-local seconds.
- **Reliability:** Atomic range writes + bounded retries; per-message URL/index checksum/ETag/Last-Modified/GRIB checksum.
- **Plan update:** Individual members annual alınmadığı için `raw_gefs_frequency` baseline, validated `raw_gefs_mean_spread` olarak superseded.
- **Boundary:** Gerçek annual result implementasyon commit'i sonrası görülecek; label join/model score yok.

### D-0106 — 2026-09-05 — Annual GEFS aggregate feature gate geçti

- **Durum:** `ACTIVE`
- **Coverage:** 3,374/3,374 message ve 362/362 timely gün complete; exact=122, proxy=240; finite/plausible %100.
- **Transfer:** 1,600,972,976 byte=1.490 GiB; corrective pilot projection'ıyla uyumlu.
- **Reliability:** 46 transient transport error bounded atomic retry ile recovered; terminal failure/partial admission 0.
- **Features:** Overlap/interior mean-max + peak spread, max block spread, exact/proxy ve outside seconds.
- **Three-source set:** NBM∩GEFS∩LCDv2 exact 357/365=%97.808; locked joined ≥%97 tarih-seti gate geçti, final schema join bekliyor.
- **Integrity:** Sekiz exclusion explicit; imputation/alternate cycle yok. Model/split/score henüz yok.

### D-0107 — 2026-09-05 — Final model-ready join sözleşmesi kilitlendi

- **Durum:** `ACTIVE`
- **Hipotez:** Exact NBM∩GEFS∩LCDv2 kesişimi 357 unique ve finite satırla, sıfır publication leakage altında dondurulabilir.
- **Schema:** Station/date/decision timestamps, 7 NBM, 5 GEFS, GEFS window-quality, 4 calendar ve Fahrenheit label alanları.
- **Gates:** Exact 357 satır, joined ≥%97, duplicate/nonfinite/leakage 0; inner join, imputation yok.
- **Provenance:** Üç input result checksum'ı, canonical row checksum'ı ve explicit exclusion reasons output'ta zorunlu.
- **Boundary:** Split veya model skoru bu join sonucu görülmeden hesaplanmayacak.

### D-0108 — 2026-09-05 — KORD annual model-ready dataset gate geçti

- **Durum:** `ACTIVE`
- **Result:** 357/365 satır=%97.808; exact pre-registered row count ve joined ≥%97 gate geçti.
- **Integrity:** Duplicate=0, nonfinite=0, publication leakage=0; imputation/fallback yok.
- **Composition:** 121 exact GEFS partition, 236 proxy; NBM v4.3=244, v5.0=113.
- **Exclusions:** GEFS-only 2, NBM-only 2, NBM+GEFS 1, label-only 3 olmak üzere sekiz gün explicit.
- **Freeze:** Canonical row SHA-256 `45d2ab2e480a27529fbd52ba8546676bdf3bc794061cad726965a994e1bc75fd`.
- **Decision:** Forecast dataset deneyi `PASSED`; model skoru görülmeden temporal split/baseline config kilitlenecek.
- **Boundary:** Bu dataset market fiyatı/execution/settlement içermediğinden kârlılık veya EV kanıtı değildir.

### D-0109 — 2026-09-05 — Baseline walk-forward protokolü model skorlarından önce kilitlendi

- **Durum:** `ACTIVE`
- **Development:** İlk 120 eligible gün train; sonra 2026-06-30'a kadar expanding one-step-ahead OOS.
- **Consumed period:** 2026-07-01–08-31 önceki diagnostic nedeniyle selection/final-test dışında.
- **Final test:** 2026-09-01 sonrası henüz gözlenmemiş prospektif veri; mevcut annual setten final-test iddiası yok.
- **Outcome:** Integer Celsius bins −50…50; primary multiclass log loss, secondary Brier/RPS.
- **Baselines:** Seasonal climatology Gaussian, raw NBM Gaussian, raw NBM quantile CDF, raw GEFS Gaussian.
- **Gates:** OOS ≥170, finite/sum-valid probability %100; bu ilk koşu descriptive, EV/trading kararı yok.
- **Attempt 1:** Skor oluşmadan Fahrenheit discrete-bucket validator 1°C sınıf aralığını reddetti; locked Celsius outcome değişmedi, doğrudan CDF-boundary hesabı corrective implementation olarak kullanıldı.

### D-0110 — 2026-09-05 — İlk annual baseline walk-forward sonucu

- **Durum:** `ACTIVE`
- **Quality:** 298 development event, ilk 120 train, 178 one-step OOS (2026-01-01–06-30); invalid vector 0, gate geçti.
- **Primary log loss:** NBM Gaussian 2.0608; climatology 3.4633; NBM quantile 3.9851; GEFS Gaussian 3.9866.
- **Evidence:** NBM Gaussian eksi climatology −1.4025, date-bootstrap %95 CI [−1.5545, −1.2396].
- **Tail failure:** NBM quantile 15 ve GEFS Gaussian 7 eventte floor-like log loss >20; sırasıyla finite-support tail ve underdispersion işareti.
- **Regime:** NBM v5.0 döneminde Gaussian/quantile 1.701/1.750; v4.3'te 2.218/4.958. Version farkı zaman/mevsimle confounded, nedensel upgrade sonucu değildir.
- **Decision:** Raw NBM Gaussian calibration için reference baseline; quantile tail ve GEFS spread calibration olmadan reddedilir.
- **Boundary:** Development OOS descriptive; prospective final test, market benchmark ve EV yok.

### D-0111 — 2026-09-05 — NBM Gaussian calibration deneyi ön kaydı

- **Durum:** `ACTIVE`
- **Hipotez:** Strictly-prior expanding grid calibration, raw NBM Gaussian'a karşı ≥%2 OOS log-loss iyileşmesi sağlar ve Brier'ı kötüleştirmez.
- **Grid:** Bias −5…+5°F / 0.25°F; spread scale 0.5…3.0 / 0.25; past mean log loss selection.
- **Protocol:** Aynı frozen development cohort, ilk 120 train ve exact 178 one-step OOS; günlük refit, deterministic tie-break.
- **Strong gate:** Calibrated-minus-raw paired-date bootstrap %95 CI upper <0; exact OOS=178.
- **Boundary:** Consumed Temmuz–Ağustos ve prospektif final test kapalı; market/EV/orders yok.

### D-0112 — 2026-09-05 — Expanding NBM calibration gate başarısız

- **Durum:** `ACTIVE`
- **Quality:** 451 candidate, exact 178 OOS; pipeline gate geçti.
- **Result:** Raw/calibrated log loss 2.0608/2.0893; relative improvement −%1.385; Brier farkı +0.00991.
- **Uncertainty:** Calibrated-minus-raw %95 CI [−0.0274,+0.0840]; strong/practical gate ikisi de `FAILED`.
- **Failure mode:** v4.3'te −0.032 log-loss farkı, v5.0'da +0.167; expanding geçmiş düzeltmesi regime upgrade sonrasında zarar verdi.
- **Decision:** Calibration v1 reddedildi, eşikler değişmedi; raw NBM Gaussian reference baseline olarak korunuyor.
- **Learning:** Provider version/drift state'i calibration modelinde zorunlu; aynı consumed OOS üzerinde yeni strong-evidence iddiası kurulamaz.
- **Boundary:** Pozitif EV/trading kanıtı yok.

### D-0113 — 2026-09-05 — NBM residual drift diagnostic ön kaydı

- **Durum:** `ACTIVE`
- **Hypothesis:** v4.3/v5.0 residual bias veya spread farkı ortak expanding calibration'ın failure mode'unu açıklar.
- **Data:** 2026-06-30'a kadar 298 development row; artık consumed diagnostic, yeni strong-evidence skoru değil.
- **Metrics:** Bias/std/MAE/RMSE, standardized residual mean/std ve nominal %50/%80/%90 coverage; version/month/exact-proxy slices.
- **Drift flags:** Her version ≥30 row; bias farkı ≥1°F veya spread ratio ≥1.25 ortak calibration'ı unsafe işaretler.
- **Calibration flag:** Nominal %80 coverage mutlak hatası >10 puan ise raw spread miscalibrated kabul edilir.
- **Boundary:** Bu diagnostic yeni model başarısı değildir; prospective aday ayrı dondurulacak.

### D-0114 — 2026-09-05 — NBM version drift tüm preregistered flag'leri tetikledi

- **Durum:** `ACTIVE`
- **Bias:** v4.3 +1.085°F, v5.0 −0.885°F residual mean; absolute fark 1.969°F ≥1°F.
- **Spread:** v4.3/v5.0 residual std 3.748/2.056°F; ratio 1.823 ≥1.25.
- **Coverage:** Nominal %80 interval v4.3=%70.49, v5.0=%90.74; iki rejim zıt miscalibration gösteriyor.
- **Overall:** 298 row MAE 2.577°F, RMSE 3.657°F; nominal %50/%80/%90 coverage %51.34/%74.16/%85.23.
- **Decision:** Ortak-version expanding calibration `UNSAFE`; üç preregistered drift flag'i de true.
- **Caveat:** Version ile mevsim/tarih confounded; diagnostic mekanizma sinyali verir, nedensellik veya yeni OOS improvement kanıtı değildir.
- **Next design:** Raw NBM ile yalnız-v5 frozen moment calibration iki aday olarak prospektif dönemde karşılaştırılacak.

### D-0115 — 2026-09-06 — EMOS-style ridge development modeli ön kaydı

- **Durum:** `ACTIVE`
- **Mean model:** Ridge; NBM mean, GEFS−NBM disagreement, seasonal sin/cos, NBM v5, GEFS exact ve outside-hour features.
- **Nested protocol:** Outer ilk 120 train/178 OOS; her adımda geçmişin son 30 günü inner blocked validation.
- **Selection:** Lambda {0.1,1,10,100} × NBM spread scale {0.75,1,1.25,1.5,2}; inner log loss.
- **Promotion:** Raw NBM'e karşı ≥%3 log-loss improvement, Brier ≤0 fark ve paired-date CI upper <0.
- **Interpretation:** Dönem daha önce consumed olduğu için promotion yalnız prospective challenger freeze anlamına gelir; independent final-test değildir.
- **Boundary:** Market/EV/trading yok.

### D-0116 — 2026-09-06 — EMOS-style ridge promotion gate başarısız

- **Durum:** `ACTIVE`
- **Quality:** Exact 178 nested walk-forward OOS; implementation/data gate geçti.
- **Result:** Raw/EMOS log loss 2.0608/2.1090; relative improvement −%2.339; Brier farkı +0.01113.
- **Uncertainty:** EMOS-minus-raw %95 CI [−0.1069,+0.2092]; promotion `FAILED`.
- **Temporal stability:** Ocak/Şubat fark −0.222/−0.047; Mart–Haziran +0.231/+0.097/+0.152/+0.063.
- **Decision:** Ridge v1 reddedildi; ek veri olmadan feature/model complexity artırılmayacak.
- **Champion:** Raw NBM Gaussian development champion olarak freeze edilecek; gerçek değer artık market executable fiyatına incremental comparison ile sınanacak.
- **Boundary:** Forecast skill, pozitif net EV değildir.

### D-0117 — 2026-09-06 — Forecast champion ve Paper Day 1 settlement ön kaydı

- **Durum:** `ACTIVE`
- **Champion:** `RAW_NBM_GAUSSIAN_V1`; prior-day 07Z f41, Gaussian(mean, max(sd,1°F)); baseline artifact checksum-locked.
- **Paper event:** Chicago/KORD 2026-09-04, event 952456, checksum-locked executable books/fees/decisions.
- **Outcome sources:** Official api.weather.gov KORD local-day observations + terminal Gamma market outcomes.
- **Gates:** NOAA obs ≥20, exactly one Gamma YES winner, NOAA max bucket = Gamma winner.
- **P&L:** Frozen decisions only; Gaussian `NO_TRADE`, quantile hypothetical fill cost+fee; outcome sonrası karar değişmez.
- **Boundary:** Tek event edge kanıtı değildir, canlı emir yok.

### D-0118 — 2026-09-06 — Paper Day 1 NOAA/Gamma settlement reconciliation geçti

- **Durum:** `ACTIVE`
- **NOAA:** KORD local-day query 314 temperature observation; rounded maximum 93°F → `92–93°F` bucket.
- **Gamma:** Exactly one resolved YES winner, market 4115804 `92–93°F`; NOAA bucket exact match.
- **Frozen Gaussian:** `NO_TRADE`, paper P&L $0; outcome sonrası karar değişmedi.
- **Frozen quantile:** `86–87°F` $10 VWAP paper buy kaybetti; $0.445 fee dahil P&L −$10.445.
- **Learning:** Finite-tail quantile'ın calibration failure'ı ekonomik zarara dönüştü; forecast calibration gate trading öncesi zorunlu.
- **Decision:** `RAW_NBM_GAUSSIAN_V1` tek forecast champion; quantile strategy `REJECTED`.
- **Boundary:** n=1 execution observation edge/kârlılık kanıtı değildir; canlı işlem yok.

### D-0119 — 2026-09-06 — Upcoming discovery source-regime düzeltmesi

- **Durum:** `ACTIVE`
- **Attempt:** 123 active event içinde Chicago Sep 6/7 bulundu fakat legacy Wunderground-only primary check ikisini yanlış dışladı.
- **Observed source:** Exact `https://www.weather.gov/wrh/timeseries?site=kord`; Paper Day 1 settlement'ta doğrulanan NOAA WRH family.
- **Correction:** Supported primary allowlist Wunderground KORD veya exact NOAA WRH KORD; arbitrary KORD URL fail-closed.
- **Timing:** Sep 6 eventinin 11Z decision zamanı kaçtı; Sep 7 event 968537 bir sonraki eligible aday.
- **Boundary:** Source kuralı sonucu etkileyen veri görülmeden yalnız observed contract'a göre düzeltildi; order yok.

### D-0120 — 2026-09-06 — Discovery decision-time eligibility düzeltmesi

- **Durum:** `ACTIVE`
- **Failure:** Source-corrected run Sep 6 eventini seçti; event açık olsa da prior-day 11Z strategy decision time geçmişti.
- **Correction:** `eventDate−1 day 11:00 UTC >= observed_at` zorunlu `decision_time_future` gate'i eklendi.
- **Expected:** Sep 6 fail-closed; Sep 7/event 968537 seçilecek.
- **Boundary:** Geçmiş snapshot yeniden yaratılmayacak; look-ahead/execution backfill yok.

### D-0121 — 2026-09-06 — Gaussian Paper Day 2 config donduruldu

- **Durum:** `ACTIVE`
- **Event:** 968537, Chicago/KORD Sep 7, 11 buckets; exact NOAA WRH rule hash ve token identity checksum.
- **Window:** 2026-09-06 10:45–11:15 UTC; runner window dışında network/data write öncesi fail-closed.
- **Model:** Yalnız `RAW_NBM_GAUSSIAN_V1`; quantile paper-decision kolu disabled.
- **Execution:** $10/bucket ask-depth VWAP, live fee reconciliation, 2pp resolution haircut, adjusted edge ≥3pp.
- **Safety:** Paper only, orders false; outcome henüz kullanılmayacak.

### D-0122 — 2026-09-06 — Paper Day 2 local heartbeat önerildi

- **Durum:** `ACTIVE`
- **Schedule:** 2026-09-06 10:45 UTC / 13:45 Europe/Istanbul, single occurrence.
- **Action:** Frozen Day 2 config ile immutable raw/processed capture, test/QC, plan/report update ve mevcut branch'e commit/push.
- **Safety:** Gaussian-only paper decision; orders/wallet/credentials false; capture-window gate fail-closed.
- **Host dependency:** Local execution için laptop uyku modunda olmamalı ve internet bağlantısı bulunmalı.

### D-0123 — 2026-09-06 — Gaussian Paper Day 2 capture geçti ve sinyal üretti

- **Durum:** `ACTIVE`
- **Timing:** 10:49–10:50 UTC inside locked window; forecast-to-last-book skew 0.874s.
- **Forecast:** NBM v5.0 07Z f41, mean 79°F, sd 2°F; probability sum 1.0.
- **Execution:** 11/11 bucket $10 ask-depth executable; fee identity 11/11, request error 0.
- **Signal:** `76–77°F`; q=0.18657, $10 VWAP=0.09, taker fee=$0.455.
- **Edge:** Gross +9.657pp, fee sonrası +9.247pp, 2pp resolution haircut sonrası +7.247pp ≥3pp.
- **Decision:** `PAPER_TRADE`, 111.111 hypothetical shares; `order_sent=false`.
- **Boundary:** Outcome/P&L pending; tek açık sinyal pozitif EV veya kârlılık kanıtı değildir.

### D-0124 — 2026-09-06 — Multi-city historical inventory pivot ön kaydı

- **Durum:** `ACTIVE`
- **Known source:** 8,222 closed highest-temperature event, 54 city, 89,536 bucket; prior metadata counts disclosed.
- **Hypothesis:** ≥40 şehirde ≥30 exactly-one-winner, source/unit/date ve tüm bucket identity-complete event bulunur.
- **Eligibility:** Closed, eventDate, resolution source, temperature unit, exactly one resolved YES winner, complete market/condition/token identities.
- **Gates:** Duplicate 0, eligible event ≥%90, eligible city ≥40, research city ≥40.
- **Output:** Immutable normalized event registry + per-city/source/unit/exclusion coverage; price/forecast join sonraki ayrı gate.
- **Boundary:** Bu envanter EV/backtest sonucu değildir; orders false.

### D-0125 — 2026-09-06 — Multi-city parser attempt 1 post-hoc düzeltmesi

- **Durum:** `ACTIVE`
- **Attempt 1:** 262/8,222 eligible; unit ambiguity 7,321 ve missing eventDate 450 nedeniyle gate fail.
- **Root cause:** Rule text toggle talimatında hem °F hem °C geçiyor; gerçek bucket label'ları tek ve açık unit taşıyor.
- **Correction (post-hoc):** Unanimous bucket-label unit primary; description fallback. Missing eventDate için endDate UTC calendar date explicit provenance fallback.
- **Unchanged:** Source/winner/identity şartları ve tüm numeric gate eşikleri değişmedi.
- **Retry:** Yeni immutable v2 output; attempt 1 overwrite edilmeyecek.

### D-0126 — 2026-09-06 — Multi-city normalized inventory gate geçti

- **Durum:** `ACTIVE`
- **Coverage:** 7,573/8,222=%92.107 eligible; 52 eligible city, ≥30 eventli 48 research city/7,512 event.
- **Identity:** 82,407 bucket; duplicate event 0; exactly-one terminal winner ve full bucket identity tüm admitted rows'ta.
- **Units:** Celsius 5,655, Fahrenheit 1,918 event.
- **Sources:** Wunderground 7,312, NOAA weather.gov 261 admitted event.
- **Dates:** 2025-12-30–2026-08-29; eventDate 7,124, explicit endDate fallback 449.
- **Exclusions:** Missing source 639, winner-count anomaly 10, incomplete identity 2; reason'lar overlap olabilir.
- **Decision:** Inventory gate `PASSED`; 48-city universe multi-horizon price-series coverage'a alınacak.
- **Boundary:** Forecast/price henüz join edilmedi; EV/P&L yok.

### D-0127 — 2026-09-06 — Multi-city price-horizon pilot ön kaydı

- **Durum:** `ACTIVE`
- **Sample:** 48 research city × 2 deterministic early/late-half event = exactly 96 unique event.
- **Horizons:** Event end zamanından 6/12/18/24/36 saat önce; yalnız cutoff-oncesi son YES price.
- **Usable vector:** Tüm bucket'lar mevcut ve her nokta en fazla 12 saat stale; coverage normalization öncesi ölçülür.
- **Gates:** Request error ≤%2; en az bir horizonda full-vector event ≥%20; herhangi horizonda usable event bulunan city ≥30; duplicate 0.
- **Known evidence:** Chicago probe 30/30 eventte any-history bulmuştu; multi-city ve horizon-complete coverage bilinmiyor.
- **Boundary:** Price-only indicative benchmark; historical L2/fill, forecast, EV veya P&L iddiası yok; orders false.

### D-0128 — 2026-09-06 — Multi-city price-horizon pilot gate geçti

- **Durum:** `ACTIVE`
- **Retrieval/QC:** 1,056/1,056 token request başarılı; 4,381 point; duplicate/conflict/out-of-window/non-strict 0.
- **Coverage:** 6h %75 (72/96), 12h %75, 18h %75, 24h %62.5 (60/96), 36h %56.25 (54/96).
- **Breadth:** 48/48 city en az bir horizonda usable full-vector event içeriyor.
- **Missingness:** Horizon uzadıkça incomplete vector artıyor: 6h 16 event → 36h 41 event; stale-complete kayıp 1–8 event.
- **Market diagnostic:** Usable vector median raw YES sum 1.0305–1.0475; scoring öncesi raw sum korunup categorical normalization gerekli.
- **Decision:** Gate `PASSED`; 96-event cohort model-ready multi-city pilot join'ine alınabilir.
- **Boundary:** Bunlar indicative price; historical spread/depth/fill veya net EV kanıtı değil. Execution doğrulaması ayrı kalacak.

### D-0129 — 2026-09-06 — Multi-city station mapping ön kaydı

- **Durum:** `ACTIVE`
- **Hypothesis:** Frozen 96 eventin ≥%85'i ve ≥40 city exact resolution station + official coordinate ile fail-closed eşlenebilir.
- **Rules:** Wunderground final ICAO path veya NOAA WRH exact `site`; city-centroid fallback yok; station değişimi ayrı regime.
- **Gates:** Parse ≥%95, coordinate ≥%85, mapped city ≥40, duplicate 0, admitted known identity mismatch 0.
- **Known evidence:** Önceden 11 reviewed identity var; Karachi/OPKC rule-source contradiction known ve dışlanacak; 96-event coverage bilinmiyor.
- **Boundary:** Forecast retrieval/model/EV yok; orders false.

### D-0130 — 2026-09-06 — Station mapping v1 metadata coverage gate başarısız

- **Durum:** `ACTIVE`
- **Parse:** Resolution URL→ICAO 96/96=%100; duplicate 0.
- **Coordinate coverage:** 22/96=%22.92 ve 11 city; locked ≥%85/≥40 gate'leri başarısız.
- **Identity safety:** Known mismatch admitted 0.
- **Root cause:** Önceki AviationWeather evidence snapshot yalnız küçük manual-review cohort'unu içeriyor; global 48-city metadata kataloğu değil.
- **Decision:** v1 `FAILED`; eşikler değiştirilmedi. Mevcut official NOAA ISD global catalog ile corrective v2 ön kayıtlanacak.
- **Boundary:** Forecast/model/EV yok; eksik coordinate için city centroid kullanılmadı.

### D-0131 — 2026-09-06 — Station mapping corrective v2 ön kaydı

- **Durum:** `ACTIVE`
- **Correction:** Aynı sample/eşik/parser; 12-station snapshot yerine frozen official NOAA ISD global history catalog.
- **Join:** Exact uppercase ICAO; multiple rows için latest END/BEGIN; finite physical coordinates; centroid/fuzzy fallback yok.
- **Activity:** BEGIN≤target ve END staleness≤550 gün, açık `RECENT_ACTIVITY_PROXY`; 2026 observation availability iddiası değil.
- **Safety:** Önceki independent evidence'ta identity mismatch olan ICAO admission dışı; izin verilen mismatch 0.
- **Known result:** v1 %100 parse fakat %22.92 coordinate/11 city; v2 full join coverage henüz bilinmiyor.
- **Boundary:** Forecast/model/EV yok; orders false.

### D-0132 — 2026-09-06 — Station mapping corrective v2 gate geçti

- **Durum:** `ACTIVE`
- **Coverage:** ICAO parse 96/96; official ISD coordinate 92/96=%95.83; 46 mapped city; duplicate 0.
- **Exclusions:** Karachi/OPKC 2 known identity mismatch; Panama City/MPMG 2 missing admissible ISD coordinate.
- **Regime:** Paris sample LFPB ve LFPG içeriyor; ayrı station regimes olarak korunacak.
- **Review depth:** 20 admitted event prior manual identity review taşıyor; diğer exact ICAO join'ler forecast availability için yeterli, live promotion için değil.
- **Decision:** Corrective v2 `PASSED`; 46-city/92-event cohort GEFS archive availability pilotuna alınacak.
- **Boundary:** `RECENT_ACTIVITY_PROXY` target-date observation kanıtı değil; forecast accuracy/model/EV henüz yok.

### D-0133 — 2026-09-06 — Multi-city GEFS availability ön kaydı

- **Durum:** `ACTIVE`
- **Cohort:** Station gate'ten geçen exact 92 event/46 city; official coordinate→frozen IANA 2026c timezone.
- **Forecast:** Target local date prior-day GEFS 00Z; local günle overlap tüm canonical 6h TMAX step; `geavg`+`gespr`, data+idx.
- **Horizons:** Event endDate−6/12/18/24/36h; pair'in later S3 LastModified zamanı cutoff'tan önce olmalı.
- **Primary gate:** 18h complete+admissible event ≥%90, city ≥40; timezone failure 0, listing error ≤%2, duplicate 0.
- **Known evidence:** KORD representative archive continuity geçmişte geçti; multi-city step/publication coverage bilinmiyor.
- **Boundary:** Inventory-only; değer/accuracy/model/EV yok; aggregate products full ensemble değil; orders false.
- **Pre-data amendment:** Horizon cutoff için gereken `endDate`, frozen 96-event selected manifestten explicit dependency olarak eklendi; sample/eşik/metrik değişmedi.

### D-0134 — 2026-09-06 — Multi-city GEFS availability gate geçti

- **Durum:** `ACTIVE`
- **Retrieval/QC:** 40 unique run-date listing başarılı; request/timezone/duplicate failure 0; required pair missing 0.
- **Availability:** 6/12/18/24h'de 92/92 event ve 46/46 city complete+publication-admissible.
- **36h boundary:** 0/92; tüm dosyalar var fakat cutoff sonrası yayımlanmış. Bu contractta 36h GEFS feature dışı.
- **Local-day semantics:** 6 event exact 4-block partition; 86 event 5-block overlap ve 6 saat outside-local contamination.
- **Decision:** Primary model-vs-market horizon 18h; 6/12/24h secondary. GEFS overlap proxy ve contamination feature birlikte tutulacak.
- **Boundary:** Henüz forecast value indirilmedi; availability accuracy/edge/EV kanıtı değil.

### D-0135 — 2026-09-06 — Multi-city GEFS extraction pilot ön kaydı

- **Durum:** `ACTIVE`
- **Parent:** 18h usable market vector ∩ admitted station ∩ admissible GEFS = known 70 event/44 city.
- **Pilot:** Longitude/latitude/date/event sıralamasında eşit aralıklı 12 event; outcome/price/forecast değeri selection dışı; ≥10 city.
- **Extraction:** Prior-day 00Z `geavg`+`gespr`, local-day overlap tüm 6h TMAX block, yalnız indexed byte range, nearest grid decode.
- **Gates:** Message success ≥%98, content/leakage 0, coordinate delta ≤0.36°, physical value ranges, projected 70-event transfer <2 GiB.
- **Known evidence:** KORD compact extraction geçti; global değerler ve transfer maliyeti bilinmiyor.
- **Boundary:** Pilot training set değil; aggregate/full ensemble ve overlap/resolution eşdeğer değil; outcome/EV yok.

### D-0136 — 2026-09-06 — Global GEFS compact extraction pilot geçti

- **Durum:** `ACTIVE`
- **Sample:** Longitude-stratified 12 event/12 city; SF→Wellington geographic span.
- **Retrieval:** 116/116 message success; 1 transient retry ile recovered; content error ve temporal leakage 0.
- **Cost:** 44,778,354 byte observed; 70-event/690-message projection 266,354,002 byte (~254 MiB) <2 GiB.
- **Spatial QC:** Max station-grid delta 0.1669° ≤0.36°.
- **Values:** GEFS mean 45.95–102.47°F (median 78.17); spread 0.36–3.06°F (median 1.08); finite/plausible gate geçti.
- **Decision:** Pilot `PASSED`; frozen 70-event parent için full compact ingestion ekonomik ve teknik olarak uygun.
- **Boundary:** Outcome kullanılmadı; bu model/accuracy/EV sonucu değil.

### D-0137 — 2026-09-06 — Full 70-event GEFS ingestion ön kaydı

- **Durum:** `ACTIVE`
- **Scope:** Frozen 18h intersection'ın tamamı, 70 event/44 city/expected 690 message; outcome/forecast-value selection yok.
- **Contract:** Pilotla aynı prior-day 00Z aggregate TMAX indexed-range ve nearest-grid decode.
- **Gates:** Event 70/city≥44, message success ≥%98, content/leakage 0, grid delta≤0.36°, physical ranges, transfer<2 GiB.
- **Known pilot:** 116/116 success, 44.8 MB; projected parent 266.4 MB; max delta 0.1669°.
- **Boundary:** Bu forecast input layer; outcome/market join ve model fit henüz yok.

### D-0138 — 2026-09-06 — Full 70-event GEFS ingestion gate geçti

- **Durum:** `ACTIVE`
- **Coverage:** 70 event/44 city, 690/690 message success; 7 transient retry recovered; terminal content/leakage 0.
- **Transfer:** 248,128,443 byte (~236.6 MiB), locked 2 GiB sınırının altında.
- **Spatial/value QC:** Max grid delta 0.1669°; mean 38.75–105.89°F, spread 0.18–5.22°F; tümü finite/plausible.
- **Semantics:** 5 event 8-message exact partition, 65 event 10-message overlap proxy.
- **Artifact note:** Immutable raw result legacy `PILOT_PASS` label taşıyor; metrik/gate doğru, tracked karar `GEFS_FULL_INGESTION_PASS`; runner geleceğe dönük düzeltildi.
- **Decision:** Full forecast input layer `PASSED`; event-level outcome/market join açılabilir.
- **Boundary:** Henüz model fit veya edge/EV yok.

### D-0139 — 2026-09-06 — Multi-city model-ready join ön kaydı

- **Durum:** `ACTIVE`
- **Cohort:** Upstream frozen 18h intersection, exact 70 event/44 city; event_id one-to-one join.
- **Market/outcome:** Exactly-one terminal winner; raw YES vector/sum korunur, positive full vector normalize edilir.
- **Buckets:** Native integer bounds; ±0.5 native continuity correction sonra °F threshold; open tails korunur.
- **GEFS:** Overlap-block max mean, aynı peak-step spread (tie→lowest step), max block spread; exact/outside-local metadata.
- **Gates:** Exact 70/44, duplicate/missing/nonfinite/leakage/winner/message mismatch 0, normalization error≤1e-9.
- **Boundary:** Fit bu gate'ten sonra; indicative market fill değil, overlap proxy resolution-equivalent değil; EV yok.
- **Pre-data amendment:** Exact/overlap, outside-local, expected message ve cutoff için frozen GEFS horizon artifact explicit dependency eklendi; cohort/formül/eşik değişmedi.

### D-0140 — 2026-09-06 — Multi-city model-ready dataset gate geçti

- **Durum:** `ACTIVE`
- **Join/QC:** 70/70 event, 44 city; exclusion/duplicate/missing/nonfinite/leakage/winner/message mismatch 0; normalization error max 1.11e-16.
- **Span:** 2026-03-28–2026-08-21; 54 °C/16 °F; her event 11 bucket; 7 tail winner.
- **Sparsity:** 26 city iki, 18 city tek event; yalnız 5 exact partition, 65 overlap proxy.
- **Market:** Raw probability sum 0.9615–1.113, median 1.033; raw diagnostic ve normalized vector birlikte saklandı.
- **Decision:** Dataset gate `PASSED`; ilk evaluation chronological ve düşük kapasiteli fixed baseline olmalı. City-specific/high-capacity fit yasak.
- **Boundary:** Dataset-ready model-skill veya EV kanıtı değildir; historical prices indicative.

### D-0141 — 2026-09-07 — Multi-city fixed benchmark ön kaydı

- **Durum:** `ACTIVE`
- **Split:** Development ≤Jul11 n=34; validation Jul12–18 n=16; untouched test ≥Jul20 n=20; aynı target-date bölünmez.
- **Models:** Uniform, normalized 18h market, raw GEFS Gaussian (spread floor 1°F), fixed 50/50 market-GEFS blend; tuning yok.
- **Primary hypothesis:** Blend test log loss markete göre ≥%2 iyi, Brier farkı≤0 ve target-date cluster-bootstrap paired log-loss CI95 upper<0.
- **Metrics:** Log loss floor 1e-6; Brier/RPS; 10,000 date-cluster bootstrap, seed 20260907.
- **Boundary:** Pass yalnız research signal; small clustered sample ve indicative/non-executable price; live authorization yok.

### D-0142 — 2026-09-07 — Fixed GEFS-market blend reddedildi

- **Durum:** `ACTIVE`
- **Test scores:** Market/GEFS/blend/uniform log loss 1.2567/6.2400/1.7168/2.3979; Brier 0.6643/1.2320/0.8464/0.9091.
- **Incremental result:** Blend markete göre log loss'u %36.61 kötüleştirdi; Brier farkı +0.1821.
- **Uncertainty:** Date-cluster paired blend−market log loss +0.4601, CI95 [+0.3321,+0.6149], 8 test date cluster.
- **Slices:** GEFS hem °C/°F hem exact/proxy segmentlerinde marketten kötü; tek bir contamination açıklaması yeterli değil.
- **Decision:** `FIXED_BLEND_REJECT`; normalized 18h market mevcut benchmark champion. Raw GEFS Gaussian ve 50/50 blend promote edilmez.
- **Test policy:** Jul20+ test consumed; weight/spread tuning veya model selection için yeniden kullanılamaz.
- **Boundary:** Historical market indicative, execution/EV yok; sonuç live trading yetkisi vermez.

### D-0069 — 2026-09-03 — Paper day 1 identity ve dual-model runner hazır

- **Durum:** `ACTIVE`
- **Lock:** Day 1 target Sep 4, event 952456, rule hash `98b9…3c85`, 11 market identity önceki checksum-locked discovery'den; cohort forecast/price görülmeden config oluşturuldu.
- **Runner:** Aynı immutable NBM/books üzerinde Gaussian + quantile probabilities, TV, V2 fee, $10 VWAP ve model-başına locked paper threshold kararı üretiyor; `order_sent=false`.
- **Kalite:** 111/111 full tests, scoped Ruff 0; day config JSON valid.
- **Zaman:** İlk run yalnız 2026-09-03 10:45–11:15 UTC içinde eligible.

## 13. Open Questions

- Polymarket historical L2/order-book verisi ne kadar geriye ve hangi çözünürlükte erişilebilir?
- Mevcut weather marketlerin her biri hangi istasyon ve resolution source'u kullanıyor?
- Forecast-as-issued arşivlerinde NBM/GEFS/HRRR/ECMWF için maliyet ve retention nedir?
- Polymarket weather fee/rebate schedule market metadata ile tarihsel olarak versioned alınabilir mi?
- Negative-risk marketlerde tüm bucket'ları kapsayan gerçek execution mekaniği nedir?
- Türkiye'den kullanım, fonlama, vergi ve raporlama açısından hangi profesyonel doğrulamalar gerekir?
- İlk veri toplama döneminde yeterli market sıklığı ve depth var mı?

## 14. Next Action

**Tek sonraki adım:** GEFS mean error ve spread miscalibration'ını yalnız development+validation üzerinde tanıla; testte tuning yapma. Sonuca göre nested chronological calibration challenger veya GEFS feature'ını bırakma kararı ver.

Paper Day 1 frozen settlement reconciliation ve yeni 14:00 order-book capture, forecast dataset çalışmasını engellemeyen paralel execution-evidence işi olarak korunur.

Beklenen artifact'lar:

- `src/weather_quant/ingestion/polymarket_markets.py`
- sanitized API fixtures ve identifier contract testleri
- WebSocket raw event/replay contract'ı
- forced reconnect + REST reconciliation artifact'ı

Phase 1 sonunda experiment planı, experiment index ve project Decision Log ölçülen coverage/missingness sonuçlarıyla güncellenecek ve ayrı experiment commit'i oluşturulacaktır. Phase 0'ın kalan idari işi lisans seçimidir.
