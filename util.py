import enum
import numpy as np
import pathlib
import time


# niter - number of iterations
# buff - window not to change it
# step - steps to change the isels by
# voltage_setting - voltage to make middle of the range
def calib_isels(radiant, niter=10, buff=32, step=4, voltage_setting=1250):
	reset(radiant)
	radiant.calib.resetCalib()
	radiant.calib.load(radiant.dna()) # load whatever calibration has already been done

	radiant.logger.info(f"Start isel values: {[radiant.calib.calib['specifics'][ch][10] for ch in range(24)]}")
	for iIter in range(niter):
		radiant.logger.info(f"calib_isels: starting iteration {iIter} of {niter}")
		reset(radiant)

		for ch in range(24):
			radiant.labc.update(ch)

		radiant.pedestal(int((voltage_setting/3300)*4095))
		time.sleep(0.5)
		radiant.calib.updatePedestals()

		# Now going to fit a line through those two points
		for ch in range(24):
			x0 = voltage_setting
			y0 = np.median(radiant.calib.calib['pedestals'][ch][:1024])

			if(y0 == 0):
				continue

			radiant.logger.debug(f"{iIter} {ch} {y0}")
			if(y0 + buff < 2047):
				radiant.calib.calib['specifics'][ch][10] += step
			elif(y0 - buff > 2047):
				radiant.calib.calib['specifics'][ch][10] -= step

	radiant.logger.info(f"Final isel values: {[radiant.calib.calib['specifics'][ch][10] for ch in range(24)]}")
	radiant.calib.save(radiant.dna())


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
