
from .helpers import R2T_inverse_polylog

# A Cernox in TIME
R2T_CX69932_R_BORDER = 280
R2T_CX69932_LOW_A = [-1.0144,1.5967,-0.9655,0.28459,-0.041285,0.0023801]
R2T_CX69932_HIGH_A = [-34.653,25.733,-7.4689,1.047,-0.070295,0.0018475]
def R2T_CX69932(inRes):
	if inRes < R2T_CX69932_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX69932_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX69932_HIGH_A)
		
