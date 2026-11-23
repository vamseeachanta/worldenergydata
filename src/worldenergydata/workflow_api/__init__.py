# ABOUTME: Public surface for worldenergydata's deterministic workflow runner (workspace-hub#3286).
"""worldenergydata deterministic workflow API.

``run_workflow(workflow_id, params=None, cfg=None, verify_reproducible=False)``
drives a worldenergydata workflow through the wed engine's embed path
(side-effect-free) and returns the shared
:class:`assetutilities.workflow_api.ResultEnvelope` (workspace-hub#3282). This
module REUSES assetutilities' envelope/locator/hashing primitives; it owns no
copy of the contract.
"""

from worldenergydata.workflow_api.runner import run_workflow

__all__ = ["run_workflow"]
