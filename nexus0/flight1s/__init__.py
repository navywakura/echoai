"""FLIGHT-1S — software-in-the-loop flight with PX4 SITL and Gazebo.

Infrastructure and body dynamics. Nothing here imports the fast loop, WSP,
CAM, Q, T, PATTERN or the gate, and nothing here publishes a simulated
sensor as evidence: PX4 uses its IMU, barometer and navsat internally to
stabilise, and that is where they stop. SENSOR-1 defines provenance,
noise, latency and loss; GROUND-1 does the translation to the one bus.

``nexus0/sim3/`` is a closed dependency: imported, never modified.
"""

SCHEMA_VERSION = 1
PROFILE = "flight1s-x500-v1"
SCOPE = "flight_software_in_the_loop"
DATASET_KIND = "rehearsal"

__all__ = ["SCHEMA_VERSION", "PROFILE", "SCOPE", "DATASET_KIND"]
