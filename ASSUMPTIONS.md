# Assumptions

These decisions are used throughout the app. They are also summarised in the README.

## Timezone

All timestamps are treated as **UTC**. January has no UK DST, so UTC equals UK local time in this dataset.

## Decision cutoff

Default cutoff is **09:00 UTC on D-1** (hour and minute are configurable; they are never hard-coded in selection logic).

Reason: the GB day-ahead auction the buyer would typically use closes around **09:20 UK time**. Using 09:00 leaves a short buffer before gate close so the forecast shown is one the buyer could actually have used.

Sources:

- EPEX SPOT Day-Ahead GB 60-minute auction: order book closes **09:20 GMT/BST on D-1**; results from 09:30 GMT/BST. See [EPEX SPOT trading products](https://www.epexspot.com/en/tradingproducts) and EPEX SPOT Operational Rules (GB 60min Auction 09:20 GMT/BST D-1).
- Nord Pool N2EX GB day-ahead auction closes later (**09:50 GMT**). See [Nord Pool N2EX Day Ahead Auction](https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-n2ex-day-ahead-auction).

We default to the earlier (EPEX 09:20) market with a 20-minute operational buffer.

## Elexon Insights API (confirmed, not guessed)

Sources:

- OpenAPI spec: [https://data.elexon.co.uk/swagger/v1/swagger.json](https://data.elexon.co.uk/swagger/v1/swagger.json)
- Stream docs: [FUELHH/stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), [WINDFOR/stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
- Developer portal: [https://developer.data.elexon.co.uk/](https://developer.data.elexon.co.uk/)

| Item | Confirmed value |
|---|---|
| Base URL | `https://data.elexon.co.uk/bmrs/api/v1` (`servers[0].url` in the OpenAPI spec) |
| Actuals path | `GET /datasets/FUELHH/stream` |
| Forecasts path | `GET /datasets/WINDFOR/stream` |
| FUELHH query params | `settlementDateFrom`, `settlementDateTo` (`yyyy-MM-dd`); `fuelType` (array; we send `WIND`); optional `publishDateTimeFrom` / `publishDateTimeTo`. **Settlement date params cannot be combined with publish-date params.** |
| WINDFOR query params | `publishDateTimeFrom`, `publishDateTimeTo` only. No `startTime` filter on the API. |
| Auth | None. Public API; no key required. |
| Response shape (stream) | JSON **array** of rows (not `{data: [...]}`). Fields: `startTime`, `publishTime`, `generation` (FUELHH also has `fuelType`, `settlementDate`, `settlementPeriod`). |
| Max date range | The OpenAPI descriptions for these two **stream** endpoints do **not** state a maximum window. The developer portal says stream endpoints have **no restrictions or limits on data return**. Non-stream endpoints elsewhere in the spec sometimes do (e.g. INDGEN "maximum data output range of 1 day"). We still fetch in **7-day chunks** with retries to stay resilient to timeouts and HTTP 429. |
| Rate limiting | Both stream endpoints document HTTP **429**. |

Fetch windows we use:

- Actuals: `settlementDateFrom=2026-01-01` … `settlementDateTo=2026-01-31`, `fuelType=WIND`, then keep `startTime` in `[2026-01-01 00:00 UTC, 2026-01-31 23:30 UTC]`.
- Forecasts: `publishDateTimeFrom=2025-12-15T00:00:00Z` … `publishDateTimeTo=2026-02-01T00:00:00Z` (chunked), then **keep only rows whose target `startTime` is in January 2026**.

## Observed snapshot (Phase 2 run)

- Actuals: **1488** rows, full 30-minute grid for January 2026, no null generation, no duplicate `startTime`.
- Forecasts: **18080** rows after January-target filter. Unique `startTime` values are **hourly** (minute always `00`). That is **744** of **1488** half-hour targets. The missing 744 periods are the `:30` slots. We do **not** interpolate or fill those with zero; they are coverage gaps.
- Earliest forecast `publishTime` for January 2026 targets was `2025-12-30 02:30 UTC`, so the December 15 publish-window start was wide enough.

## Scope

- National-level wind only.
- Data from **Elexon BMRS only** (FUELHH actuals, WINDFOR forecasts). No other data sources.

## Forecast horizon

`horizon_hours = (startTime - publishTime)` in hours.

## Error convention

`error = forecast - actual`. **Positive means over-forecast** (forecast too high). For the buyer, over-forecast wind means they may under-buy thermal power and risk a shortfall.

## Missing data

Missing forecasts are reported as coverage gaps. They are not filled with zeros or interpolated values.

## Runtime data

The deployed app uses a **cached parquet snapshot** under `data/`. It never calls the Elexon API at request time.

## Sample for error percentiles

Error percentiles (P50 / P90 / P95) are computed from **January 2026 data only**. That is a single month, so the sample is limited.
