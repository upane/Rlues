#!/usr/bin/env python3
"""Native CX review binding CLI; see --help."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'hooks'))
from _review_binding import main
if __name__ == '__main__':
    raise SystemExit(main())
