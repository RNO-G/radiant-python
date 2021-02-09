from serialcobsdevice import SerialCOBSDevice
from enum import Enum
from radcpld import RadCPLD
from lab4_controller import LAB4_Controller

from radcalib import RadCalib

class RADIANT:
	##### GLOBAL CRAP
	
	map = { 'FPGA_ID' : 0x0,
			'FPGA_DATEVERSION' : 0x4,
			'CPLD_CONTROL' : 0x8,
			'PPS_SEL' : 0x10,
			'RESET' : 0x14,
			'GEN_CONTROL' : 0x18,
			'LJTAG' : 0x1C,
			'RJTAG' : 0x20,
			'SPISS' : 0x24,
			'DNA' : 0x2C,
			'SPIBASE' : 0x30,
			'LAB4_CTRL_BASE' : 0x10000,
			'BM_ID' : 0x400000,
			'BM_DATEVERSION' : 0x400004,
			'BM_CONTROL' :     0x40000C
			}

	class DateVersion:
		def __init__(self, val):
			self.major = (val >> 12) & 0xF
			self.minor = (val >> 8) & 0xF
			self.rev = (val & 0xF)
			self.day = (val >> 16) & 0x1F
			self.mon = (val >> 21) & 0xF
			self.year = (val >> 25) & 0x7F
		
		def __str__(self):
			return f'v{self.major}.{self.minor}.{self.rev} {self.mon}/{self.day}/{self.year}'
		
		def __repr__(self):
			val = (self.year << 25) | (self.mon << 21) | (self.day << 16) | (self.major<<12) | (self.minor<<8) | self.rev
			return f'RADIANT.DateVersion({val})'
		
	class BurstType(Enum):
		BYTE = 0x000
		WORD = 0x100
		DWORD = 0x200
                
	class DeviceType(Enum):
		SERIAL = 'Serial'		
	
	#### ACTUAL INITIALIZATION
	# dumb map function
	def radiantLabMontimingMap(lab):
		return int(lab/12)
		
	def __init__(self, port, type=DeviceType.SERIAL):
		if type == self.DeviceType.SERIAL:
			self.dev = SerialCOBSDevice(port, 1000000)

		# create the CPLDs. These are really only for JTAG configuration.
		self.cpl = RadCPLD(self, self.map['LJTAG'], self.cpldJtag)
		self.cpr = RadCPLD(self, self.map['RJTAG'], self.cpldJtag)		
		# LAB4 Controller.
		# Dummy calibration for now. Need to redo the calibration core anyway.
		self.labc = LAB4_Controller(self, self.map['LAB4_CTRL_BASE'], calib=RadCalib(), numLabs=24, labAll=31, syncOffset=560, labMontimingMapFn=self.radiantLabMontimingMap)

        # these almost should be considered internal: to burst write/read use the burstread/burstwrite functions
	def multiread(self, addr, num):
		if addr & 0x400000:
			print("RADIANT board manager does not support multireads")
			return None
		return self.dev.multiread(addr, num)

	def multiwrite(self, addr, data):
		if addr & 0x400000:
			print("RADIANT board manager does not support multiwrites")
			return None
		return self.dev.multiwrite(addr, data)

	# Convenience function to enable bursts in JTAG, where we already know reset register
	def setJtagBurstType(self, type=BurstType.BYTE):
		val = 0x80000000 | type.value
		self.write(self.map['RESET'], val)

	def setBurstType(self, type=BurstType.BYTE):
		val = self.read(self.map['RESET'])
		val = 0xFFFFFCFF | type.value
		self.write(self.map['RESET'], val)
	
	def burstRead(self, addr, len, burstType=BurstType.BYTE, inBurst=False, endBurst=True):
		if not inBurst:
			self.write(self.map['BM_CONTROL'], 8)
		resp = None
		if burstType is self.BurstType.BYTE:
			# easy
			resp = self.multiread(addr, len)
		elif burstType is self.BurstType.WORD:
			# handle later. we need to unpack the return data
			# 2 words at a time
			pass
		elif burstType is self.BurstType.DWORD:
			# handle later. we need to unpack the return data
			# 4 words at a time
			pass
		if endBurst:
			self.write(self.map['BM_CONTROL'], 0)	
		return resp
	
	def burstWrite(self, addr, data, burstType=BurstType.BYTE, inBurst=False, endBurst=True):
		# Note, add stupid length check here
		if not inBurst:
			self.write(self.map['BM_CONTROL'], 8)
		resp = None
		if burstType is self.BurstType.BYTE:
			# easy
			resp = self.multiwrite(addr, data)
		elif burstType is self.BurstType.WORD:
			tx = bytearray(0)
			for w in data:
				tx.append(w & 0xFF)
				tx.append((w>>8) & 0xFF)
			resp = self.multiwrite(addr, tx)
		elif burstType is self.BurstType.DWORD:
			tx = bytearray(0)
			for w in data:
				tx.append(w & 0xFF)
				tx.append((w>>8) & 0xFF)
				tx.append((w>>16) & 0xFF)
				tx.append((w>>24) & 0xFF)
			resp = self.multiwrite(addr, tx)
		if endBurst:
			self.write(self.map['BM_CONTROL'], 0)
			
	def read(self, addr):
		return self.dev.read(addr)
	
	def write(self, addr, val):
		return self.dev.write(addr, val)		

	def cpldJtag(self, enable):
		# enable is bit 31 of reset reg
		val = self.read(self.map['RESET'])
		val = val & 0x7FFFFFFF		
		if enable == True:
			val |= 0x80000000
		self.write(self.map['RESET'], val)
		
	def identify(self):
		def str4(num):
			id = str(chr((num>>24)&0xFF))
			id += chr((num>>16) & 0xFF)
			id += chr((num>>8) & 0xFF)
			id += chr(num & 0xFF)
			return id
			
		fid = str4(self.read(self.map['FPGA_ID']))
		fdv = self.DateVersion(self.read(self.map['FPGA_DATEVERSION']))
		dna = self.dna()
		print("FPGA:", fid, fdv, hex(dna))
		bid = str4(self.read(self.map['BM_ID']))
		bver = self.DateVersion(self.read(self.map['BM_DATEVERSION']))
		print("Board Manager:", bid, bver)
			
	def dna(self):
		self.write(self.map['DNA'], 0x80000000)
		dnaval=0
		# now burst read from the DNA address 57 times
		r = self.burstRead(self.map['DNA'], 57)		
		for i in range(57):
			val = r[i] & 0x1
			dnaval = (dnaval << 1) | val
		return dnaval
