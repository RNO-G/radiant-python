import radiant
from radiant import RADIANT
import numpy as np
import time
import copy
import os
import glob
import subprocess

def reset_sequence(dev):
    dev.labc.stop()
    dev.dma.reset()

    dev.labc.testpattern_mode(False)
    dev.calram.zero()
    dev.calram.mode(dev.calram.CalMode.NONE) 
    dev.dma.write(3, 0) 

    dev.dma.engineReset()
    dev.dma.txReset()

    # Turn off cal pulser
    for i in range(6):
        dev.write(dev.map['BM_I2CGPIO_BASE']+4*i, 0xF0)

    time.sleep(1.0)

dev = RADIANT("/dev/ttyO5")
reset_sequence(dev)

dev.calib.resetCalib()
dna = dev.dna()
dev.calib.load(dna) # load whatever calibration has already been done

niter = 10 # number of iterations
buff = 32 # window not to change it 
step = 4 # steps to change the isels by
voltage_setting = 1250 # voltage to make middle of the range

print("Start isel values:", [dev.calib.calib['specifics'][iLab][10] for iLab in range(24)])

for iIter in range(niter):
    reset_sequence(dev)

    for iLab in range(24):
        dev.labc.update(iLab)
    
    dev.pedestal(int((voltage_setting/3300)*4095))
    time.sleep(0.5)
    dev.calib.updatePedestals()

    # Now going to fit a line through those two points
    for iLab in range(24):
        x0 = voltage_setting
        y0 = np.median(dev.calib.calib['pedestals'][iLab][:1024])

        if(y0 == 0):
            continue
               
        print(iIter, iLab, y0)
        if(y0 + buff < 2047):
            dev.calib.calib['specifics'][iLab][10] += step
        elif(y0 - buff > 2047):
            dev.calib.calib['specifics'][iLab][10] -= step

print("Final isel values:", [dev.calib.calib['specifics'][iLab][10] for iLab in range(24)])

dna = dev.dna()
dev.calib.save(dna)
