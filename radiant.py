from cobs import cobs
import serial
from time import sleep

class RADIANT:
	def __init__(self, port):
		self.dev = serial.Serial(port, 1000000)
	
	def read(self, addr):
		tx = bytearray(4)
		tx[0] = (addr & 0x7F0000)>>16
		tx[1] = (addr & 0xFF00)>>8
		tx[2] = addr & 0xFF
		tx[3] = 3
		toWrite = cobs.encode(tx)
		# print(toWrite)
		self.dev.write(toWrite)
		self.dev.write(b'\x00')
		# expect 7 bytes back + 1 overhead + 1 framing
		rx = self.dev.read(9)
		pk = cobs.decode(rx[:8])
		val = pk[3]
		val |= (pk[4] << 8)
		val |= (pk[5] << 16)
		val |= (pk[6] << 24)
		return val

        def write(self, addr, val):
		tx = bytearray(7)
		tx[0] = (addr & 0x3F0000)>>16
		tx[0] |= 0x80
		tx[1] = (addr & 0xFF00)>>8
		tx[2] = addr & 0xFF
		tx[3] = val & 0xFF
		tx[4] = (val & 0xFF00)>>8
		tx[5] = (val & 0xFF0000)>>16
		tx[6] = (val & 0xFF000000)>>24
		self.dev.write(cobs.encode(tx))
		self.dev.write(b'\x00')
		# expect 4 bytes back + 1 overhead + 1 framing
		rx = self.dev.read(6)
		pk = cobs.decode(rx[:5])
		val = pk[3]
                return val
