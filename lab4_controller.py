from bf import bf
import picoblaze

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
                
        def __init__(self, dev, base, calibrations, numLabs=12, labAll=15, syncOffset=0, labMontimingMapFn=None):
            self.dev = dev
            self.base = base
            self.calibrations = calibrations
            self.numLabs = numLabs
            self.labAll = labAll
            self.pb = picoblaze.PicoBlaze(self, self.map['pb'])
            self.phasepb = picoblaze.PicoBlaze(self,self.map['PHASEPB'])

            # The phase shift clock is equal to the phase clock (half the sysclk)
            # so 80 ns. VCO is 40x sysclk, or 1 GHz, and there are 56 taps/VCO
            # clock (so 56 taps/ns). So we need to move back 560 taps for the
            # RADIANT (where the MONTIMING is 10 ns delayed due to CPLD).
            self.syncOffset = syncOffset
            
            # this is a map of LAB->MONTIMING. On the SURF5 we don't need this.
            # On the RADIANT it's just a modulo. The phase scanner only supports
            # up to 12 inputs.
            self.labMontimingMapFn = labMontimingMapFn
            
        def automatch_phab(self, lab, match=1):
            labs = []
            if lab == self.labAll:
                labs = range(self.numLabs)
            else:
                labs = [lab]
            # Find our start point. SYNC is always scan #12
            sync_edge = self.scan_edge(12, 1)
            print("Found sync edge: %d" % sync_edge)
            for i in labs:
                # If we need to map ourselves, do it now.
                if not self.labMontimingMapFn:
                    scanNum = i
                else:
                    scanNum = self.labMontimingMapFn(i)
                # Find our PHAB sampling point.
                self.set_tmon(scanNum, self.tmon['WR_STRB'])
                wr_edge = self.scan_edge(scanNum, 1, sync_edge)
                print("Found WR_STRB edge on LAB%d: %d" % (i, wr_edge))
                wr_edge = wr_edge - syncOffset
                if wr_edge < 0:
                    wr_edge = wr_edge + 56*80
                print("Adjusted WR_STRB edge on LAB%d: %d" % (i, wr_edge))
                self.set_tmon(scanNum, self.tmon['PHAB'])
                phab = self.scan_value(scanNum, wr_edge) & 0x01
                while phab != match:
                    print("LAB%d wrong PHAB phase, resetting." % i)
                    self.clr_phase(i)
                    phab = self.scan_value(scanNum, wr_edge) & 0x01

        def autotune_vadjp(self, lab, initial=2700):
                self.set_tmon(lab, self.tmon['SSPin'])
                if not self.labMontimingMapFn:
                    scanNum = i
                else:
                    scanNum = self.labMontimingMapFn(i)
                rising=self.scan_edge(scanNum, 1, 0)
                falling=self.scan_edge(scanNum, 0, rising+100)
                width=falling-rising
                if width < 0:
                        print("Width less than 0, do something.")
                        return
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
                        oldtrial = trial
                        self.l4reg(lab, 8, vadjp)
                        rising=self.scan_edge(scanNum, 1, 0)
                        falling=self.scan_edge(scanNum, 0, rising+100)
                        trial=falling-rising
                        print("Trial: vadjp %d width %f target %f" % ( vadjp, trial, width))
                return vadjp
                
        def autotune_vadjn(self, lab):
            self.set_tmon(lab, self.tmon['A1'])
            if not self.labMontimingMapFn:
                scanNum = i
            else:
                scanNum = self.labMontimingMapFn(i)
            vadjn = 1640
            delta = 20            
            self.l4reg(lab, 3, vadjn)            
            width = self.scan_width(scanNum, 64)
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
                
        def scan_free(self):
            self.write(self.map['PHASECMD'], 0x01)
            
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
        '''
        send software trigger
        '''
        def force_trigger(self):
            self.write(self.map['TRIGGER'], 2)
        '''
        clear all registers on LAB
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
            self.dev.write(addr + self.base, value)

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

        def set_fifo_empty(self, threshold):
            self.write(self.map['READOUTEMPTY'], threshold)
                
        def dll(self, lab4, mode=False, sstoutfb=104):
            '''enable/disable dll by setting VanN level'''
            if mode:
                self.run_mode(0)
                self.l4reg(lab4, 386, int(sstoutfb)) #set sstoutfb (should already be set)
                '''turn off internal Vadjn buffer bias'''
                self.l4reg(lab4, 2, 0)      #PCLK-1=2 : VanN
                
                calFbs = calibrations.read_vtrimfb(self.dev.dna())
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
            user[27:24] = lab
            user[31] = 1
            if verbose:
                print("Going to write 0x%X" % user) 
                self.write(self.map['L4REG'], int(user))
            while not user[31]:
                user = bf(self.read(self.map['L4REG']))

        def default(self, lab4=None):
            if lab4 is None:
                lab4 = self.labAll
            '''DAC default values'''
            self.l4reg(lab4, 0, 1024)      #PCLK-1=0 : Vboot 
            self.l4reg(lab4, 1, 1024)      #PCLK-1=1 : Vbsx
            self.l4reg(lab4, 2, 1024)      #PCLK-1=2 : VanN
            calNs = calibrations.read_vadjn(self.dev.dna())
            if calNs == None:
                print("Using default VadjN of 1671.")
                self.l4reg(lab4, 3, 1671)
            else:
                print("Using cal file for VadjN's")
                if lab4 == self.labAll:
                    for i in range(self.numLabs):
                        self.l4reg(i,3,calNs[i])
                    else:
                        self.l4reg(lab4, 3, calNs[lab4])

            calPs = calibrations.read_vadjp(self.dev.dna())
            if calPs == None:
                print("Using default VadjP of 2700.")
                self.l4reg(lab4, 8, 2700)
            else:
                print("Using cal file for VadjP's")
                if lab4 == self.labAll:
                    for i in range(self.numLabs):
                        self.l4reg(i,8,calPs[i])
                    else:
                        self.l4reg(lab4, 8, calPs[lab4])
                        
            self.l4reg(lab4, 4, 1024)      #PCLK-1=4 : Vbs 
            self.l4reg(lab4, 5, 1100)      #PCLK-1=5 : Vbias 
            self.l4reg(lab4, 6, 950)       #PCLK-1=6 : Vbias2 
            self.l4reg(lab4, 7, 1024)      #PCLK-1=7 : CMPbias 
            self.l4reg(lab4, 9, 1000)      #PCLK-1=9 : Qbias 
            #self.l4reg(lab4, 10, 2780)     #PCLK-1=10 : ISEL (gives ~20 us long ramp)
            #self.l4reg(lab4, 10, 2350)     #PCLK-1=10 : ISEL (gives ~5 us long ramp)
            self.l4reg(lab4, 10, 2580)     #PCLK-1=10 : ISEL (gives ~10 us long ramp)
            
            calFbs = calibrations.read_vtrimfb(self.dev.dna())
            if calFbs == None:
                print("Using default Vtrimfb of 1350.")
                self.l4reg(lab4, 11, 1350)
            else:
                print("Using cal file for Vtrimfb's")
                if lab4 == self.labAll:
                    for i in range(self.numLabs):
                        self.l4reg(i,11,calFbs[i])
                    else:
                        self.l4reg(lab4, 11, calFbs[lab4])
            
            self.l4reg(lab4, 16, 0)        #patrick said to add 6/9
            #PCLK-1=<256:384> : dTrim DACS            
            for i in range (0, 128):       
                self.l4reg(lab4, i+256, 1600)

            '''timing register default values'''        
            self.l4reg(lab4, 384, 95)      #PCLK-1=384 : wr_strb_le 
            self.l4reg(lab4, 385, 0)       #PCLK-1=385 : wr_strb_fe 
            #self.l4reg(lab4, 386, 120)     #PCLK-1=386 : sstoutfb
            self.l4reg(lab4, 386, 104)     #PCLK-1=386 : sstoutfb --optimized for lab0 on canoes, to be generalized 
            self.l4reg(lab4, 387, 0)       #PCLK-1=387 : wr_addr_sync 
            self.l4reg(lab4, 388, 55)      #PCLK-1=388 : tmk_s1_le  --was 38
            self.l4reg(lab4, 389, 86)      #PCLK-1=389 : tmk_s1_fe 
            self.l4reg(lab4, 390, 7)       #PCLK-1=390 : tmk_s2_le  --was 110
            self.l4reg(lab4, 391, 32)      #PCLK-1=391 : tmk_s2_fe  --was 20
            self.l4reg(lab4, 392, 35)      #PCLK-1=392 : phase_le -- was 45 6/8
            self.l4reg(lab4, 393, 75)      #PCLK-1=393 : phase_fe -- was 85 6/8
            self.l4reg(lab4, 394, 100)     #PCLK-1=394 : sspin_le --maybe push up to 104 to squeek out extra ABW (was at 92)
            self.l4reg(lab4, 395, 6)       #PCLK-1=395 : sspin_fe
            
            '''default test pattern'''
            self.l4reg(lab4, 13, 0xBA6)    #PCLK-1=13  : LoadTPG
