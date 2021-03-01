from bf import bf

class RadDMA:
    map = { 'CONFIG'   : 0x00,
            'CONTROL'  : 0x04,
            'CURDESCR' : 0x08,
            'TXNCOUNT' : 0x0C,
            'DESCRBASE': 0x80 }
    
    # Normal event DMA mode: no byte mode, to SPI, no receive, flag out enabled, flag thresh = 512, ext req enabled
    # 1000_0010_0000_0000 xxxx xxx0 xx0x_0101 = 0x8200_0005
    eventDmaMode = 0x82000005
    # calibration DMA mode: no byte mode, to SPI, no receive, flag out enabled, flag thresh = 512, ext req disabled
    # 1000_0010_0000_0000 xxxx xxx0 xx0x_0001 = 0x8200_0011
    calDmaMode = 0x82000001
    # CPLD config DMA mode: byte mode, byte target 0, from SPI, enable receive, flag out disabled, ext req disabled
    # 0000_0000_0000_0000 xxxx xxx1 001x_1001 = 0x0000_0129
    # NOTE: I need to add the transfer delay bits (bits [15:9]) to make this work!
    #cpldDmaMode = 0x00000129
    # this probably also works for others, think about it later

    # The BASE DMA write speed is around 20 50 MHz clocks.
    # The cycle delay just adds 1 to each of that.
    #
    # For the CPLD, it takes 4*count cycles, or up to 32 clocks to finish.
    # So the cycle delay should be 16 to be safe.
    cpldDmaMode = 0x00000129 | (16 << 9)
    # For the LAB4D, it depends on the prescale. For the RADIANT it's like
    # (26*40 ns = 1040 ns) BUT you also have the LAB4 controller latency
    # which is MUCH larger - around something like 40-50 clocks as well.
    # So it's better to make this the maximum.
    
    # LAB4 dma mode: no byte mode, from SPI, enable receive, flag out disabled, ext req disabled
    # 0000_0000_0000_0000 xxxx xxx1 0000_1001
    # NOTE: I still need to ACTUALLY confirm this works!! It'd be really
    # nice to be able to just DMA the registers in, but this should be
    # considered UnTested.
    lab4DmaMode = 0x00000109 | (127 << 9)
    
    # For DMA *calibration* writes, they're instant and need no delay.
    calDmaWriteMode = 0x00000109
    
    # SPI stuff I still need to work on, I want to get rid of the SPI core and use
    # a PicoBlaze based guy like in HELIX. That'll allow things to be done close to
    # max speed, I think.
    
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
        
                
                