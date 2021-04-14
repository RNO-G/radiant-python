#!/bin/bash

# this is really a ramdisk
TMPDIR=/dev/shm

echo "Deleting temporaries in $TMPDIR"
rm -f $TMPDIR/*.bin
goldname=$1
goldext=${goldname##*.}
if [ "$goldext" = "mcs" ] ; then
   echo "Converting golden image to binary..."
   # We need to add a way to generate the critical switch section here.
   # Worry about that later.
   objcopy --input-target=ihex --output-target=binary --pad-to=15728640 --gap-fill=0xFF $goldname $TMPDIR/golden.bin
   goldname="$TMPDIR/golden.bin"
fi
goldext=${goldname##*.}
if [ "$goldext" != "bin" ] ; then
   echo "Either conversion failed, or you didn't give me a bin or mcs file for GOLDEN."
   exit -1
fi
upname=$2
upext=${upname##*.}
if [ "$upext" = "mcs" ] ; then
   echo "Converting upgrade image to binary..."
   objcopy --input-target=ihex --output-target=binary --pad-to=15728640 --gap-fill=0xFF $upname $TMPDIR/upgrade.bin
   upname="$TMPDIR/upgrade.bin"
fi
upext=${upname##*.}
if [ "$upext" != "bin" ] ; then
   echo "Either conversion failed, or you didn't give me a bin or mcs file for UPGRADE."
   exit -1
fi   
bootname=$3
bootext=${bootext##*.}
if [ "$bootext" = "mcs" ] ; then
   echo "Converting bootloader image to binary..."
   objcopy --input-target=ihex --output-target=binary --pad-to=2097152 --gap-fill=0xFF $bootname $TMPDIR/bootloader.bin
   bootname="$TMPDIR/bootloader.bin"
fi
bootext=${bootname##*.}
if [ "$bootext" != "bin" ] ; then
   echo "Either conversion failed, or you didn't give me a bin or mcs file for BOOTLOADER."
   exit -1
fi
echo "Building $TMPDIR/image.bin from:"
echo "GOLDEN: $goldname"
echo "UPGRADE: $upname"
echo "BOOTLOADER: $bootname"
cat $goldname $upname $bootname > $TMPDIR/image.bin

