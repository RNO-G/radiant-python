# This class is a replacement for the old SURF calibrations stuff.
# Instead of calling out things like vtrimfb/vadjn/vadjp, we
# split the LAB4D parameters into "global" and "specific". Global
# defaults are pulled in by the LAB4 controller and loaded via
# the labAll load. Specific defaults are loaded one at a time
# (... for now, I guess)
#
# This class also pulls in a lot of behavior from the surf_daq's
# calibration's stuff (tuneLoop, etc.) because it did a ton of the
# math off-board. Now that we can do it on-board, it makes more
# sense to bury it in a generic calibrations class.
#
# If we make a SURF5 DMA engine which matches the SPIDMA's interface
# this will work there as well, which is pretty damn cool (obviously
# once the SURF5 gets a CALRAM as well).
import logging
import numpy as np
import pickle
from os import path
import os 
import random
import time

class RadCalib:
    # do something at init
    # trigsPerRoll is the number of triggers I have to generate
    # to get through a full 4096 samples
    def __init__(self, dev, genericFn, numLabs=24, trigsPerRoll=4, channelMask=0, calibPath="./calib", logger=logging.getLogger('root')):
        self.dev = dev
        self.trigsPerRoll = 4
        self.channelMask = 0
        self.numLabs=numLabs
        self.calibPath = calibPath
        self.logger = logger
        os.makedirs(calibPath, exist_ok=True) 
        # Build up a generic RADIANT: 24x generic parameters, all independent
        generic = pickle.load(open(genericFn, "rb"))
        self.generic = generic.copy()
        # reset the calib
        self.resetCalib()

    def resetCalib(self):
        self.calib = {}
        self.calib['pedestals'] = None
        specs = []
        for i in range(self.numLabs):
            specs.append(self.generic.copy())
        self.calib['specifics'] = specs
        
    # Save our calibration.
    def save(self, dna):
        namestr = path.join(self.calibPath, "cal_"+format(dna,'x')+".npy")
        np.save(namestr, self.calib)
    
    # Load our calibration.
    def load(self, dna):
        namestr = path.join(self.calibPath, "cal_"+format(dna,'x')+".npy")
        if path.isfile(namestr):
            self.calib = {}
            tmp = np.load(namestr)
            # This is probably insane: I should change
            # this to use JSON, but the problem is that
            # it'll convert the integer keys to strings,
            # and then it's not quite as simple to load them.
            # Need to see if there's a simple way to work
            # around that...
            #
            # yeah, we should do that: we'll save them
            # as JSON that way both C and Python stuff
            # can use them. To Be Done!
            self.calib = tmp[()]
        else:
            self.logger.warning(f"File {namestr} not found: using defaults")
            self.resetCalib()
    
    # Gets the LAB4-specific parameters for each LAB.
    def lab4_specifics(self, lab):
        return self.calib['specifics'][lab]

    def lab4_specifics_set(self, lab, key, value):
        self.calib['specifics'][lab][key] = value

    def lab4_resetSpecifics(self, lab):
        self.calib['specifics'][lab] = self.generic.copy()
    
    # Updates pedestals, both locally
    # *and* in the CALRAM.
    def updatePedestals(self):
        self.logger.info("Updating pedestals...")
        self.dev.labc.stop()
        self.dev.calram.zero()
        self.dev.calram.mode(self.dev.calram.CalMode.PEDESTAL)
        self.dev.labc.start()
        # Build up 512-sample sum of pedestals. The 512 here is magic,
        # it's the amount needed for the zerocrossing
        for i in range(4*self.trigsPerRoll):
            self.dev.labc.force_trigger(block=True, numTrig=128, safe=True)
        self.dev.labc.stop()
        # peds are updated, dump them
        self.logger.info("Fetching pedestals...")
        self.dev.dma.engineReset()
        self.dev.dma.txReset()
        self.dev.dma.enable(True, self.dev.dma.calDmaMode)
        for i in range(self.numLabs):
            final = i==(self.numLabs-1)
            self.dev.dma.setDescriptor(i, self.dev.calram.base+4096*4*i, 4096, increment=True, final=final)

        self.dev.dma.beginDMA()
        rawped = np.frombuffer(bytearray(self.dev.dma.dmaread(4096*4*self.numLabs)),dtype=np.uint32)
        rawped = rawped/512
        self.calib['pedestals'] = rawped.reshape(24, 4096)
        self.logger.info("Update complete")

    def getPedestals(self, asList=False):
        if asList:
            return self.calib['pedestals'].tolist()
        return self.calib['pedestals']
