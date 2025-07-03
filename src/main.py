#!/usr/bin/env python3
"""Main entry point for the speech-to-text transcriber."""

import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

# Ensure STT_ORIGINAL_CWD is set (fallback if not set by shell script)
if 'STT_ORIGINAL_CWD' not in os.environ:
    os.environ['STT_ORIGINAL_CWD'] = os.getcwd()

from transcriber.cli import main

if __name__ == '__main__':
    main()