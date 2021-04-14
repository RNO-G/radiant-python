incredibly horrible flash procedure! This procedure is for BEFORE we have the
"golden image" / QuickBoot setup complete - in other words "radiant.layout"
should only have golden, upgrade, and bootloader sections.

CHECK flash_image.sh TO MAKE SURE THE SPI DEVICE IS CORRECT AND THE PATHS ARE
WHAT YOU WANT. Specifically it needs the path to radiant.layout.

What you need:
a) flashrom 1.1 or greater (use Debian testing's flashrom)
b) objcopy (this *really* should be installed)
c) at *least* the bootloader.bin from github.com/barawn/radiant
d) either an MCS or BIN file you want to program.

The image builder needs both a golden image and an upgrade image, even if you're
only going to program one. So just use whatever MCS/BIN file you're
going to program *twice*.

We'll call the new file you want to program "new_bitstream.mcs", and assume
you're going to program it into the golden section for now.

1: radiant_to_bootloader.py
2: enable_spi.py
3: build_image.sh new_bitstream.mcs new_bitstream.mcs bootloader.bin
4: flash_image.sh golden
5: radiant_to_golden.py

That's it. radiant_to_golden.py should report the new version.
