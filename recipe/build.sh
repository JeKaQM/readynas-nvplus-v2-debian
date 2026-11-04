#!/bin/sh
# Build the NAS kernel, the installer ramdisk and the NAND boot initrd with Buildroot, then the USB bundle.
# Usage: ./build.sh CONFIGURED_RECIPE WORK_DIR PAYLOAD_DIR
#   CONFIGURED_RECIPE  output of prepare.sh
#   WORK_DIR           Buildroot source, downloads and outputs (about 10 GB); the bundle lands in WORK_DIR/usb
#   PAYLOAD_DIR        output of fetch-payload.sh
set -e
[ $# -eq 3 ] || { sed -n '3,6p' "$0"; exit 2; }
C=$(cd "$1" && pwd); mkdir -p "$2"; W=$(cd "$2" && pwd); DL=$(cd "$3" && pwd)
BR=2025.02.19; BR_SHA256=e5e58bff1da91f022f60cefdfe280140c08023cd0aeec1e5f6f9da0ea866d69c
! grep -rqE '@(UNIT_MAC|UNIT_MAC_BYTES|FALLBACK_IP|FALLBACK_GW|FALLBACK_DNS)@' "$C" || { echo "$C still has placeholders: run prepare.sh"; exit 1; }
if [ ! -d "$W/buildroot-$BR" ]; then
	curl -fL -o "$W/buildroot-$BR.tar.xz" "https://buildroot.org/downloads/buildroot-$BR.tar.xz"
	echo "$BR_SHA256  $W/buildroot-$BR.tar.xz" | sha256sum -c
	tar -xJf "$W/buildroot-$BR.tar.xz" -C "$W"
fi
cd "$W/buildroot-$BR"
make O="$W/out-nas-inst" BR2_EXTERNAL="$C" nvplus_nas_installer_defconfig
make O="$W/out-nas-rd" BR2_EXTERNAL="$C" nvplus_nas_bootrd_defconfig
make O="$W/out-nas-inst"
make O="$W/out-nas-rd"
sh "$C/make-usb.sh" "$W" "$DL" "$W/usb"
