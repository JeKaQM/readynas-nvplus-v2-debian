#!/bin/sh
# Download and verify the two external payload files (Debian 13 armel base rootfs, Webmin) into DIR.
# Usage: ./fetch-payload.sh DIR
# Pins: debuerreotype "dist-arm32v5" commit (the official Debian container rootfs builds) and Webmin 2.670.
# To move to a newer rootfs: take a newer commit of that branch, and use the "digest" of the single layer in
# trixie/oci/blobs/image-manifest.json (sha256:...) as ROOTFS_SHA256.
set -e
D=${1:?usage: fetch-payload.sh DIR}; mkdir -p "$D"; cd "$D"
ROOTFS_COMMIT=40e479f81323a5347481dccbd8f341218fcf261e
ROOTFS_SHA256=49eebe9825563c4d645a935992f1602e05bccea6dfe4c79e51c1fda75045c88e
WEBMIN_SHA256=9fdacf6b219a186ec5d7dbbbe0f46e9802cbd7050d91605bd0dfc48e150e47dc
curl -fL -o debian-trixie-armel-rootfs.tar.gz \
	"https://raw.githubusercontent.com/debuerreotype/docker-debian-artifacts/$ROOTFS_COMMIT/trixie/oci/blobs/rootfs.tar.gz"
curl -fL -o webmin_2.670_all.deb https://github.com/webmin/webmin/releases/download/2.670/webmin_2.670_all.deb
echo "$ROOTFS_SHA256  debian-trixie-armel-rootfs.tar.gz" | sha256sum -c
echo "$WEBMIN_SHA256  webmin_2.670_all.deb" | sha256sum -c
