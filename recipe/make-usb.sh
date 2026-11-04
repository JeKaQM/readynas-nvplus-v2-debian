#!/bin/sh
# Assemble the USB stick bundle from the two Buildroot outputs and the verified downloads.
# Usage: make-usb.sh BUILD_DIR PAYLOAD_DIR OUT_DIR
#   BUILD_DIR    holds the Buildroot outputs out-nas-inst/ and out-nas-rd/
#   PAYLOAD_DIR  holds debian-trixie-armel-rootfs.tar.gz and webmin_2.670_all.deb (see fetch-payload.sh)
#   OUT_DIR      is created; copy its contents to the root of the FAT32 stick (a .zip is written next to it)
set -e
[ $# -eq 3 ] || { sed -n '3,6p' "$0"; exit 2; }
B=$1; DL=$2; U=$3; R=$(cd "$(dirname "$0")" && pwd)
I=$B/out-nas-inst/images; D=$B/out-nas-rd/images
rm -rf "$U"; mkdir -p "$U/nas-install/payload" "$U/nas-install/hooks"
cp "$I/uImage-nas" "$U/uImage-recovery"; cp "$I/uInitrd-installer" "$U/initrd-recovery.gz"
P=$U/nas-install/payload
cp "$I/uImage-nas" "$D/uInitrd-nas" "$I/modules-6.12.115.tar.gz" "$DL/debian-trixie-armel-rootfs.tar.gz" "$DL/webmin_2.670_all.deb" "$P/"
OV=$(mktemp -d); cp -a "$R/debian-overlay/." "$OV/"; install -D -m 0755 "$R/board/nvplus-nas/common/nvplus-nand" "$OV/usr/local/sbin/nvplus-nand"
find "$OV" -type d -exec chmod 0755 {} +; find "$OV" -type f -exec chmod 0644 {} +; chmod 0755 "$OV"/usr/local/sbin/* "$OV"/usr/local/bin/lcd-show
tar -C "$OV" --owner=0 --group=0 --numeric-owner -czf "$P/nas-overlay.tar.gz" .; rm -rf "$OV"
(cd "$P" && sha256sum * > SHA256SUMS)
cp "$R/stick/nas-install.conf" "$R/stick/README.txt" "$U/nas-install/"; cp "$R/stick/hooks-README.txt" "$U/nas-install/hooks/README.txt"
cp "$R/stick/README.txt" "$U/README.txt"
(cd "$U" && sha256sum uImage-recovery initrd-recovery.gz > SHA256SUMS-boot)
find "$U" -type d -exec chmod 0755 {} +; find "$U" -type f -exec chmod 0644 {} +
Z="$U.zip"; rm -f "$Z"
python3 -I - "$U" "$Z" <<'PY'
import os, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(root, f); z.write(p, os.path.relpath(p, src))
PY
echo "stick bundle: $U (and $Z)"
