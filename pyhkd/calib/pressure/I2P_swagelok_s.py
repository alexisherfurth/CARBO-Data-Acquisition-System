

# Swagelok S Model Transducer, 4-20 mA version.
# Got standard calibration by emailing Swagelok
I2P_swagelok_s_m = 0.358 * 0.001 * 0.01934 # (mA/psi)*(A/mA)(psi/Torr) = A/Torr
I2P_swagelok_s_b = 9.262 * 0.001 # mA*(A/mA) = A
I2P_swagelok_s_1atm = 760 # 1 atm in Torr, since the original equation gives 0 psi at atmosphere
def I2P_swagelok_s(i_in):
	if i_in <= 0:
		return 0.0
	return float(((i_in-I2P_swagelok_s_b)/I2P_swagelok_s_m) + I2P_swagelok_s_1atm)
