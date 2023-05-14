from .bf import bf
from enum import Enum

class LAB4_Calram:
    
    # CalMode NONE     : disables the RAM and passes the LAB4 data
    #                  : untouched.
    # CalMode ADJUSTPOS: uses the RAM to pedestal-adjust the LAB4 data upward by
    #                    adding the low 9 bits in the CalRam to each output
    # CalMode ADJUSTNEG: similar to ADJUSTPOS but subtracts. Probably most useful.
    # CalMode PEDESTAL : accumulates incoming LAB4 data in the CalRam
    # CalMode ZEROCROSSING : accumulates zero-crossings (based on top 18 bits)
    #                        of LAB4 data in the CalRam
    class CalMode(Enum):
        NONE = 'None'
        ADJUSTPOS = 'Adjust Up'
        ADJUSTNEG = 'Adjust Down'
        PEDESTAL = 'Pedestal'
        ZEROCROSSING = 'Zerocrossing'

    map = { 'CONTROL'   : 0x0000,
            'MODE'      : 0x0004,
            'ROLLCOUNT' : 0x0008 };
        
    # Need a pointer to the LABC to handle forced triggering.
    def __init__(self, dev, base, labc, numLabs=24, labAllMagic=31):
        self.dev = dev
        self.base = base
        self.labc = labc
        self.numLabs = numLabs
        self.labAllMagic = labAllMagic
        
    # each LAB gets 16 kB chunks
    def read(self, lab, addr):
        return self.dev.read(self.base + 16384*lab + addr)
    
    def write(self, lab, addr, value):
        return self.dev.write(self.base + 16384*lab + addr, value)
    
    def numRolls(self):
        return self.read(self.numLabs, self.map['ROLLCOUNT'])
    
    def mode(self, mode):
        # mode control is in the numLabs space
        if mode is self.CalMode.NONE:
            # disable
            self.write(self.numLabs, self.map['CONTROL'], 0)
            self.write(self.numLabs, self.map['MODE'], 0)
        elif mode is self.CalMode.ADJUSTPOS:
            self.write(self.numLabs, self.map['CONTROL'], 0)
            self.write(self.numLabs, self.map['MODE'], 0x8)
        elif mode is self.CalMode.ADJUSTNEG:
            self.write(self.numLabs, self.map['CONTROL'], 0)
            self.write(self.numLabs, self.map['MODE'], 0x18)
        elif mode is self.CalMode.PEDESTAL:
            # reset the address counter and disable
            self.write(self.numLabs, self.map['CONTROL'], 2)
            # now do a config write (this write HAS to happen)
            # to set ZC mode to 0
            self.write(self.numLabs, self.map['MODE'], 0)
            # now enable
            self.write(self.numLabs, self.map['CONTROL'], 1)            
        elif mode is self.CalMode.ZEROCROSSING:
            # reset the address counter and disable
            self.write(self.numLabs, self.map['CONTROL'], 2)
            # now do a config write to set ZC mode to 1
            # *and* ZC read mode to 1. ZC read mode = 0
            # is practically pointless, so if in some wacko
            # case we need readback, just set the mode to Pedestal
            # and read that way. Whatever.
            self.write(self.numLabs, self.map['MODE'], 5)
            # now enable
            self.write(self.numLabs, self.map['CONTROL'], 1)
        else:
            print("Illegal calram mode")
            
    # Empty everything. The calrams have a way to do
    # this automatically. This only works if the LAB controller's NOT running.
    def zero(self, zerocrossOnly=False):
        ctrl = self.labc.read(self.map['CONTROL'])
        if ctrl & 0x2:
            print("LAB4 in run mode, can't zero calram")
            return 1
        
        toWrite = 0x2
        if zerocrossOnly is not False:
            toWrite |= 0x1
        self.write(self.numLabs, self.map['CONTROL'], 3)
        self.write(self.numLabs, self.map['MODE'], toWrite)
        
        self.labc.start()
        
        self.labc.force_trigger(block=True)
        self.labc.force_trigger(block=True)
        self.labc.force_trigger(block=True)
        self.labc.force_trigger(block=True)
        
        self.labc.stop()
        
            