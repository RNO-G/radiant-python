
class RadJTAG: 

    def __init__(self, dev, debug = False): 

        self.dev = dev
        self.dbg = debug
        self.in_tlr = False
        self.in_rti = False

    def disable(self): 
        self.dev.write(self.dev.map['BM_CONTROL'], 0) 
   
    def tdo(self):
        rsp =  self.dev.read(self.dev.map['BM_CONTROL'])
        if self.dbg:
            print('  Read from BM_Control:', hex(rsp))
        ret = True if (rsp & (1 <<19)) else False 
        if self.dbg:
            print('  ->', ret)



        return ret 



    def clock(self, tms_val, tdi_val):

        if self.dbg:
            print('::clock(tms=', tms_val, ', tdi=', tdi_val,')')


        # clear these, since don't know
        self.in_rti = False
        self.in_tlr = False
 
        val = 1 << 9 # jtag_enable

        if tdi_val: 
            val |= 1 << 18
        if tms_val: 
            val |= 1 << 17

        if self.dbg:
            print('  Setting BM_Control to ', hex(val))

        #set tdi/tms
        self.dev.write(self.dev.map['BM_CONTROL'], val) 

        # clock rising edge
        val |= 1 << 16 

        if self.dbg:
            print('  Rising edge, setting BM_Control to ', hex(val))
        self.dev.write(self.dev.map['BM_CONTROL'], val) 

        #falling edge
        val &= ~(1 << 16)
        if self.dbg:
            print('  Falling edge, Setting BM_Control to ', hex(val))
        self.dev.write(self.dev.map['BM_CONTROL'], val) 

    

    def tlr(self):
        if self.in_tlr: 
            return 
        for i in range(5): 
            self.clock(1,0) 
        self.in_tlr = True

    def rti(self): 
        if self.in_rti: 
            return
        self.tlr() 
        self.clock(0,0) 
        self.in_rti=True

   # 6 bit val, I guess? 
    def shiftir(self,nbits, val):
        self.rti() 
        self.clock(1,0) # select-dr
        self.clock(1,0) # select-ir
        self.clock(0,0) # capture-ir
        self.clock(0,0) # shfit-ir 
        for i in range(nbits): 
            self.clock(i == nbits-1, val & (1 << i))
        #go to rti 
        #already in exit1-ir 
        self.clock(1,0)
        self.clock(0,0)
        self.in_rti = True

    def shiftdr(self, nbits, val_in = 0):
        # of course, if we're not in RTI already we probably end up with idcode here...  
        self.rti() 
        self.clock(1,0) # select dr
        self.clock(0, 0) # capture dr
        self.clock(0, 0)  # shift dr
        val = 0
        for i in range(nbits): 
            if self.tdo(): 
                val |= (1 << i) 
            self.clock(i == nbits-1, val_in & (1 << i))

        # now go back to rti 
        # already in exit1-dr
        self.clock(1,0) 
        self.clock(0,0) 
        self.in_rti = True 
        return val


    def enumerate(self): 
        self.tlr() #loads idcode 
        return self.shiftdr(32) 


