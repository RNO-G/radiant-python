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
dev.identify()
uid = dev.uid()
dev.labc.stop()
dev.labc.reg_clr()
dev.labc.testpattern_mode(False)
# things are weird, let's try a different tactic
ok = []
for i in range(24):
    dev.labc.default(i)
    matchok = dev.labc.automatch_phab(i)
    if matchok:
        # give the DLL some time to settle?
        time.sleep(0.5)
        tuneok = dev.calib.initialTune(i)
        if tuneok:
            ok.append(TuneResult.SUCCESS)
        else:
            ok.append(TuneResult.TUNE_FAIL)
    else:
        ok.append(TuneResult.AUTOMATCH_FAIL)
for i in range(24):
    print("LAB",i,"tune: ", ok[i].name)

dev.calib.save(uid)
