## cli entry point
import argparse
from jumpstart.init import main as init_project

def main():
    parser = argparse.ArgumentParser(description="Chromium Jump Starter CLI")
    parser.add_argument("command", choices=["init"], help="Command to run")
    args = parser.parse_args()

    if args.command == "init":
        init_project()

if __name__ == "__main__":
    main()
