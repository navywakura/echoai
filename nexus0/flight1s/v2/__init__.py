"""FLIGHT-1S v2 — the repaired protocol, beside v1 and never on top of it.

v1 asked one question where there were three. Its ``disturbance`` group
required the closed-loop excursion to reach twice the nominal envelope,
so two flights that received a real wrench, showed 963 and 957 parts per
thousand of the commanded impulse, left the recovery band and came back
were failed for being rejected too well by PX4. That is a defect in the
measurement, not in the vehicle.

v2 separates them: **stimulus** (was a physical input applied?),
**challenge** (did it take the body out of the band?) and **recovery**
(did PX4 bring it back and hold it?). Each has its own group, its own
denominator, and no power to compensate for another.

This subpackage exists as a subpackage on purpose. The v1 runtime lock
hashes ``nexus0/flight1s/*.py`` with a non-recursive glob, so nothing
here changes v1's ``code_sha256`` and the v1 report keeps reconstructing
byte for byte. Nothing in ``nexus0/flight1s/*.py`` is edited by v2; the
host supervisor, the runner asset, the world builder and the container
are imported and reused exactly as v1 froze them.
"""

SCHEMA_VERSION = 2
PROFILE = "flight1s-x500-v2"
SCOPE = "flight_software_in_the_loop"
DATASET_KIND = "rehearsal"

# The v1 result this repairs. Recorded so that no v2 artefact can be read
# without a pointer back to the red it does not erase.
V1_PROTOCOL_SHA256 = (
    "ac1db6f9abf849f96ee3671e73ce63c116d62a43dc4d9c5184c4598e65c98229")
V1_REPORT_SHA256 = (
    "57ccea7f19ebc3b3851abe6faf9c5f1a25365be1f6181291c8e748414944e809")
V1_CODE_SHA256 = (
    "c4dd8fdb6f4f7dbcfb4e473f6ae8464a86def6cf58ba7dce0b0cf08b7ee3102c")

__all__ = ["SCHEMA_VERSION", "PROFILE", "SCOPE", "DATASET_KIND",
           "V1_PROTOCOL_SHA256", "V1_REPORT_SHA256", "V1_CODE_SHA256"]
