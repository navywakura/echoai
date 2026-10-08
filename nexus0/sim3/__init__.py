"""SIM-3 — declarative worlds, real physics, and an information boundary.

This package is infrastructure, not cognition. Nothing here imports the
fast loop, WSP, CAM, Q or the gate, and nothing here is allowed to hand
simulator truth to the process that receives ticks. See
``echoai/docs/SIM3-DESIGN.md`` for the contract this implements.

Floats live here because SDF and Gazebo are float physics. They stop at
the boundary: every quantity SIM-3 itself reasons about (poses, sizes,
grids, tolerances) is an exact integer in millimetres.
"""

SCHEMA_VERSION = 1
PROFILE = "sim3-boxes-v1"
SCOPE = "simulation_infrastructure"
DATASET_KIND = "rehearsal"

__all__ = ["SCHEMA_VERSION", "PROFILE", "SCOPE", "DATASET_KIND"]
