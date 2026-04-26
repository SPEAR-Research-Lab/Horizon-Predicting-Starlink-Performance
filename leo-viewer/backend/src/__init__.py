from pathlib import Path

from .logger import LogUtils

data_dir = Path(__file__).parent.parent / "data"
models_dir = Path(__file__).parent.parent / "models"
logger = LogUtils.init_logger()
