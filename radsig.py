# Python code for handling the ADF4351
# for signal generation.
import logging
import time
try:
    import adf435x.interfaces
    from adf435x import calculate_regs, make_regs
except:
    pass

# How to use-
# dev = RADIANT("/dev/ttyO5")
# sig = dev.radsig
# sig.signal(pulse=False, band = 1)
# sig.enable(True)
# sig.setFrequency(150.0)
# then of course something like dev.calSelect(0) to select the quad
# that gets the signal.
class RadSig:
    def __init__(self, dev, logger=logging.getLogger('root')):
        self.dev = dev
        self.logger = logger
        self.adf4351 = adf435x.interfaces.RadSig(dev)
        self.gpioaddr = dev.map['BM_I2CGPIO_BASE']+4*6
        
    def enable(self, onoff):
        cur = self.dev.read(self.gpioaddr)
        if onoff:
            cur |= 0b01000000
        else:
            cur &= 0b10111111
        self.dev.write(self.gpioaddr, cur)
    
    def setFrequency(self, freq):
        INT, MOD, FRAC, output_divider, band_select_clock_divider = \
                calculate_regs(freq=freq, ref_freq=10.0)
        regs = make_regs(INT=INT, MOD=MOD, FRAC=FRAC,
                output_divider=output_divider,
                band_select_clock_divider=band_select_clock_divider)
        self.adf4351.set_regs(regs[::-1])
        
        
    # Bands are:
    # 0 : 50-100 MHz
    # 1 : 100-300 MHz
    # 2 : 300-600 MHz
    # 3 : 600 MHz+
    # The pulse path doesn't go through the band filter (because I'm dumb, apparently, the 600 MHz+ path would've been fine)
    # so 'band' for it doesn't matter.
    #
    # 2023-08-30 Michael Korntheuer:  changed band addressing for RADIANT V3
    def signal(self, pulse=False, band=0):
        cur = self.dev.read(self.gpioaddr)  # self.gpioaddr = 0x400058
        cur &= 0xCF   # = 0b11001111
        if pulse:
            # set bit 4 not bit 5
            cur |= 0x10     # = 0b00010000
        else:
            # now we *also* select band, so we kill bits 0/2/3/7
            cur &= 0b01000010
            # set bit 5 not bit 4
            cur |= 0b00100000
            if band == 0:
                # CALFIL=1000: set only bit 3
                cur |= 0b00001000
            elif band == 1:
                # CAL_FIL=1110: set bit 7 and 3 and 0
                cur |= 0b10001001
            elif band == 2:
                # CAL_FIL=0001: set only bit 2
                cur |= 0b00000100
            elif band == 3:
                # CAL_FIL=0111: set bit 7 and 2 and 0
                cur |= 0b10000101
            else:
                self.logger.error("Illegal band, must be 0/1/2/3")
                return
        self.logger.debug(f"write {cur:#b}")
        self.dev.write(self.gpioaddr, cur)
            

            
