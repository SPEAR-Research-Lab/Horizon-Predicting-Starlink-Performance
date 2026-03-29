from pathlib import Path

from .logger import LogUtils

logger = LogUtils.init_logger()
data_dir = (Path(__file__).parent / ".." / "data").resolve()
output_dir = (Path(__file__).parent / ".." / "output").resolve()

if not output_dir.exists():
    output_dir.mkdir(parents=True)
