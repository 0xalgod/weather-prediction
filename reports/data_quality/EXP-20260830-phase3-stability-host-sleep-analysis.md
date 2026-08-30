# EXP-20260830 — Phase 3 uyku-kontaminasyonlu stability koşusu

**Değerlendirme tarihi:** 2026-08-31

**Koşu:** `run=20260830T1145Z-phase3-stability-24h-v1`

**Karar:** `INVALID_FOR_STABILITY_GATE_VALID_FOR_FAILURE_DIAGNOSIS`

## Hipotez

Ara koşudaki düşük useful uptime'ın önemli bölümü collector yazılımından değil, macOS host'un
uykuya girmesinden kaynaklandı. Raw replay ayrıca uyku dışındaki protokol/state problemlerini
ayırabilmelidir.

## Ölçülen kanıt

- Collector 37.015 saniye wall-clock sonrasında kontrollü olarak kesildi; 86.400 saniyelik gate
  tamamlanmadı.
- Özet snapshot useful uptime `%82,14`, ready checkpoint coverage `%98,64` ve REST anchor match
  `%99,789` gösterdi.
- macOS `pmset -g log` gerçek Clamshell/Idle/Maintenance Sleep aralıklarını doğruladı. Önemli
  aralıklar yerel saatle 14:49–15:07, 17:32–18:37 ve 31 Ağustos 00:25–00:54'tür.
- Raw replay 27 connection dosyasında 69.461 frame ve 16.936 advertised-top mismatch üretti.
  Mismatch'ler Toronto'da 11.394, Panama City'de 5.542; Mexico City'de 0 olarak yoğunlaştı.
- İlk connection 1.269 frame/21 dakika boyunca mismatch olmadan ready kaldı. İlk host sleep
  sonrasındaki connection'larda mismatch başladı.
- Son reconnect serisinde connection başına yalnız 6/12 full book geldi. Fixed asset setinin
  market lifecycle/availability durumu da 15 saniyelik full-base gate'i için yeniden
  doğrulanmalıdır.

## Yorum

Host sleep, düşük uptime ve bazı reconnect'leri doğrulanmış biçimde açıklar; bu nedenle koşu
collector reliability gate'ine sokulamaz. Fakat sleep, advertised-top mismatch'i otomatik olarak
açıklamaz: her reconnect yeni state ile başlamasına rağmen mismatch tekrarlandı. REST anchor
eşleşmesinin çok yüksek olması state'in çoğu anchor anında executable top'u yakaladığını, fakat
event-level delta/top sözleşmesinin veya gap detection'ın hâlâ güvenilir olmadığını gösterir.

Checkpoint coverage da güvenilir değildir: mevcut runner yalnız gerçekleşen checkpointleri
paydaya koyuyor; host askıdayken kaçırılan wall-clock checkpointleri sayılmıyor.

## Karar ve düzeltme sırası

1. Koşuyu `HOST_SLEEP_CONTAMINATED_INTERRUPTED` olarak koru; 24 saat başarı/başarısızlık oranına
   dahil etme.
2. Wall-clock checkpointleri schedule slotları üzerinden say; kaçırılan slotları not-ready yaz.
3. REST anchor I/O'sunu WebSocket receive döngüsünden ayır.
4. Reconnect öncesi assetlerin hâlâ aktif/book-capable olduğunu kontrol et; lifecycle değişimini
   ayrı reason code ile bitir veya asset rotation uygula.
5. İlk mismatch öncesi ve sonrası delta'ları event-advertised top ve yakın REST anchor ile
   inceleyerek protocol state repair/gap kararını pre-register et.
6. Düzeltmeden sonra `caffeinate` altında 15 dakika regression, ardından 1 saat soak; ikisi
   geçmeden yeni 24 saat gate başlatma.

## Artifact'lar

- `reports/data_quality/EXP-20260830-phase3-stability-host-sleep-analysis.json`
- `scripts/analyze_polymarket_stability_capture.py`
- local raw: `data/raw/polymarket_ws/run=20260830T1145Z-phase3-stability-24h-v1/`
