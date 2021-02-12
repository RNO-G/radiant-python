#!/usr/bin/env python3

from radiant import RADIANT
import sys, getopt

helpstring="radidentify.py -p|--port <port>"

def main(argv):
    port = "/dev/ttyO5"
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
    dev.identify()

if __name__ == "__main__":
    main(sys.argv[1:])
    