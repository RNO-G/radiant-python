#!/usr/bin/env python3

from radiant import RADIANT
from enum import Enum
import time

class TuneResult(Enum):
    SUCCESS = 0
    AUTOMATCH_FAIL = 1
    TUNE_FAIL = 2

# This is an *incredibly* aggressive way of doing this.
# If something goes wrong, it'll... just keep trying for like, 50 attempts.
# So you kinda need to watch it.
#
# This is also slow, as it does the initial tunes one by one, not all at once.

# make sure:
# LABs are all on (should happen by default)
# CPLDs are programmed (run radcpldprog.py)
# Pedestal is at desired/attenuators set right (really!! run analog_setup.py)

dev = RADIANT("/dev/ttyO5")
dev.labc.stop()
dev.identify()
dev.calib.resetCalib()

dna = dev.dna()
dev.calib.load(dna)

dev.labc.reg_clr()
dev.labc.testpattern_mode(False)

# things are weird, let's try a different tactic
ok = []
phaberror = {}
tuneok = {}
for quad in range(3): # loop over quads
    labs = [int(4 * quad + i) for i in range(4)] + [int(4 * quad + i + 12) for i in range(4)]

    for lab in labs:
        dev.labc.default(lab)
        phaberror[lab] = dev.labc.automatch_phab(lab)

    # give the DLL some time to settle?
    time.sleep(0.5)
    tuneok_quad = dev.calib.initialTune(quad)
    for key in tuneok_quad:
        tuneok[key] = tuneok_quad[key]
        
print("Final result")
for key in tuneok:
    print("LAB",key,"tune:\t", tuneok[key], "\t phab err:\t", phaberror[key])
    

dev.calib.save(dna)
dev.radsig.enable(False); 
dev.calSelect(None) 
