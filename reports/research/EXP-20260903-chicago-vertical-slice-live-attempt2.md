# Chicago vertical slice — live attempt 2

**Decision:** `VERTICAL_SLICE_MECHANICS_PASS`  
**Meaning:** the forecast→bucket probability→executable price→fee calculation works end to end  
**Meaning it does not have:** proven edge, calibration, paper trade or live trade

## What passed

The latest available selection chose NOAA NBM 07Z after the 08Z object returned 404. KORD had exactly one locked target record: forecast hour 17, mean 90°F, standard deviation 4°F and reported p10/p25/p50/p75/p90 of 86/87/89/94/95°F.

Event 946566 matched the locked rule and all 11 market/condition/token identities. Bucket probabilities summed to 1.0. Every YES book had enough displayed ask depth for an independent `$10` VWAP; seven were two-sided and four one-sided. No public request failed and forecast retrieval to final book receipt took 1.413 seconds.

Fee parameters reconciled 11/11 through the official condition-level CLOB V2 `fd` object and Gamma: rate 0.05, exponent 1, taker-only. The applied taker fee is `shares × rate × price × (1-price)` for each fill.

## Diagnostic output

| Bucket | NBM Gaussian q | $10 ask VWAP | Net edge/share | After 2pp haircut |
|---|---:|---:|---:|---:|
| ≤79°F | 0.43% | 0.18¢ | +0.25pp | −1.75pp |
| 80–81°F | 1.25% | 0.17¢ | +1.07pp | −0.93pp |
| 82–83°F | 3.53% | 1.02¢ | +2.46pp | +0.46pp |
| 84–85°F | 7.82% | 1.74¢ | +6.00pp | +4.00pp |
| 86–87°F | 13.57% | 4.85¢ | +8.49pp | +6.49pp |
| 88–89°F | 18.43% | 7.40¢ | +10.68pp | +8.68pp |
| 90–91°F | 19.59% | 10.78¢ | +8.33pp | +6.33pp |
| 92–93°F | 16.30% | 26.59¢ | −11.26pp | −13.26pp |
| 94–95°F | 10.62% | 49.00¢ | −39.63pp | −41.63pp |
| 96–97°F | 5.42% | 18.17¢ | −13.50pp | −15.50pp |
| ≥98°F | 3.04% | 6.22¢ | −3.47pp | −5.47pp |

These are not recommendations. They show a very large disagreement: the market concentrated around 94–95°F while the Gaussian baseline centered near 90°F.

## Why we must not trade this apparent edge

NBM's own quantiles are visibly non-Gaussian relative to mean 90°F / sd 4°F. A Gaussian would imply approximately 84.87/87.30/90.00/92.70/95.13°F, while NBM reports 86/87/89/94/95°F. Tail probabilities—and therefore the cheapest buckets' apparent dollar EV—are highly sensitive to this assumption.

This is one event observed close to resolution, without calibration history or a verified outcome. A positive calculated edge can therefore be model misspecification, valid later market information, forecast-product time-window mismatch, or genuine disagreement. One row cannot distinguish them.

## Decision

The project has now entered quantitative research: executable prices and costs can be compared with a reproducible probability baseline. The next step is not capital deployment. It is a preregistered prospective daily paper dataset at fixed lead times, retaining every signal and no-signal observation, while the Sep 4 settlement capture independently validates the label.

Primary fee references: `https://docs.polymarket.com/trading/fees` and `https://docs.polymarket.com/api-reference/markets/get-clob-market-info`.
