# Prospective Wunderground freeze snapshot contract

**Experiment:** `EXP-20260830-data-source-feasibility`

**Cut-off:** 2026-09-02

**Status:** `PASSED` for fixture/replay contract validation

## Amaç

Polymarket KORD kuralı, target gün sıcaklık revizyonlarını ertesi günün ilk datapoint'ına kadar kabul ediyor. Yalnız target sayfasını daha sonra çekmek freeze anındaki değeri kanıtlamıyor. Bu nedenle evidence bundle iki raw sayfayı birlikte saklar:

1. target local date sayfası ve daily high;
2. following local date sayfası ve en az bir observation.

Capture ancak following local midnight sonrasında ve trigger observation gerçekten mevcutsa eligible olur.

## Saklanan kanıt

- event ID, market/following local date;
- exact station code/name/timezone ve temperature unit;
- rule text SHA-256, rule version ve parser version;
- target/trigger URL, requested/received timestamp, byte count ve SHA-256;
- parsed identity, daily high ve observation metrikleri;
- her qualification check sonucu;
- canonical content-derived snapshot ID.

Raw HTML SHA-256 adresli dosyalarda, manifest ayrı immutable JSON'da saklanır. Aynı canonical payload idempotent replay olur; aynı event/date için değişmiş content yeni snapshot/revision üretir. Eski revision silinmez.

## Ön-kayıtlı test sonucu

| Senaryo | Beklenen | Sonuç |
|---|---|---|
| Valid two-page fixture | Eligible | `PASSED` |
| Deterministic replay | Aynı snapshot ID | `PASSED` |
| Capture before following midnight | Fail closed | `PASSED` |
| Empty following-date observations | Fail closed | `PASSED` |
| Station mismatch | Fail closed | `PASSED` |
| Unit mismatch | Fail closed | `PASSED` |
| Rule-hash mismatch | Fail closed | `PASSED` |
| First write | Append | `PASSED` |
| Duplicate write | Idempotent/no new manifest | `PASSED` |
| Changed target content | New revision | `PASSED` |
| Raw before tamper | Checksum valid | `PASSED` |
| Raw after tamper | Verification failure | `PASSED` |

Toplam `12/12`; contract gate `PASSED`. Full suite `76` test ve Ruff kontrolü geçti.

## Sınırlar

- Fixture sentetiktir; gerçek Wunderground uptime veya DOM stability ölçülmedi.
- Fixture başarısı geçmiş eventlerin freeze değerini geri getirmez.
- Target sayfasının trigger sayfasından birkaç saniye sonra alınması mümkündür; requested/received zamanları bu capture latency'yi görünür tutar.
- Persistent collector başlatılmadı.
- Canlı bir event ancak exact versioned rule ve iki gerçek response ile `PROSPECTIVE_FREEZE_TRIGGER_CAPTURE` olabilir.

## Karar ve sonraki adım

Storage/replay/idempotency contract `PASSED`; Phase 5 `IN_PROGRESS`. Sonraki en küçük adım, mevcut Polymarket inventory'den exact Wunderground/KORD rule'a sahip uygun upcoming event olup olmadığını read-only keşfetmek ve varsa tek-event bounded prospective capture planını ön-kaydetmektir. Event yoksa `NOT_AVAILABLE` raporlanacak; outcome-seçilmiş ikame yapılmayacak ve arka planda collector başlatılmayacaktır.
