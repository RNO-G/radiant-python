import pathlib
import time
from multiprocessing import Process


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


def analog_setup(radiant):
    # From radiant-python/example/analog_setup.py

    # enable LAB4 + trigger and set LED red
    for i in range(6):
        radiant.write(radiant.map['BM_I2CGPIO_BASE'] + 4 * i, 0xF0)

    # set pedestal to 0.76V
    radiant.pedestal(int((1100 / 3300) * 4095))

    # set all trigger biases to 1.2V
    # set all attenuators to 0 dB
    for ch in range(24):
        # trigger bias
        radiant.write(radiant.map['BM_TRIGDAC_BASE'] + 4 * ch, 2500)
        # signal attenuator
        radiant.atten(ch, 0, trigger=False)
        # trigger attenuator
        radiant.atten(ch, 0, trigger=True)


def program_cplds(radiant, version=3):
    """ Program the left and right aux CPLDs via JTAG. """
    cpld_fw = pathlib.Path(__file__).parent / 'data' / f'radiant_aux_v{version}.bit'

    for name, cpld in [("left", radiant.cpl), ("right", radiant.cpr)]:
        p = Process(target=cpld.configure, args=(cpld_fw,))

        p.start()
        p.join(timeout=10)
        p.terminate()

        if p.exitcode is None:
            radiant.logger.error(f"Programming of the {name} CPLD timed out.")
            raise TimeoutError()


def lab4_setup(radiant, labs=None, pedestals=True):
    """
    Initialize the LAB4Ds (defaults, phase matching, calibration) and take pedestals.

    Parameters
    ----------
    labs: list of int, optional (Default: None)
        If given, only initialize these LABs (e.g., to heat up the RADIANT with limited power).
        All other LABs stay cleared and no pedestals are taken: the board is not ready
        for data taking.
    pedestals: bool, optional (Default: True)
        Take pedestals at the end (only if `labs` is None).
    """
    radiant.labc.stop()
    radiant.dma.reset()

    radiant.labc.reg_clr()

    # `default()` and `update()` write the calibration in memory (empty after the RADIANT
    # object was (re)created) to the LABs: load it from file, without writing all LABs.
    radiant.calib.load(radiant.uid(), update_labs=False)

    lab_list = range(radiant.labc.numLabs) if labs is None else labs

    # Separate loops: kickstart all DLLs first (in `default()`) so they have time to settle
    # before `automatch_phab` checks the delay lines (as in `tune.py`).
    for lab in lab_list:
        radiant.labc.default(lab)

    if labs is None:
        # The "all LABs" index scans for the SYNC edge once instead of once per LAB
        radiant.labc.automatch_phab(radiant.labc.labAll)
    else:
        for lab in labs:
            radiant.labc.automatch_phab(lab)

    # `automatch_phab` may set register 8 to its generic value: write the calibration again
    for lab in lab_list:
        radiant.labc.update(lab)

    radiant.labc.testpattern_mode(False)

    radiant.calram.zero()
    radiant.calram.mode(radiant.calram.CalMode.NONE)

    if pedestals and labs is None:
        radiant.calib.updatePedestals()


def setup_radiant(station, version=3):
    radiant = station.radiant_board
    radiant.logger.info("Start setup radiant!")
    program_cplds(radiant, version)
    analog_setup(radiant)
    lab4_setup(radiant)
