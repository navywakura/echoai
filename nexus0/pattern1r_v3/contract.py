"""Only estimator barometer uncertainty changes; perception stays frozen."""
import math
import xml.etree.ElementTree as ET
from echoai.nexus0.pattern1r_v2.contract import *
from echoai.nexus0.pattern1r_v2 import contract as prior
from echoai.nexus0.flight1s.v3 import campaign as c


def barometer_uncertainty():
    path = c.ECHOAI/'nexus0/sensor1s/assets/models/x500_sensor1s_base/model.sdf'
    noise = ET.parse(path).getroot().find('.//sensor[@name="air_pressure_sensor"]/air_pressure/pressure/noise/stddev')
    pressure_sigma = float(noise.text)
    # Standard atmosphere derivative near sea level. PX4's documented floor
    # exceeds this simulation sensor's noise, including pressure quantisation.
    derivative = 44330.0 * 0.190295 / 101325.0
    pressure_float32_ulp = 2.0**(math.floor(math.log2(101325.0))-23)
    altitude_sigma = derivative*math.sqrt(pressure_sigma**2+pressure_float32_ulp**2/12)
    return dict(pressure_sigma_pa=pressure_sigma, derivative_m_pa=derivative,
                pressure_float32_ulp_pa=pressure_float32_ulp, altitude_sigma_m=altitude_sigma,
                px4_minimum_m=0.01, configured_sigma_m=max(0.01,altitude_sigma))


def configuration():
    cfg = prior.configuration()
    cfg['px4_parameters'] = dict(cfg['px4_parameters'], EKF2_BARO_NOISE=barometer_uncertainty()['configured_sigma_m'])
    cfg['candidate'] = 'pattern1r-baro-covariance'
    cfg['profile'] = 'pattern1r-x500-v3'
    return cfg
