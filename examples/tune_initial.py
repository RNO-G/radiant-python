#!/usr/bin/env python3

from radiant import RADIANT

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
dna = dev.dna()
dev.labc.stop()
dev.labc.reg_clr()
dev.labc.default(dev.labc.labAll)
dev.labc.testpattern_mode(False)
ok = []
for i in range(24):
    ok.append(dev.labc.automatch_phab(i))
for i in range(24):
    print("LAB",i,"automatch", end='')
    if ok[i]:
        print("SUCCESS")
    else:
        print("FAILURE")
        
ok = []
for i in range(24):
    ok.append(dev.labc.initialTune(i))

for i in range(24):
    print("LAB",i,"tune", end='')
    if ok[i]:
        print("SUCCESS")
    else:
        print("FAILURE")

dev.calib.save(dna)
