from __future__ import division, print_function
from .helpers import R2T_inverse_polylog

# He4 Cond in K0 fridge (CX45972)
R2T_He4_Cond_K0_A = [2.0668, -0.7469, 0.073751, -0.0009101]
def R2T_He4_Cond_K0(inRes):
	return R2T_inverse_polylog(inRes, R2T_He4_Cond_K0_A)

