# Starlink TLE Data

Automatically collects and archives **Two-Line Element (TLE)** data for Starlink satellites from **Celestrak**.

## Usage

Run locally:

```bash
python celestrak-collection.py
```

New TLE files are saved to `data/` with date-based naming (`DD-MM-YYYY.tle`).

## Data

Daily snapshots maintained via GitHub Actions (15:00 UTC). Data sourced from [Celestrak](https://celestrak.org/) (`GROUP=starlink`).
