#!/usr/bin/env python3

# This script right now only does a pedestal run for
# channel 0!
#
# Why? I need to check a few dumb things in the
# magic "do this for all LABs" defaults before I
# just go ahead, guns blazing.
#
# This exists right now just for me to remember
# procedures!!!
#
# This assumes everything is quiet and ready to run!
#
from radiant import RADIANT

dev = RADIANT("/dev/ttyO5")

# make sure we're stopped
dev.labc.stop()
# make sure the DMA engine's OK
dev.dma.reset()
# regclr
dev.labc.reg_clr()
# default timings - do dev.labc.labAll instead of 0 here
dev.labc.default(0)
# synchronize - do dev.labc.labAll here instead of 0
dev.labc.automatch_phab(0)
# shutoff testpattern mode
dev.labc.testpattern_mode(False)
# zero the calrams
dev.calram.zero()
# set up calram mode
dev.calram.mode(dev.calram.CalMode.PEDESTAL)
# start the LAB4 Controller
dev.labc.start()
# trigger 4x512 times (4x because each trigger is 1024 samples
# right now!)
for i in range(512):
    dev.labc.force_trigger(block=True)
    dev.labc.force_trigger(block=True)
    dev.labc.force_trigger(block=True)
    dev.labc.force_trigger(block=True)
    if i==511:
        end='\n'
    else:
        end='\r'
    print("trigger ", i, "/512", end=end)

dev.labc.stop()

# set up DMA.
# Change the length to 4096*24 for a full pedestal run
dev.dma.setDescriptor(0, dev.calram.base, 4096, increment=True, final=True)
dev.dma.enable(True, dev.dma.calDmaMode)
# Change the length to 4096*4*24 for a full pedestal run
len = 4096*4
pedarr = dev.dma.dmaread(len)

# Change this to 4096*24 for a full pedestal run
for i in range(4096):
    val = pedarr[4*i]+(pedarr[4*i+1]<<8)+(pedarr[4*i+2]<<16)+(pedarr[4*i+3]<<24)
    print(val)

