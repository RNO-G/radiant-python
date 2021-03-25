from Adafruit_BBIO.SPI import SPI
import Adafruit_BBIO.GPIO as GPIO

class BBSPI:
    def __init__(self):
        # SCHEMATIC PINS ARE MIRRORED
        GPIO.setup("P8_26", GPIO.OUT)
        GPIO.output("P8_26", GPIO.LOW)
        self.spi = SPI(0,0)
        self.spi.msh = 48000000
        self.spi.mode = 0
        self.xfer = self.spi.xfer
        self.xfer2 = self.spi.xfer2
        self.close = self.spi.close
        
    def __del__(self):
        GPIO.output("P8_26", GPIO.HIGH)