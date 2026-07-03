"""Under-pressured gas/condensate well & field screen (issue #710, epic #708).

Consumes per-well pressure-observation tables (the #709 schema produced by
state ingests such as kansas_kgs #725), estimates BHP from wellhead shut-in
readings, classifies pressure-gradient tiers, ranks fields, and enforces a
validation gate that the known analogs (Hugoton/Panoma) are recovered.

Entry point: ``python -m worldenergydata.analysis.underpressured_screen.screen``.
"""
