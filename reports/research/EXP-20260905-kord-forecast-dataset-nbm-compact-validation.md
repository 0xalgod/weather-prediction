# EXP-20260905 — Compact KORD NBM retrieval validation

**Karar:** `COMPACT_NBM_RETRIEVAL_PASS`

NBM 2026-07-07 07Z dosyasında bounded HTTP byte-range yöntemi, daha önce indirilmiş tam source object'e karşı doğrulandı.

| Kontrol | Sonuç |
|---|---:|
| HTTP response | 206 Partial Content |
| Tam source büyüklüğü | 34.724.473 byte |
| İndirilen range | 1.000.001 byte |
| Saklanan KORD block | 3.684 byte |
| Full-object ve range station block eşleşmesi | Exact byte match |
| Parse edilen MaxT record | 9 |
| Exact gerekli f41 record | 1 |

KORD block checksum'ı iki yolda da `e0636b…ed05a` oldu. Böylece tek validation vakasında range extraction'ın forecast değerlerini değiştirmediği kanıtlandı.

Yıllık kaba maliyet tam object'leri saklarsak 11,83 GiB; aynı range genişliğiyle yaklaşık 348 MiB ağ trafiği ve 1,28 MiB station-block depolamasıdır.

Bu yalnız tek NBM v5.0 vakasıdır. Batch ingestion her gün station identity, required marker, exact f41 ve range drift kontrollerinde fail-closed davranmalıdır. Henüz 362 günlük feature dataset oluşturulmadı veya model skoru hesaplanmadı.
