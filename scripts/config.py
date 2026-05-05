from pathlib import Path

scripts_dir = Path(__file__).parent
root_dir = scripts_dir.parent
data_collection_dir = root_dir / "data-collection"
src_output_dir = data_collection_dir / "output"

script_output_dir = scripts_dir / "output"
script_output_dir.mkdir(exist_ok=True)
