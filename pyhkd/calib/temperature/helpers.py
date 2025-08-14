

import os
import math

# Helper function for a fit of the form: 1 / (A0 + A1 ln(r) + A2 ln(r)^2 + ...)
def R2T_inverse_polylog(inRes, A):
	
	if inRes <= 0:
		return 0.0
		
	z = math.log(inRes)
	
	y = A[0] + A[1] * z # Save the overhead of math.pow for the easy ones
	for i in range(2, len(A)):
		y += A[i] * math.pow(z, i) # Use math and not np, as math will promote ints to floats
		
	if y > 0:
		return (1.0/y)
	else:
		return 0

# Helper function that defines a typical Lakeshore Chebyshev coefficient calibration procedure
def R2T_chebyshev(inRes, ZU, ZL, RU, RL, CC, logZ = True):

	if inRes <= 0:
		return 0.0
	
	if logZ:
		Z = math.log10(inRes)
	else:
		Z = inRes
		
	temp = 0
	for i in range(len(CC)):
		if inRes >= RL[i]:
			X = ((Z-ZL[i])-(ZU[i]-Z)) / (ZU[i]-ZL[i])
			for j in range(len(CC[i])):
				temp += CC[i][j] * (math.cos(j * math.acos(X)))
			break
	return temp 
	
# Helper function for a fit of the form: (A0 + A1 r + A2 r^2 + ...)
def R2T_polynomial(inRes, A):
	
	if inRes <= 0:
		return 0.0
		
	y = A[0] + A[1] * inRes # Save the overhead of math.pow for the easy ones
	for i in range(2, len(A)):
		y += A[i] * math.pow(inRes, i) # Use math and not np, as math will promote ints to floats
		
	return y

########
# Thanks to Bryan Steinbach for the following code that interprets Lakeshore cof files
########

def getline(f):
	line = f.readline()
	sep = ':'
	name,_,val = line.partition(sep)
	name = name.strip()
	val = val.strip()
	#~ print(name,val)
	return name,val

# Creates and returns a calibration function based on a lakeshore cof
def load_cof(fn):
	
	assert_msg = "Failure while loading cof file " + str(fn)
	
	f = open(fn,'r')

	thermoname = os.path.splitext(os.path.split(fn)[1])[0]

	name,val = getline(f)
	assert name == 'Number of fit ranges', assert_msg
	nfit = int(val)

	Zls = []
	Zus = []
	Rls = []
	Rus = []
	cc = []
	logZ = None
	
	for i in range(1,nfit+1):
		name,val = getline(f)
		assert name.startswith('FIT RANGE'), assert_msg
		assert val == str(i)

		name,val = getline(f)
		assert name.startswith('Fit type for range'), assert_msg
		
		if val.startswith('LOG'):
			if logZ == False:
				raise ValueError("Changing between linear and log fits in the same cof file is not currently supported.")
			logZ = True
		elif val.startswith('LIN'):
			if logZ == True:
				raise ValueError("Changing between linear and log fits in the same cof file is not currently supported.")
			logZ = False
		else:
			raise ValueError("Unexpected fit type in cof file: " + str(val))
			
		name,val  = getline(f)
		assert name.startswith('Order of fit range'), assert_msg
		norder = int(val)

		name,val = getline(f)
		assert name.startswith('Zlower for fit range'), assert_msg
		Zl = float(val)
		name,val = getline(f)
		assert name.startswith('Zupper for fit range'), assert_msg
		Zu = float(val)
		
		name,val = getline(f)
		assert name.startswith('Lower'), assert_msg
		assert 'limit for fit range' in name, assert_msg
		Rl = float(val)
		name,val = getline(f)
		assert name.startswith('Upper'), assert_msg
		assert 'limit for fit range' in name, assert_msg
		Ru = float(val)

		c = []
		for j in range(norder+1):
			name,val = getline(f)
			assert name.startswith('C(%d) Equation'%(j)), assert_msg
			c.append(float(val))

		Zls.append(Zl)
		Zus.append(Zu)
		Rls.append(Rl)
		Rus.append(Ru)
		cc.append(c)
		
	func = lambda r: R2T_chebyshev(r, Zus, Zls, Rus, Rls, cc, logZ)
	
	func.__name__ = fn
	
	return func
