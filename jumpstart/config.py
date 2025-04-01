import json
import os

CONFIG_FILENAME = "jumpstart.config.json"

DEFAULT_CONFIG = {
    "metadata": {
        "name": "",
        "version": "0.1",
        "description": "Custom Chromium build configuration",
        "base_chromium_version": "latest",
        "init": {
            "project_dir": "",
            "chromium_src": "",
            "depot_tools": False,
        }
    },
    "paths": {
        "chromium_src": ""
    },
    "features": {
        "security": {
            "sandboxing": True,
            "site_isolation": True
        },
        "performance": {
            "gpu_acceleration": True
        },
        "privacy": {
            "tracking_protection": True,
            "ad_blocking": True
        }
    },
    "build": {
        "optimization_level": "O2",
        "disable_google_update_check": True,
        "is_debug": False,
        "use_jumbo_build": True,
        "thin_lto": True,
        "custom_build_flags": None
    }
}

def generate_config():
    """Return a copy of the default configuration options."""
    return DEFAULT_CONFIG.copy()

def validate_config(config_path):
    """
    Validate and load a configuration file.
    If validation fails, return the default configuration.
    Basic check: ensure 'metadata' and 'paths' keys are present.
    """
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        if "metadata" not in config or "paths" not in config:
            print("[WARN] Config file missing required keys. Using default config.")
            return generate_config()
        # TODO: Extend validation as needed.
        return config
    except Exception as e:
        print(f"[WARN] Error reading config file: {e}. Using default config.")
        return generate_config()

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
