# GEFS TMAX local-day semantik sonucu

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Data cut-off:** 2026-07-23  
**Ölçüm:** 2026-08-31  
**Kaynak:** NOAA/NCEP GEFS operational archive

## Soru

GEFS 2 m `TMAX` alanları, Polymarket'in istasyon-yerel `[00:00, sonraki 00:00)` gününe doğrudan eşit bir günlük maksimum tahmini olarak kullanılabilir mi?

Ön-kayıtlı örnekler Phase 2'de doğrulanan Toronto/CYYZ (`America/Toronto`, 2026-07-23, DST aktif) ve Kuala Lumpur/WMKK (`Asia/Kuala_Lumpur`, 2026-06-22, DST yok) kayıtlarıdır.

## Birincil ürün kanıtı

NCEP'in resmi GEFS inventory yüzeyi forecast saatine göre alan ve zaman aralığını yayınlar. Resmî f003 örneği TMAX'i `0-3 hour max` olarak gösterir: <https://www.nco.ncep.noaa.gov/pmb/products/gens/gec00.t00z.pgrb2s.0p25.f003.shtml>. Ürün sayfası atmosfer dosyalarının 192 saate kadar üç saatlik forecast-hour aralıklarında bulunduğunu belirtir: <https://www.nco.ncep.noaa.gov/pmb/products/gens/>.

Gerçek historical indeksler daha ayrıntılı bir dönüşümlü yapı gösterdi:

```text
f003 = 0-3h max      f006 = 0-6h max
f009 = 6-9h max      f012 = 6-12h max
f015 = 12-15h max    f018 = 12-18h max
...
```

Bu nedenle ön-kayıtlı “her f003 adımı `(step-3)-step` penceresidir” hipotezi yanlıştır. Günlük aggregation için kullanılabilecek canonical seri `f006, f012, f018, ...` biçimindeki ardışık 6 saatlik bloklardır.

## Ölçülen sonuç

| Metrik | Toronto | Kuala Lumpur |
|---|---:|---:|
| Yerel günün UTC karşılığı | 23 Jul 04Z–24 Jul 04Z | 21 Jun 16Z–22 Jun 16Z |
| Yerel gün süresi | 24 saat | 24 saat |
| Örtüşen canonical step'ler | 30,36,42,48,54 | 18,24,30,36,42 |
| Seçilen 6h pencere | 5 | 5 |
| Kapsanmayan hedef süre | 0 saat | 0 saat |
| Hedef gün dışından dahil olan süre | 6 saat | 6 saat |
| Exact local-day partition | Hayır | Hayır |
| Gerçek GRIB TMAX range | 5/5 geçerli | 5/5 geçerli |

On gerçek range toplam 4.259.526 byte'tır. Her biri HTTP 206, tek GRIB mesajı, `GRIB` başlangıcı ve `7777` sonlandırıcısı kontrollerini geçti. Object timestamp'leri run'dan yaklaşık 3,8–4,1 saat sonradır ve artifact'ta ayrı ayrı saklanmıştır.

## Karar

- **Gate A FAILED:** Her üç saatlik forecast dosyası bağımsız üç saatlik TMAX penceresi değildir.
- **Gözlenen canonical 6h seri PASSED:** `f006, f012, ...` blokları UTC'de gap/overlap olmadan ardışıktır.
- **Gate B FAILED:** Her iki station-local günde de exact partition yerine 6 saat boundary contamination oluşur.
- **Range integrity PASSED:** Sorun dosya yokluğu veya bozuk veri değildir; zaman penceresi semantiğidir.

GEFS interval TMAX bundan sonra resolution-equivalent günlük MaxT veya doğrudan label olarak kullanılamaz. İzin verilen kullanım:

1. Yalnız tamamen yerel gün içinde kalan üç 6h pencerenin maksimumu, 18 saatlik **interior lower-feature** olarak;
2. Yerel güne dokunan beş pencerenin maksimumu, 6 saat dış-süre bayrağı taşıyan **overlap upper-feature** olarak;
3. Her satırda run/publish/valid interval ve `outside_local_seconds` saklanarak;
4. Bu iki feature'ın istasyon outcome'larına karşı walk-forward kalibrasyonu ayrıca geçmeden olasılık veya EV girdisi sayılmayarak.

“Upper/lower” ifadeleri model gridindeki interval maksimumları arasındaki kapsama ilişkisini anlatır; gerçek istasyon sıcaklığı için fiziksel garanti değildir.

## Beklenmedik hata kaydı

İlk probe çıktısı 3h ara ve 6h canonical pencereleri birlikte seçerek coverage'ı çift saydı. Eşik değiştirilmedi; çıktı `reports/data_quality/EXP-20260831-phase4-gefs-local-day-semantics-attempt1.json` olarak korundu, seçim yalnız canonical 6h seriye düzeltildi ve nihai artifact yeniden üretildi.

## Sonraki en küçük adım

Phase 5'e geçerek CYYZ ve WMKK için kaynakla eşleşen station observation geçmişini ve revision/final semantics'i ölçmek; ardından interior/overlap/TMP feature politikalarını gerçek local-day MaxT outcome'larına karşı, analizden önce kilitlenen zaman penceresinde karşılaştırmak.
