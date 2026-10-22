"""Refresh the intervention inventory from manifest-backed public INCINV records.

Shares the drilling refresh configuration, download, QA and provenance. Keyword
hits describe the available investigation text; they do not establish service
categories or a join to local well activity reports. Run with --help for paths.
"""

from drilling_hse_patterns_analysis import main

if __name__ == "__main__":
    main()
