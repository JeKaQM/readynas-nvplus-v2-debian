#!/bin/sh
# Installer ramdisk: move the kernel modules out (they go into Debian, not into RAM), add the shared NAND tool.
set -e
T="$1"; N="$BR2_EXTERNAL_NVPLUS_NAS_PATH/board/nvplus-nas"
K=6.12.115
if [ -d "$T/lib/modules" ]; then	# fresh kernel install; on rebuilds the modules are already packed
	[ -d "$T/lib/modules/$K" ] || { echo "unexpected module dir: $(ls "$T/lib/modules")"; exit 1; }
	rm -f "$T/lib/modules/$K/build" "$T/lib/modules/$K/source"
	tar -C "$T/lib/modules" --owner=0 --group=0 --numeric-owner -czf "$BINARIES_DIR/modules-$K.tar.gz" "$K"
	rm -rf "$T/lib/modules"
fi
[ -s "$BINARIES_DIR/modules-$K.tar.gz" ] || { echo "modules-$K.tar.gz missing"; exit 1; }
install -m 0755 "$N/common/nvplus-nand" "$T/usr/sbin/nvplus-nand"
chmod 0755 "$T"/etc/init.d/S05nvplus-hw "$T"/etc/init.d/S40network "$T"/etc/init.d/S45nvplus-stick "$T"/etc/init.d/S60nvplus-status \
	"$T"/etc/init.d/S90nas-install "$T"/usr/sbin/nas-install "$T"/usr/sbin/nvplus-monitor "$T"/www/cgi-bin/poweroff
grep -q '/sbin/watchdog' "$T/etc/inittab" || echo '::respawn:/sbin/watchdog -F -t 5 -T 20 /dev/watchdog' >> "$T/etc/inittab"
mkdir -p "$T/mnt/stick" "$T/target"
