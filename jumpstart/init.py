import os
import json
import subprocess
import time
import sys
from jumpstart.config import load_config


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

def run_command(command, cwd=None, check=True):
    """Run a shell command and return output."""
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"❌ Command failed: {command}")
        print(result.stderr)
        exit(1)
    return result.stdout.strip()

def check_chromium_source():
    """Check if Chromium source is already installed."""
    return os.path.exists(CHROMIUM_SRC_DIR)

def setup_depot_tools():
    """Ensure depot_tools is installed, added to PATH, and verified."""
    if os.path.exists(DEPOT_TOOLS_DIR):
        print("✅ Depot Tools already installed.")
    else:
        print("🚀 Installing Depot Tools...")
        run_command(f"git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git {DEPOT_TOOLS_DIR}")

    # Add depot_tools to PATH
    depot_path = f"{DEPOT_TOOLS_DIR}"
    current_path = os.environ.get("PATH", "")

    if depot_path not in current_path:
        os.environ["PATH"] = f"{depot_path}:{current_path}"
        print("✅ Depot Tools added to PATH.")

    # Debugging: Check if fetch is accessible
    try:
        fetch_path = run_command("which fetch", check=True)
        print(f"✅ Depot Tools setup complete. Fetch located at: {fetch_path}")
    except:
        print("❌ Depot Tools installed but not found in PATH!")
        print("➡️ Current PATH:", os.environ.get("PATH", ""))
        print("⚠️ Restart your terminal or manually run:")
        print(f"   export PATH={DEPOT_TOOLS_DIR}:$PATH")
        exit(1)

FETCH_TIMEOUT = 600  # 10 minutes of no progress = potential stall
LOG_UPDATE_INTERVAL = 1  # Check log every 1 seconds

def fetch_chromium_source():
    """Ensure Chromium source directory exists, detect corrupt fetches, and show real-time progress on a single line."""

    # Ensure chromium_src directory exists
    if not os.path.exists(CHROMIUM_SRC_DIR):
        print(f"📂 Creating Chromium source directory at {CHROMIUM_SRC_DIR}...")
        os.makedirs(CHROMIUM_SRC_DIR, exist_ok=True)

    src_path = os.path.join(CHROMIUM_SRC_DIR, "src")
    bad_scm_path = os.path.join(CHROMIUM_SRC_DIR, "_bad_scm")

    # Check for previous failed fetch and clean up
    if os.path.exists(bad_scm_path):
        print("⚠️ Chromium fetch was previously corrupted (detected _bad_scm/).")
        print("🛠 Cleaning up before reattempting fetch...")
        run_command(f"rm -rf {CHROMIUM_SRC_DIR}")
        os.makedirs(CHROMIUM_SRC_DIR, exist_ok=True)

    # If Chromium is already downloaded correctly, skip fetch
    if os.path.exists(src_path):
        print(f"✅ Chromium source found at {CHROMIUM_SRC_DIR}. Skipping download.")
        return

    print("⏳ Preventing system sleep during fetch...")
    print("--")
    print("🚀 Fetching Chromium source (this may take a while)...")
    print("--")

    fetch_log = f"{CHROMIUM_SRC_DIR}/fetch_error.log"
    fetch_cmd = f"caffeinate -dims fetch --nohooks chromium 2>&1 | tee {fetch_log}"

    try:
        # Start fetch in a background process
        fetch_process = subprocess.Popen(fetch_cmd, shell=True, cwd=CHROMIUM_SRC_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Monitor fetch progress
        last_log_size = 0
        start_time = time.time()

        while fetch_process.poll() is None:  # While fetch is running
            time.sleep(LOG_UPDATE_INTERVAL)  # Check log every 60 seconds

            if os.path.exists(fetch_log):
                log_size = os.path.getsize(fetch_log)
                if log_size > last_log_size:
                    last_log_size = log_size  # Fetch is still progressing
                    start_time = time.time()  # Reset timeout counter

                    # Get last log line
                    with open(fetch_log, "r") as f:
                        lines = f.readlines()
                        last_line = lines[-1].strip() if lines else "..."

                    # Print last log line on the same line (overwrite previous output)
                    sys.stdout.write(f"\r{last_line}    ")  # Extra spaces clear leftovers
                    sys.stdout.flush()

                elif time.time() - start_time > FETCH_TIMEOUT:
                    print("\n⚠️ Chromium fetch appears to be stalled. No new log updates for 10 minutes.")
                    print("🔄 You may choose to wait or manually stop the fetch and retry.")
                    break  # Exit loop but leave fetch running in case it recovers

        fetch_process.wait()  # Ensure process finishes

        # Verify fetch succeeded
        if not os.path.exists(src_path):
            print("\n❌ Chromium fetch completed, but 'src/' is missing.")
            print("⚠️ The fetch may have been interrupted (e.g., system sleep).")
            print(f"📝 Check the logs at: {fetch_log}")
            print("🔄 Please rerun `jumpstart init` to retry the fetch.")
            exit(1)

        print("\n✅ Chromium source successfully downloaded.")

    except:
        print(f"\n❌ Error: Chromium fetch failed. Check logs at {fetch_log}")
        print("🔄 Please rerun `jumpstart init` to retry the fetch.")
        exit(1)


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
        config = load_config(project_path)  # Use centralized function
        apply_build_flags(config)

        print(f"\n🎉 Project '{project_name}' is ready!")
        print(f"📂 Navigate to the project: `cd {project_name}`")
        print(f"⚙️ Modify your config: `{project_path}/jumpstart.config.json`")
        print(f"🔨 Start building: `cd {CHROMIUM_SRC_DIR} && ninja -C out/{project_name}`")

if __name__ == "__main__":
    main()
