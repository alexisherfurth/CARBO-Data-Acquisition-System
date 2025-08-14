
from .helpers import R2T_inverse_polylog


# A Cernox in TIME
R2T_CX63841_R_BORDER = 222
R2T_CX63841_LOW_A = [-4.2664,2.7288,-0.58493,0.042132]
R2T_CX63841_HIGH_A = [3.1054,-1.1496,0.094651,2.4725E-3]
def R2T_CX63841(inRes):
	if inRes < R2T_CX63841_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX63841_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX63841_HIGH_A)
