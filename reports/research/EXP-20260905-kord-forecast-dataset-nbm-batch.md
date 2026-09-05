# EXP-20260905 — KORD annual compact NBM feature batch

**Karar:** `ANNUAL_NBM_FEATURE_GATE_PASS`

Checksum-locked source inventory'deki 362 publication-admissible NBM 07Z object compact byte-range yöntemiyle işlendi.

| Metrik | Sonuç | Gate |
|---|---:|---:|
| Retrieval + parse | 362/362 | ≥%99 — geçti |
| Required MaxT fields complete | %100 | ≥%99 — geçti |
| Retrieval failure | 0 | Geçti |
| Publication leakage | 0 | Geçti |
| Exact f41 record | 362/362 | Geçti |
| Network range bytes | 362.000.362 | Ölçüldü |
| Saklanan station bytes | 1.363.866 | Ölçüldü |

NBM v4.3 246 gün, v5.0 116 gün bulundu. İki sürümün station sırası farklı olduğu için v4.3 günlerinde ilk bounded-range denemesi KORD bulmadı; pre-registered ikinci range 246/246 günü çıkardı. Bunlar gizlenmedi ve schema-range probe miss olarak artifact'ta saklandı.

NBM-admissible ve NOAA-label-admissible günlerin kesişimi 359/365=%98,356'dır. Bu, overall joined ≥%97 gate'ini şimdilik karşılar; nihai karar GEFS ve final join sonrasında verilecektir.

NBM v4.3→v5.0 değişimi bir regime boundary'dir. Model değerlendirmesinde provider version açık feature/segment olarak tutulacak ve sonuçlar sürüm bazında raporlanacaktır.

Henüz label join tablosu dondurulmadı, split seçilmedi ve model skoru hesaplanmadı.
