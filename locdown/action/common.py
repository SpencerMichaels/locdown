import json
from pathlib import Path

def expand_dest_dir(dest):
  return Path(dest).expanduser() if dest else Path.cwd()

def stringify_metadata(metadata):
  return json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False)
