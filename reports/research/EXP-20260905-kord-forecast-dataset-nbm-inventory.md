# EXP-20260905 — KORD annual NBM 07Z inventory

**Karar:** `NBM_SOURCE_INVENTORY_PASS`

365 hedef günün her biri için bir önceki günün NBM 07Z probabilistic text object'i HEAD metadata ile ölçüldü.

| Metrik | Sonuç | Yorum |
|---|---:|---|
| Mevcut object | 365/365 | %100 |
| Terminal transport hatası | 0 | Geçti |
| 11:00 UTC kararından önce yayımlanan | 362/365 | %99,178; gate geçti |
| Geç yayımlanan | 3 | Dataset'ten dışlanacak |

Geç yayımlanan source run tarihleri 2026-01-25, 2026-02-21 ve 2026-05-07'dir. Bunların hedef günleri sırasıyla 26 Ocak, 22 Şubat ve 8 Mayıs'tır. Alternatif cycle veya ileri tarihli veri kullanılmayacaktır.

Tam 365 ülke dosyasını indirmek yaklaşık 11,83 GiB gerektirir. Sonraki adım yalnız KORD station block'unu güvenilir biçimde çıkaran compact ingestion yaklaşımını doğrulamaktır. Required NBM alan coverage'ı ancak içerik parse edildikten sonra kesinleşir.

Bu aşamada hiçbir feature değeri, model skoru veya trading sonucu hesaplanmadı.
