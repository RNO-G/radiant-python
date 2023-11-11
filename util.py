import pathlib
import time


class DateVersion(object):
	def __init__(self, val):
		self.major = (val >> 12) & 0xF
		self.minor = (val >> 8) & 0xF
		self.rev = (val & 0xFF)
		self.day = (val >> 16) & 0x1F
		self.mon = (val >> 21) & 0xF
		self.year = (val >> 25) & 0x7F

	def __str__(self):
		return f'v{self.major}.{self.minor}.{self.rev} {self.mon}/{self.day}/{self.year}'

	def __repr__(self):
		val = (self.year << 25) | (self.mon << 21) | (self.day << 16) | (self.major<<12) | (self.minor<<8) | self.rev
		return f'DateVersion({val})'

	def toDict(self):
		return { 'version': f'{self.major}.{self.minor}.{self.rev}', 'date': f'{self.year+2000}-{self.mon:02d}-{self.day:02d}' }


def register_to_string(val):
	id = str(chr((val >> 24) & 0xFF))
	id += chr((val >> 16) & 0xFF)
	id += chr((val >> 8) & 0xFF)
	id += chr(val & 0xFF)
	return id


def reset(radiant):
	radiant.labc.stop()
	radiant.dma.reset()

	radiant.labc.testpattern_mode(False)
	radiant.calram.zero()
	radiant.calram.mode(radiant.calram.CalMode.NONE)
	radiant.dma.write(3, 0)

	radiant.dma.engineReset()
	radiant.dma.txReset()

	# Turn off cal pulser
	for i in range(6):
		radiant.write(radiant.map['BM_I2CGPIO_BASE']+4*i, 0xF0)

	time.sleep(1)
 
 
 
def _analog_setup(radiant):
    # From radiant-python/example/analog_setup.py
    
	# enable LAB4 + trigger and set LED red
	for i in range(6):
		radiant.write(radiant.map['BM_I2CGPIO_BASE']+4*i, 0xF0)

	# set pedestal to 0.76V
	radiant.pedestal(int((1100/3300)*4095))

	# set all trigger biases to 1.2V
	# set all attenuators to 0 dB
	for ch in range(24):
		# trigger bias
		radiant.write(radiant.map['BM_TRIGDAC_BASE']+4*ch, 2500)
		# signal attenuator
		radiant.atten(ch, 0, trigger=False)
		# trigger attenuator
		radiant.atten(ch, 0, trigger=True)


def _create_RADIANT_object(station):
	from .radiant import RADIANT

	station.radiant_board = RADIANT(port=station.station_conf["daq"]["radiant_board_dev"])


def setup_radiant(station, version=3):
	_create_RADIANT_object(station)

	cpld_fw = pathlib.Path(__file__).parent / 'data' / f'radiant_aux_v{version}.bit'
	station.radiant_board.cpl.configure(cpld_fw)
	station.radiant_board.cpr.configure(cpld_fw)

	_analog_setup(station.radiant_board)

	station.radiant_board.labc.stop()
	station.radiant_board.dma.reset()
	station.radiant_board.labc.reg_clr()

	station.radiant_board.labc.default(station.radiant_board.labc.labAll)
	station.radiant_board.labc.automatch_phab(station.radiant_board.labc.labAll)

	station.radiant_board.calib.resetCalib()
	dna = station.radiant_board.dna()
	station.radiant_board.calib.load(dna)

	station.radiant_board.labc.testpattern_mode(False)

	station.radiant_board.calram.zero()
	station.radiant_board.calram.mode(station.radiant_board.calram.CalMode.NONE)
	station.radiant_board.calib.updatePedestals()
