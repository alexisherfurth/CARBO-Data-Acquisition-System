

import math

# A calibrated Ro600E2 thermometer with serial number 3633 for LE Cryostat 
R2T_RO600E2_3633_RL = [2800, 1478, 0]
R2T_RO600E2_3633_CC = [[3.000000E+5, 5.700000E+2, -4.056486E-5, 1.733865E+0],
					   [4.999994E+4, 9.639625E+2, -2.517468E-5, 1.554129E+0],
					   [2.549996E+4, 9.571107E+2, -2.328548E-4, 1.418132E+0]]
def R2T_RO600E2_3633(inRes):
	for i in range(len(R2T_RO600E2_3633_RL)):
		if inRes > R2T_RO600E2_3633_RL[i]:
			return R2T_RO600E2_3633_CC[i][0] * pow(1/(inRes - R2T_RO600E2_3633_CC[i][1]) + R2T_RO600E2_3633_CC[i][2], R2T_RO600E2_3633_CC[i][3])
	return 0.0
