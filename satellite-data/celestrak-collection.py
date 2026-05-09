import datetime
from pathlib import Path

import requests

CELESTRAK_STARLINK = (
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
)
DATA_DIR = Path(__file__).parent / "data"


def fetch_starlink_tle(tle_path: Path) -> None:
    url = CELESTRAK_STARLINK
    resp = requests.get(url)
    resp.raise_for_status()
    with open(tle_path, "w") as f:
        f.write(resp.text)
    print(f"Downloaded current Starlink TLE to {tle_path}")


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    fetch_starlink_tle(
        DATA_DIR / f"{datetime.datetime.now().date().strftime('%d-%m-%Y')}.tle"
    )
