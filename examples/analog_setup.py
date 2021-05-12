#!/usr/bin/env python3

from radiant import RADIANT

dev = RADIANT("/dev/ttyO5")
# OK this is just my preference, I like green to indicate the
# selected cal port. Plus if there's a failure on the cal amp
# I *think* the LED will stay red.
# (I need to add options to tristate all the LEDs anyway for power savings...)
for i in range(6):
    # enable LAB4 + trigger and set LED red
    dev.write(dev.map['BM_I2CGPIO_BASE']+4*i, 0xF0)

# set pedestal to 0.76V
dev.pedestal(int((760/3300)*4095))

# set all trigger biases to 1.2V
# set all attenuators to 0 dB
for i in range(24):
    # trigger bias
    dev.write(dev.map['BM_TRIGDAC_BASE']+4*i, 2500)
    # signal attenuator
    dev.atten(i, 0)
    # trigger attenuator
    dev.atten(i, 0, trigger=True)
    
# done