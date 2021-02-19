#!/usr/bin/env python3

from radiant import RADIANT

# This example just sets the frequency to 91 MHz and leaves
# it on. I don't have an example to turn it off. Need to add
# command line crap here. I also don't select a quad (that's
# dev.calSelect).

dev = RADIANT("/dev/ttyO5")
dev.radsig.enable(True)
# bands 1 and 3 are wonky right now, and band 2 is 
# actually the 600+ MHz band
dev.radsig.signal(pulse=False, band=0)
dev.radsig.setFrequency(91.0)
