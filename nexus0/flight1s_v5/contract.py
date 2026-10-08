"""Reuse v4 acceptance exactly; change only the fixed physical configuration."""
from echoai.nexus0.flight1s_v4.contract import (
    group, sign_tail, lower_bound, separation, displacement, verdict,
)
from echoai.nexus0.flight1s_v4 import contract as v4
from echoai.nexus0.flight1s.v3 import campaign as c

IMAGE = 'localhost/echoai-flight1s-px4:v1.15.4-gpsaccuracy'


def protocol():
    p = v4.protocol()
    cfg = c.configuration('gpsfix_7n')
    cfg['candidate'] = 'gpsaccuracy_7n'
    cfg['image'] = IMAGE
    cfg['px4_parameters']['EKF2_GPS_V_NOISE'] = 0.158
    p.update(version=5, configuration=cfg)
    p['stages']['validation']['seed'] = 20260923
    p['stages']['bench']['seed'] = 20260924
    return p


def validate(p):
    if p != protocol():
        raise ValueError('v5 protocol differs from preregistration')
