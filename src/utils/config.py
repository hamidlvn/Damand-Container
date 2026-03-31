import yaml
from pathlib import Path
from typing import Dict, Any

def load_config(config_path: str = "configs/pipeline.yaml") -> Dict[str, Any]:
    with open(config_path, "r") as file:
        return yaml.safe_load(file)
