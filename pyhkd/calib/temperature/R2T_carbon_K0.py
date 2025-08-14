from __future__ import division, print_function
from .helpers import R2T_inverse_polylog

# Allen-Bradley 1.6k ohm from Duband
R2T_carbon_K0_A = [2.2587, -0.78337, 0.085379, -0.0027947]
def R2T_carbon_K0(inRes):
	return R2T_inverse_polylog(inRes, R2T_carbon_K0_A)
