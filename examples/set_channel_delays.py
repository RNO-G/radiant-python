from radiant import RADIANT
import sys
import argparse

#python3 channel_delays.py --rf0_delay 0 --rf1_delay 0 --rf0_groups 0 --rf1_groups 0

parser=argparse.ArgumentParser(description='Set channel delays')
parser.add_argument('--rf0_delay',action='store',default=0,help='rf0 trigger readout delay: 0-127')
parser.add_argument('--rf0_groups',action='store',default=0,help='rf0 trigger readout delay group mask: 0b(gr3 gr2 gr1 gr0)')
parser.add_argument('--rf1_delay',action='store',default=0,help='rf1 trigger readout delay: 0-127')
parser.add_argument('--rf1_groups',action='store',default=0,help='rf1 trigger readout delay group mask: 0b(gr3 gr2 gr1 gr0)')

args=parser.parse_args()
print(args)

rf0_delay=int(args.rf0_delay)
rf0_groups=int(args.rf0_groups)
rf1_delay=int(args.rf1_delay)
rf1_groups=int(args.rf1_groups)

#delays are 7 lsb bits of 32bits for up to 127 clock cycle delays
#masks are 4 lsb bits for which groups get delayed 0b(group3 group2 group1 group0)

dev = RADIANT("/dev/ttyO5")
dev.raddelays.set_delays(rf0_delay=rf0_delay,rf0_groups=rf0_groups,rf1_delay=rf1_delay,rf1_groups=rf1_groups)


