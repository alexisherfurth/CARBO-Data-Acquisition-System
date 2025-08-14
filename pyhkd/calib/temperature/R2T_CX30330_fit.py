from __future__ import division, print_function
from .helpers import R2T_chebyshev
import math

# X30330 cernox in K0	
R2T_CX30330_A0 = 1.42046611e-01
R2T_CX30330_A1 = 3.66391016e-01
R2T_CX30330_A2 = 5.45788848e-02
R2T_CX30330_A3 = -5.96458573e-04
R2T_CX30330_A4 = 1.91102437e-03
R2T_CX30330_A5 = -8.64263074e-05
def R2T_CX30330(inRes):
	
	if inRes <= 0:
		return 0.0
	
	Z = 1000 / inRes
	temp = R2T_CX30330_A0 + (R2T_CX30330_A1 * Z) + (R2T_CX30330_A2 * math.pow(Z, 2)) + (R2T_CX30330_A3 * math.pow(Z, 3) + (R2T_CX30330_A4 * math.pow(Z, 4)) + + (R2T_CX30330_A5 * math.pow(Z, 5)))
	return temp

