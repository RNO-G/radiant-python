#!/usr/bin/env python3

from radiant import RADIANT
import sys
import getopt


def main(argv):
    port = "/dev/ttyRadiant"
    try:
        opts, args = getopt.getopt(argv,"hp:",["port="])
    except getopt.GetoptError:
        print(helpstring)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(helpstring)
            sys.exit()
        elif opt in ("-p", "--port"):
            port = arg
    
    dev = RADIANT(port)
    print(hex(dev.jtag.enumerate()))

if __name__ == "__main__":
    main(sys.argv[1:])
    
