from __future__ import division, print_function
from .helpers import R2T_inverse_polylog

# He4 Evap in K0 fridge (CX45758)
R2T_He4_Evap_K0_A = [7.015, -2.8844, 0.36308, -0.012291]
def R2T_He4_Evap_K0(inRes):
	return R2T_inverse_polylog(inRes, R2T_He4_Evap_K0_A)

