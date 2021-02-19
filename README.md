# RADIANT Python code

## Requirements

* Python 3
* pyserial
* COBS
* pyadf435x with RADIANT interface (installed)
  
## pyadf435x

There's a version of pyadf435x with a RADIANT interface here:

http://github.com/barawn/pyadf435x

It should be installed (python3 setup.py install).

# Examples

## radidentify

Prints RADIANT identification stuff.

## radcpldprog

Configures (both) CPLDs on the RADIANT with configuration file
specified.

## radsig

Turns on and configures the signal generator for a 91 MHz sine wave
(and leaves it on). Need to add command line options to change freq
and turn off, etc.