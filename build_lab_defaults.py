import pickle
from radiant import RADIANT

# Run this script once to generate the two files below.

if RADIANT.SAMPLING_RATE == 2400:
    speed_desc='2G4'
if RADIANT.SAMPLING_RATE == 2400:
    speed_desc='3G2'


# Name for the global defaults
fnd = "lab4defaults_"+speed_desc+".p"
# Name for the *generic* (starting) defaults
fns = "lab4generic_"+speed_desc+".p"

d = {}

## NOTE NOTE: These parameters ALONE WILL NOT
## let a LAB4 function! They're missing
# VadjN default @ 3200MHZ = 1671, @2400MHz = 1511
# VadjP default @ 3200MHZ = 2700, @2400MHz = 2822
# VtrimFB default @ 3200MHZ = 1300, @2400MHz = 1180
# 256-383 (lab specific trims) default @ 3200MHZ = 1600, @2400MHz = 2000

if RADIANT.SAMPLING_RATE==2400:
    d[0] = 1024   # Vboot
    d[1] = 1024   # Vbsx
                  # VadjN is lab-specific (...maybe)
    d[4] = 1024   # Vbs
    d[5] = 1100   # Vbias
    d[6] = 1000   # Vbias2
    d[7] = 1024   # CMPbias
                  # VadjP is lab-specific (...maybe)
    d[9] = 900    # Qbias 900
                  # VtrimFB is lab-specific
    d[16] = 0     # uh... I don't remember
                  # 256-383 are lab-specific trims
    d[384] = 93   # wr_strb_le
    d[385] = 125  # wr_strb_fe
    d[386] = 108  # sstoutfb (appears to be generic) #110
    d[387] = 0    # wr_addr_sync
    d[388] = 55   # tmk_s1_le
    d[389] = 86   # tmk_s1_fe
    d[390] = 7    # tmk_s2_le
    d[391] = 32   # tmk_s2_fe
    d[392] = 35   # phase_le
    d[393] = 75   # phase_fe
    d[394] = 103  # sspin_le (not worth being lab-specific)
    d[395] = 9    # sspin_fe

    d[13] = 0xBA6 # testpattern

    # LAB-specific defaults
    s = {}
    s[2] = 0      # VanN  : note 0 is DLL ON MODE!!, 1024 drives VadjN on its own with Qbias
    s[3] = 1511   # VadjN 
    s[8] = 2822   # VadjP
    s[10] = 2500  # Isel
    s[11] = 1180  # VtrimFB

else: # RADIANT.SAMPLING_RATE==3200:
    d[0] = 1024   # Vboot
    d[1] = 1024   # Vbsx
                  # VadjN is lab-specific (...maybe)
    d[4] = 1024   # Vbs
    d[5] = 1100   # Vbias
    d[6] = 1000   # Vbias2
    d[7] = 1024   # CMPbias
                  # VadjP is lab-specific (...maybe)
    d[9] = 900    # Qbias 900
                  # VtrimFB is lab-specific
    d[16] = 0     # uh... I don't remember
                  # 256-383 are lab-specific trims
    d[384] = 95   # wr_strb_le
    d[385] = 0    # wr_strb_fe
    d[386] = 104  # sstoutfb (appears to be generic) #110
    d[387] = 0    # wr_addr_sync
    d[388] = 55   # tmk_s1_le
    d[389] = 86   # tmk_s1_fe
    d[390] = 7    # tmk_s2_le
    d[391] = 32   # tmk_s2_fe
    d[392] = 35   # phase_le
    d[393] = 75   # phase_fe
    d[394] = 100  # sspin_le (not worth being lab-specific)
    d[395] = 6    # sspin_fe

    d[13] = 0xBA6 # testpattern

    # LAB-specific defaults
    s = {}
    s[2] = 0     # VanN  : note 0 is DLL ON MODE!!, 1024 drives VadjN on its own with Qbias
    s[3] = 1671  # VadjN 
    s[8] = 2700  # VadjP
    s[10] = 2500 # Isel
    s[11] = 1300 # VtrimFB

# By default, we start everyone EXCEPT
# the slow sample at 2000, and start
# the slow sample at 500.
#
# The initial tune then updates the trim
# an common values to find a point where
# the slow sample is *fast* (under 290 ps)
# and the feedback is close to optimal.
#
# The key here is that we *don't actually touch*
# the slow sample's trim! We change *everyone else*
# instead, to push the slow sample into our
# target range. By leaving it at 500, we guarantee
# we've got enough *voltage* range left on it
# to move it around - especially because we're pulling
# it *fast* (so in the end it needs to be *slowed down*.
#
# NEW: At 2400MHz sampling rate, the slow sample isn't as slow
# so we can tune where every sample is now 416ps

for i in range(0,127):
    s[i+256] = 2000 #Sample Specific VTrim
s[383] = 500

pickle.dump( d, open(fnd,"wb"))
pickle.dump( s, open(fns,"wb"))

