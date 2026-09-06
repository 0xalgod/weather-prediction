# EXP-20260906 Multi-city Station Mapping v1

## Status

`FAILED` — mapping was run on 2026-09-06; metadata coverage gates failed.

## Why this gate exists

A global grid forecast can only be joined after each market's exact resolution location is known. A city centroid or similarly named airport can create a plausible but wrong training feature. This experiment therefore maps the resolution URL's station identifier to official coordinates and preserves station changes as separate regimes.

## Locked hypothesis and gates

At least 85% of the 96 selected events and at least 40 cities can be mapped fail-closed. Station-code parse coverage must be at least 95%, duplicate events must be zero, and no known identity contradiction may enter the admitted set.

Wunderground URLs use their final path segment; NOAA WRH URLs use the exact `site` query parameter. Both must be four-letter ICAO identifiers. Coordinates come only from the checksum-identified prior AviationWeather metadata evidence. Missing metadata remains missing; it is not replaced by a city centroid.

## Known evidence disclosure

Eleven identity records were independently reviewed before this experiment. Karachi's rule text and OPKC source-code identity are known to contradict each other and must remain excluded. Coverage for the complete 96-event sample is unknown.

## Boundary

This is an identity and coordinate coverage test. It retrieves no forecast values and makes no accuracy, EV, P&L, fill, or trading claim.

## Result

Resolution URL parsing succeeded for all 96 events with zero duplicates. The locked prior AviationWeather evidence snapshot supplied coordinates for only 22/96 events (22.92%) across 11 cities, below the 85% event and 40-city gates. No known identity mismatch was admitted.

The failure is attributable to the intentionally small earlier metadata snapshot, not to station identifiers in the market rules. Thresholds will not be changed. A corrective v2 may use the already downloaded official NOAA ISD global station-history catalog and must remain fail-closed on identity contradictions.
