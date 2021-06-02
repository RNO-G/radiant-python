#!/usr/bin/env python3

from radiant import RADIANT
import time
import numpy as np

dev = RADIANT("/dev/ttyO5")
# switch to pulse
dev.radsig.signal(pulse=True)
dev.trig.pulseconfig(10000)
dev.trig.write(dev.trig.map['TRIGINEN'], 0xFFFFFFFF)

# internal PPS
dev.write(0x10, (1<<31) | 0xa)
# scalers
sc = np.empty([24, 10])    

for q in range(3):
    print("Building quad",q,"and",q+3,":",end='',flush=True)
    dev.calSelect(q)
    for i in range(4):
        dev.trig.thresh(4*q + i, 500)
        dev.trig.thresh(4*q + i + 12, 500)
    time.sleep(1)
    for step in range(10):
        print(" ", step, end='', flush=True)
        # set thresholds
        for i in range(4):
            dev.trig.thresh(4*q + i, 500 + 100*step)
            dev.trig.thresh(4*q + i + 12, 500 + 100*step)
        # accumulate
        time.sleep(3)
        # read values. Just do this by hand.
        l0 = dev.read(0x40800+4*(2*q))
        sc[ 4*q + 0 ][step] = l0 & 0xFFFF
        sc[ 4*q + 1 ][step] = (l0 >> 16) & 0xFFFF
        l1 = dev.read(0x40800+4*(2*q+1))
        sc[ 4*q + 2 ][step] = l1 & 0xFFFF
        sc[ 4*q + 3 ][step] = (l1 >> 16) & 0xFFFF        
        r0 = dev.read(0x40800+4*(2*q+12))
        sc[ 4*q + 12 ][step] = r0 & 0xFFFF
        sc[ 4*q + 13 ][step] = (r0 >> 16) & 0xFFFF
        r1 = dev.read(0x40800+4*(2*q+1+12))
        sc[ 4*q + 14 ][step] = r1 & 0xFFFF
        sc[ 4*q + 15 ][step] = (r1 >> 16) & 0xFFFF                
    print("")
for i in range(24):
    print("Channel",i,":",end='',flush=True)
    for j in range(10):
        print(" ", sc[i][j], end='', flush=True)
    print("")
