
class RadJTAG: 

    def __init__(self, dev, debug = False): 

        self.dev = dev
        self.dbg = debug

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
        for i in range(5): 
            self.clock(1,0) 


    def enumerate(self): 
        self.tlr()
        self.clock(0,0)
        self.clock(1,0)
        self.clock(0,0)
        idcode = 0
        for i in range(32):
            if self.tdo(): 
                idcode |= (1 << i)
            self.clock(0,0)
        self.tlr() 
        return idcode 



