#!/usr/bin/env python3

import argparse
import logging

import radiant


parser = argparse.ArgumentParser()
parser.add_argument('--device', type=str, default='/dev/ttyRadiant', help='RADIANT serial device file')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output (logging level DEBUG)')
args = parser.parse_args()

if args.verbose:
	logging.basicConfig(level=logging.DEBUG)
else:
	logging.basicConfig(level=logging.INFO)

radiant_board = radiant.RADIANT(port=args.device)
print(radiant_board.identify())
