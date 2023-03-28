#! /usr/bin/env python3 
import radiant
from radiant import RADIANT
import sys.argv 

mask=0xffffff
if len(sys.argv) > 1: 
    mask = int(sys.argv[1])

dev = RADIANT("/dev/ttyRadiant")
dna = dev.dna()
dev.calib.load(dna)

for i in range(24): 
    if mask & (1 << i): 
        dev.calib['specifics'][i] = dev.calib.generic.copy() 


dev.calib.save(dna)
