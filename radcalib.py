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
            print("File", namestr, "not found: using defaults")
            self.resetCalib()
    
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
        print("Update complete")

    # assumes *nothing* other than the LAB4's been defaulted and testpatern mode is off
    # The initial tune finds the trim feedback and shifts all the trims to ensure
    # the slow sample is tunable
    def initialTune(self, quad, maxTries=50):
        # Got to make sure that the labs selected are in the right quads
        # quad 0 and 3
        # quad 1 and 4
        # quad 2 and 5
        # then the labs in each are
        # quad 0 and 3: lab 0,1,2,3 and 12, 13, 14, 15
        
        if(quad > 2):
            quad -= 3

        labs = [int(4 * quad + i) for i in range(4)] + [int(4 * quad + i + 12) for i in range(4)]

        return_matrix = [True if i in labs else False for i in range(24)]
        
        # Start off by dead-reckoning the initial target
        # SSPin is *supposed* to be around 600 samples long in an ideal world,
        # but in reality we really need to just be around a width of less than 1000
        # for sampling to not be utter horsecrap.
        #
        # So hilariously, most of this is just noise (randomly showing up above 1000)
        # but the process of *forcing* it below 1000 (by raising the constants)
        # tends to make the later convergence process Really Fast.
        #
        # ... thus implying I really should be using *this* as my "starting point"
        # scan.

        for lab in labs:
            self.dev.monSelect(lab)
            self.dev.labc.set_tmon(lab, self.dev.labc.tmon['SSPin'])

            scan = 0
            if lab > 11:
                scan = 1
            width = self.dev.labc.scan_width(scan)
            curTry = 0
            print("Lab %i) Initial SSPin width:" % lab, width)
            while width > 1000 and curTry < maxTries:
                newAvg = 0
                for i in range(257, 383):
                    newval = self.calib['specifics'][lab][i]
                    self.calib['specifics'][lab][i] = newval + 25
                    newAvg += newval + 25
                
                self.dev.labc.update(lab)
                time.sleep(0.1)
                width = self.dev.labc.scan_width(scan)
                print("Lab %i) New SSPin width (avg" % lab, newAvg/126,"):",width)
                curTry = curTry + 1
        
            if curTry == maxTries:
                print("Lab %i) initial tune failed!" % lab)
                return_matrix[lab] = False
        
        # Put its quad into calibration mode
        self.dev.calSelect(quad)
        self.dev.radsig.enable(False)
        self.dev.radsig.signal(pulse=False, band = 2)
        self.updatePedestals() # update the pedestals
        self.dev.radsig.enable(True) # turn on the sine wave
        self.dev.radsig.setFrequency(510.)

        t = self.getTimeRun(510e6, verbose=False) # get the initial time loop

        seamSamples = [0 for i in range(24)]
        slowSamples = [0 for i in range(24)]
        oldavgs = [0 for i in range(24)]        
        
        for lab in labs:
            # Dont try to tune it if it failed in the first half of the function call
            if not(return_matrix[lab]):
                continue
            
            print("lab %i) Initial seam/slow sample timing:" % lab, t[lab][0], t[lab][127])
            # Check the times to see if we're *so* far off that
            # our measured seam time might actually be *negative*.
            # Note that even if it isn't, just declaring that it's
            # negative is fine, the result is the same. The
            # times that come from getTimeRun *cannot* be negative.
            if np.sum(t[lab][1:128]) > 39900:
                print("Lab %i) Feedback LAB%d way off (%f): %d -> %d" % (lab, lab, 40000-np.sum(t[lab][1:128]), t[lab][0], -1*t[lab][0]))
                t[lab][0] = -1*t[lab][0]
            # copied from surf_daq's tune loop. Note that our times are
            # shifted one forward, but the trims are *not*. So in our
            # case the times and the trims are the same!
            seamSamples[lab] = t[lab][0]
            slowSamples[lab] = t[lab][127]
            # get what the initial average is
            oldavgs[lab] = 0
            for i in range(257, 383):
                oldavgs[lab] += self.calib['specifics'][lab][i]
            oldavgs[lab] = oldavgs[lab]/126
            print("Lab %i) Starting average trim:" % lab, oldavgs[lab])

        curTrys = [0 for i in range(24)]
        
        while(np.any(np.array(slowSamples)[return_matrix] > 290) or
              np.any(np.array(seamSamples)[return_matrix] > 350) or
              np.any(np.array(seamSamples)[return_matrix] < 290)):

            print("Top of loop. The NTries are: ", end = '')
            for lab in labs:
                print("Lab %i) %i \t " % (lab, curTrys[lab]), end = '')
            print("")
            
            for lab in labs:
                # Dont try to tune it if it failed in the first half of the function call
                if not(return_matrix[lab]):
                    continue
                
                if slowSamples[lab] > 290 or seamSamples[lab] > 350 or seamSamples[lab] < 290:
                    if curTrys[lab] >= maxTries:
                        print("Lab %i) initial tune failed!" % lab)
                        return_matrix[lab] = False
                        continue
                    
                    # Fix the seam if it's gone off too much.
                    if seamSamples[lab] < 290 or seamSamples[lab] > 350:
                        # Build the delta. This is totally hacked together.
                        # Decrease if too fast, increase if too slow.
                        # Change by 3 if it's within 50, change by 7 if it's between 50-100, 
                        # change by 15 otherwise. Convergence here is slow, but we're trying to 
                        # avoid bouncing, and we're also trying to avoid the negative case.
                        diff = np.abs(seamSamples[lab] - 312.5)
                        delta = 3
                        if diff > 50:
                            delta += 4
                        if diff > 100:
                            delta += 8
                        if seamSamples[lab] < 290:
                            delta = -1*delta
                        cur = self.calib['specifics'][lab][11]
                        print("Lab %i) Feedback LAB%d (%f): %d -> %d" % (lab, lab, seamSamples[lab], cur, cur+delta))
                        self.calib['specifics'][lab][11] = cur+delta
                    elif slowSamples[lab] > 290:
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
                        oldavgs[lab] = 0
                        for i in range(257, 383):
                            old = self.calib['specifics'][lab][i]
                            oldavgs[lab] += old                    
                            self.calib['specifics'][lab][i] = old + 25
                        oldavgs[lab] = oldavgs[lab]/126
                        print("Lab %i) Slowing early samples: LAB%d (%f): %d -> %d" % (lab, lab, slowSamples[lab], oldavgs[lab], oldavgs[lab] + 25))
                        oldavgs[lab] = oldavgs[lab] + 25
                    # now update
                    print("Lab %i) Updating..." % lab)
                    self.dev.labc.update(lab)

            print("Done with all labs in loop.")

            # fetch times again
            t = self.getTimeRun(510e6, verbose=False)
            for lab in labs:
                # Dont try to tune it if it failed in the first half of the function call
                if not(return_matrix[lab]):
                    continue

                print("Lab %i) Seam/slow sample timing now:" % lab, t[lab][0], t[lab][127])
                if np.sum(t[lab][1:128]) > 39900:
                    print("Lab %i) Feedback LAB%d way off (%f): %d -> %d" % (lab, lab, 40000-np.sum(t[lab][1:128]), t[lab][0], -1*t[lab][0]))
                    t[lab][0] = -1*t[lab][0]
                seamSamples[lab] = t[lab][0]
                slowSamples[lab] = t[lab][127]
                curTrys[lab] = curTrys[lab] + 1

        for lab in labs:
            print("Lab %i) Ending seam sample :" % lab, t[lab][0],"feedback",self.calib['specifics'][lab][11])
            print("Lab %i) Ending slow sample :" % lab, t[lab][127],"average earlier trims", oldavgs[lab])

        # make a quick dictionary out of the return matrix to make it easier to parse 
        return_matrix_ = {}
        for lab in labs:
            return_matrix_[lab] = return_matrix[lab]
        return return_matrix_
        
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
