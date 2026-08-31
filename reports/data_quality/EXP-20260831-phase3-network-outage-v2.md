# EXP-20260831 — Phase 3 replacement v2 network-outage diagnosis

**Koşu:** `run=20260831T0820Z-phase3-stability-24h-v2`

**Karar:** `NETWORK_OUTAGE_CONTAMINATED_INTERRUPTED`

## Sonuç

Replacement v2 ilk yaklaşık iki saat boyunca temizdi. Yerel internet/DNS kesintisi sonrasında
registered gate geri döndürülemez biçimde başarısız oldu ve collector kontrollü durduruldu.

Kesinti/stop snapshot'ı:

- elapsed: 11.463 saniye;
- useful uptime: `%91,4008`;
- ready wall-clock coverage: 174/190, `%91,5789`;
- missed checkpoint: 13;
- connection attempt/error/reconnect: 117/116/117;
- advertised-top mismatch: 160;
- REST anchor: 408/408 match, 0 anchor error;
- local raw: 117 connection file, yaklaşık 6,9 MB.

Error history DNS/network kesintisini doğrudan gösterdi: `gaierror: nodename nor servname
provided` olayları `2026-08-31T10:26:00Z` itibarıyla başladı; ardından close-frame olmayan socket
kapanması ve tekrar DNS hataları görüldü. Network geri geldiğinde fresh base alınsa da aktif
price-change döneminde advertised-top mismatch state'i fail-closed invalidated etti.

## Yorum

Bu koşu collector stability başarısı veya provider outage ölçümü değildir; kullanıcı interneti
kesintisiyle kontaminedir. Buna rağmen iki gerçek failure mode kanıtladı:

1. Backoff başarılı TCP/WebSocket bağlantısı kurulur kurulmaz 1 saniyeye resetleniyor. Bağlantı
   kısa süre sonra desync olursa hızlı reconnect storm oluşuyor.
2. Network recovery sonrası event-level mismatch hâlâ çözülmemiştir. REST anchor'ların tamamı
   eşleşse de event-time state için sessiz repair yapılamaz.

## Sonraki düzeltme

- Backoff ancak bağlantı belirli bir stable grace süresini ve full-base koşulunu geçerse resetlensin.
- Ardışık desync için circuit breaker/cooldown ve reason-segmented sayaç eklensin.
- Network outage, protocol desync, lifecycle failure ve host sleep ayrı hata sınıfları olsun.
- Raw v2 replay ile ilk post-recovery mismatch öncesindeki base/delta dizisi incelensin.
- İnternet kararlı değilken yeni 24 saat gate başlatılmasın; önce forced-disconnect regression ve
  kısa recovery soak geçsin.
