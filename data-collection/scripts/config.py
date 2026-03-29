from pathlib import Path

scripts_dir = Path(__file__).parent
data_collection_dir = scripts_dir.parent
src_output_dir = data_collection_dir / "output"

script_output_dir = scripts_dir / "output"
script_output_dir.mkdir(exist_ok=True)
