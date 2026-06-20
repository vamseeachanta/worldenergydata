# ABOUTME: Flywheel subpackage - workflow-run readiness and manifest glue.
# ABOUTME: Intentionally import-light so probe modules load without the heavy root __init__.
"""Flywheel: readiness probing and workflow-run manifest support.

This subpackage is deliberately free of heavy imports so that
``worldenergydata.flywheel.readiness_probe`` can be imported (and tested)
without triggering the data-loading side effects of the root package.
"""
