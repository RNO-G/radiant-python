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

dev = RADIANT("/dev/ttyO5")
#dev.labc.stop()
#dev.identify()
#dev.calib.resetCalib()

dna = dev.dna()
#dev.calib.load(dna)
#
#dev.labc.reg_clr()
#dev.labc.testpattern_mode(False)
#
mask = 0xffffff 

if len(sys.argv) > 1: 
    mask = int(sys.argv[1],0)

# things are weird, let's try a different tactic
ok = []
for i in range(24):

    if not (mask & (1 <<i)): 
        print("Skipping channel ",i)
        ok.append(TuneResult.SKIPPED)
        continue 

    dev.labc.default(i)
    time.sleep(0.1) 
    matchok = dev.labc.automatch_phab(i)

    nattempts = 0
    while matchok and nattempts < 3: 
        matchok = dev.labc.automatch_phab(i)
        time.sleep(0.1) 
        nattempts+=0 

    if not(matchok):
        # give the DLL some time to settle?
        time.sleep(0.5)
        tuneok = dev.calib.initialTune(i)
        if tuneok:
            ok.append(TuneResult.SUCCESS)
        else:
            ok.append(TuneResult.TUNE_FAIL)
    else:
        print("automatch_phab failed a bunch of times...") 
        ok.append(TuneResult.AUTOMATCH_FAIL)
for i in range(len(ok)):
    print("LAB",i,"tune: ", ok[i].name)

dev.calib.save(dna)
dev.radsig.enable(False); 
dev.calSelect(None) 
