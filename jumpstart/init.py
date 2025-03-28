import os
import json
import subprocess

CHROMIUM_SRC_DIR = os.path.expanduser("~/chromium_src")
DEPOT_TOOLS_DIR = os.path.expanduser("~/depot_tools")

DEFAULT_CONFIG = {
    "metadata": {
        "name": "",
        "version": "0.1",
        "description": "Custom Chromium build configuration",
        "base_chromium_version": "latest"
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

def run_command(command, cwd=None):
    """Run a shell command and return output."""
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {command}")
        print(result.stderr)
        exit(1)
    return result.stdout.strip()

def check_chromium_source():
    """Check if Chromium source is already installed."""
    return os.path.exists(CHROMIUM_SRC_DIR)

def setup_depot_tools():
    """Ensure depot_tools is installed and configured."""
    if not os.path.exists(DEPOT_TOOLS_DIR):
        print("🚀 Installing depot_tools...")
        run_command(f"git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git {DEPOT_TOOLS_DIR}")

    # Add depot_tools to PATH
    os.environ["PATH"] = f"{DEPOT_TOOLS_DIR}:{os.environ['PATH']}"

def fetch_chromium_source():
    """Fetch Chromium source if it doesn't exist."""
    if check_chromium_source():
        print(f"✅ Chromium source found at {CHROMIUM_SRC_DIR}. Skipping download.")
    else:
        print("🚀 Fetching Chromium source (this may take a while)...")
        os.makedirs(CHROMIUM_SRC_DIR, exist_ok=True)
        run_command("fetch --nohooks chromium", cwd=CHROMIUM_SRC_DIR)
        run_command("gclient sync", cwd=CHROMIUM_SRC_DIR)

def install_mac_dependencies():
    """Ensure Mac build dependencies are installed."""
    print("🔧 Installing Chromium Mac build dependencies...")
    run_command("brew install ninja ccache", cwd=CHROMIUM_SRC_DIR)
    run_command("./build/install-build-deps.sh --mac", cwd=CHROMIUM_SRC_DIR)

def apply_build_flags(config):
    """Apply optimization flags from config to Chromium build system."""
    build_flags = []

    if config["build"]["optimization_level"]:
        build_flags.append(f"is_optimized={config['build']['optimization_level'] != 'O0'}")

    if config["build"]["is_debug"]:
        build_flags.append("is_debug=true")
    else:
        build_flags.append("is_debug=false")

    if config["build"]["use_jumbo_build"]:
        build_flags.append("use_jumbo_build=true")

    if config["build"]["thin_lto"]:
        build_flags.append("thin_lto=true")

    if config["build"]["disable_google_update_check"]:
        build_flags.append("disable_google_update_check=true")

    if config["build"]["custom_build_flags"]:
        build_flags.append(config["build"]["custom_build_flags"])

    build_args = " ".join(build_flags)
    print(f"🔧 Applying build flags: {build_args}")

    run_command(f'gn gen out/Default --args="{build_args}"', cwd=CHROMIUM_SRC_DIR)

def prompt_user():
    """Prompt user for project setup details."""
    project_name = input("Enter your project name: ").strip()
    return project_name

def create_project_directory(project_name):
    """Create a new directory for the project."""
    project_path = os.path.join(os.getcwd(), project_name)
    
    if os.path.exists(project_path):
        print(f"❗ Directory '{project_name}' already exists. Choose a different name or delete the old one.")
        return None
    
    os.makedirs(project_path)
    os.makedirs(os.path.join(project_path, "scripts"))
    os.makedirs(os.path.join(project_path, "src"))
    return project_path

def write_config_file(project_path, project_name):
    """Write the jumpstart.config.json file."""
    config = DEFAULT_CONFIG.copy()
    config["metadata"]["name"] = project_name

    config_path = os.path.join(project_path, "jumpstart.config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    
    print(f"✅ Created configuration file: {config_path}")

def setup_build_directory(project_path):
    """Create an output build directory for the browser fork."""
    build_dir = os.path.join(CHROMIUM_SRC_DIR, "out", os.path.basename(project_path))
    os.makedirs(build_dir, exist_ok=True)
    print(f"✅ Created build directory: {build_dir}")

def main():
    """Main function to initialize a new Chromium Jumpstart project."""
    print("\n🚀 Setting up Chromium Jumpstart environment...")
    
    setup_depot_tools()
    fetch_chromium_source()
    install_mac_dependencies()

    project_name = prompt_user()
    if not project_name:
        print("❌ Project name cannot be empty.")
        return
    
    print(f"\n🚀 Initializing Chromium Jumpstart project: {project_name}...")
    
    project_path = create_project_directory(project_name)
    if project_path:
        write_config_file(project_path, project_name)
        setup_build_directory(project_path)

        # Load config and apply build flags
        config_path = os.path.join(project_path, "jumpstart.config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
            apply_build_flags(config)
        else:
            print("⚠️ No config file found. Using defaults.")

        print(f"\n🎉 Project '{project_name}' is ready!")
        print(f"📂 Navigate to the project: `cd {project_name}`")
        print(f"⚙️ Modify your config: `{project_path}/jumpstart.config.json`")
        print(f"🔨 Start building: `cd {CHROMIUM_SRC_DIR} && ninja -C out/{project_name}`")

if __name__ == "__main__":
    main()
