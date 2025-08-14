
from .helpers import R2T_inverse_polylog

# A Cernox in TIME
R2T_CX63836_R_BORDER = 346
R2T_CX63836_LOW_A = [2.2703,-1.8716,0.51163,-0.034786,-0.0059144,0.000756]
R2T_CX63836_HIGH_A = [0.86125,-0.79063,0.34839,-0.084631,0.0098528,-0.0003853]
def R2T_CX63836(inRes):
	if inRes < R2T_CX63836_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX63836_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX63836_HIGH_A)
		
