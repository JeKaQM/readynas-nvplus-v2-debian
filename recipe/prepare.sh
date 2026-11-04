#!/bin/sh
# Fill one unit's values (site.conf) into a build copy of this recipe.
# Usage: ./prepare.sh site.conf OUT_DIR      (OUT_DIR must not exist; it becomes the Buildroot BR2_EXTERNAL tree)
set -e
[ $# -eq 2 ] || { sed -n '2,3p' "$0"; exit 2; }
CONF=$1; OUT=$2; SRC=$(cd "$(dirname "$0")" && pwd)
[ ! -e "$OUT" ] || { echo "$OUT exists"; exit 1; }
get() { v=$(tr -d '\r' < "$CONF" | sed -n "s/^$1=//p" | tail -1); [ -n "$v" ] || { echo "$1 missing in $CONF"; exit 1; }; echo "$v"; }
MAC=$(get UNIT_MAC | tr 'A-F' 'a-f'); IP=$(get FALLBACK_IP); GW=$(get FALLBACK_GW); DNS=$(get FALLBACK_DNS)
echo "$MAC" | grep -qE '^([0-9a-f]{2}:){5}[0-9a-f]{2}$' || { echo "UNIT_MAC must look like 00:11:22:33:44:55"; exit 1; }
[ "$MAC" != 00:11:22:33:44:55 ] || { echo "UNIT_MAC is still the example value"; exit 1; }
for a in "$IP" "$GW" "$DNS"; do echo "$a" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}$' || { echo "not an IPv4 address: $a"; exit 1; }; done
mkdir -p "$OUT"; cp -a "$SRC/." "$OUT/"
rm -f "$OUT/site.conf" "$OUT/prepare.sh"
BYTES=$(echo "$MAC" | tr ':' ' ')
grep -rl -E '@(UNIT_MAC|UNIT_MAC_BYTES|FALLBACK_IP|FALLBACK_GW|FALLBACK_DNS)@' "$OUT" | while read -r f; do
	sed -i -e "s/@UNIT_MAC_BYTES@/$BYTES/g" -e "s/@UNIT_MAC@/$MAC/g" -e "s/@FALLBACK_IP@/$IP/g" \
	       -e "s/@FALLBACK_GW@/$GW/g" -e "s/@FALLBACK_DNS@/$DNS/g" "$f"
done
! grep -rn -E '@(UNIT_MAC|UNIT_MAC_BYTES|FALLBACK_IP|FALLBACK_GW|FALLBACK_DNS)@' "$OUT" || { echo "placeholders left"; exit 1; }
echo "configured recipe: $OUT (MAC $MAC, fallback $IP via $GW, DNS $DNS)"
