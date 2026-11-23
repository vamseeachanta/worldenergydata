#!/usr/bin/env python3
"""Back-compat wrapper: generalized to ingest_contractor_spec_pdfs.py (#991)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingest_contractor_spec_pdfs import main

if __name__ == "__main__":
    if not any(a.startswith("--contractor") for a in sys.argv[1:]):
        sys.argv.insert(1, "--contractor=noble")
    sys.exit(main())
