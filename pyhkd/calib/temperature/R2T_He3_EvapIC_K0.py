from __future__ import division, print_function
from .helpers import R2T_inverse_polylog

# He3 Evap IC in K0 fridge (CX45528)
#R2T_He3_EvapIC_K0_A = [109.1, -40.869, 5.0206, -0.19808] ; DUBAND
R2T_He3_EvapIC_K0_A = [328.96639, -242.30209, 70.777761, -10.260934, 0.73874177, -0.021073715] #; Skillo
def R2T_He3_EvapIC_K0(inRes):
	return R2T_inverse_polylog(inRes, R2T_He3_EvapIC_K0_A)

