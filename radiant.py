from serialcobsdevice import SerialCOBSDevice
from enum import Enum
from radcpld import RadCPLD


class RADIANT:
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
			'BM_ID' : 0x400000,
			'BM_DATEVERSION' : 0x400004 }

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
		

	class DeviceType(Enum):
		SERIAL = 'Serial'		
		
	def __init__(self, port, type=DeviceType.SERIAL):
		if type == self.DeviceType.SERIAL:
			self.dev = SerialCOBSDevice(port, 1000000)

		# create the CPLDs. These are really only for JTAG configuration.
		self.cpl = RadCPLD(self, self.map['LJTAG'], self.cpldJtag)
		self.cpr = RadCPLD(self, self.map['RJTAG'], self.cpldJtag)		

	def multiread(self, addr, num):
		if addr & 0x400000:
			print("RADIANT board manager does not support multireads")
			return None
		return self.dev.multiread(addr, num)

	def multiwrite(self, addr, num):
		if addr & 0x400000:
			print("RADIANT board manager does not support multiwrites")
			return None
		return self.dev.multiwrite(addr, num)

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
		print("FPGA:", fid, fdv)
		bid = str4(self.read(self.map['BM_ID']))
		bver = self.DateVersion(self.read(self.map['BM_DATEVERSION']))
		print("Board Manager:", bid, bver)
			
