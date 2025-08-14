
from .helpers import R2T_inverse_polylog

		
# A Cernox in TIME
R2T_CX63814_R_BORDER = 216.6
R2T_CX63814_LOW_A = [-3.4193,2.2355,-0.48995,0.036098]
R2T_CX63814_HIGH_A = [0.75612,0.094419,-0.12683,0.015765]
def R2T_CX63814(inRes):
	if inRes < R2T_CX63814_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX63814_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX63814_HIGH_A)
