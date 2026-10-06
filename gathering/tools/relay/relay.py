#!/usr/bin/env python3
"""Gathering entry point for the shared offline receipt bridge."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[3] / 'shared/receipt_bridge.py'),
                   run_name='__main__')
