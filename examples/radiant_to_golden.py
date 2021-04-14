#!/usr/bin/env python3
from radiant import RADIANT
import time
import sys

bootload_id = 0x5244424C
normal_id = 0x52444E54

dev = RADIANT("/dev/ttyO5")
# reset command path
dev.reset()

print("Booting golden image...", end='', flush=True)
dev.reboot(0)
time.sleep(1)
dev.reset()
id = dev.read(dev.map['FPGA_ID'])
if id != normal_id:
    print("Reboot to golden failed:", hex(id))
    sys.exit(1)
else:
    print("RADIANT is running golden image:")
    dev.identify()
    sys.exit(0)
