def sync(dev):
    synced = False
    lastpps = None    
    while not synced:
        if lastpps is not None:
            curpps = dev.read(0x30004)
            if curpps != lastpps:
                dev.write(0x30000, 2)
                print("Synced at", curpps+1, "keyed by", lastpps, "->", curpps)
                synced=True
        else:
            lastpps = dev.read(0x30004)

def setup(dev):
    dev.dma.reset()
    dev.calram.mode(dev.calram.CalMode.NONE)
    dev.write(0x30000, 0x4)
    dev.dma.setDescriptor(0, 0x30100, 8, increment=True, final=False)
    for i in range(24):
        dev.dma.setDescriptor(i+1, 0x20000+0x800*i, 512, increment=False, final=(i==23))
    dev.dma.enable(True, dev.dma.eventDmaMode)
    dev.write(0x10, (1<<31) | 0xa)
    sync(dev)
    
        