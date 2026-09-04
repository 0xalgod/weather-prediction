# NBM KORD maximum-temperature local-day semantics

**Date:** 2026-09-04  
**Decision:** `PROXY_FEATURE_NOT_RESOLUTION_EQUIVALENT`

## Official product definition

NOAA's NBM text-product documentation states that maximum temperature is calculated over 18 hours, from 12Z on the current UTC day through 06Z on the following day, and is reported at 00Z on the following day. The NBP key states that TXNMN/TXNSD/TXNP rows use that maximum/minimum convention and maximum values appear at 00Z.

Sources:

- [NOAA NBM text products](https://vlab.noaa.gov/web/mdl/nbm-text-products)
- [NOAA NBM bulletin card and element key](https://vlab.noaa.gov/web/mdl/nbm-textcard-v4.2)

## Comparison with the Chicago market day

For the July–August 2026 sample, Chicago uses CDT (UTC−5):

- Polymarket/Chicago local calendar day: target 05Z through next-day 05Z, 24 hours.
- NBM maximum window: target 12Z through next-day 06Z, 18 hours.
- Shared interval: 17 hours.
- Market interval omitted by NBM: 7 hours at the start.
- NBM interval outside the market day: 1 hour at the end.

The windows are not identical. The f41 record used in the 07Z run correctly points to the documented 00Z-reported maximum, but that maximum is not a literal KORD local-calendar-day maximum.

## Research consequence

The completed 30-date baseline scoring remains valid as a test of an NBM-derived predictive proxy against the actual resolved market buckets. It must not be described as comparing two identical meteorological targets.

NBM may remain a useful feature because daytime highs usually occur inside the overlapping interval, and any systematic mismatch can potentially be learned from outcomes. That claim must be measured through walk-forward calibration; it cannot be assumed.

Future datasets must explicitly store both windows and label NBM TXN distributions `PROXY_18H_MAX`. Resolution-equivalent labels continue to come from the market's frozen source/settlement record.
