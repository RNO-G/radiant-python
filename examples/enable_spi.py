#!/usr/bin/env python3

import Adafruit_BBIO.GPIO as GPIO

# SCHEMATIC PINS ARE MIRRORED
GPIO.setup("P8_26", GPIO.OUT)
GPIO.output("P8_26", GPIO.LOW)
