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
import numpy as np
import pickle
from os import path
import time

class RadCalib:
    # do something at init
    # trigsPerRoll is the number of triggers I have to generate
    # to get through a full 4096 samples
    def __init__(self, dev, genericFn, numLabs=24, trigsPerRoll=4, channelMask=0, calibPath="./calib"):
        self.dev = dev
        self.trigsPerRoll = 4
        self.channelMask = 0
        self.numLabs=numLabs
        self.calibPath = calibPath
        # calib hashmap for saving/loading
        self.calib = {}
        self.calib['pedestals'] = None        
        # Build up a generic RADIANT: 24x generic parameters, all independent
        generic = pickle.load(open(genericFn, "rb"))
        self.generic = generic.copy()
        specs = []
        for i in range(numLabs):
            specs.append(generic.copy())
            
        self.calib['specifics'] = specs

    # Save our calibration.
    def save(self, dna):
        namestr = "cal_" + format(dna, 'x') + ".npy"
        np.save(namestr, self.calib)
    
    # Load our calibration.
    def load(self, dna):
        namestr = self.calibPath + "cal_" + format(dna, 'x') + ".npy"
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
            self.calib = {}
    
    # Gets the LAB4-specific parameters for each LAB.
    def lab4_specifics(self, lab):
        return self.calib['specifics'][lab]

    def lab4_resetSpecifics(self, lab):
        self.calib['specifics'][lab] = self.generic.copy()
    
    # Updates pedestals, both locally
    # *and* in the CALRAM.
    def updatePedestals(self):
        print("Updating pedestals...")
        self.dev.labc.stop()
        self.dev.calram.zero()
        self.dev.calram.mode(self.dev.calram.CalMode.PEDESTAL)        
        self.dev.labc.start()
        # Build up 512-sample sum of pedestals. The 512 here is magic,
        # it's the amount needed for the zerocrossing
        for i in range(4*self.trigsPerRoll):
            self.dev.labc.force_trigger(block=True, numTrig=128, safe=False)
        self.dev.labc.stop()
        # peds are updated, dump them
        print("Fetching pedestals...")
        self.dev.dma.enable(True, self.dev.dma.calDmaMode)
        for i in range(self.numLabs):
            final = i==(self.numLabs-1)
            self.dev.dma.setDescriptor(i, self.dev.calram.base+4096*4*i, 4096, increment=True, final=final)

        self.dev.dma.beginDMA()
        rawped = np.frombuffer(bytearray(self.dev.dma.dmaread(4096*4*self.numLabs)),dtype=np.uint32)
        rawped = rawped/512
        self.calib['pedestals'] = rawped.reshape(24, 4096)
        print("Update complete")

    # assumes *nothing* other than the LAB4's been defaulted and testpatern mode is off
    # The initial tune finds the trim feedback and shifts all the trims to ensure
    # the slow sample is tunable
    def initialTune(self, lab, maxTries=25):
        # Start off by dead-reckoning the initial target
        self.dev.monSelect(lab)
        self.dev.labc.set_tmon(lab, self.dev.labc.tmon['SSPin'])
        # SSPin is *supposed* to be around 600 samples long in an ideal world,
        # but in reality we really need to just be around a width of less than 1000
        # for sampling to not be utter horsecrap.
        scan = 0
        if lab > 11:
            scan = 1
        width = self.dev.labc.scan_width(scan)
        curTry = 0
        print("Initial SSPin width:", width)
        while width > 1000 and curTry < maxTries:
            newAvg = 0
            for i in range(257, 383):
                newval = self.calib['specifics'][lab][i]
                self.calib['specifics'][lab][i] = newval + 25
                newAvg += newval + 25
                
            self.dev.labc.update(lab)
            time.sleep(0.1)
            width = self.dev.labc.scan_width(scan)
            print("New SSPin width (avg", newAvg/126,"):",width)
            curTry = curTry + 1
        
        if curTry == maxTries:
            print("initial tune failed!")
            return
        # Put its quad into calibration mode
        self.dev.calSelect(int(lab/4))
        self.dev.radsig.enable(False)
        self.dev.radsig.signal(pulse=False, band = 2)
        # update the pedestals
        self.updatePedestals()
        # turn on the sine wave
        self.dev.radsig.enable(True)
        self.dev.radsig.setFrequency(510.)
        # get the initial time loop
        t = self.getTimeRun(510e6, verbose=False)
        print("Initial seam/slow sample timing:", t[lab][0], t[lab][127])
        # Check the times to see if we're *so* far off that
        # our measured seam time might actually be *negative*.
        # Note that even if it isn't, just declaring that it's
        # negative is fine, the result is the same. The
        # times that come from getTimeRun *cannot* be negative.
        if np.sum(t[lab][1:128]) > 39900:
            print("Feedback LAB%d way off (%f): %d -> %d" % (lab, 40000-np.sum(t[lab][1:128]), t[lab][0], -1*t[lab][0]))
            t[lab][0] = -1*t[lab][0]
        # copied from surf_daq's tune loop. Note that our times are
        # shifted one forward, but the trims are *not*. So in our
        # case the times and the trims are the same!
        seamSample = t[lab][0]
        slowSample = t[lab][127]
        # get what the initial average is
        oldavg = 0
        for i in range(257, 383):
            oldavg += self.calib['specifics'][lab][i]
        oldavg = oldavg/126
        print("Starting average trim:", oldavg)
        curTry = 0
        while slowSample > 290 or seamSample > 350 or seamSample < 290:
            if curTry >= maxTries:
                print("initial tune failed!")
                return
            # Fix the seam if it's gone off too much.
            if seamSample < 290 or seamSample > 350:
                # Build the delta. This is totally hacked together.
                # Decrease if too fast, increase if too slow.
                # Change by 3 if it's within 50, change by 7 if it's between 50-100, 
                # change by 15 otherwise. Convergence here is slow, but we're trying to 
                # avoid bouncing, and we're also trying to avoid the negative case.
                diff = np.abs(seamSample - 312.5)
                delta = 3
                if diff > 50:
                    delta += 4
                if diff > 100:
                    delta += 8
                if seamSample < 290:
                    delta = -1*delta
                cur = self.calib['specifics'][lab][11]
                print("Feedback LAB%d (%f): %d -> %d" % (lab, seamSample, cur, cur+delta))
                self.calib['specifics'][lab][11] = cur+delta
            elif slowSample > 290:
                # We ONLY DO THIS if the seam sample's close.
                # This is because the slow sample changes with the seam timing like
                # everything else (actually a little more)
                #
                # So now, we're trying to find a *global* starting point where
                # the slow sample is *too fast*. Because slowing it down is easy!
                # So to do that, we slow everyone else down. Doing that means the
                # the DLL portion speeds up, so the slow sample speeds up as well.
                # This slows down trims 1->126 by adding 25 to them.
                # Remember trim 127 is the slow sample, and trim 0 is the multichannel clock alignment trim.
                
                # Trim updating is a pain, sigh.
                oldavg = 0
                for i in range(257, 383):
                    old = self.calib['specifics'][lab][i]
                    oldavg += old                    
                    self.calib['specifics'][lab][i] = old + 25
                oldavg = oldavg/126
                print("Slowing early samples: LAB%d (%f): %d -> %d" % (lab, slowSample, oldavg, oldavg + 25))
                oldavg = oldavg + 25
            # now update
            print("Updating...", end='', flush=True)
            self.dev.labc.update(lab)
            print("done")
            # fetch times again
            t = self.getTimeRun(510e6, verbose=False)
            print("Seam/slow sample timing now:", t[lab][0], t[lab][127])
            if np.sum(t[lab][1:128]) > 39900:
                print("Feedback LAB%d way off (%f): %d -> %d" % (lab, 40000-np.sum(t[lab][1:128]), t[lab][0], -1*t[lab][0]))
                t[lab][0] = -1*t[lab][0]
            seamSample = t[lab][0]
            slowSample = t[lab][127]
        print("Ending seam sample :", t[lab][0],"feedback",self.calib['specifics'][lab][11])
        print("Ending slow sample :", t[lab][127],"average earlier trims", oldavg)
        
        
    # Gets times from a zero-crossing run. Assumes pedestals loaded, sine wave running.
    # Each run here *should* get us around 1960 zero crossings, which means
    # the precision of each is roughly 7 picoseconds, obviously reducing in quadrature
    # with multiple runs. We probably only need to get to half that, so
    # when the stdev() gets to 10 picoseconds, the loop should then call this
    # 4 times and average them, and at 5 ps call this loop 16 times and average
    # those, and then bail at 3 ps limit.
    #
    # Need to time this loop to figure out how long it takes. I don't think it's that
    # long (update: it takes like, 5 seconds, and this is overkill, since we transfer
    # ALL of the LAB4s, and we only need 1/3 of them). Working on it!!!
    def getTimeRun(self, frequency, verbose=True):
        if verbose:
            print("Calculating times...", end='', flush=True)
        self.dev.labc.stop()
        self.dev.calram.zero(zerocrossOnly=True)
        self.dev.calram.mode(self.dev.calram.CalMode.NONE)
        self.dev.labc.start()
        # junk the first 4
        self.dev.labc.force_trigger(block=True, numTrig=self.trigsPerRoll, safe=False)
        # swap the CalMode to zerocrossing
        self.dev.calram.mode(self.dev.calram.CalMode.ZEROCROSSING)
        # Run to 384 samples, I dunno what happens at 512 yet, screw it.
        for i in range(3*self.trigsPerRoll):
            self.dev.labc.force_trigger(block=True, numTrig=128, safe=False)
        if verbose:
            print("done.")
        self.dev.labc.stop()
            
        # This should check to make sure it's actually 384, which it *should* be.
        # We're doing things in groups of 384 because it can't trip the ZC overflow
        # limit.
        numRolls = self.dev.calram.numRolls()        
        if verbose:
            print("Fetching times for", numRolls, "successful rolls...", end='', flush=True)
        self.dev.dma.enable(True, self.dev.dma.calDmaMode)
        for i in range(self.numLabs):
            final = i==(self.numLabs-1)
            self.dev.dma.setDescriptor(i, self.dev.calram.base+4096*4*i, 4096, increment=True, final=final)
        
        self.dev.dma.beginDMA()
        # Data comes in as 4096*4*numLabs bytes in little-endian format.
        # Convert it to 4096*numLabs uint32's.
        rawtime = np.frombuffer(bytearray(self.dev.dma.dmaread(4096*4*self.numLabs)), dtype=np.uint32)
        if verbose:
            print("done.")
        # Now view it as an array of [numLabs][4096]
        timeByLab = rawtime.reshape(self.numLabs, 4096)
        # Building up the times is a little harder than the pedestals.
        # The first thing we do is zero out the invalid seams. That way when we add everything,
        # all we need to do is rescale the seam by 8/3s. 
        # The invalid seams are 0 and every (sample % 256) = 128 for *every trigger*.
        # So if we have 4 triggers in a roll of 4096, the invalid seams are 0, 128, 384, 640, 896.
        # and we only have 3/8 valid.
        
        # NOTE: I could almost certainly do this by reshaping/transposing magic crap. Screw it for now.
        for i in range(self.numLabs):
            # What we do depends on the record length. If we have 4 trigs per roll, it's
            # 8 windows per record. If it's 2 trigs per roll, we have 16 windows per record.
            samplesPerRecord = int(4096/self.trigsPerRoll)
            for j in range(self.trigsPerRoll):
                # The first one is always invalid because we don't have the last when it arrives.                
                timeByLab[i][samplesPerRecord*j] = 0
                windowsPerRecord = samplesPerRecord/128
                # Now every (sample % 256) == 128 is invalid because we buffer them in case the
                # next seam is invalid due to being the end of the record.
                for k in range(int(windowsPerRecord/2)):
                    timeByLab[i][samplesPerRecord*j+256*k+128] = 0

        # We now reshape our times by window. 128 samples per window, 32 windows per roll.
        # So we're now an array of [numLabs][32][128].
        timeByWindow = timeByLab.reshape(self.numLabs, 32, 128)

        # Sum along the window axis, because the samples within a window have the same time.
        # We're now shape (24, 128)
        timeByWindow = timeByWindow.sum(axis=1)
        
        # convert to time. The denominator is number of windows in a roll, numerator is number of picoseconds/cycle.
        convFactor = (1e12/frequency)/(numRolls*32)
        # This has to be A = A*B because we're actually creating a new array
        # since we're moving to floats.
        timeByWindow = timeByWindow*convFactor
        
        # Now rescale the seams, because the seams have lower statistics.
        # This is the number of windows in a record (eg if 4 trigs = 8)
        windowsPerRecord = 4096/(self.trigsPerRoll*128)
        # This is the number of *valid* windows per record (e.g. if 4 trigs = 3)
        validWindowsPerRecord = (windowsPerRecord/2 - 1)
        rescale = (validWindowsPerRecord*self.trigsPerRoll)/32
        # Transposing gets us shape (128, 24), and we can
        # rescale all of the LABs automatically. This is just a loop over all LABs
        # rescaling time 0. So if we had 4 trigs per roll, that means only 12/32 of
        # the zerocrossings were nonzero, so we divide by 12/32 (or multiply by 32/12).
        timeByWindow.transpose()[0] /= rescale
        # and we're done
        return timeByWindow
