
from .helpers import R2T_inverse_polylog

# A Cernox in TIME
R2T_CX69935_R_BORDER = 350
R2T_CX69935_LOW_A = [-0.73019,1.0216,-0.5707,0.15941,-0.022304,0.0012576]
R2T_CX69935_HIGH_A = [-36.956,25.397,-6.8827,0.90867,-0.057838,0.0014412]
def R2T_CX69935(inRes):
	if inRes < R2T_CX69935_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX69935_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX69935_HIGH_A)
