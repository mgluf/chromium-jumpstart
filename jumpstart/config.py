# Handles reading/writing `jumpstart.config.json`

import json
import os

CONFIG_FILENAME = "jumpstart.config.json"

def load_config(project_path):
    """Load jumpstart.config.json from the given project directory."""
    config_path = os.path.join(project_path, CONFIG_FILENAME)
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    print("⚠️ No config file found. Using defaults.")
    return {}

def write_config(project_path, config):
    """Write jumpstart.config.json to the given project directory."""
    config_path = os.path.join(project_path, CONFIG_FILENAME)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    print(f"✅ Config file written: {config_path}")
