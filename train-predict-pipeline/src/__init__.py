import logging
from pathlib import Path

root_dir = Path(__file__).parent.parent
models_dir = root_dir / "models"
output_dir = root_dir / "output"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("horizon")
