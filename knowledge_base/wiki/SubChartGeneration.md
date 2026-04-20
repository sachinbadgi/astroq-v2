# Sub-Year Chart Generation (Goswami 1952, pp. 234–235)

This page documents the **canonical Lal Kitab method** for deriving Monthly, Daily, and Hourly charts from an Annual chart. The source is B.M. Goswami's Jyotish Lal Kitab (1952 Edition), pages 234–235.

## The Core Principle

Each finer time-resolution chart is derived from its parent by **rotating the parent chart** so that a specific "clock planet" lands on House 1 (or at a computed offset). All other planets shift accordingly relative to this new reference house.

## Sub-Chart Hierarchy

| Chart Level | Clock Planet | Method |
|---|---|---|
| **Annual** | *(from Natal via Varshphal Matrix)* | Use canonical 120-year matrix |
| **Monthly** | **Sun** | Rotate annual chart so Sun's house = House 1 |
| **Weekly** | **Venus** | Rotate monthly chart so Venus's house = House 1 |
| **Daily** | **Mars** | From monthly chart: count N days elapsed in month from Mars's house |
| **Hourly** | **Jupiter** | From daily chart: count N hours of day from Jupiter's house |
| **Minute** | **Saturn** | From hourly chart: count N minutes from Saturn's house |
| **Seconds** | **Mercury** | From minute chart: count N seconds from Mercury's house |
| **Degrees** | **Moon** | From minute chart: rotate by N degrees |
| **Night** | **Rahu** | Move Rahu to its HQ (House 2) |
| **Day** | **Ketu** | Move Ketu to House 2 |

## Rotation Algorithm

All sub-charts use the same mathematical pattern:
1. Find the **clock planet's current house** `H_clock` in the parent chart.
2. Compute **rotation offset** = `H_clock - 1` (zero-indexed number of positions to shift left).
3. For each planet in the parent chart: `new_house = ((old_house - rotation_offset - 1) % 12) + 1`

## Daily Chart Specifics (Goswami Example, p.235)

The daily chart uses a **day-count offset** rather than placing the house at 1:
1. Find Mars's house `H_mars` in the Monthly chart.
2. Compute: `daily_offset = (days_elapsed_in_month + H_mars - 1) % 12 + 1`  
   *(this is the house Mars lands in for the daily chart)*
3. Rotate all planets using Mars's new house as the reference.

## Vikrami Calendar House-Month Correspondence

The 12 houses map to the 12 Vikrami months (starting ~13 April each year):

| House | Month | Approx. Gregorian |
|---|---|---|
| 1 | Vaisakh | ~April 13 – May 12 |
| 2 | Jeth | ~May 13 – June 12 |
| 3 | Asadh | ~June 13 – July 12 |
| 4 | Savan | ~July 13 – Aug 12 |
| 5 | Bhado | ~Aug 13 – Sep 12 |
| 6 | Asoj | ~Sep 13 – Oct 12 |
| 7 | Kartik | ~Oct 13 – Nov 12 |
| 8 | Maghar | ~Nov 13 – Dec 12 |
| 9 | Poh | ~Dec 13 – Jan 12 |
| 10 | Magh | ~Jan 13 – Feb 12 |
| 11 | Fagan | ~Feb 13 – Mar 12 |
| 12 | Chet | ~Mar 13 – Apr 12 |

## Implementation Notes

> **Note**: The "rotation" does NOT generate a new astronomical chart from ephemeris. It is a purely deterministic **house-shift operation** on the existing planet positions of the parent chart. Planet dignity states (Exalted, Debilitated, Fixed House Lord) must be recomputed based on the new house positions.

## System Consistency

To prevent **System Drift** (where the natal potential and annual fulfillment become misaligned), the pipeline enforces that the `chart_system` used for the birth chart (e.g., Vedic Lahiri) MUST be used for all 75 annual charts. Mixing systems in a single payload is prohibited as it creates "Frankenstein" charts that produce hallucinated results.
