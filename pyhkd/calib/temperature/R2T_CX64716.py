
from .helpers import R2T_inverse_polylog


# A Cernox in TIME
R2T_CX64716_R_BORDER = 183.935
R2T_CX64716_LOW_A = [-2.2711,1.5553,-0.35749,0.027695]
R2T_CX64716_HIGH_A = [-0.03222,0.50471,-0.20143,0.020616]
def R2T_CX64716(inRes):
	if inRes < R2T_CX64716_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX64716_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX64716_HIGH_A)
