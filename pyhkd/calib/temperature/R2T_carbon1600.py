
from .helpers import R2T_inverse_polylog

# Allen-Bradley 1.6k ohm from Duband
R2T_carbon1600_cof = [1.9555, -0.68477, 0.07484, -0.0024271]
def R2T_carbon1600(inRes):
	return R2T_inverse_polylog(inRes, R2T_carbon1600_cof)
	
