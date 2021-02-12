#!/usr/bin/env python3

from radiant import RADIANT
import sys, getopt

helpstring="radcpldprog.py [-p|--port <port>] -f|--file bitfile"

def main(argv):
    port = "/dev/ttyO5"
    fn = None
    
    try:
        opts, args = getopt.getopt(argv,"hp:f:",["port=","file="])
    except getopt.GetoptError:
        print(helpstring)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(helpstring)
            sys.exit()
        elif opt in ("-p", "--port"):
            port = arg
        elif opt in ("-f", "--file"):
            fn = arg
    if fn is None:
        print("radcpldprog.py: Filename is required.")
        print(helpstring)
        sys.exit(2)
    
    dev = RADIANT(port)
    # I need to add exceptions to these...
    dev.cpl.configure(fn)
    dev.cpr.configure(fn)

if __name__ == "__main__":
    main(sys.argv[1:])
    