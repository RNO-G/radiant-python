
class RadJTAG: 

    def __init__(self, dev, debug = False): 

        self.dev = dev
        self.dbg = debug

    def disable(self): 
        self.dev.write(self.dev.map['BM_CONTROL'], 0) 
   
    def clock(self, tms_val, tdi_val):

        if self.dbg:
            print('::clock(', tms_val, ',', tdi_val,')')

        rsp =  self.dev.read(self.dev.map['BM_CONTROL'])
        if self.dbg:
            print('  Read from BM_Control:', hex(rsp))

 
        val = 0x200     

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
            print('Setting BM_Control to ', hex(val))
        self.dev.write(self.dev.map['BM_CONTROL'], val) 

        rsp =  self.dev.read(self.dev.map['BM_CONTROL'])
        if self.dbg:
            print('  Read from BM_Control:', hex(rsp))


        #falling edge
        val &= ~(1 << 16)
        if self.dbg:
            print('  Setting BM_Control to ', hex(val))
        self.dev.write(self.dev.map['BM_CONTROL'], val) 

        rsp =  self.dev.read(self.dev.map['BM_CONTROL'])
        if self.dbg:
            print('  Read from BM_Control:', hex(rsp))

        ret = (rsp & (1 << 19 )) != 0
 
        if self.dbg:
            print('->',ret)

        return ret


    def tlr(self):
        for i in range(5): 
            self.clock(1,1) 


    def enumerate(self, disable_after = True): 
        self.tlr()
        self.clock(0,0)
        self.clock(1,0)
        self.clock(0,0)
        idcode = 0
        for i in range(32):
            idcode >>=1 
            tdobit = self.clock(0,0)
            if tdobit: 
                idcode |= 0x80000000
        self.tlr() 
        return idcode 



