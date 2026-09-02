# NOAA WRH KORD declared-source surface discovery

**Experiment:** `EXP-20260830-data-source-feasibility`

**Cut-off:** 2026-09-02

**Decision:** `FAILED_NOT_MACHINE_RECONCILABLE_WITHIN_OFFICIAL_ORIGIN_SCOPE`

## Amaç

Current Chicago eventlerinin declared primary URL'si `https://www.weather.gov/wrh/timeseries?site=kord`. Bu deney, resmî NOAA/NWS origin içinde exact KORD identity, timestamp, timezone, °F temperature rows ve following-local-date first observation trigger'ının makinece yeniden kurulup kurulamadığını test etti.

## Bounded retrieval sonucu

- Aynı page iki kez HTTP 200 döndü.
- Content type iki istekte aynıydı.
- İki response 64.758 byte ve aynı SHA-256 değerindeydi.
- Static HTML observation payload içermiyor; data client-side yükleniyor.
- First-party `obs.js` asset'i page tarafından version query ile referans ediliyor.

Dolayısıyla HTML transport/schema stability geçti, fakat static page tek başına station observation evidence değildir.

## Data dependency bulgusu

Resmî client script şu semantik parametreleri kuruyor:

- station `STID`;
- Fahrenheit `units=temp|F`;
- `obtimezone=local`;
- timeseries observation request.

Ancak timeseries origin `api.synopticdata.com` olup NOAA/NWS first-party origin değildir. Request bir client-side token değişkeni kullanıyor. Public credential helper'ın yalnız checksum/metadata'sı ve credential assignment bulunduğu kaydedildi; credential değeri raw katmana, artifact'a, loga veya repository'ye yazılmadı.

## Ön-kayıtlı semantic gate

| Check | Sonuç |
|---|---|
| İki page HTTP 200 | `PASSED` |
| Page schema stabil | `PASSED` |
| Page content stabil | `PASSED` |
| Official page client script referansı | `PASSED` |
| Official-origin machine endpoint | `FAILED` |
| Exact KORD machine payload | `FAILED` |
| Timestamped temperature rows | `FAILED` |
| Following-local-date trigger selection | `FAILED` |

Overall semantic gate `FAILED`.

## Revision ve operasyonel risk

NOAA WRH sayfası görüntülenen veriyi preliminary ve quality-control adjustment'a açık olarak tanımlıyor. Sayfa ayrıca download-data özelliğinin mevcut olmadığını ve geri dönüş zamanı için tahmin bulunmadığını belirtiyor. Bu iki durum quant pipeline açısından önemlidir:

- görünen değer sonradan değişebilir;
- first-publication/freeze version geçmişe dönük kanıtlanamaz;
- browser-visible data ile otomasyon için kullanılan üçüncü taraf endpoint arasında access/licensing/availability bağımlılığı vardır;
- token'ı sayfadan çıkarıp doğrudan kullanmak proje güvenlik ve provenance standardına uygun kabul edilmedi.

Revision statüsü `HISTORICAL_FREEZE_AS_OF_UNRESOLVED` kalır.

## Karar

Declared NOAA WRH page insan tarafından görüntülenebilir bir resolution surface olsa da, preregistered official-origin scope altında makinece reconcile edilebilir timestamped observation feed değildir. Chicago NOAA-primary regime bu haliyle automated exact settlement-label pipeline için `FAILED`/blocked source sınıfındadır; market outcome bucket terminal Polymarket label olarak ayrı kalır.

## Sonraki en küçük adım

Credential çıkarmadan, resmî sayfanın browser-rendered DOM'unda KORD identity, timestamp, unit ve hourly rows'un deterministik snapshot olarak saklanıp saklanamayacağı ayrı ön-kayıtla test edilecek. Bu yalnız browser-visible declared-source evidence olabilir; üçüncü taraf API erişim hakkı veya historical revision çözümü sayılmaz. Rendered DOM stabil/parse edilebilir değilse Chicago NOAA-primary exact-temperature pipeline `NO_GO` olur.
