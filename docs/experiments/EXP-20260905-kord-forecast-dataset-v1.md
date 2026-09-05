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

Henüz kaynak envanteri çalıştırılmadı.

## Sıradaki en küçük adım

365 günlük kaynak envanteri runner'ını oluştur, contract testlerini yaz ve model değerlerini hesaplamadan coverage artifact'ını üret.
