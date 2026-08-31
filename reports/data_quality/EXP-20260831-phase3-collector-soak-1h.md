# EXP-20260831 — Phase 3 remediated collector 1 saat soak

**Tarih:** 2026-08-31

**Koşu:** `run=20260831T0045Z-phase3-soak-1h-v1`

**Durum:** `PASSED_WITH_ACTIVITY_LIMITATION`

## Hipotez ve gate

15 dakika regression'ı geçen collector, `caffeinate` altında güncel ve test horizon'ı boyunca
aktif 12 token ile bir saat boyunca authoritative state, wall-clock checkpoint ve REST anchor
sözleşmesini koruyabilir.

Koşudan önce gate: elapsed ≥3.600 saniye, useful uptime ≥%99, ready coverage ≥%95,
delta-before-book ve advertised-top mismatch 0; 60 scheduled slot eksiksiz sayılmalıydı.

## Sonuç

| Metrik | Sonuç | Gate |
|---|---:|---:|
| Elapsed | 3.600,069 sn | ≥3.600 |
| Useful uptime | %99,9915 | ≥%99 |
| Ready checkpoint | 60/60, %100 | ≥%95 |
| Missed checkpoint | 0 | 0 beklenir |
| Connection attempt/error/reconnect | 1 / 0 / 0 | — |
| Full book | 12/12 | %100 |
| Delta-before-book | 0 | 0 |
| Advertised-top mismatch | 0 | 0 |
| REST anchors | 132/132 | raporlanır |
| Anchor error | 0 | 0 |
| Heartbeat/PONG | 359/359 | sürekli |
| Max inter-frame gap | 10,259 sn | heartbeat ile uyumlu |
| Raw frame/byte | 360 / 125.109 | ölçüldü |
| Price-change/applied change | 0 / 0 | faaliyet sınırlaması |

## Yorum

Transport, heartbeat, full-base persistence, scheduled-slot accounting ve non-blocking REST
reconciliation gate'i geçti. Ancak seçilen kitaplarda saat boyunca fiyat değişimi olmadığından bu
koşu delta replay'i tek başına yeniden doğrulamaz. Delta kanıtı aynı remediated code path'inin
önceki 15 dakikalık v3 regression'ındaki 785 price-change/1.570 applied change, sıfır mismatch ve
24/24 REST anchor sonucuyla birlikte değerlendirilmelidir.

Bu iki koşunun birleşik sonucu replacement 24 saat gate'i başlatmaya yeterlidir; Phase 3 henüz
`PASSED` değildir. Yeni 24 saat koşusunda market horizon guard, `caffeinate`, wall-clock slotlar,
non-blocking anchors ve fail-closed desync aynen korunacaktır.

## Local artifact'lar

- `data/interim/polymarket_ws/soak-1h-v1.json`
- `data/raw/polymarket_ws/run=20260831T0045Z-phase3-soak-1h-v1/`
