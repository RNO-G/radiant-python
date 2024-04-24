#!/bin/bash

# this is really a ramdisk
TMPDIR=/dev/shm
IMGSIZE=15728640
BOOTSIZE=2097152

echo "Deleting temporaries in $TMPDIR"
rm -f $TMPDIR/*.bin
goldname=$1
goldext=${goldname##*.}
if [ "$goldext" = "mcs" ] ; then
   echo "Converting golden image to binary..."
   # We need to add a way to generate the critical switch section here.
   # Worry about that later.
   objcopy --input-target=ihex --output-target=binary --pad-to=$IMGSIZE --gap-fill=0xFF $goldname $TMPDIR/golden.bin
   goldname="$TMPDIR/golden.bin"
elif [ "$goldext" = "bin" ] ; then
   fsize=$(stat -c%s "$goldname")
   if (($fsize > $IMGSIZE)) ; then
     echo "$goldname is too big ($fsize > $IMGSIZE)"
     exit -1

   elif  (($fsize < $IMGSIZE)) ; then
     echo "Padding golden image binary"
     objcopy --input-target=binary --output-target=binary --pad-to=$IMGSIZE --gap-fill=0xFF $goldname $TMPDIR/golden.bin
     goldname="$TMPDIR/golden.bin"
   fi
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
   objcopy --input-target=ihex --output-target=binary --pad-to=$IMGSIZE --gap-fill=0xFF $upname $TMPDIR/upgrade.bin
   upname="$TMPDIR/upgrade.bin"
elif [ "$upext" = "bin" ] ; then
   fsize=$(stat -c%s "$upname")
   if (($fsize > $IMGSIZE)) ; then
     echo "$upname is too big ($fsize > $IMGSIZE)"
     exit -1
   elif  (($fsize < $IMGSIZE)) ; then
     echo "Padding upgrade image binary"
     objcopy --input-target=binary --output-target=binary --pad-to=$IMGSIZE --gap-fill=0xFF $upname $TMPDIR/upgrade.bin
     upname="$TMPDIR/upgrade.bin"
   fi

fi
upext=${upname##*.}
if [ "$upext" != "bin" ] ; then
   echo "Either conversion failed, or you didn't give me a bin or mcs file for UPGRADE."
   exit -1
fi

bootname=$3
bootext=${bootname##*.}
if [ "$bootext" = "mcs" ] ; then
   echo "Converting bootloader image to binary..."
   objcopy --input-target=ihex --output-target=binary --pad-to=$BOOTSIZE --gap-fill=0xFF $bootname $TMPDIR/bootloader.bin
   bootname="$TMPDIR/bootloader.bin"
elif [ "$bootext" = "bin" ] ; then

   fsize=$(stat -c%s "$bootname")
   if (($fsize > $BOOTSIZE)) ; then
     echo "$upname is too big ($fsize > $IMGSIZE)"
     exit -1
   elif  (($fsize < $BOOTSIZE)) ; then
       echo "Padding bootloader image ..."
       objcopy --input-target=binary --output-target=binary --pad-to=$BOOTSIZE --gap-fill=0xFF $bootname $TMPDIR/bootloader.bin
       bootname="$TMPDIR/bootloader.bin"
   fi
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

