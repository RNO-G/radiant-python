from bf import bf

class RadDMA:
    map = { 'CONFIG'   : 0x00,
            'CONTROL'  : 0x04,
            'CURDESCR' : 0x08,
            'TXNCOUNT' : 0x0C,
            'DESCRBASE': 0x80 }
    
    # Normal event DMA mode: no byte mode, no incr address, to SPI, no receive, flag out enabled, flag thresh = 512, ext req enabled
    # 1000_0010_0000_0000 xxxx xxx0 xx00_0101 = 0x8200_0005
    eventDmaMode = 0x82000005
    # calibration DMA mode: no byte mode, incr address, to SPI, no receive, flag out enabled, flag thresh = 512, ext req disabled
    # 1000_0010_0000_0000 xxxx xxx0 xx01_0001 = 0x8200_0011
    calDmaMode = 0x82000011
    # CPLD config DMA mode: byte mode, byte target 0, no incr address, from SPI, enable receive, flag out disabled, ext req disabled
    # 0000_0000_0000_0000 xxxx xxx1 0010_0001 = 0x0000_0121
    # NOTE: I need to add the transfer delay bits (bits [15:9]) to make this work!
    cpldDmaMode = 0x00000121
    # this probably also works for others, think about it later
            
    def __init__(self, dev, base, spi):
        self.dev = dev
        self.base = base
        self.spi = spi
        
    def write(self, addr, value):
        self.dev.write(addr+self.base, value)
        
    def read(self, addr):
        return self.dev.read(addr+self.base)
    
    def setDescriptor(self, num, addr, length, increment=False, final=True):
        if length <= 0 or length > 4096:
            printf("length must be between 1-4096")
            return
        if num > 31:
            printf("descriptor number must be between 0-31")
            return
        # The FPGA's space is nominally 22 bit:
        # drop the bottom 2 (32-bit addresses only)
        # and drop the top 2 (unused) - gives us 18
        toWrite = (addr >> 2) & 0x3FFFF
        if increment:
            toWrite |= (1<<18)
        # Subtract 1 from length (0-4095 = 1-4096)
        length = length - 1
        toWrite = toWrite | (length << 19)
        if final:
            toWrite = toWrite | (1 << 31)
        
        self.write(self.map['DESCRBASE']+4*num, toWrite)
    
    def enable(self, onoff, mode=0):
        if not onoff:
            self.write(self.map['CONFIG'], 0)
        else:
            self.write(self.map['CONFIG'], mode)
    
    def engineReset(self):
        self.write(self.map['CONTROL'], 0x4)
    
    def rxReset(self):
        self.write(self.map['CONTROL'], 0x2)
    
    def txReset(self):
        self.write(self.map['CONTROL'], 0x1)
    
    # NOTE: This is only needed for SOFT-TRIGGERED DMA -
    # as in, when YOU'RE FORCING some bit of RAM to be dumped.
    def beginDMA(self):
        self.write(self.map['CONTROL'], 0x8)
        
    def dmaread(self, length):
        dum = [0]*512
        ret = []
        tot = 0
        while tot < length:
            d = None
            if length - tot < 512:
                d = self.spi.xfer2(dum[0:(length-tot)])
                tot = length
            else:
                d = self.spi.xfer2(dum)
                tot = tot + 512
            ret.extend(d)
        return ret
    
    def dmawrite(self, data):
        start = 0
        stop = len(data)
        while start < stop:
            if stop-start < 512:
                self.spi.xfer2(data[start:stop])
                start = stop
            else:
                self.spi.xfer2(data[start:start+512])
                start = start+512
        
                
                