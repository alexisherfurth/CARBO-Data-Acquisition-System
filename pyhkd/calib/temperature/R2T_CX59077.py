
from .helpers import R2T_inverse_polylog

# A Cernox in TIME
R2T_CX59077_R_BORDER = 235
R2T_CX59077_LOW_A = [-0.44047, 1.182, -0.9289, 0.32333, -0.052827, 0.0033327]
R2T_CX59077_HIGH_A = [53.518, -36.909, 10.36, -1.5034, 0.1125, -0.0032782]
def R2T_CX59077(inRes):
	if inRes < R2T_CX59077_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX59077_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX59077_HIGH_A)
