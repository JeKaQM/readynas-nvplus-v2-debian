#!/bin/sh
# NAND boot initrd (minirootfs partition, 16 MiB): uImage ramdisk, as the stock bootcmd's bootm expects.
set -e
BIN="$1"
"$HOST_DIR/bin/mkimage" -A arm -O linux -T ramdisk -C gzip -a 0 -e 0 -n nvplus-boot -d "$BIN/rootfs.cpio.gz" "$BIN/uInitrd-nas"
s=$(stat -c%s "$BIN/uInitrd-nas"); [ "$s" -le 12582912 ] || { echo "uInitrd-nas is $s bytes: too big"; exit 1; }
