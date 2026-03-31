import os
from typing import Tuple

import pandas as pd

from config import data_collection_dir


def ensure_env_file_exists() -> None:
    env_file_path = os.path.join(data_collection_dir, ".env")

    if not os.path.exists(env_file_path):
        print(f".env file not found at {env_file_path}. Let's create one.\n")

        db_host = input("DB_HOST (default: localhost): ") or "localhost"
        db_port = input("DB_PORT (default: 5432): ") or "5432"
        db_user = input("DB_USER (default: postgres): ") or "postgres"
        db_password = input("DB_PASSWORD: ")
        db_name = input("DB_NAME: ")

        env_content = f"""DB_HOST={db_host}
DB_PORT={db_port}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_NAME={db_name}
"""

        with open(env_file_path, "w") as f:
            f.write(env_content)

        print(f"\nCreated .env file at {env_file_path}")


def split_by_source(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Splits the input DataFrame into two DataFrames based on the 'source' column.

    Returns:
        A tuple containing the two DataFrames (Cloudflare AIM and NDT7, in this order).
    """
    cloudflare_df = df[df["data_source"] == "Cloudflare AIM"]
    ndt7_df = df[df["data_source"] == "NDT7"]
    return cloudflare_df, ndt7_df
