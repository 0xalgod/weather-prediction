# EXP-20260905 — KORD bir yıllık forecast dataset v1

**Durum:** `IN_PROGRESS`  
**Ön kayıt tarihi:** 2026-09-05  
**Amaç:** Forecast-first model araştırması için bir tam yıllık, timestamp-doğru ve yeniden üretilebilir KORD veri seti kurmak.

## Sınanabilir hipotez

KORD için 2025-09-01–2026-08-31 arasındaki 365 hedef günün en az %97'sinde, karar anında yayımlanmış NBM ve GEFS tahmin özellikleri NOAA'nın Chicago yerel günlük maksimum sıcaklık etiketiyle sıfır temporal leakage altında birleştirilebilir.

## Neden bu deney?

Mevcut 112 günlük örnek yalnızca 2026 sıcak sezonunu kapsıyor. Basit pipeline ve baseline karşılaştırması için yararlı olsa da mevsimsel genelleme veya geniş model araması için yeterli değil. Ayrıca daha önce kullanılan 52 günlük OOS dönem artık model seçimi için tüketilmiş kabul edilir.

Bu deney model performansını ölçmez. Önce öğrenilebilir veri tabanının gerçekten var olduğunu ve zaman semantiğinin doğru olduğunu ölçer.

## Veri sözleşmesi

Her ana satır bir `station × target_local_date × decision_time` gözlemidir.

### Kimlik ve zaman

- İstasyon: KORD / `USW00094846`
- Yerel saat: `America/Chicago`, DST tarih bazında uygulanır
- Hedef: yerel takvim gününün günlük maksimum sıcaklığı
- Karar anı: hedef günden bir gün önce 11:00 UTC
- `model_run_time`, kaynak `Last-Modified`, `retrieved_at` ve hedef valid/window zamanları ayrı tutulur

### Tahmin özellikleri

- NBM 07Z: mean, standard deviation, P10/P25/P50/P75/P90 MaxT
- NBM MaxT açıkça `PROXY_18H_MAX`; tam yerel günle eşdeğer gösterilmez
- GEFS 00Z: control + 30 perturbed member; tam yerel günü oluşturan TMAX pencereleri
- Takvim: döngüsel day-of-year, ay ve DST offset

### Etiket

- NOAA LCDv2 `DailyMaximumDryBulbTemperature`
- Chicago yerel günü ve Fahrenheit
- Forecast eğitimi için primary observation label
- Tarihsel Polymarket settlement-as-of kanıtı değildir; ekonomik testte frozen resolution kaynağı ayrıca gerekir

## Önceden kilitlenen gate'ler

- Tam 365 hedef gün
- Joined eligible coverage ≥%97
- NBM required-field coverage ≥%99
- GEFS 31-member completeness ≥%97
- Label coverage ≥%99
- Publication/decision temporal leakage = 0
- Duplicate station-date = 0
- Non-finite admitted value = 0

Eksik gün için alternatif cycle, ileri tarihli kaynak, imputation veya provider değiştirme otomatik uygulanmaz. Böyle bir düzeltme yeni ve açıkça post-hoc deney gerektirir.

## Uygulama aşamaları

1. **Kaynak envanteri:** 365 gün için NBM 07Z, GEFS 00Z/31 member ve LCDv2 label erişimini yalnız metadata/index üzerinden ölç.
2. **Compact ingestion:** Yalnız gerekli station block ve GRIB byte range'lerini immutable raw katmana indir; tam ülke dosyalarını gereksiz yere çoğaltma.
3. **Normalization:** Timestamp, unit, local-day window, provider version ve checksum alanlarını normalize et.
4. **Join/QC:** Exact station/date join, leakage, duplicate, coverage ve finite kontrollerini çalıştır.
5. **Dataset freeze:** Model-ready tabloyu schema/version/checksum ile dondur.
6. **Yeni model ön kaydı:** Veri sonucunu gördükten sonra fakat model skorlarını görmeden temporal train/validation/test sınırlarını kilitle.

Her aşamadan sonra bu dosyanın durum/kanıt bölümü ve `PROJECT_PLAN.md` Decision Log güncellenir; ayrı commit ve push yapılır.

## Modelleme sınırı

Bu veri gate'i geçmeden feature seçimi, hyperparameter tuning veya yeni model skoru hesaplanmaz. İlk yarış seasonal climatology, raw NBM quantiles ve raw GEFS frequency ile başlar. Ana metrik OOS multiclass log loss; Brier, RPS, ECE ve CRPS ikincil metriklerdir.

## Bulgular

- **Label coverage (2026-09-05):** NOAA LCDv2 refresh sonucunda 362/365 gün (%99,178) non-null günlük maksimumla bulundu; ön-kayıtlı ≥%99 gate geçti.
- Eksik 2026-08-29–31 günleri provider publication lag; imputation uygulanmadı.
- Duplicate, identity ve terminal transport hatası 0.
- Kaynak sonucu checksum-locked ve ayrıntılı artifact'a bağlandı.
- **NBM inventory (2026-09-05):** Prior-day 07Z object availability 365/365; terminal transport error 0.
- Üç source object 11:00 UTC kararından sonra yayımlandı; admissible 362/365=%99,178 ve bu tarihler fallback olmadan dışlanacak.
- Tam object indirme tahmini 11,83 GiB olduğundan compact KORD extraction doğrulanmadan bulk download yapılmayacak.
- **Compact NBM validation (2026-09-05):** 1.000.001-byte range'den çıkarılan 3.684-byte KORD block, checksum-locked 34.724.473-byte full object'teki block ile exact byte match verdi.
- NBM v5.0 block 9 MaxT record ve exact bir f41 target record ile parse edildi; validation gate geçti.
- Yıllık tahmini transfer yaklaşık 348 MiB, station-block depolama yaklaşık 1,28 MiB; batch koşusunda drift fail-closed kalacak.
- **Batch runner (2026-09-05):** Checksum-locked inventory'den yalnız 362 publication-admissible günü seçen, iki schema-offset range'ini fail-closed deneyen ve her gün exact station/required fields/f41 kontrolü yapan runner eklendi.
- Batch gerçek veri koşusu henüz çalıştırılmadı; implementasyon ve contract testleri sonuçtan önce commitlenecek.
- **NBM batch result (2026-09-05):** 362/362 publication-admissible gün başarıyla alındı; required fields/exact f41 %100, retrieval failure ve leakage 0.
- NBM v4.3 246 gün, v5.0 116 gün; provider upgrade açık regime boundary olarak saklanacak.
- NBM + mevcut label kesişimi şimdilik 359/365=%98,356; overall ≥%97 gate GEFS/final join sonuna kadar provisional.
- **GEFS window semantics (2026-09-05):** 125/365 kış-saati günü exact local-day partition; 240 gün DST/boundary nedeniyle 1–6 saat outside-local contamination taşıyor.
- GEFS yıl boyunca resolution-equivalent sayılmayacak; exact veya interior/overlap proxy feature ve `outside_local_seconds` olarak açıkça saklanacak.
- **GEFS inventory runner (2026-09-05):** Günlük public S3 listing'lerinden 31 member × gerekli 4–5 canonical step için hem data hem index object ve publication timestamp kontrolü yapan runner eklendi.
- Full inventory sonucu henüz görülmedi; implementasyon ve contract testleri sonuçtan önce commitlenecek.

## Sıradaki en küçük adım

GEFS 00Z control+30 member için 365 günlük full-membership ve gerekli canonical TMAX window source envanterini ölç; exact/proxy rejim alanlarını koru ve model skoru hesaplama.
