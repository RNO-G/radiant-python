#!/usr/bin/env python3

from radiant import RADIANT
import time
import numpy as np

dev = RADIANT("/dev/ttyO5")
# switch to pulse
dev.radsig.signal(pulse=True)
# internal PPS
dev.write(0x10, (1<<31) | 0xa)
# scalers
sc = np.empty([24, 10])    

for q in range(3):
    print("Building quad",q,"and",q+3,":",end='',flush=True)
    dev.calSelect(q)
    for i in range(4):
        dev.thresh(4*q + i, 500)
        dev.thresh(4*q + i + 12, 500)
    time.sleep(1)
    for step in range(10):
        print(" ", step, end='', flush=True)
        # set thresholds
        for i in range(4):
            dev.thresh(4*q + i, 500 + 100*step)
            dev.thresh(4*q + i + 12, 500 + 100*step)
        # accumulate
        time.sleep(3)
        # read values
        for i in range(4):
            sc[ 4*q + i ][step] = dev.read(0x30400+4*(4*q+i))
            sc[ 4*q + i + 12][step] = dev.read(0x30400+4*(4*q+i+12))
    print("")
for i in range(24):
    print("Channel",i,":",end='',flush=True)
    for j in range(10):
        print(" ", sc[i][j], end='', flush=True)
    print("")
