from pathlib import Path

from .logger import LogUtils

root_dir = Path(__file__).parent.parent
data_dir = root_dir / "data"
models_dir = root_dir / "models"
output_dir = root_dir / "output"
config_dir = root_dir / "config"
satellite_data_dir = root_dir.parent / "satellite-data" / "data"

logger = LogUtils.init_logger()
