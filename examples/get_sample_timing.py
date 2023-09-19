import radiant
from radiant import RADIANT
import numpy as np
import time
import copy
from os import path

#dev.calib.resetCalib()
#dna = dev.dna()
#dev.calib.load(dna)

#dev.labc.testpattern_mode(False)
dev=RADIANT('/dev/ttyO5')
dev.calram.zero()
dev.calram.mode(dev.calram.CalMode.NONE)
dev.calib.updatePedestals()

np.save("peds.npy", dev.calib.calib['pedestals'])

#print timing
labs=[8]
labs=np.arange(0,24,1)
for i in range(1):
    print()
    for lab in labs:
        print(lab)
        #dump strobes 
        dev.labc.scan_dump(lab)
        freq=510
        dev.calSelect(int(lab/4))
        dev.radsig.enable(False)
        dev.radsig.signal(pulse=False,band = (2 if freq>100 else 0))
        dev.calib.updatePedestals()
        dev.radsig.enable(True)
        dev.radsig.setFrequency(freq)
        t=dev.calib.getTimeRun(freq*1e6,verbose=False)
        print('time through fast samples = %0.3f'%(np.sum(t[lab][0:127])/1000),' ns')
        print('time through all samples = %0.3f'%(np.sum(t[lab][0:128])/1000),' ns')
        print('seam sample = %0.3f'%t[lab][0],' ps')
        print('slow sample = %0.3f'%t[lab][127], ' ps')
        print('avg of middle samples = %0.3f'%np.mean(t[lab][1:127]),' ps')
        np.savez('timing_data/lab_%i.npz'%lab,timing=t[lab][0:128])
        time.sleep(0.2)
        print()
#for lab in labs:
#    print('lab ',lab,' dumping internal strobes')
#    dev.labc.scan_dump(lab)
