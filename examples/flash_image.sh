#!/bin/bash

# flashrom isn't the nicest of programs: it requires that you give it an
# image file of the FULL flash even if you DON'T plan on writing all of it.
# So you need to build an 'idea' of what the flash should look like
# (which we do in build_image.sh , in /dev/shm, because it looks like /tmp
#  is a real directory on my BeagleBone). Then you tell it what parts to do stuff on.

# Image file location. Should match TMPDIR/image.bin from build_image.sh
IMAGE=/dev/shm/image.bin

# Linux SPI device. Change this to what's needed!!
SPIDEV=/dev/spidev0.0
SPISPEED=16000
FLASHROM_DEV="linux_spi:dev=$SPIDEV,spispeed=$SPISPEED"
FLASHTYPE="S25FL256S......0"
LAYOUT="/home/debian/radiant.layout"

flashrom -p "$FLASHROM_DEV" -c "$FLASHTYPE" -w "$IMAGE" -l "$LAYOUT" -i $1 -VVV

