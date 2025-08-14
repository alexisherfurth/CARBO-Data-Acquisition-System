from __future__ import division, print_function
from .helpers import R2T_inverse_polylog

# He3 Evap UC in K0 fridge (CX41473)
#R2T_He3_EvapUC_K0_A = [542.61, -227.27, 31.499, -1.4365] ; DUBAND
R2T_He3_EvapUC_K0_A = [-15.005863, 26.823492, -13.438935, 2.9166204, -0.29335934, 0.011436003] #; Skillo
def R2T_He3_EvapUC_K0(inRes):
	return R2T_inverse_polylog(inRes, R2T_He3_EvapUC_K0_A)

