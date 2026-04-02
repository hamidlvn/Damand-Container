import yaml
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def load_config(config_path: str = "configs/pipeline.yaml") -> Dict[str, Any]:
    resolved = PROJECT_ROOT / config_path
    with open(resolved, "r") as file:
        return yaml.safe_load(file)
