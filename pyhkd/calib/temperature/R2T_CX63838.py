
from .helpers import R2T_inverse_polylog

# A Cernox in TIME
R2T_CX63838_R_BORDER = 1793
R2T_CX63838_LOW_A = [34.98,-30.487,10.69,-1.8785,0.1643,-0.0056479]
R2T_CX63838_HIGH_A = [-20.511,13.882,-3.7414,0.48733,-0.02993,0.0007136]
def R2T_CX63838(inRes):
	if inRes < R2T_CX63838_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX63838_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX63838_HIGH_A)
