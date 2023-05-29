import enum
import numpy as np
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


def setup_radiant(radiant):
	cpld_fw = pathlib.Path(__file__).parent / 'data' / 'radiant_aux_v2.bit'
	radiant.cpl.configure(cpld_fw)
	radiant.cpr.configure(cpld_fw)

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

	radiant.labc.stop()
	radiant.dma.reset()
	radiant.labc.reg_clr()

	radiant.labc.default(radiant.labc.labAll)
	radiant.labc.automatch_phab(radiant.labc.labAll)

	radiant.calib.resetCalib()
	dna = radiant.dna()
	radiant.calib.load(dna)

	radiant.labc.testpattern_mode(False)

	radiant.calram.zero()
	radiant.calram.mode(radiant.calram.CalMode.NONE)
	radiant.calib.updatePedestals()

	np.save('peds.npy', radiant.calib.calib['pedestals'])


class TuneResult(enum.Enum):
	SUCCESS = enum.auto()
	AUTOMATCH_FAIL = enum.auto()
	TUNE_FAIL = enum.auto()
	SKIPPED = enum.auto()


def tune_initial(radiant, do_reset=False, mask=0xFFFFFF):
	dna = radiant.dna()
	radiant.calib.load(dna)

	if do_reset:
		for ch in range(24):
			radiant.calib.lab4_resetSpecifics(ch)
			if (mask & (1 << ch)):
				radiant.labc.default(ch)
		for ch in range(24):
			if (mask & (1 << ch)):
				radiant.labc.automatch_phab(ch)
	else:
		radiant.calib.load(dna)

	fail_mask = 0x0
	ok = list()
	for ch in range(24):
		if not (mask & (1 << ch)):
			radiant.logger.warning(f"Skipping channel {ch}")
			ok.append(TuneResult.SKIPPED)
			continue
		tuneok = radiant.calib.initialTune(ch)
		if tuneok:
			ok.append(TuneResult.SUCCESS)
		else:
			ok.append(TuneResult.TUNE_FAIL)
			fail_mask |= (1 << ch)

	for ch in range(len(ok)):
		radiant.logger.info(f"LAB{ch} tune: {ok[ch].name}")
	radiant.logger.info(f"Fail mask: {fail_mask:#X}")

	radiant.calib.save(dna)
	radiant.radsig.enable(False)
	radiant.calSelect(None)

	return fail_mask
