#!/usr/bin/env python3

import argparse
import logging

import radiant


parser = argparse.ArgumentParser()
parser.add_argument('--device', type=str, default='/dev/ttyRadiant', help='RADIANT serial device file')
parser.add_argument('--mask', type=int, default=0xFFFFFF, help='channel mask')
parser.add_argument('--reset', action='store_true', help='reset RADIANT board')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output (logging level DEBUG)')
args = parser.parse_args()

if args.verbose:
	logging.basicConfig(level=logging.DEBUG)
else:
	logging.basicConfig(level=logging.INFO)

radiant_board = radiant.RADIANT(port=args.device)
fail_mask = radiant.tune_initial(radiant_board, args.reset, args.mask)
with open('/tmp/radiant-fail-mask', 'w') as f:
	f.write(hex(fail_mask) + '\n')
