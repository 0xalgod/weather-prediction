# EXP-20260909-kord-hourly-two-year-v1

## Status

`PREREGISTERED` — 2024 retrieval and hourly parsing have not run.

## Purpose

Temporarily remove Polymarket from the target and build a pure meteorological forecasting dataset. For KORD, collect NOAA LCDv2 hourly temperature, dew point, humidity, wind, pressure, visibility, and precipitation from 2024-08-01 through 2026-07-31. Predict the official target-date SOD maximum temperature using only observations available by 18:00 local standard time on the previous day.

NOAA documents hourly time as local standard time with no DST adjustment. The parser must preserve that semantic rather than interpreting timestamps as UTC or daylight-adjusted civil time.

## Gates

Require exactly 730 target days, at least 99% non-null SOD maximum labels, at least 95% of input days with 18 distinct temperature-observation hours, exact station identity, no duplicate SOD date, and no hourly dry-bulb value outside -60°C to 60°C. Passing permits feature/model preregistration, not fitting in this experiment.
