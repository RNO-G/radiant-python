#!/usr/bin/env python3

import argparse
import logging

import radiant


parser = argparse.ArgumentParser()
parser.add_argument('--device', type=str, default='/dev/ttyRadiant', help='RADIANT serial device file')
parser.add_argument('--num-iterations', dest='num_iterations', type=int, default=10, help='number of iterations')
parser.add_argument('--buff', type=int, default=32, help='window not to change it')
parser.add_argument('--step', type=int, default=4, help='steps to change the isels by')
parser.add_argument('--voltage-setting', dest='voltage_setting', type=int, default=1250, help='voltage to make middle of the range')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose output (logging level DEBUG)')
args = parser.parse_args()

if args.verbose:
	logging.basicConfig(level=logging.DEBUG)
else:
	logging.basicConfig(level=logging.INFO)

radiant_board = radiant.RADIANT(port=args.device)
radiant.calib_isels(radiant_board, args.num_iterations, args.buff, args.step, args.voltage_setting)
