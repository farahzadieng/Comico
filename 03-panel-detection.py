from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "01-Panel-Detection"
MAIN = PROJECT / "main.py"


def main():
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python Panel-Detection.py <config.json>\n\n"
            "Example:\n"
            "  python Panel-Detection.py config.json"
        )
        sys.exit(1)

    config_path = Path(sys.argv[1])

    # Resolve relative config paths from the directory
    # where Panel-Detection.py is executed.
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()

    if not config_path.exists():
        print(f"Error: config file not found: {config_path}")
        sys.exit(1)

    command = [
        sys.executable,
        str(MAIN),
        "--config",
        str(config_path),
        *sys.argv[2:],
    ]

    try:
        result = subprocess.run(
            command,
            check=False,
        )

        sys.exit(result.returncode)

    except KeyboardInterrupt:
        print("\nPanel detection interrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()