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
path_to_radcplddata = path.join(path_to_radiant, "radiant_aux_v2.bit")

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

dev.labc.default(dev.labc.labAll)
dev.labc.automatch_phab(dev.labc.labAll)

dev.calib.resetCalib()
uid = dev.uid()
dev.calib.load(uid)

# Using default isels for now

#isels = [2482, 2492, 2510, 2480, 2480, 2515, 2480, 2525, 2502, 2492, 2494, 2505, 2480, 2500, 2495, 2511, 2487, 2483, 2507, 2500, 2535, 2499, 2505, 2490] # Works for 2.5
#for iLab in range(24):
#    dev.labc.l4reg(iLab, 10, isels[iLab])
#    dev.labc.update(iLab)

dev.labc.testpattern_mode(False)

dev.calram.zero()
dev.calram.mode(dev.calram.CalMode.NONE)
dev.calib.updatePedestals()
np.save("peds.npy", dev.calib.calib['pedestals'])


