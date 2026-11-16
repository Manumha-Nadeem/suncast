"""
physics.py

The physics formula from our Deliverable 2 baseline, adapted for a rooftop:

    kW = system_kw * (radiation / 1000) * (1 + GAMMA * (module_temp - 25)) * LOSS_FACTOR

The weather forecast gives air temperature, not panel temperature, so the
panel temperature is estimated with the standard NOCT rule:

    module_temp = air_temp + 0.03125 * radiation

The backend uses this as the comparison line ("baseline") on every forecast,
and as a fallback if the ML predictor is not available.
"""

import numpy as np

GAMMA = -0.004        # power change per degree C above 25 C (same as physics_baseline.py)
T_REF = 25.0          # standard test temperature (C)
NOCT_FACTOR = 0.03125 # (45 - 20) / 800, for a panel with NOCT of 45 C
LOSS_FACTOR = 0.86    # wiring, dust and inverter losses (assumed, stated in the report)


def module_temperature(radiation, temp_c):
    """Estimated panel temperature (C) from radiation (W/m2) and air temperature (C)."""
    return np.asarray(temp_c) + NOCT_FACTOR * np.asarray(radiation)


def physics_kw(radiation, temp_c, system_kw):
    """Hourly output in kW for a rooftop system of `system_kw` kW."""
    radiation = np.asarray(radiation, dtype=float)
    t_mod = module_temperature(radiation, temp_c)
    kw = system_kw * (radiation / 1000) * (1 + GAMMA * (t_mod - T_REF)) * LOSS_FACTOR
    return np.clip(kw, 0, None)
