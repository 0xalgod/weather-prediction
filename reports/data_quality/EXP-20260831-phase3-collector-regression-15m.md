# EXP-20260831 — Phase 3 collector remediation ve 15 dakika regression

**Tarih:** 2026-08-31

**Koşu:** `run=20260830T2224Z-phase3-regression-15m-v3`

**Durum:** `PASSED`

## Hipotez ve önceden yazılan gate

Host-sleep kontaminasyonundan ayrıştırılan collector; güncel ve test ufkunun sonuna kadar aktif
token seçimi, wall-clock slot accounting, non-blocking REST anchors ve fail-closed mismatch
handling ile 15 dakika boyunca güvenilir authoritative book state tutabilir.

Gate koşudan önce: elapsed ≥900 saniye, useful uptime ≥%99, ready checkpoint coverage ≥%95,
delta-before-book 0, advertised-top mismatch 0; ayrıca 60 saniyelik slotların tamamı sayılmalı ve
REST anchor sonuçları raporlanmalıydı.

## Yapılan düzeltmeler

- Asset seçim kaydına market `end_at` eklendi; market test horizon'ından önce bitiyorsa runner
  fail-closed duruyor.
- Checkpoint paydası yalnız callback sayısı yerine beklenen wall-clock slotlardan üretiliyor;
  kaçırılan slotlar `missed_checkpoint_count` olarak ayrıca tutuluyor.
- Final boundary slotu da sayılıyor; ilk v2 koşusundaki 900 saniye/14 slot sonucu bu nedenle
  geçersiz kılındı ve v3 tekrarlandı.
- REST anchor fetch'leri WebSocket receive loop dışında async task olarak çalışıyor.
- Advertised top ile reconstructed top uyuşmazsa state `desynchronized` oluyor, ready sayılmıyor
  ve fresh full-book reconnect gerektiriyor; veri sessizce tamir edilmiyor.
- Regression güncel active inventory ve 66/66 başarılı REST snapshot üzerinden seçilen 12
  two-sided tokenla `caffeinate` altında çalıştırıldı.

## Ölçülen sonuç

| Metrik | Sonuç | Gate |
|---|---:|---:|
| Elapsed | 900,068 sn | ≥900 |
| Useful uptime | %99,9592 | ≥%99 |
| Ready checkpoint | 15/15, %100 | ≥%95 |
| Missed checkpoint | 0 | 0 beklenir |
| Connection attempt/error/reconnect | 1 / 0 / 0 | — |
| Full book | 12/12 | %100 |
| Price-change / applied change | 785 / 1.570 | ≥1 |
| Delta-before-book | 0 | 0 |
| Advertised-top mismatch | 0 | 0 |
| REST anchors | 24/24 eşleşme | raporlanır |
| Anchor error | 0 | 0 |
| Heartbeat/PONG | 89/89 | sürekli |
| Raw frame/byte | 875 / 800.932 | ölçüldü |

## Karar

15 dakika remediation regression gate'i geçti. Bu sonuç 24 saat stability gate'i değildir ve
ekonomik edge kanıtı değildir. Bir sonraki pre-registered aşama aynı kod ve güncel lifecycle-safe
asset setiyle 1 saatlik caffeinated soak'tır. Soak sırasında tek mismatch bile fail-closed reconnect
üretmeli ve sonuçta ayrı raporlanmalıdır.

## Local artifact'lar

- `data/interim/polymarket_ws/regression-15m-v3.json`
- `data/raw/polymarket_ws/run=20260830T2224Z-phase3-regression-15m-v3/`

Bu dosyalar Git dışında tutulur; bu rapor sonuç özetini ve veri cut-off kimliğini korur.
