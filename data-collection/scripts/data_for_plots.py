import subprocess
import sys

import pandas as pd

from config import data_collection_dir, script_output_dir, src_output_dir
from utils import ensure_env_file_exists, split_by_source

ensure_env_file_exists()

subprocess.run(
    [
        sys.executable,
        "-m",
        "src.main",
        "--init",
        "--update-best-servers",
        "2025-09",
        "--date-range",
        "2025-09-01:2025-09-30",
        "--export-raw",
        "data_before_filtration.csv",
        "--export-monthly",
        "2025-09",
    ],
    cwd=data_collection_dir,
    check=True,
)

subprocess.run(
    [
        sys.executable,
        "-m",
        "src.main",
        "--process-cloudflare-mean-and-p90-for-experiment",
        "2025-09",
    ],
    cwd=data_collection_dir,
    check=True,
)

sept_data_after_filtration = pd.read_csv(src_output_dir / "download_2025_9.csv")
cf_median_df, ndt7_df = split_by_source(sept_data_after_filtration)
cf_median_df.to_csv(script_output_dir / "cf_median_sept.csv", index=False)
cf_median_df.to_csv(script_output_dir / "cf_sept_after.csv", index=False)
ndt7_df.to_csv(script_output_dir / "ndt7_sept.csv", index=False)
ndt7_df.to_csv(script_output_dir / "ndt7_sept_after.csv", index=False)

sept_data_before_filtration = pd.read_csv(src_output_dir / "data_before_filtration.csv")
cf_median_df_before, ndt7_df_before = split_by_source(sept_data_before_filtration)
cf_median_df_before.to_csv(script_output_dir / "cf_sept_all.csv", index=False)  # TODO: also run through enrich
ndt7_df_before.to_csv(script_output_dir / "ndt7_sept_all.csv", index=False)  # TODO: also run through enrich

cf_mean_df = pd.read_csv(src_output_dir / "cf_mean.csv")
cf_90th_percentile_df = pd.read_csv(src_output_dir / "cf_90th_percentile.csv")

cf_mean_df.to_csv(script_output_dir / "cf_mean_sept.csv", index=False)
cf_90th_percentile_df.to_csv(script_output_dir / "cf_p90_sept.csv", index=False)

print(f"Data processing complete. Processed files saved in {script_output_dir}.")
