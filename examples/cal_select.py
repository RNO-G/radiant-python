#!/usr/bin/env python3


#no args to select nothing, otherwise select the quad

from radiant import RADIANT
import sys

dev = RADIANT("/dev/ttyO5")

if len(sys.argv) == 1: 
    dev.calSelect(None) 

else:
    dev.calSelect(int(sys.argv[1]))


