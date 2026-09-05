# EXP-20260905 — KORD NBM residual drift v1

**Durum:** `PASSED_DIAGNOSTIC_DRIFT_DETECTED`

298 development satırında residual `gerçek maksimum − NBM mean` olarak ölçüldü. Bu dönem daha önce model development için tüketildiğinden sonuç yeni OOS model kanıtı değildir.

## Ana sonuç

| Rejim | n | Bias °F | Residual std °F | %80 coverage |
|---|---:|---:|---:|---:|
| NBM v4.3 | 244 | +1.085 | 3.748 | %70.49 |
| NBM v5.0 | 54 | −0.885 | 2.056 | %90.74 |

Mutlak bias farkı 1.969°F ve residual spread oranı 1.823'tür. Önceden kilitlenen 1°F ve 1.25× eşiklerinin ikisi de aşıldı; %80 coverage flag'i de tetiklendi.

Ortak expanding calibration bu nedenle unsafe kabul edildi. v4.3 düzeltmesini v5.0'a taşımak bias yönünü yanlış ve dağılımı gereğinden geniş hale getiriyor.

## Sınır ve karar

Version değişimi mevsim ve takvim zamanı ile çakışmaktadır; bu sonuç v5'in nedensel olarak daha iyi olduğunu kanıtlamaz. Sonraki aday yalnız v5 geçmişinden tek seferlik moment parametreleriyle dondurulacak ve raw NBM'e karşı yalnız 2026-09-01 sonrası prospektif veride değerlendirilecektir.
