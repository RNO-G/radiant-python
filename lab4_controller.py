from bf import bf
import picoblaze
import pickle
from os import path
import time

# Parameterized LAB4 controller (hopefully...)
class LAB4_Controller:
 
        map = { 'CONTROL'			: 0x00000,
                'SHIFTPRESCALE'		        : 0x00004,
		'RDOUTPRESCALE'		        : 0x00008,
		'WILKDELAY'			: 0x0000C,
		'WILKMAX'			: 0x00010,
		'TPCTRL'			: 0x00014,
		'L4REG'				: 0x00018,
                'PHASECMD'                      : 0x00020,
                'PHASEARG'                      : 0x00024,
                'PHASERES'                      : 0x00028,
                'PHASEZERO'                     : 0x0002C,
                'PHASEPB'                       : 0x0003C,
		'TRIGGER'			: 0x00054,
                'READOUT'                       : 0x00058,
                'READOUTEMPTY'                  : 0x0005C,
                'pb'				: 0x0007C,
                }
                
        # default (SURF) config. Override these as needed.
        # montimingSelectFn doesn't actually need to return anything, it's done here so I don't need to check if it's not None
        defconfig = { 'numLabs'    : 12,           # number of LAB4s
                      'labAll'     : 15,           # magic # to use for selecting all LABs
                      'syncOffset' : 0,            # how far to go back in automatch PHAB
                      'invertSync' : False,
                      'labMontimingMapFn' : lambda lab: lab,  # function to use for converting LAB# to MONTIMING#
                      'montimingSelectFn' : lambda lab: lab,  # function to call for selecting MONTIMING for LAB
                      'regclrAll'         : 0xFFF  # value to write to REGCLR to clear all LABs
                      }
                      
        amon = { 'Vbs'                      : 0,
                 'Vbias'                    : 1,
                 'Vbias2'                   : 2,
                 'CMPbias'                  : 3,
                 'VadjP'                    : 4,
                 'Qbias'                    : 5,
                 'ISEL'                     : 6,
                 'VtrimT'                   : 7,
                 'VadjN'                    : 8,
                 }
        tmon = {'A1'                        : 0,
                'B1'                        : 1,
                'A2'                        : 2,
                'B2'                        : 3,
                'SSPout'                    : 68,
                'SSTout'                    : 100,
                'PHASE'                     : 4,
                'PHAB'                      : 5,
                'SSPin'                     : 6,
                'WR_STRB'                   : 7,
                }

        # the kwargs list was long: see above for the list of all config options.
        def __init__(self, dev, base, calibrations, **kwargs):
            self.defaults = None
            
            #numLabs=12, labAll=15, syncOffset=0, labMontimingMapFn=None, regclrAll=0xFFF):
            self.dev = dev
            self.base = base
            self.calibrations = calibrations
            # defaulty-defaulty
            for item in self.defconfig:
                if not item in kwargs:
                    kwargs[item] = self.defconfig[item]
            # now all of these will complete
            self.numLabs = kwargs['numLabs']
            self.labAll = kwargs['labAll']
            self.syncOffset = kwargs['syncOffset']
            self.invertSync = kwargs['invertSync']
            self.labMontimingMapFn = kwargs['labMontimingMapFn']
            self.montimingSelectFn = kwargs['montimingSelectFn']
            self.regclrAll = kwargs['regclrAll']
                
            self.pb = picoblaze.PicoBlaze(self, self.map['pb'])
            self.phasepb = picoblaze.PicoBlaze(self,self.map['PHASEPB'])

        # We use python properties for anything that can be both
        # written and read back. So that's like, internal stuff to
        # the LAB controller, not anything in the LAB4D (no readback).
        @property
        def shiftprescale(self):
            return self.read(self.map['SHIFTPRESCALE'])
        
        @shiftprescale.setter
        def shiftprescale(self, scale):
            self.write(self.map['SHIFTPRESCALE'], scale)
        
        @property
        def rdoutprescale(self):
            return self.read(self.map['RDOUTPRESCALE'])
        
        @rdoutprescale.setter
        def rdoutprescale(self, scale):
            self.write(self.map['RDOUTPRESCALE'], scale)

        @property
        def readoutempty(self):
            return self.read(self.map['READOUTEMPTY'])
        
        @readoutempty.setter
        def readoutempty(self, threshold):
            self.write(self.map['READOUTEMPTY'], threshold)

        def load_defaults(self, fn="lab4defaults_3G2.p"):
            if not path.isfile(fn):
                print("Cannot open file ", fn)
            self.defaults = pickle.load(open(fn, "rb"))
            
        # We do match=1 here because we find the first WR_STRB edge
        # after SYNC's rising edge, which means it's latching the WR
        # when SYNC=1. syncOffset allows for compensating a
        # SYNC (internal) <-> MONTIMING (external) mismatch.
        # invertSync allows for dealing with WR mismatches caused
        # by shift delays (for instance, shoving WR forward 2 sysclks
        # to compensate for an external delay)
        def automatch_phab(self, lab, match=1):
            labs = []
            if lab == self.labAll:
                labs = range(self.numLabs)
            else:
                labs = [lab]
            # Find our start point. SYNC is always scan #12
            sync_edge = self.scan_edge(12, 1)
            if sync_edge == 0xFFFF:
                # this will never happen
                print("No sync edge found??")
                return False
            
            print("Found sync edge: %d" % sync_edge)
            err = False
            for i in labs:
                self.montimingSelectFn(i)
                scanNum = self.labMontimingMapFn(i)
                # Check to see if we're working *at all*!
                # The issue here is that if we're starting up
                # and the DLL isn't running, then the trims
                # can start up in a state where SST doesn't
                # make it through the delay line,
                # because the falling edge is faster.
                # Solution there is to lower SSP a bit,
                # which allows it to propagate and the
                # DLL to begin properly seeing edges.
                #
                # Might fix this in the default function
                # as well by starting with DLL, then
                # if nothing is working, switch on VadjN's
                # buffer and let it run the delay line
                # which should force the DLL to a known
                # spot too.
                
                self.set_tmon(lab, self.tmon['SSTout'])
                width = self.scan_width(scanNum)
                if width < 200 or width > 4000:
                    # not working
                    print("Delay line not working (width", width, "), trying to kick")
                    self.l4reg(lab, 8, 2500)
                    time.sleep(0.1)
                    width = self.scan_width(scanNum)
                    print("Width now", width)
                    if width < 200 or width > 4000:
                        print("still not working, bailing")
                        err = True
                        continue
                    self.l4reg(lab, 8, 2700)
                
                
                # Find our PHAB sampling point.
                self.set_tmon(lab, self.tmon['WR_STRB'])
                wr_edge = self.scan_edge(scanNum, 1, sync_edge)
                if wr_edge == 0xFFFF:
                    print("No WR_STRB edge found for LAB%d, skipping!" % i)
                    err = True
                    continue
                # if WR_STRB edge finding worked, PHAB should too
                print("Found WR_STRB edge on LAB%d: %d" % (i, wr_edge))
                wr_edge = wr_edge - self.syncOffset
                if wr_edge < 0:
                    wr_edge = wr_edge + 56*80
                print("Adjusted WR_STRB edge on LAB%d: %d" % (i, wr_edge))
                self.set_tmon(lab, self.tmon['PHAB'])
                phab = self.scan_value(scanNum, wr_edge) & 0x01
                if self.invertSync:
                    phab = phab ^ 0x01
                    
                while phab != match:
                    print("LAB%d wrong PHAB phase, resetting." % i)
                    self.clr_phase(i)
                    phab = self.scan_value(scanNum, wr_edge) & 0x01
                    if self.invertSync:
                        phab = phab ^ 0x01
            return err

        def autotune_vadjp(self, lab, initial=2700):
                self.set_tmon(lab, self.tmon['SSPin'])
                self.montimingSelectFn(lab)
                scanNum = self.labMontimingMapFn(lab)
                
                rising=self.scan_edge(scanNum, 1, 0)
                if rising == 0xFFFF:
                    print("No rising edge on VadjP: looks stuck")
                    return
                falling=self.scan_edge(scanNum, 0, rising+100)
                if falling == 0xFFFF:
                    print("No falling edge on VadjP: looks stuck")
                    return
                
                width=falling-rising
                if width < 0:
                        print("Width less than 0, do something.")
                        return
                width = int(width*1.05)
                print("SSPout target: ", width)
                vadjp=initial
                delta=20
                self.l4reg(lab, 8, vadjp)
                self.set_tmon(lab, self.tmon['SSPout'])
                rising=self.scan_edge(scanNum, 1, 0)
                falling=self.scan_edge(scanNum, 0, rising+100)
                trial=falling-rising
                if trial < 0:
                        print("Trial width less than 0, do something.")
                        return
                oldtrial=trial
                while abs(trial-width) > 2:
                        if trial < width:
                                if oldtrial > width:
                                        delta=delta/2
                                        if delta < 1:
                                                delta = 1
                                vadjp += delta
                        else:
                                if oldtrial < width:
                                        delta=delta/2
                                        if delta < 1:
                                                delta = 1
                                vadjp -= delta
                        vadjp = int(vadjp)
                        oldtrial = trial
                        self.l4reg(lab, 8, vadjp)
                        rising=self.scan_edge(scanNum, 1, 0)
                        falling=self.scan_edge(scanNum, 0, rising+100)
                        trial=falling-rising
                        print("Trial: vadjp %d width %f target %f" % ( vadjp, trial, width))
                return vadjp
                
        def autotune_vadjn(self, lab):
            self.set_tmon(lab, self.tmon['A1'])
            self.montimingSelectFn(lab)
            scanNum = self.labMontimingMapFn(lab)

            vadjn = 1640
            delta = 20            
            self.l4reg(lab, 3, vadjn)            
            width = self.scan_width(scanNum, 64)
            if width == 0 or width > 4400:
                print("VadjN looks stuck")
                return 0
            oldwidth = width
            print("Trial: vadjn %d width %f" % ( vadjn, width))
            while abs(width-840) > 0.5:
                if (width < 840):
                    if (oldwidth > 840):
                        delta = delta/2
                        if delta < 1:
                            delta = 1
                    vadjn -= delta
                else:
                    if (oldwidth < 840):
                        delta = delta/2
                        if delta < 1:
                            delta = 1
                    vadjn += delta
                oldwidth = width
                self.l4reg(lab, 3, vadjn)
                width = self.scan_width(scanNum, 64)
                print("Trial: vadjn %d width %f" % ( vadjn, width))
            return vadjn            
                
        ''' switch the phase scanner to free-scan (ChipScope view) mode '''
        def scan_free(self):
            self.write(self.map['PHASECMD'], 0x01)

        ''' dump timing parameters '''
        def scan_dump(self, lab):
            self.montimingSelectFn(lab)
            scanNum = self.labMontimingMapFn(lab)            
            for strb in ['A1', 'A2', 'B1', 'B2']:
                self.set_tmon(lab, self.tmon[strb])
                param = self.scan_pulse_param(scanNum, 0)
                # this should be 4480 - the total length of the phase scanner
                # but we give it some margin
                if param[0] == 0 or param[0] > 4470.0:
                    print(strb, ": not present")
                else:
                    print(strb, ": width ", param[0], "from", param[1], "-",param[2])
            for strb in ['SSPin', 'SSPout']:
                self.set_tmon(lab, self.tmon[strb])
                # get the first pulse
                p1 = self.scan_pulse_param(scanNum, 0)
                if p1[0] == 0 or p1[0] > 4470.0:
                    print(strb, ": not present")
                    continue
                # get the second pulse, after the end of the first
                p2 = self.scan_pulse_param(scanNum, p1[2])
                print(strb, ": width ", p1[0], "from", p1[1],"-",p1[2], "and", p2[1], "-", p2[2])
                
        def scan_pulse_param(self, scan, start):
            param = []
            width = self.scan_width(scan)
            param.append(width)
            re = self.scan_edge(scan, 1, start)
            param.append(re)
            newStart = start + re
            fe = self.scan_edge(scan, 0, (start+re) % 4480)
            param.append(fe)
            return param
            
        ''' scan the full width of a signal (how many 1s are in a 2-clock period) '''
        def scan_width(self, scanNum, trials=1):
            self.write(self.map['PHASEARG'], scanNum)
            res = 0
            for i in range(trials):
                self.write(self.map['PHASECMD'], 0x02)
                val = self.read(self.map['PHASECMD'])
                while val != 0x00:
                    val = self.read(self.map['PHASECMD'])
                res += self.read(self.map['PHASERES'])                
            return res/(trials*1.0)

        ''' get the value of a signal at a specific phase step '''
        def scan_value(self,scanNum,position):
            if position > 4479:
                print("Position must be 0-4479.")
                return None
            val = bf(0)                
            val[15:0] = position
            val[19:16] = scanNum
            self.write(self.map['PHASEARG'], int(val))
            self.write(self.map['PHASECMD'], 0x03)
            res = self.read(self.map['PHASECMD'])
            while res != 0x00:
                res = self.read(self.map['PHASECMD'])
            return self.read(self.map['PHASERES'])
        
        ''' locate the edge of a signal. 65535 means "no edge found" '''
        def scan_edge(self,scanNum, pos=0, start=0):
            val = bf(0)
            val[15:0] = start
            val[24] = pos
            val[19:16] = scanNum
            self.write(self.map['PHASEARG'], int(val))
            self.write(self.map['PHASECMD'], 0x04)
            ret=self.read(self.map['PHASECMD'])
            while ret != 0x00:
                ret = self.read(self.map['PHASECMD'])
            return self.read(self.map['PHASERES'])

        def ssp_width(self, lab):
            self.montimingSelectFn(lab)
            scanNum = self.labMontimingMapFn(lab)
            self.set_tmon(lab, self.tmon['SSPin'])            
            width = self.scan_width(scanNum)
            return width
        
        def set_amon(self, lab, value):
            self.l4reg(lab, 12, value)

        def set_tmon(self, lab, value):
            self.l4reg(lab, 396, value)
            
        def clr_phase(self, lab):
            self.l4reg(lab, 396, self.tmon['PHAB']+128)
            self.l4reg(lab, 396, self.tmon['PHAB'])

        def start(self):
            ctrl = bf(self.read(self.map['CONTROL']))
            while not ctrl[2]:
                ctrl[1] = 1
                self.write(self.map['CONTROL'], int(ctrl))
                ctrl = bf(self.read(self.map['CONTROL']))
                
        def stop(self):
            ctrl = bf(self.read(self.map['CONTROL']))
            while ctrl[2]:
                ctrl[1] = 0
                self.write(self.map['CONTROL'], int(ctrl))
                ctrl = bf(self.read(self.map['CONTROL']))
        
        ''' set trigger repeat level. This is an immensely crude way
            of adjusting the readout length: you can change it in units of 1024 samples
            complain to me later :) '''
        def set_trigger_repeat(self, repeat=0):
            if repeat > 2:
                print("Trigger can only repeat up to 2 times")
                return
            ctrl = bf(self.read(self.map['CONTROL']))
            if ctrl[1]:
                print("cannot change trigger repeat: LAB4 in run mode")
                return
            # Set trigger repeat. To do that, we have
            # to set bit 31 (to indicate we're updating the repeat)
            # and set repeat in bits [25:24].
            trig = (1<<31) | (repeat<<24)
            print("setting trigger register:", hex(trig))
            self.write(self.map['TRIGGER'], trig)
            return                
                
        '''
        send software trigger. block=True means wait until readout complete. numTrig sends that many triggers (up to 256).
        safe allows disabling the run mode check if you already know it is running
        '''
        def force_trigger(self, block=False, numTrig=1, safe=True):
            if block is True and safe is True:
                ctrl = bf(self.read(self.map['CONTROL']))
                if not ctrl[1]:
                    print("Can't trigger, LAB4 not in run mode")
            if numTrig > 256:
                print("limiting to 256 triggers")
                numTrig = 256
            numTrig = numTrig - 1
            self.write(self.map['TRIGGER'], 2 | (numTrig << 8))
            if block is True:
                busy = 1
                while busy != 0:
                    # check readout busy and force trigger sequence
                    busy = self.read(self.map['READOUT']) & 0x21
        '''
        clear all registers on LAB.
        '''
        def reg_clr(self):
            ctrl = bf(self.read(self.map['CONTROL']))
            if ctrl[1]:
                print("cannot issue REG_CLR: LAB4 in run mode")
                return 1
            else:
                self.write(0, 0xFFF0000)
                self.write(0, 0)
                return 0
        '''
        reset FIFO on FPGA, which holds LAB4 data
        '''
        def reset_fifo(self, force=False, reset_readout=True):
            ctrl = bf(self.read(self.map['CONTROL']))
            if ctrl[1] and not force:
                print("cannot reset FIFO: LAB4 in run mode")
                return 1
            else:
                if reset_readout:
                        self.run_mode(0)
                rdout = bf(self.read(self.map['READOUT']))
                rdout[1] = 1
                rdout[2] = reset_readout
                self.write(self.map['READOUT'], rdout) 
                return 0
        '''
        reset Wilkinson ramp controller
        '''
        def reset_ramp(self):
                ctrl = bf(self.read(self.map['CONTROL']))
                ctrl[8] = 1
                self.write(self.map['CONTROL'], ctrl)
        
        '''
        enables LAB run mode (sample+digitize+readout)
        '''    
        def run_mode(self, enable=True):
            ctrl = bf(self.read(self.map['CONTROL']))
            if enable:
                ctrl[1] = 1
                self.write(self.map['CONTROL'], ctrl)
            else:
                ctrl[1] = 0
                self.write(self.map['CONTROL'], ctrl)
        '''
        enable serial test-pattern data on output
        '''
        def testpattern_mode(self, enable=True):     #when enabled, SELany bit is 0
            rdout = bf(self.read(self.map['READOUT']))
            if enable:
                rdout[4] = 0 
                self.write(self.map['READOUT'], rdout)
            else:
                rdout[4] = 1
                self.write(self.map['READOUT'], rdout)

        def testpattern(self, lab4, pattern=0xBA6):
            self.l4reg(lab4, 13, pattern)
            return [lab4, pattern]

        '''
        Enable test-pattern data into readout RAM (prints out counter)
        '''
        def readout_testpattern_mode(self, enable=True):
            ctrl = bf(self.read(self.map['CONTROL']))
            if enable:
                ctrl[15] = 1
            else:
                ctrl[15] = 0
            self.write(self.map['CONTROL'], ctrl)
    
        def read(self, addr):
            return self.dev.read(addr + self.base)
    
        def write(self, addr, value):
            self.dev.write(addr + self.base, int(value))

        def check_fifo(self, check_fifos=False):
            rdout = bf(self.read(self.map['READOUT']))
            '''
            check_mode = 0, check if data available on any fifo (not empty)
            check_mode = 1, check individual readout fifo empties, return 12 bits
            '''
            if check_fifos:
                return rdout[27:16]    
            else:
                return rdout[3]

        def dll(self, lab4, mode=False, sstoutfb=104):
            '''enable/disable dll by setting VanN level'''
            if mode:
                self.run_mode(0)
                self.l4reg(lab4, 386, int(sstoutfb)) #set sstoutfb (should already be set)
                '''turn off internal Vadjn buffer bias'''
                self.l4reg(lab4, 2, 0)      #PCLK-1=2 : VanN
                
                calFbs = None
                if calFbs == None:
                    print("Using default Vtrimfb of 1300.")
                    self.l4reg(lab4, 11, 1300)
                else:
                    print("Using cal file for Vtrimfb's")
                    if lab4 == self.labAll:
                        for i in range(self.numLabs):
                            self.l4reg(i,11,calFbs[i])
                        else:
                            self.l4reg(lab4, 11, calFbs[lab4])                             
            else:
                '''turn on internal Vadjn buffer bias'''
                self.l4reg(lab4, 2, 1024)
                
        def l4reg(self, lab, addr, value, verbose=False):
            ctrl = bf(self.read(self.map['CONTROL']))
            if ctrl[1]:  #should be checking ctrl[2], which indicates run-mode. but not working 6/9
                print("LAB4_Controller is running, cannot update registers.") 
                return
            user = bf(self.read(self.map['L4REG']))
            if user[31]:
                print("LAB4_Controller is still processing a register?")
                return
            user[11:0] = value
            user[23:12] = addr
            user[28:24] = lab
            user[31] = 1
            if verbose:
                print("Going to write 0x%X" % int(user)) 
            self.write(self.map['L4REG'], int(user))
            while not user[31]:
                user = bf(self.read(self.map['L4REG']))

        ''' Just return the value to be written into L4REG rather than doing something '''
        def l4regval(self,lab,addr,value):
           user = bf(0)
           user[11:0] = value
           user[23:12] = addr
           user[28:24] = lab
           user[31] = 1
           return int(user)

        ''' update the *specifics* for a given lab4 '''
        def update(self, lab4):
            spec = self.calibrations.lab4_specifics(lab4)
            for item in spec.items():
                self.l4reg(lab4, item[0], item[1])
                
        ''' fully initialize a LAB4 '''
        def default(self, lab4=None, initial=True):
            if lab4 is None:
                lab4 = self.labAll
            
            # There are two sets of defauts: there's the universal LAB4 defaults,
            # which are basically only sampling-rate dependent, and then there's
            # the per-LAB guys.
            #
            # The universal ones are just grabbed by the LAB4 controller,
            # and then we grab the per-LAB ones from RadCalib, which, if they
            # haven't been loaded yet, tries the defaults.
                
            # Try to load the global defaults if we haven't already.
            if self.defaults is None:
                self.load_defaults()
            
            # and use defaults. These can be globally loaded if desired.
            print("Loading global defaults...", end='', flush=True)
            for item in self.defaults.items():
                self.l4reg(lab4, item[0], item[1])
            print("done.")            
            
            # The specs, however, have to be loaded 1 by 1.
            larr = []
            if lab4 == self.labAll:                
                for i in range(self.numLabs):
                    larr.append(i)
            else:
                larr.append(lab4)
            
            for li in larr:
                print("Loading specifics for LAB%d..." % li, end='', flush=True)
                self.update(li)
                print("done.")
                if initial:
                    # "initial" implies this was a startup.
                    # So we need to drive VadjN to a reasonable value and let the DLL
                    # take over from there.
                    print("Kickstarting LAB%d..." % li, end='', flush=True)
                    self.l4reg(lab4, 2, 1024)
                    time.sleep(0.5)
                    self.l4reg(lab4, 2, 0)
                    print("done.")
                
