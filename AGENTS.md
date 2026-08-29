# Weather Prediction Quant Research — Agent Operating Rules

## 1. Projenin amacı

Bu repository'nin amacı, Polymarket hava durumu piyasalarında küçük sermayeyle uygulanabilecek, maliyetler sonrası pozitif beklenen değere sahip bir niche stratejinin varlığını **veriyle sınamak** ve yalnızca yeterli kanıt oluşursa kontrollü biçimde canlıya almaktır.

Bu bir "kârlı bot yap" projesi değildir. Ana araştırma sorusu şudur:

> Belirli şehir/istasyon, lead time ve piyasa koşullarında; gerçekleşebilir fiyatlar, tüm ücretler ve execution etkileri hesaba katıldıktan sonra tekrarlanabilir pozitif EV var mı?

Başarılı sonuç, pozitif bulgu kadar güvenilir bir "edge yok" kararı da olabilir.

## 2. Kaynak önceliği

Kararlar şu kanıt sırasına göre alınır:

1. Timestamp'li ham veri ve yeniden üretilebilir analiz
2. Polymarket, NOAA/NWS, ECMWF ve çözüm kaynağı gibi birincil dokümantasyon
3. Hakemli çalışma veya resmî teknik rapor
4. Güvenilir ikincil kaynak
5. Forum, sosyal medya ve trader iddiaları — yalnızca hipotez üretmek için

Sosyal medya P&L ekran görüntüsü, win rate veya tekil trader başarısı edge kanıtı değildir.

## 3. Değişmez araştırma ilkeleri

- Her tahmin yalnızca karar anında gerçekten erişilebilir veriyi kullanmalıdır.
- Forecast `model_run_time`, `published_time`, `ingested_time` ve market snapshot `observed_at` ayrı saklanmalıdır.
- Backtestte midpoint veya kapanış fiyatı fill fiyatı gibi kullanılmamalıdır. Gerçek bid/ask, depth, fee, slippage ve partial fill modellenmelidir.
- Sonuç kaynağı, istasyon, yerel gün, saat dilimi, DST ve yuvarlama/bucket kuralları market bazında versioned olarak saklanmalıdır.
- Train/validation/test ayrımı zamansal olmalı; random split kullanılmamalıdır.
- Test dönemi, model seçimi veya feature tuning için tekrar tekrar kullanılmamalıdır.
- Eksik veri sessizce doldurulmamalıdır. İmputation yöntemi, oranı ve etkisi raporlanmalıdır.
- Model versiyonları, veri dönüşümleri ve deney konfigürasyonları yeniden üretilebilir olmalıdır.
- Brüt edge değil, **maliyet ve belirsizlik sonrası net EV** optimize edilmelidir.
- Sonuçlar şehir, istasyon, mevsim, lead time, fiyat aralığı ve maker/taker rejimine göre parçalanmalıdır.
- Bir strateji yalnızca toplu P&L pozitif diye kabul edilmez; konsantrasyon ve rejim dayanıklılığı incelenir.
- Veri yetersizliği "0 edge" değil, "karar verilemez" sonucudur.

## 4. Her iş adımında zorunlu çalışma döngüsü

Her anlamlı görevde aşağıdaki döngü izlenir:

1. `PROJECT_PLAN.md` içindeki aktif fazı ve en son decision log kaydını oku.
2. Tek cümlelik sınanabilir hipotezi tanımla.
3. Gerekli veri, zaman aralığı, metrik ve kabul/red eşiğini analizden **önce** yaz.
4. En küçük yeniden üretilebilir analizi uygula.
5. Veri kalite kontrollerini çalıştır.
6. Sonucu hem ekonomik hem istatistiksel olarak değerlendir.
7. Bulguyu artifact olarak kaydet; yalnızca terminal çıktısına bırakma.
8. `PROJECT_PLAN.md` dosyasını aynı değişiklik setinde güncelle:
   - durum ve tarih,
   - elde edilen kanıt,
   - metrikler,
   - karar,
   - varsayım değişikliği,
   - sıradaki en küçük adım.
9. Sonuç hipotezi zayıflatıyorsa planı savunmak yerine planı değiştir.

Kod veya analiz tamamlanıp plan güncellenmemişse görev tamamlanmış sayılmaz.

## 5. Plan güncelleme kuralları

- `PROJECT_PLAN.md` yaşayan tek üst-seviye plan kaynağıdır.
- Faz durumu yalnızca `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `PASSED`, `FAILED` veya `DEFERRED` olabilir.
- Her güncelleme `Decision Log` bölümüne tarihli bir kayıt eklemelidir.
- Eski kararlar silinmez; yanlışlandılarsa `SUPERSEDED` olarak işaretlenir ve yeni karara bağlanır.
- Scope genişlemesi — yeni şehir, yeni market türü, yeni veri sağlayıcı veya canlı risk artışı — veriyle gerekçelendirilmelidir.
- Bir gate başarısızsa sonraki faza geçilmez. Düzeltici deney veya projenin durdurulması seçilir.
- Metrik eşikleri sonuç görüldükten sonra değiştirilirse bu açıkça "post-hoc" olarak işaretlenmelidir.

## 6. Veri sözleşmesi ve provenance

Mümkün olduğunda immutable raw katman korunur:

```text
data/
  raw/          # Kaynaktan geldiği haliyle; elle düzenlenmez
  interim/      # Normalize edilmiş ara tablolar
  processed/    # Model-ready, versioned dataset
  external/     # Lisanslı veya manuel sağlanan referans veri
