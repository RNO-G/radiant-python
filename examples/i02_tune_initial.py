#!/usr/bin/env python3

from radiant import RADIANT
from enum import Enum
import time
import sys 

class TuneResult(Enum):
    SUCCESS = 0
    AUTOMATCH_FAIL = 1
    TUNE_FAIL = 2
    SKIPPED = 3

# This is an *incredibly* aggressive way of doing this.
# If something goes wrong, it'll... just keep trying for like, 50 attempts.
# So you kinda need to watch it.
#
# This is also slow, as it does the initial tunes one by one, not all at once.

# make sure:
# LABs are all on (should happen by default)
# CPLDs are programmed (run radcpldprog.py)
# Pedestal is at desired/attenuators set right (really!! run analog_setup.py)

dev = RADIANT("/dev/ttyRadiant")

dna = dev.dna()
dev.calib.load(dna)
mask = 0xffffff 
do_reset = False
if len(sys.argv) > 1: 
    mask = int(sys.argv[1],0)

if len(sys.argv) > 2: 
    do_reset = bool(sys.argv[2]) 
# things are weird, let's try a different tactic
ok = []

if do_reset: 
    for i in range(24): 
        dev.calib.lab4_resetSpecifics(i) 
        if (mask & (1 <<i)): 
            dev.labc.default(i) 
    for i in range(24): 
        if (mask & (1 <<i)): 
            dev.labc.automatch_phab(i) 


else: 
    dev.calib.load(dna)



fail_mask = 0x0 

for i in range(24):

    if not (mask & (1 <<i)): 
        print("Skipping channel ",i)
        ok.append(TuneResult.SKIPPED)
        continue 

    tuneok = dev.calib.initialTune(i)
    if tuneok:
        ok.append(TuneResult.SUCCESS)
    else:
        ok.append(TuneResult.TUNE_FAIL)
        fail_mask |= (1 << i); 

for i in range(len(ok)):
    print("LAB",i,"tune: ", ok[i].name)

print("Fail mask:" + hex(fail_mask))

dev.calib.save(dna)
dev.radsig.enable(False); 
dev.calSelect(None) 
