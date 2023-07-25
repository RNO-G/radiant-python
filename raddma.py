class RadDMA:
    map = { 'CONFIG'   : 0x00,
            'CONTROL'  : 0x04,
            'CURDESCR' : 0x08,
            'TXNCOUNT' : 0x0C,
            'DESCRBASE': 0x80 }
    
    # Endian-swap mode bit. This is here just to clarify for Cosmin:
    # take the rest of the mode and OR it with this and you get byte-swapped output.
    # as in, (eventDmaMode | bigEndianMode) gets you big endian output from an event.
    # Don't do this in any of the byte modes... but we don't really use those anyway.
    bigEndianMode = 0x10
    
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
    # The cycle delay just adds 16 to each of that. But you should *ignore* the
    # base speed, as I might speed it up! The cycle delay will *always*
    # be 16 clocks each.
    #
    # For the CPLD, it takes 4*count cycles, or up to 32 clocks to finish.
    # So the cycle delay should be 2 to be safe.
    cpldDmaMode = 0x00000129 | (2 << 9)
    # For the LAB4D, it depends on the prescale. 
    # For the RADIANT it's like ~160 clocks, including the LAB4 controller
    # latency. So the cycle delay should be 12 to be safe.
    
    # LAB4 dma mode: no byte mode, from SPI, enable receive, flag out disabled, ext req disabled
    # 0000_0000_0000_0000 xxxx xxx1 0000_1001

    lab4DmaMode = 0x00000109 | (12 << 9)
    
    # For DMA *calibration* writes, they're instant and need no delay.
    calDmaWriteMode = 0x00000109
    
    # SPI stuff I still need to work on, I want to get rid of the SPI core and use
    # a *very very* compact PicoBlaze core *just* to handle 
    
    def __init__(self, dev, base, spi):
        self.dev = dev
        self.base = base
        self.spi = spi
        
    def get_base(self):
        return self.base

    def write(self, addr, value):
        self.dev.write(addr+self.base, value)
        
    def read(self, addr):
        return self.dev.read(addr+self.base)
    
    def setDescriptor(self, num, addr, length, increment=False, final=True):
        if length <= 0 or length > 4096:
            print("length must be between 1-4096")
            return
        if num > 31:
            print("descriptor number must be between 0-31")
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

    def reset(self):
        self.engineReset()
        self.rxReset()
        self.txReset()
            
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
        
    def selftest(self):
        self.reset()
        # read from the ID registers
        self.setDescriptor(0, 0, 2, increment=True, final=True)
        addr0 = self.dev.read(0)
        addr1 = self.dev.read(4)
        # calDmaMode is pretty much the basic DMA read mode
        self.enable(True, mode=self.calDmaMode)
        self.beginDMA()
        ret = self.dmaread(8)
        test_addr0 = (ret[3] << 24) | (ret[2]<<16) | (ret[1]<<8) | ret[0]
        test_addr1 = (ret[7] << 24) | (ret[6]<<16) | (ret[5]<<8) | ret[4]
        print("Read:",hex(test_addr0),"correct is",hex(addr0))
        print("Read:",hex(test_addr1),"correct is",hex(addr1))
        self.enable(False)
        return((test_addr0==addr0) and (test_addr1==addr1))
        
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
                
