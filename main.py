from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predictive_maintenance.api_server import run_server
from predictive_maintenance.config import APP_HOST, APP_PORT
from predictive_maintenance.data.external import import_ai4i_dataset
from predictive_maintenance.data.simulate import generate_dataset
from predictive_maintenance.training import train_model


def bootstrap() -> None:
    generate_dataset()
    train_model()


def bootstrap_ai4i() -> None:
    import_ai4i_dataset()
    train_model()


def main() -> None:
    parser = argparse.ArgumentParser(description="Predictive maintenance project runner")
    parser.add_argument(
        "command",
        choices=["bootstrap", "bootstrap-ai4i", "generate", "import-ai4i", "train", "serve", "verify"],
        help="Command to execute",
    )
    args = parser.parse_args()

    if args.command == "bootstrap":
        bootstrap()
    elif args.command == "bootstrap-ai4i":
        bootstrap_ai4i()
    elif args.command == "generate":
        generate_dataset()
    elif args.command == "import-ai4i":
        import_ai4i_dataset()
    elif args.command == "train":
        train_model()
    elif args.command == "serve":
        run_server(APP_HOST, APP_PORT)
    elif args.command == "verify":
        import unittest

        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="*_test.py")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
