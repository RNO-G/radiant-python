from radiant import RADIANT
import numpy as np
import time
import copy
import os
import glob

board_name = "test_test"
file_name_start = "."+str(board_name)+"/"
if(len(glob.glob("."+str(board_name)+"*")) == 0):
    print("!!!! Directory doesn't exist!")
    os.system("mkdir ."+str(board_name))

print("!!!! File name will be ", board_name)

print("!!!! About to program CPLDs.")
os.system("python3 examples/radcpldprog.py -f radiant_aux_v2.bit")

print("!!!! About to set analog settings.")
os.system("python3 examples/analog_setup.py")

dev = RADIANT("/dev/ttyO5")

dev.labc.stop()
dev.dma.reset()
dev.labc.reg_clr()

dev.labc.default(dev.labc.labAll)
dev.labc.automatch_phab(dev.labc.labAll)

dev.calib.resetCalib()
dna = dev.dna()
dev.calib.load(dna)

for lab in range(24):
    base_addr = 256

    for i in range(128):
        if(i >= 16 and i < 32):
            dev.calib.calib['specifics'][lab][base_addr + i] = 0
        else:
            dev.calib.calib['specifics'][lab][base_addr + i] = 2000 
        
    dev.labc.l4reg(lab, 11, 1000)
    dev.labc.update(lab)

dev.labc.testpattern_mode(False)

dev.calram.zero()
dev.calram.mode(dev.calram.CalMode.NONE) 
dev.dma.write(3, 0) # reset transaction counter

print("!!!! About to recalculate and save pedestals.")
#dev.labc.reset_fifo(force=True)
dev.calib.updatePedestals()
print("!!!! "+str(file_name_start)+"/peds")
np.save(file_name_start+"/peds", dev.calib.calib['pedestals'])

nruns = 4
    
for Ncalselect in range(3):
    dev.calram.zero()
    dev.calram.mode(dev.calram.CalMode.NONE) 
    dev.dma.write(3, 0) # reset transaction counter

    # Turn on the calibration pulser
    dev.radsig.enable(False)
    dev.calSelect(Ncalselect)
    dev.radsig.signal(pulse=False, band=2)
    #dev.radsig.signal(pulse=False, band=0)
    dev.radsig.enable(True)
    dev.radsig.setFrequency(510.0)
    #dev.radsig.setFrequency(91.0)    

    for jjj in range(nruns): # Run a bunch to flush out bad apples?
        print("!!!! Starting run", jjj, "cal_select", Ncalselect)
        #dev.labc.reset_fifo(force=True)
    
        dev.labc.start()
        dev.labc.force_trigger(block=True, numTrig=1, safe=False)
        time.sleep(1.0)
        dev.labc.stop()

        dev.dma.write(3, 0) # reset transaction counter?
        dev.dma.engineReset()
        dev.dma.txReset()
        for i in range(24):
            final = i==(24-1)
            dev.dma.setDescriptor(i, 0x020000 + 0x000800 * i, 512, increment=True, final=final)
            dev.dma.enable(True, dev.dma.eventDmaMode)
        dev.dma.beginDMA()

        step = 2048 # 4096
   
        data = dev.dma.dmaread(step * 24)

        if(jjj != nruns-1):
            continue

        print("!!!! Saving", jjj)
    
        for i in range(24):
            data_ = data[step * i: step * (i+1)] 
            #print(i, len(data_))
        
            pts = []
            for j in range(0, len(data_), 4):
                ret = data_[j:j+4]
        
                ret_1 = copy.deepcopy(ret[1])
                ret[1] = ret[1] & 0x0F
            
                ret_3 = copy.deepcopy(ret[3])
                ret[3] = ret[3] & 0x0F
                
                number_2 = (ret[3]<<8) | ret[2]
                number_1 = (ret[1]<<8) | ret[0]
            
                pts += [number_1]
                pts += [number_2]

                #if((number_1 != 0 or number_2 != 0) and jjj == 3 and j % 100):
                #    print(i, "\t", number_1, "\t", number_2, end = " | ")
        
            np.savez(file_name_start+"/sinewaves_channel_"+str(i)+"_"+str(Ncalselect)+"outputs", trace=pts)    


print("!!!! About to start the analog scan")

dev.calram.zero()
dev.calram.mode(dev.calram.CalMode.NONE) 
dev.dma.write(3, 0) # reset transaction counter

# Turn on the calibration pulser
dev.radsig.enable
