
import numpy as np
import matplotlib.pyplot as pl

'''
Bryan, 2021 11 14
I noticed that FPU2 has a non-monotonic, noisy calibration.
I moved it to R2T_XSKFPU2.interp_old
This script generates a new calibration from that file, which is smoothed to eliminate the non-monotonicity and eliminate the non-physical high frequency noise.
'''

r,t = np.loadtxt('R2T_XSKFPU2.interp_old').T

#y = 1000. / r
#p = np.polyfit(np.log(y),np.log(t),3)
#tf = np.polyval(p,y)

# A polynomial in log-log space seems to work well for this thermometer
# I found 5 was the lowest order for this thermometer that reduced low frequency wiggles to below the level of the high frequency noise.
p = np.polyfit(np.log(r),np.log(t),5)
tf = np.exp(np.polyval(p,np.log(r)))

# Save it as a linear interpolation on the same resistances to avoid changing the hw_sk.json file.
np.savetxt('R2T_XSKFPU2.interp',np.vstack((r,t)).T,fmt='%.6f')

pl.subplot(211)
pl.plot(r,t)
pl.plot(r,tf)
pl.gca().set_xscale('log')
pl.gca().set_yscale('log')
pl.grid()
pl.subplot(212)

pl.plot(r,(t-tf)/tf)
pl.gca().set_xscale('log')
pl.grid()
pl.show()

