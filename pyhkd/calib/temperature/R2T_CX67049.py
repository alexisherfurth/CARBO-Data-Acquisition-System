from __future__ import division, print_function
from .helpers import R2T_chebyshev
import math

# A cernox in K0
R2T_CX67049_A0 = 0.0956436
R2T_CX67049_A1 = 0.326795
R2T_CX67049_A2 = 0.0218064
R2T_CX67049_A3 = 0.0132351
def R2T_CX67049(inRes):
	
	if inRes <= 0:
		return 0.0
	
	Z = 1000 / inRes
	temp = R2T_CX67049_A0 + (R2T_CX67049_A1 * Z) + (R2T_CX67049_A2 * math.pow(Z, 2)) + (R2T_CX67049_A3 * math.pow(Z, 3))
	return temp

