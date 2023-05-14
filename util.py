import numpy as np
import pathlib


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