```

Her veri seti için en az şu metadata tutulur:

- kaynak ve endpoint/doküman URL'si,
- timezone ve timestamp semantiği,
- çekim zamanı,
- kapsanan market/istasyon/tarih aralığı,
- schema versiyonu,
- checksum veya immutable object kimliği,
- lisans/erişim kısıtı,
- bilinen eksikler ve kalite sorunları.

Raw veri üzerinde overwrite yapılmaz. Düzeltme gerekiyorsa yeni versiyon üretilir.

## 7. Deney ve model standardı

Her deney kaydı şunları içermelidir:

- deney ID'si,
- hipotez,
- train/validation/test tarihleri,
- dataset ve feature versiyonu,
- baseline,
- model ve hyperparameter'lar,
- pre-registered metrikler,
- calibration sonuçları,
- execution varsayımları,
- net sonuç ve belirsizlik aralığı,
- karar ve takip deneyi.

Minimum benchmark seti:

- climatology,
- basit persistence/son gözlem,
- resmî deterministik tahmin,
- ham ensemble frequency,
- varsa NBM/QMD veya eşdeğer probabilistik ürün,
- executable Polymarket fiyatı.

Model, market fiyatına karşı maliyet sonrası incremental değer göstermelidir. Yalnızca hava tahmin skorunu iyileştirmek yeterli değildir.

## 8. Backtest ve istatistiksel doğrulama

- Primary değerlendirme walk-forward out-of-sample olmalıdır.
- Aynı gün/şehir outcome'ları bağımsız kabul edilmemelidir; belirsizlik hesabında tarih/market cluster bootstrap tercih edilmelidir.
- Multiple testing ve strategy selection bias raporlanmalıdır.
- P&L ile birlikte log loss, Brier score, calibration curve/ECE, net EV, turnover, fill rate, drawdown ve capacity raporlanmalıdır.
- Ana sonuç için güven aralığı verilmelidir.
- Slippage, fee, latency ve fill varsayımlarına stress test uygulanmalıdır.
- Survivorship bias yaratacak biçimde yalnızca bugün aktif şehirler incelenmemelidir.
- Model drift ve forecast-provider versiyon değişiklikleri regime boundary olarak işaretlenmelidir.

## 9. Execution ve risk güvenliği

- Kullanıcı ayrıca açıkça istemedikçe canlı emir gönderilmez, cüzdan bağlanmaz ve credential talep edilmez.
- Paper trading, canlı işlem değildir; ikisi ayrı veri ve rapor katmanlarında tutulur.
- `PROJECT_PLAN.md` içindeki canlı gate geçilmeden otomatik trading kodu aktif hale getirilmez.
- Secret'lar repository'ye, loglara, notebook output'una veya plan dosyasına yazılmaz.
- Varsayılan emir tipi pasif limit/maker'dır; taker kullanımının gerekçesi ve beklenen değeri ayrıca ölçülür.
- Position sizing, tahminin nokta değerine değil belirsizlik düzeltilmiş edge'e dayanır.
- Full Kelly kullanılmaz. Canlı pilotta fractional Kelly ve mutlak pozisyon limitleri zorunludur.
- Aynı meteorolojik olaya bağlı pozisyonların korelasyonu toplam riskte dikkate alınır.
- Manipülasyon, veri kalite bayrağı, çözüm belirsizliği veya istasyon anomalisi varsa `NO_TRADE` uygulanır.
- Yerel hukuk, platform erişimi, vergi ve kullanım şartları canlı gate'in zorunlu girdileridir; hukuk varsayımı yapılmaz.

## 10. Kod ve artifact standardı

- Python kodu mümkün olduğunda package modüllerinde; notebook'lar keşif ve sunum için kullanılmalıdır.
- Notebook sonuçları temiz kernel ile baştan sona yeniden çalışabilmelidir.
- Deterministik seed, dependency lock ve açık konfigürasyon kullanılmalıdır.
- Kritik dönüşümler ve fee/EV hesapları unit test ile korunmalıdır.
- Veri schema ve timezone dönüşümleri için contract test yazılmalıdır.
- Büyük binary/raw dosyalar source control'e eklenmeden önce depolama politikası belirlenmelidir.
- Üretilen her raporda veri cut-off tarihi ve model versiyonu görünmelidir.

Önerilen üst seviye yapı:

```text
src/
  ingestion/
  normalization/
  features/
  forecasting/
  market_model/
  backtest/
  execution/
  risk/
tests/
configs/
notebooks/
reports/
experiments/
data/
```

## 11. Tamamlanma tanımı

Bir görev yalnızca şu koşullarda tamamlanır:

- çıktı yeniden üretilebilir,
- test/kalite kontrolü çalışmıştır,
- ekonomik varsayımlar görünürdür,
- sonuç ilgili baseline ile karşılaştırılmıştır,
- artifact dosyası kaydedilmiştir,
- `PROJECT_PLAN.md` güncellenmiştir,
- sıradaki karar veya deney açıktır.

