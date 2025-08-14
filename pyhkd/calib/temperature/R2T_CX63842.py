
from .helpers import R2T_inverse_polylog

# A Cernox in TIME
R2T_CX63842_R_BORDER = 428.6
R2T_CX63842_LOW_A = [9.5976, -9.8374, 3.9656, -0.78156, 0.0746133, -0.00271]
R2T_CX63842_HIGH_A = [-22.5, 17.662, -5.3124, 0.76132, -0.051838, 0.00137]
def R2T_CX63842(inRes):
	if inRes < R2T_CX63842_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX63842_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX63842_HIGH_A)
