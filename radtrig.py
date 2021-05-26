from bf import bf

class RadTrig:
    map = { 'PWM_BASE'    : 0x0200,
            'MASTEREN'    : 0x0600,
            'TRIGINEN'    : 0x0604,
            'PULSECTRL'   : 0x0608,
            'TRIGEN0'     : 0x0700,
            'TRIGMASKB0'  : 0x0704,
            'TRIGWINDOW0' : 0x0708,
            'TRIGTHRESH0' : 0x070C }
            
    def __init__(self, dev, base):
        self.dev = dev
        self.base = base
    
    def read(self, addr):
        return self.dev.read(self.base+addr)
    
    def write(self, addr, value):
        self.dev.write(self.base+addr, value)

    # note: you do NOT have to do the enable thing
    # every time. I just have it here to allow None
    # to allow you to disable it. I guess. Like we care.
    #
    # you *actually* only need to write threshold to self.map['PWM_BASE'] + 0x100 + 4*channel
    #
    # HIGHER THRESHOLD MEANS SMALLER SIGNAL
    # THRESHOLD HERE IS IN MILLIVOLTS CUZ I CAN
    # ANYTHING ABOVE LIKE, 1300 mV IS POINTLESS
    def thresh(self, channel, threshInMv):
        oeb = bf(self.read(self.map['PWM_BASE']+0x4))
        if threshInMv is None:
            oeb[channel] = 1
            self.write(self.map['PWM_BASE']+0x4, int(oeb))
            return
        else:
            # magic value here is (1<<24)-1, it's a 24-bit output
            # no, you don't really need 150 microvolt resolution
            value = (threshInMv/2500.)*16777215
            self.write(self.map['PWM_BASE']+0x100+4*channel, int(value))
            # this is the not needed part: you can just enable all of the
            # channels you want right at the start and never bother with
            # this.
            if oeb[channel]:
                oeb[channel] = 0
                self.write(self.map['PWM_BASE']+0x4, int(oeb))
                
    # Configuration.
    # trig0/trig1 are hashes:
    # trig0['MASKB'] specifies included channels
    # trig0['WINDOW'] specifies window
    # trig0['THRESH'] specifies the threshold (number of channels needed)
    def configure(self, inBitmask, trig0=None, trig1=None):
        men = self.read(self.map['MASTEREN'])
        if men != 0:
            print("Trigger is enabled, can't configure!")
            return
        self.write(self.map['TRIGINEN'], inBitmask)
        self.tconf(0, trig0)
        self.tconf(1, trig1)
        
    def tconf(self, number, conf):
        if conf is not None:
            self.write(self.map['TRIGEN0']+number*0x10, (1<<31))
            self.write(self.map['TRIGMASKB0']+number*0x10, conf['MASKB'])
            winreg = 0
            tot = conf['WINDOW']
            # these go N*31+1
            if tot < 32:
                winreg = tot
            elif tot < 63:
                winreg = ((tot-63)<<5) | 31
            elif tot < 94:
                winreg = ((tot-94)<<10) | (31<<5) | 31
            elif tot < 125:
                winreg = ((tot-125)<<15) | (31<<10) | (31<<5) | 31
            self.write(self.map['TRIGWINDOW0']+number*0x10, winreg)
            self.write(self.map['TRIGTHRESH0']+number*0x10, conf['THRESH'])
        else:
            self.write(self.map['TRIGEN0']+number*0x10, 0)
        
    def pulseconfig(self, period, sharp=False, disabled=False):
        rv = period
        if sharp:
            rv = rv | (1<<30)
        if disabled:
            rv = rv | (1<<31)
        self.write(self.map['PULSECTRL'], rv)
            
    def enable(self, onoff):
        if onoff:
            self.write(self.map['MASTEREN'], 1)
        else:
            self.write(self.map['MASTEREN'], 0)
            