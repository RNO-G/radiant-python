#!/usr/bin/env python3
from radiant import RADIANT
import time
import sys

bootload_id = 0x5244424C
normal_id = 0x52444E54

dev = RADIANT("/dev/ttyO5")
# reset command path
dev.reset()
# are we already in bootloader mode?
id = dev.read(dev.map['FPGA_ID'])
if id == bootload_id:
    print("Already in bootloader, not doing anything.")
    sys.exit(0)
else:
    print("In normal running mode. Kicking to bootloader...", end='', flush=True)
    dev.reboot(2)
    time.sleep(1)
    dev.reset()
    id = dev.read(dev.map['FPGA_ID'])
    if id != bootload_id:
        print("Reboot to bootloader failed:", hex(id))
        sys.exit(1)
    else:
        print("RADIANT is in BOOTLOADER mode.")
        sys.exit(0)
