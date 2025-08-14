

import math

# A cernox in Short Keck	
R2T_CX67544_A0 = 0.0987294
R2T_CX67544_A1 = 0.364596
R2T_CX67544_A2 = 0.0268477
R2T_CX67544_A3 = 0.0188578
def R2T_CX67544(inRes):
	
	if inRes <= 0:
		return 0.0
	
	Z = 1000 / inRes
	temp = R2T_CX67544_A0 + (R2T_CX67544_A1 * Z) + (R2T_CX67544_A2 * math.pow(Z, 2)) + (R2T_CX67544_A3 * math.pow(Z, 3))
	return temp
	
