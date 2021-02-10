#
# RADIANT CPLD code
# "Ported" (copied) from the micropython stuff
# "dev" here needs a class with write/read
# we also need a function to enable/disable JTAG
# Don't call private functions.
#
from time import sleep
import binascii

class RadCPLD:
	def __init__(self, dev, addr, jtagEnableFn):
		self.dev = dev
		self.addr = addr
		self.enable = jtagEnableFn
        # Magic JTAG movement stuff
        # go to TLR
		self.__tlr = 0x44001F00
		# go to RTI
		self.__rti = 0x45001F00
        # go to shift-IR (or go to shift-DR from shift-IR)
		self.__sir = 0x43000300
		# go to RTI from shift-IR
		self.__sirrti = 0x41000100
		# go to shift-DR
		self.__sdr = 0x42000100
		# shift-8-and-exit
		self.__se8 = 0x47008000
		# shift 8
		self.__s8 =  0x47000000
		
    # get device ID
	def id(self):
		self.enable(True)
		self.dev.write(self.addr, self.__tlr)
		self.__shiftir(0xE0)
		self.dev.write(self.addr, self.__sir)
		val = self.__readdr32()
		self.dev.write(self.addr, self.__tlr)
		self.enable(False)
		return val

	# program in a CPLD bitstream
	# useBurst is ~12x faster: requires setJtagBurstType and burstWrite
	def configure(self, fn, useBurst=True):
		if useBurst:
			self.dev.setJtagBurstType(self.dev.BurstType.BYTE)		
		
		f = self.getbitstream(fn)
		if f is None:
			print("File not OK")
			return False
		
		self.dev.write(self.addr, self.__tlr)
		
		# ISC_ENABLE
		self.__shiftirdr(0xC6, 0x00)
		# ISC_ERASE
		self.__shiftirdr(0x0E, 0x01, False)
		self.__runtest(1)
		# BYPASS
		self.__shiftir(0xFF, False)
		# go to RTI
		self.dev.write(self.addr, self.__sirrti)
		# LSC_INIT_ADDRESS
		self.__shiftirdr(0x46, 0x1, False)
		# LSC_BITSTREAM_BURST
		self.__shiftir(0x7A, False)
		# Go to SDR (using magic shift-IR + self.sir = shift-DR)
		self.dev.write(self.addr, self.__sir)
		if useBurst:	
			# clock a lot of FFs to ensure we're starting off OK
			self.dev.write(self.addr, 0x670000FF)
			# now burst in 97 at a time, and exit still in burst mode
			burst = bytearray(b'\xFF')*97
			self.dev.burstWrite(self.addr, burst, endBurst=False)
			self.dev.burstWrite(self.addr, burst, inBurst=True, endBurst=False)
			self.dev.burstWrite(self.addr, burst, inBurst=True, endBurst=False)
			self.dev.burstWrite(self.addr, burst, inBurst=True, endBurst=False)
			# this is around ~12x faster than non-bursting.
			# Can speed up about ~2x more by adding an option to not wait for a response
			# first value
			val = f.read(1)
			# next value
			nv = f.read(1)
			# burst list
			b = bytearray(0)
			while len(nv) > 0:
				b.append(ord(val))
				val = nv
				nv = f.read(1)
				lastXfer = (len(nv) == 0)
				if len(b) == 128 or lastXfer:
					self.dev.burstWrite(self.addr, b, inBurst=True, endBurst=lastXfer)
					b = bytearray(0)		
		else:
			# clock a lot of FFs to ensure we're starting off OK
			for i in range(388):
				self.dev.write(self.addr, 0x670000FF)
			# get data from bitstream
			# run 1 ahead so that we can detect if we're
			# the last value to be clocked in
			val = f.read(1)
			# next value
			nv = f.read(1)
			while len(nv) > 0:
				self.dev.write(self.addr, 0x67000000 | ord(val))
				val = nv
				nv = f.read(1)

		# now we're on the last, and we're out of burst mode.
		self.dev.write(self.addr, 0x67008000 | ord(val))
		# runtest for a while
		self.dev.write(self.addr, self.__sirrti)
		for i in range(50):
			self.__runtest(0.002)
		# and disable ISC
		self.__isc_disable(False)
		f.close()
		self.enable(False)

	# Useful for checking if the file you've got is
	# correct *before* screwing with things.
	# Call this with the filename, if it returns None
	# it's not a bitstream file.
	# Then close the returned object.
	def getbitstream(self, fn):
		# fetch a zero terminated string
		def readstr(f):
			b = bytearray()
			b.extend(f.read(1))
			while b[-1] != 0:
				b.extend(f.read(1))
			s = str(b, "utf-8")
			return s
		# Check the first two bytes, they
		# should be 0xFF 0x00
		f = open(fn, "rb")
		val = f.read(2)
		if val != b'\xff\x00':
			return None
		# Now dump the first 13 strings
		# as output, just to check
		# we're parsing right.
		for i in range(13):
			s = readstr(f)
			print(s)

		# Now check to see if the next is 0xFF
		val = f.read(1)
		if val != b'\xff':
			return None
			
		# now return the open file
		return f

	# go to RTI and wait a while
	def __runtest(self, wt):
		self.dev.write(self.addr, 0x41000000)
		sleep(wt)

	# fetch an 8-bit value previously clocked in
	def __read8(self):
		rv = self.dev.read(self.addr)
		rv >>= 16
		rv &= 0xFF
		return rv

	# Read a 32-bit value from the CPLD.
	def __readdr32(self):
		val = 0
		for i in range(4):
			self.dev.write(self.addr, self.__s8)
			rv = self.__read8()
			rv <<= i*8
			val |= rv
		return val
		
	# Shift an instruction in and optionally
	# go to RTI first
	def __shiftir(self, instr, dorti=True):
		if dorti:
			self.dev.write(self.addr, self.__rti)
		self.dev.write(self.addr, self.__sir)
		self.dev.write(self.addr, self.__se8 | instr)
		
	# Shift an instruction, then data,
	# optionally going to RTI first
	def __shiftirdr(self, ir, dr, dorti=True):
		self.__shiftir(ir, dorti)
		self.dev.write(self.addr, self.__sir)
		self.dev.write(self.addr, self.__se8 | dr)
		self.dev.write(self.addr, self.__sirrti)
		self.__runtest(0.001)
		
    # get status register
	def __read_status(self):
		self.__shiftir(0x3C)
		self.dev.write(self.addr, self.__sirrti)
		self.__runtest(0.001)
		self.dev.write(self.addr, self.__sdr)
		val = self.__readdr32()
		self.dev.write(self.addr, self.__tlr)
		return val
		
    # disable in-system configuration
	def __isc_disable(self, dorti=True):
		self.__shiftir(0x26, dorti)
		self.dev.write(self.addr, self.__sirrti)
		self.__runtest(1)
		self.__shiftir(0xFF, False)
		self.dev.write(self.addr, self.__sirrti)
		for i in range(50):
			self.__runtest(0.002)
		self.dev.write(self.addr, self.__tlr)
		
    # read the FEABITS in CPLD
	def __read_feabits(self):
		self.__shiftirdr(0x74, 0x08)
		# READ_FEABITS
		self.__shiftir(0xFB, False)
		self.dev.write(self.addr, self.__sir)
		val = self.__readdr32()
		val &= 0xFFFF
		self.dev.write(self.addr, self.__sirrti)
		# and disable ISC
		self.__isc_disable(False)
		
