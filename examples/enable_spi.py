#!/usr/bin/env python3

# This program sets up the SPI so that flashrom can use
# it when we're in the bootloader.

from Adafruit_BBIO.SPI import SPI
import Adafruit_BBIO.GPIO as GPIO

# SCHEMATIC PINS ARE MIRRORED
GPIO.setup("P8_26", GPIO.OUT)
GPIO.output("P8_26", GPIO.LOW)

spi = SPI(0,0)
spi.mode = 0
spi.xfer([0xFF,0xFF,0xFF])

