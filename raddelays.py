# Documentation since lab4control isn't in the register docx
# Info can also be found in the wiki under the Operations tab
#
# There's one delay for each of the Radiant triggers (since we should only need them on surface trigger events)
# Delay settings are in units of sys clock cycles. (1/18.75MHz=53.33ns for 2400MHz sampling)
# The settings are ints that can be from 0 (no delays) up to 127 (53.33ns*127)
# The masks are group masks, 4 in total. Split between in-ice antennas and surface antennas on each side (ch 0-11 and ch 12-23)
# The groups to channel masks are as follows:
#    group 0 = 0b0001 => channels = 0-11 = 0x0001ff
#    group 1 = 0b0010 => channels = 12-14 = 0x000e00
#    group 2 = 0b0100 => channels = 15-20 = 0x1ff000
#    group 3 = 0b1000 => channels = 21-23 = 0xe00000
#

class RadDelays:
    def __init__(self,dev):
        self.dev=dev
        self.rf0_delay_addr  = 0x10080
        self.rf0_groups_addr = 0x10084
        self.rf1_delay_addr  = 0x10088
        self.rf1_groups_addr = 0x1008c

    def set_delays(self,rf0_delay=0,rf0_groups=0,rf1_delay=0,rf1_groups=0):
        print('chosen values: rf0d ',rf0_delay,' ; rf0gr ',rf0_groups,' ; rf1d ', rf1_delay,' ; rf1gr ',rf1_groups)
        if(rf0_delay>127 or rf1_delay>127 or rf0_groups>15 or rf1_groups>15):
            print('chosen values exceed current limit in fpga - see register doc for more')
            exit()

        print('reading in values first')
        self.read_delays()

        print('writing new values')
        self.dev.write(self.rf0_delay_addr,rf0_delay)
        self.dev.write(self.rf0_groups_addr,rf0_groups)
        self.dev.write(self.rf1_delay_addr,rf1_delay)
        self.dev.write(self.rf1_groups_addr,rf1_groups)

        print('checking written values')
        self.read_delays()
        print('done')

    def read_delays(self):
        print('RF0 delays: getting ',self.dev.read(self.rf0_delay_addr),' from ',self.rf0_delay_addr)
        print('RF0 groups: getting ',self.dev.read(self.rf0_groups_addr),' from ',self.rf0_groups_addr)
        print('RF1 delays: getting ',self.dev.read(self.rf1_delay_addr),' from ',self.rf1_delay_addr)
        print('RF1 groups: getting ',self.dev.read(self.rf1_groups_addr),' from ',self.rf1_groups_addr)
