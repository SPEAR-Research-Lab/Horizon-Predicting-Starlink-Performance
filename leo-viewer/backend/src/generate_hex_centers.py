import json
from pathlib import Path

import h3
import pandas as pd

from .__init__ import data_dir, logger
from .generate_adaptive_hex_centers import generate_adaptive_hex_centers

COVERAGE_JSON = Path(__file__).parent.parent.parent / "frontend" / "public" / "h3-country-coverage.json"
RESOLUTIONS = [2, 3, 4]


def generate_hex_centers(adaptive: bool = True) -> None:
    """
    Generate hex center files for the prediction pipeline.

    Args:
        adaptive: If True (default), use data-density-based adaptive resolution.
                  If False, use static generation from coverage JSON.
    """
    if adaptive:
        logger.info("Using adaptive hex generation (density-based resolution)")
        generate_adaptive_hex_centers()
        return

    with open(COVERAGE_JSON) as f:
        coverage = json.load(f)

    for res in RESOLUTIONS:
        res_key = str(res)
        if res_key not in coverage:
            logger.warning(f"Resolution {res} not found in coverage JSON")
            continue

        hex_indexes = list(coverage[res_key].keys())
        rows = []
        for h3_index in hex_indexes:
            lat, lon = h3.cell_to_latlng(h3_index)
            rows.append({"h3Index": h3_index, "lat": round(lat, 6), "lon": round(lon, 6)})

        df = pd.DataFrame(rows)
        out_path = data_dir / f"hex_centers_res{res}.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"Generated {len(df)} hex centers for resolution {res} -> {out_path}")


if __name__ == "__main__":
    generate_hex_centers()
