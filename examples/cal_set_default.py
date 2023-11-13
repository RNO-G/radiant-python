#! /usr/bin/env python3 
import radiant
from radiant import RADIANT
import sys.argv 

mask=0xffffff
if len(sys.argv) > 1: 
    mask = int(sys.argv[1])

dev = RADIANT("/dev/ttyRadiant")
uid = dev.uid()
dev.calib.load(uid)

for i in range(24): 
    if mask & (1 << i): 
        dev.calib.lab4_resetSpecifics(i) 


dev.calib.save(uid)
