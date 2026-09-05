# KORD annual model-ready dataset — final join sonucu

## Sonuç

Önceden kilitlenen veri gate'i geçti. 365 hedef günün 357'sinde (%97,808) NBM, GEFS aggregate ve LCDv2 günlük maksimum etiketi aynı KORD/hedef-tarih anahtarında birleştirildi.

- Duplicate station-date: 0
- Non-finite feature veya label: 0
- Publication leakage: 0
- Imputation veya alternatif cycle: yok
- Canonical rows SHA-256: `45d2ab2e480a27529fbd52ba8546676bdf3bc794061cad726965a994e1bc75fd`

Sekiz gün açıkça dışarıda tutuldu: 19–20 Aralık 2025 GEFS; 26 Ocak 2026 NBM+GEFS; 22 Şubat ve 8 Mayıs NBM; 29–31 Ağustos 2026 label eksikliği.

## Yorum

Bu sonuç, model eğitmek için zaman-doğru yıllık tabanın hazır olduğunu gösterir. Pozitif EV veya para kazanma kanıtı değildir: dataset henüz Polymarket executable fiyatlarını, fee/slippage/fill'i ve frozen settlement kayıtlarını içermez.

Sıradaki adım, model sonuçları görülmeden temporal split ve ilk baseline karşılaştırmasını kilitlemektir. NBM provider version ve GEFS exact/proxy ayrımları değerlendirmede ayrı slice olarak raporlanacaktır.
