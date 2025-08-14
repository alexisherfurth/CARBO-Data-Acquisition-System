
from .helpers import R2T_inverse_polylog


# A Cernox in TIME
R2T_CX59078_R_BORDER = 211
R2T_CX59078_LOW_A = [-7.5779,9.4711,-4.7523,1.1975,-0.15168,0.00774]
R2T_CX59078_HIGH_A = [-0.24965,1.9322,-0.81715,0.099926,-0.0018551,-8.51E-5]
def R2T_CX59078(inRes):
	if inRes < R2T_CX59078_R_BORDER:
		return R2T_inverse_polylog(inRes, R2T_CX59078_LOW_A)
	else:
		return R2T_inverse_polylog(inRes, R2T_CX59078_HIGH_A)
