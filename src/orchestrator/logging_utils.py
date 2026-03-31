"""
orchestrator/logging_utils.py
==============================
Configures dual logging: console (INFO+) and a persistent run log file.
Returns the root logger after setup so callers don't need to reconfigure.
"""

import logging
import sys
from pathlib import Path


def setup_logging(log_path: Path, level: int = logging.INFO) -> logging.Logger:
    """
    Set up root logger with:
      - StreamHandler → console (coloured prefix)
      - FileHandler   → results/run_log.txt (plain text, full detail)
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid adding duplicate handlers if called more than once
    if root.handlers:
        return root

    fmt_file    = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    fmt_console = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt_file)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt_console)

    root.addHandler(fh)
    root.addHandler(ch)

    return root
