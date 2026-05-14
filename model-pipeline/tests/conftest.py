"""
Pytest configuration for model-pipeline tests.
"""

from pathlib import Path
import sys

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
