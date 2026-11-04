#!/bin/sh
# NAS kernel as XIP uImage: the stock NAND bootcmd and the USB-recovery bootcmd both load it at 0x1200000,
# so U-Boot 1.1.4 runs it in place (no memmove over itself). Installer ramdisk as a uImage ramdisk.
set -e
BIN="$1"; KIMG="$BIN/zImage.kirkwood-netgear_readynas_nv+_v2"
"$HOST_DIR/bin/mkimage" -A arm -O linux -T kernel -C none -a 0x01200000 -e 0x01200040 -n "Linux-6.12.115-nvplus-nas" -d "$KIMG" "$BIN/uImage-nas"
"$HOST_DIR/bin/mkimage" -A arm -O linux -T ramdisk -C gzip -a 0 -e 0 -n nvplus-installer -d "$BIN/rootfs.cpio.gz" "$BIN/uInitrd-installer"
s=$(stat -c%s "$BIN/uImage-nas"); [ "$s" -le 5242880 ] || { echo "uImage-nas is $s bytes: too big for the 6 MiB NAND partition"; exit 1; }
