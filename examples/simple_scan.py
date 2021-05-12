#!/usr/bin/env python3

from radiant import RADIANT
import time

dev = RADIANT("/dev/ttyO5")
# switch to pulse
dev.radsig.signal(pulse=True)
# internal PPS
dev.write(0x10, (1<<31) | 0xa)
for i in range(24):
    dev.calSelect(int(i/4))
    scan = []
    # set threshold to initial value
    dev.thresh(i, 500)
    # and let it settle
    time.sleep(0.2)
    print("Channel",i,":",end='',flush=True)
    for step in range(500, 1500, 100):
        # set threshold to target
        dev.thresh(i, step)
        # accumulate
        time.sleep(2)
        # read value
        val = dev.read(0x30400+4*i)
        print(" ", val, end='', flush=True)
    print("")
