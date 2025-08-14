from __future__ import division, print_function
from .helpers import R2T_inverse_polylog
import math

# X59076 cernox in K0	
R2T_CX59076_A0 = 1.11413877e-01
R2T_CX59076_A1 = 4.37921941e-01
R2T_CX59076_A2 = 2.98573781e-02
R2T_CX59076_A3 = 3.36650119e-02
R2T_CX59076_A4 = -1.43346203e-04
R2T_CX59076_A5 = 5.76924080e-06
def R2T_CX59076(inRes):
	
	if inRes <= 0:
		return 0.0
	
	Z = 1000 / inRes
	temp = R2T_CX59076_A0 + (R2T_CX59076_A1 * Z) + (R2T_CX59076_A2 * math.pow(Z, 2)) + (R2T_CX59076_A3 * math.pow(Z, 3) + (R2T_CX59076_A4 * math.pow(Z, 4)) + + (R2T_CX59076_A5 * math.pow(Z, 5)))
	return temp

