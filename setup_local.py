from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    print("\n## Clyp Fast Dev setup\n")
    env = ROOT / ".env"
    if not env.exists():
        example = ROOT / ".env.example"
        if example.exists():
            env.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            print("Created .env from .env.example. Add your Gemini API key before starting.")
        else:
            print("Missing .env and .env.example")
            raise SystemExit(1)
    else:
        print("Using existing .env configuration.")

    print("Installing/updating Python requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])
    print("\nSetup complete.")
    print("Start Clyp with: py start_local.py")
    print("No XAMPP, PHP, MySQL, login or registration is required for this fast development build.\n")


if __name__ == "__main__":
    main()
