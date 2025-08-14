
from .helpers import R2T_inverse_polylog

# Special Allen-Bradley calibration for TIME HS1 from Thomas on 20160118
R2T_TIME_HS1_A = [0.755186, -0.45675, 0.078793, -0.0029921]
def R2T_TIME_HS1(inRes):
	return R2T_inverse_polylog(inRes, R2T_TIME_HS1_A)

