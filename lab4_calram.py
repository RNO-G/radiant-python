from bf import bf
from enum import Enum

class LAB4_Calram:
    
    class CalMode(Enum):
        NONE = 'None'
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
    
    def mode(self, mode):
        # mode control is in the numLabs space
        if mode is self.CalMode.NONE:
            # disable
            self.write(self.numLabs, self.map['CONTROL'], 0)
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
            self.write(self.numLabs, self.map['MODE'], 1)
            # now enable
            self.write(self.numLabs, self.map['CONTROL'], 1)
        else:
            print("Illegal calibration mode")
            
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
        
            