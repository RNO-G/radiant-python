import radiant
from radiant import RADIANT
import numpy as np
import time
import copy
from os import path
import glob
import subprocess

path_to_radiant = path.dirname(radiant.__file__)
path_to_radcpldprog = path.join(path_to_radiant, "examples/radcpldprog.py")
path_to_radcplddata = path.join(path_to_radiant, "radiant_aux_v3.bit")

print("!!!! About to program CPLDs.")
try:
    list_files = subprocess.run(["python3", path_to_radcpldprog, "-f", path_to_radcplddata], timeout = 10)
except subprocess.TimeoutExpired:
    print("!!!! CPLD Programming timed out. Is the Radiant on?")
    print("!!!! Exiting.")
    exit()
    
print("!!!! The exit code was: %d" % list_files.returncode)
if(list_files.returncode != 0): 
    print("!!!! Some error in loading CPLDs. ")
    print("Exiting.")
    exit()

path_to_analogsetup = path.join(path_to_radiant, "examples/analog_setup.py")
    
print("!!!! About to set analog settings.")
try:
    list_files = subprocess.run(["python3", path_to_analogsetup], timeout = 10)
except subprocess.TimeoutExpired:
    print("!!!! Analog setup timed out. Is the Radiant on?")
    print("!!!! Exiting.")
    exit()
    
print("!!!! The exit code was: %d" % list_files.returncode)
if(list_files.returncode != 0): 
    print("!!!! Some error in loading analog setup. ")
    print("Exiting.")
    exit()

dev = RADIANT("/dev/ttyO5")

dev.labc.stop()
dev.dma.reset()
dev.labc.reg_clr()
print('load defaults')
dev.labc.default(dev.labc.labAll)

print('autmatch phab')
dev.labc.automatch_phab(dev.labc.labAll)

dev.calib.resetCalib()
dna = dev.dna()
dev.calib.load(dna)

dev.labc.testpattern_mode(False)

dev.calram.zero()
dev.calram.mode(dev.calram.CalMode.NONE)
dev.calib.updatePedestals()

np.save("peds.npy", dev.calib.calib['pedestals'])


