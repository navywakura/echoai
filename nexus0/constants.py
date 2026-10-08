"""NEXUS-0 frozen integers. Do not invent floats."""

from echoai.core.qn import CAM_SLOTS, HAM_LIMIT, WSP_BYTES

N_SLOTS = CAM_SLOTS  # 4096
N_ACTIONS = 3
ADDR_MASK = 0xFFFF
UNKNOWN_NEXT = 0xFFFF

# a=0 approach, a=1 avoid, a=2 wait  — rel atoms from wsp.h
REL_UNIR = 11
REL_TEMER = 18
REL_OBSERVAR = 14
ACTION_REL = (REL_UNIR, REL_TEMER, REL_OBSERVAR)

ACTION_APPROACH = 0
ACTION_AVOID = 1
ACTION_WAIT = 2

Q_MIN = -127
Q_MAX = 127
GAMMA_NUM = 7
GAMMA_DEN = 8  # γ = 7/8 ; same rational as LIF leak
ALPHA_SHIFT = 2  # α = 1/4 → δ >> 2

# scaled int8 rewards (spec §9)
R_SUCCESS = 16  # approach GOAL
R_THREAT = -16  # approach THREAT
R_AVOID_OK = 8  # avoid THREAT
R_WAIT = 0
R_EMPTY = 0

GATE_OK = 0
GATE_MODIFY = 1
GATE_BLOCK = 2

WSP_FLAG_VETO = 0x80
SLOT_FLAG_INHIBIT = 0x04

C_PLASTIC = 20
U_SHORT = 60

N_CELLS = 32
# Cells where approach lands two ahead instead of one. The ring baseline
# (i±1) does not know this; T has to learn it.
JUMP_CELLS = (5, 21)
JUMP_STRIDE = 2
BENCH_TURNS = 256
BENCH_SEED = 20260903
EPS_PERIOD = 8  # every 8th turn explore a = turn % 3

HAM_MISS = 99
T_MISS_ERROR = 16  # Hamming penalty when T unknown

# NEXUS-3b eligibility traces (opt-in). TRACE_CREDIT >> TRACE_SHIFT
# equals 1 >> ALPHA_SHIFT, so the current step keeps α = 1/4 exactly and
# the tail of the path gets the remainder as z decays by γ = 7/8.
TRACE_CREDIT = 16
TRACE_SHIFT = 6
TRACE_MAX = 127

# NEXUS-4a ATTEND: a flat Q row seen this many times is settled, not
# uncertain. Below it, a flat row still counts as "no policy yet".
ATTEND_SETTLED_HITS = 2

PROBE_STEPS = 32  # greedy seeking probe after training
SAMPLE_TURNS = 8  # compact WSP rows kept for the report (spec §11)

# NEXUS-4d T_CONF: quality of one T(s,a) row as an integer 0..3.
# 0 never seen · 1 one observation · 2 consistent · 3 very consistent.
# A row with any conflict is capped at 2 however often the winner won:
# the ring already produced one stale transition (phase F, 7 → 8) and it
# must not read the same as a JUMP row seen eight times cleanly.
T_CONF_NONE = 0
T_CONF_ONCE = 1
T_CONF_DECENT = 2
T_CONF_HIGH = 3
T_CONF_HIGH_N = 8  # observations of the same s' needed for 3

# NEXUS-4e inverse model I(s, s') → a. Per slot, a short list of
# (s_next, action, count); 4096 x 8 x 3 ints, never 4096**2. In this ring
# a slot has at most three distinct successors, so 8 is slack, not a
# budget — and an observation that would not fit is counted, not dropped
# in silence (`inv_dropped`).
INV_MAX_ENTRIES = 8

# NEXUS-4f escalation: how small a Q margin has to be before the planner
# is worth running. Integer, in Q units (int8, ±100). Swept 2/4/8 — see
# docs/STATUS.md; 4 is the reported default.
ESC_MARGIN = 4
