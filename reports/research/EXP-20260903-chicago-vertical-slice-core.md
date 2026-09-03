# Chicago vertical slice — quant core result

**Decision:** `VERTICAL_SLICE_CORE_PASS`  
**Live market values used:** No  
**Focused tests:** 10/10  
**Full suite:** 104/104

The first quant mechanics core is implemented. It converts an exhaustive set of inclusive integer-temperature buckets into probabilities under the pre-registered Gaussian NBM baseline and calculates a fixed-dollar buy-YES VWAP by walking real ask depth best-price first.

Important safeguards are executable code rather than prose: bucket gaps/overlaps are rejected; probabilities must sum to one; midpoint is never an input; insufficient depth returns no VWAP; invalid price/size levels fail closed. Multi-level fills expose both VWAP and slippage above best ask.

This validates arithmetic and contracts only. It says nothing yet about NBM calibration, current Chicago prices, fees, settlement or profitability. The next run must retrieve one as-issued NBM object and contemporaneous event 946566 books under the already locked 15-minute skew gate.
