
class RADJTag: 

    def __init__(self, dev): 

        self.dev = dev

    def disable(self): 
        self.dev.write(self.dev.map['BM_CONTROL'], 0) 
   
    def clock(self, tdi_val, tms_val):
        val = 0x200     

        if tdi_val: 
            val |= 1 << 18
        if tms_val: 
            val |= 1 << 17
        self.dev.write(self.dev.map['BM_CONTROL'], val) 
        val |= 1 << 16 
        self.dev.write(self.dev.map['BM_CONTROL'], val) 
        rsp =  self.dev.read(self.dev.map['BM_CONTROL']) & (1<<19) != 0 
        return rsp 


    def tlr(self):
        for i in range(5): 
            self.clock(1,1) 


    def enumerate(self, disable_after = True): 
        self.tlr()
        self.clock(0,1)
        self.clock(1,1)
        self.clock(0,1)
        idcode = 0
        for i in range(32):
            idcode >>=1 
            tdobit = self.clock(0,1)
            if tdobit: 
                idcode |= 0x80000000
        self.tlr() 
        return idcode 



