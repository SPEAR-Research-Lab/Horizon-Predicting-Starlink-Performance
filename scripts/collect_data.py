import subprocess
import sys

from config import data_collection_dir, src_output_dir
from utils import ensure_env_file_exists

ensure_env_file_exists()

subprocess.run(
    [
        sys.executable,
        "-m",
        "src.main",
        "--init",
        "--update-best-servers",
        "2025-01:2025-11",
        "--date-range",
        "2025-01-01:2025-11-31",
        "--export-monthly",
        "2025-01,2025-02,2025-03,2025-04,2025-05,2025-06,2025-07,2025-08,2025-09,2025-10,2025-11",
    ],
    cwd=data_collection_dir,
    check=True,
)

print(f"Initial data collection and monthly export complete. Data is present in {src_output_dir}.")
