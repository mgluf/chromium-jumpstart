import os
import json
import subprocess
import time
import sys
import pty
import shlex
import argparse
from jumpstart.config import load_config

CHROMIUM_GIT_REPO = "https://chromium.googlesource.com/chromium/src.git"
STALL_TIMEOUT = 120  # 2 minutes

DEFAULT_CONFIG = {
    "metadata": {
        "name": "",
        "version": "0.1",
        "description": "Custom Chromium build configuration",
        "base_chromium_version": "latest"
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

# ----------------- Logging Functions -----------------
def log_info(message):
    print(f"\033[34m[INFO]\033[0m \033[90m{message}\033[0m")

def log_error(message):
    print(f"\033[31m[ERROR]\033[0m {message}")

def log_warn(message):
    print(f"\033[33m[WARN]\033[0m {message}")

def log_success(message):
    print(f"\033[32m[SUCCESS]\033[0m {message}")

# ----------------- Command Runner -----------------
def run_command(command, cwd=None, check=True):
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 and check:
        log_error(f"Command failed: {command}\n{result.stderr}")
        exit(1)
    return result.stdout.strip()

# ----------------- Prompt Functions -----------------
def prompt_input(message):
    return input(f"\033[35m[PROMPT]\033[0m {message} ").strip()

def prompt_chromium_src_path():
    path = prompt_input("Enter Chromium source install path \033[90m(default: ~/chromium_src):\033[0m")
    if not path:
        path = "~/chromium_src"
    return os.path.expanduser(path)

def prompt_jumpstart_repo_path():
    path = prompt_input("Enter the directory where you want to initialize the jumpstart project (default: current directory):")
    if not path:
        path = os.getcwd()
    return os.path.expanduser(path)

def prompt_project_name():
    project_name = prompt_input("Enter your project name:")
    return project_name

# ----------------- Git Clone and Sync -----------------
def perform_git_clone(chromium_src_dir):
    log_info("Cloning Chromium source...")
    cmd = shlex.split(f"git clone --progress {CHROMIUM_GIT_REPO} {chromium_src_dir}")

    def read(fd):
        last_output_time = time.time()
        try:
            while True:
                output = os.read(fd, 1024).decode(errors="ignore")
                if not output:
                    break
                # Show first 100 characters of current output line
                sys.stdout.write("\r" + output.strip().replace('\n', ' ')[:100])
                sys.stdout.flush()
                last_output_time = time.time()

                if "fatal" in output.lower():
                    log_error("Fatal error detected during clone.")
                    raise RuntimeError("fatal error")

                if time.time() - last_output_time > STALL_TIMEOUT:
                    log_warn("Git clone appears stalled for over 2 minutes.")
                    raise TimeoutError("stall detected")

        except Exception:
            return False
        return True

    try:
        return pty.spawn(cmd, read)
    except Exception as e:
        log_error(f"Git clone failed: {str(e)}")
        return False

def fetch_chromium_source(chromium_src_dir):
    if os.path.exists(chromium_src_dir):
        log_info("Chromium source already exists, skipping clone.")
        return
    # Start cloning
    success = perform_git_clone(chromium_src_dir)
    if not success:
        log_error("Fatal error during clone. Deleting partial clone and exiting.")
        run_command(f"rm -rf {chromium_src_dir}")
        exit(1)

    # Check for Chromium corruption marker in the clone
    bad_scm_path = os.path.join(chromium_src_dir, "_bad_scm")
    if os.path.exists(bad_scm_path):
        log_error("Detected Chromium corruption (_bad_scm exists).")
        confirm = input("Are you sure you want to delete and retry? (y/n): ").strip().lower()
        if confirm == 'y':
            run_command(f"rm -rf {chromium_src_dir}")
            fetch_chromium_source(chromium_src_dir)
        else:
            log_error("Aborting.")
            exit(1)

    log_info("Running gclient sync...")
    run_command("gclient sync --jobs 16 --nohooks", cwd=chromium_src_dir)

# ----------------- OS Dependencies -----------------
def install_os_dependencies(chromium_src_dir):
    # Currently supports only macOS
    log_info("Installing OS-specific dependencies for macOS...")
    run_command("brew install ninja ccache", cwd=chromium_src_dir)
    run_command("./build/install-build-deps.sh --mac", cwd=chromium_src_dir)

# ----------------- Build Configuration -----------------
def apply_build_flags(config, chromium_src_dir):
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
    log_info(f"Applying build flags: {build_args}")

    run_command(f'gn gen out/Default --args="{build_args}"', cwd=chromium_src_dir)

# ----------------- Project Setup -----------------
def create_project_directory(project_name, base_path):
    project_path = os.path.join(base_path, project_name)
    if os.path.exists(project_path):
        log_error(f"Directory '{project_path}' already exists. Choose a different name or delete the old one.")
        return None
    os.makedirs(project_path)
    os.makedirs(os.path.join(project_path, "scripts"))
    os.makedirs(os.path.join(project_path, "src"))
    return project_path

def write_config_file(project_path, project_name, chromium_src_dir):
    config = DEFAULT_CONFIG.copy()
    config["metadata"]["name"] = project_name
    config["paths"]["chromium_src"] = chromium_src_dir

    config_path = os.path.join(project_path, "jumpstart.config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    log_success(f"Created configuration file: {config_path}")

def setup_build_directory(project_path, chromium_src_dir):
    build_dir = os.path.join(chromium_src_dir, "out", os.path.basename(project_path))
    os.makedirs(build_dir, exist_ok=True)
    log_success(f"Created build directory: {build_dir}")

# ----------------- Main Flow -----------------
def main():
    parser = argparse.ArgumentParser(description="Jumpstart: Initialize Chromium project environment")
    parser.add_argument("command", help="Command to execute", choices=["init"])
    args = parser.parse_args()

    if args.command != "init":
        parser.print_help()
        exit(1)

    log_info("Setting up Chromium Jumpstart environment...")

    # Prompt for the Chromium source install path.
    chromium_src_dir = prompt_chromium_src_path()

    # Define marker file to indicate that cloning, sync, and OS dependency installation have been completed.
    marker_file = os.path.join(chromium_src_dir, ".jumpstart_installed")
    if not os.path.exists(chromium_src_dir) or not os.path.exists(marker_file):
        setup_depot_tools(chromium_src_dir)
        run_git_config()
        fetch_chromium_source(chromium_src_dir)
        install_os_dependencies(chromium_src_dir)
        # Create marker file.
        with open(marker_file, "w") as f:
            f.write("installed")
    else:
        log_info("Chromium environment already set up. Skipping clone, sync, and OS dependencies installation.")

    # Prompt for the jumpstart project initialization directory.
    jumpstart_repo_base = prompt_jumpstart_repo_path()

    project_name = prompt_project_name()
    if not project_name:
        log_error("Project name cannot be empty.")
        return

    log_info(f"Initializing Chromium Jumpstart project: {project_name}...")

    project_path = create_project_directory(project_name, jumpstart_repo_base)
    if project_path:
        write_config_file(project_path, project_name, chromium_src_dir)
        setup_build_directory(project_path, chromium_src_dir)

        config = load_config(project_path)
        apply_build_flags(config, chromium_src_dir)

        log_success(f"Project '{project_name}' is ready!")
        log_info(f"Navigate to the project: cd {project_path}")
        log_info(f"Modify your config: {os.path.join(project_path, 'jumpstart.config.json')}")
        log_info(f"Start building: cd {chromium_src_dir} && ninja -C out/{project_name}")

# ----------------- Depot Tools and Git Config -----------------
def setup_depot_tools(chromium_src_dir):
    depot_tools_dir = os.path.expanduser("~/depot_tools")
    if os.path.exists(depot_tools_dir):
        log_success("Depot Tools already installed.")
    else:
        log_info("Installing Depot Tools...")
        run_command(f"caffeinate git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git {depot_tools_dir}")
    # Ensure depot_tools is in PATH
    current_path = os.environ.get("PATH", "")
    if depot_tools_dir not in current_path:
        os.environ["PATH"] = f"{depot_tools_dir}:{current_path}"
        log_success("Depot Tools added to PATH.")
    try:
        fetch_path = run_command("which fetch", check=True)
        log_success(f"Depot Tools setup complete. Fetch located at: {fetch_path}")
    except Exception:
        log_error("Depot Tools installed but not found in PATH!")
        log_info(f"Current PATH: {os.environ.get('PATH', '')}")
        log_info(f"Restart your terminal or manually run:\n   export PATH={depot_tools_dir}:$PATH")
        exit(1)

def run_git_config():
    log_info("Configuring Git for large repository handling...")
    run_command("git config --global http.postBuffer 1048576000")
    run_command("git config --global http.lowSpeedLimit 0")
    run_command("git config --global http.lowSpeedTime 999999")
    log_success("Git configuration applied.")

if __name__ == "__main__":
    main()
