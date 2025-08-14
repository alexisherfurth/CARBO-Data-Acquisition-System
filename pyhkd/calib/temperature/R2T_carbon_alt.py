
from .helpers import R2T_inverse_polylog

# Allen-Bradley calibration from the TIME labview
R2T_carbon_alt_A = [1.2689, -0.70516, 0.11945, -0.00568]
def R2T_carbon_alt(inRes):
	return R2T_inverse_polylog(inRes, R2T_carbon_alt_A)
	
