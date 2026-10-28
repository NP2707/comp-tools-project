"""Choose a fresh output folder without altering the recorded audit source."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gitskills import template_audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    template_audit.OUTPUT = args.output.resolve()
    template_audit.main()
