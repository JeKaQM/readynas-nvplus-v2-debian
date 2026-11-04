# Debian 13 on the NETGEAR ReadyNAS NV+ v2

> [!CAUTION]
> **Experimental. This can brick your NAS and will destroy all data on its disks.**
>
> * This is an **experimental hobby project**, tested on **a single unit**. Your hardware revision,
>   firmware, bootloader settings or disks may differ in ways that were never tested.
> * Following it **erases all four disks** and **replaces software in the NAS's flash memory**. A mistake, a bug,
>   an untested difference in your unit or a power cut at the wrong moment can leave the device **unbootable
>   ("bricked")**. Recovering it may need a serial console, specialist tools, or may not be possible at all.
> * **Verify every fact, address, command and file yourself before you act on it.** Do not rely on this guide
>   alone, and do not continue past any step you do not fully understand.
> * **There is no warranty for anything here.** As a hobby project, everything is provided **"as is"**: no
>   guarantee that the information is correct or complete, that the files work, that the results are safe, and
>   no promise of support or updates. **The author accepts no responsibility or liability** for bricked
>   devices, lost data, hardware damage or any other consequence of using this guide or its files.
>   **You use it entirely at your own risk.**
> * This project is not affiliated with, endorsed or supported by NETGEAR.

**Turn an end-of-life ReadyNAS NV+ v2 into a current Debian 13 NAS with a modern Linux kernel, SSH, a web
admin UI, Samba, NFS and software RAID, without opening the case, without a serial console and without
touching the bootloader.**

| | |
|---|---|
| Status | **Experimental hobby project, no warranty.** Worked on one unit (November 2026); not tested anywhere else. |
| Result | Debian 13.7 "trixie" (armel), Linux 6.12.115 LTS (own build), Webmin 2.670, Samba 4.22, NFS, mdadm 4.4 |
| Bootloader | NETGEAR's U-Boot is never modified. USB recovery worked on this unit; it is not guaranteed. |
| Destructive | **Yes. All four disks are erased.** Back up your data first. |
| Time | Build 10–30 min (first time, depends on your PC), install about 40 min, plus a background RAID build of many hours |
| Skill level | Comfortable with a Linux shell. No soldering, no serial cable. |

> This is an unofficial, experimental community guide. NETGEAR does not support it. You do this entirely at
> your own risk; read the caution above and [Risks and recovery](#5-risks-safety-design-and-recovery) first.

---

## Contents

1. [What you get](#1-what-you-get)
2. [The hardware and the stock firmware](#2-the-hardware-and-the-stock-firmware)
3. [Key findings: why this works](#3-key-findings-why-this-works)
4. [The finished system: how it works](#4-the-finished-system-how-it-works)
5. [Risks, safety design and recovery](#5-risks-safety-design-and-recovery)
6. [Before you start](#6-before-you-start)
7. [Step by step](#7-step-by-step)
8. [Running the NAS day to day](#8-running-the-nas-day-to-day)
9. [Troubleshooting](#9-troubleshooting)
10. [Adapting this to a similar model](#10-adapting-this-to-a-similar-model)
11. [Reference data](#11-reference-data)
12. [What is in this folder](#12-what-is-in-this-folder)
13. [Credits, sources and licensing](#13-credits-sources-and-licensing)

---

## 1. What you get

The stock RAIDiator 5.3.13 firmware is based on Debian 6 "squeeze" with Linux 2.6.31. It has had no updates
for years, and its web UI only speaks TLS 1.0, which modern browsers refuse. After this procedure the same box
runs:

| Function | Software | Where |
|---|---|---|
| Operating system | Debian 13.7 armel, systemd 257, automatic security updates | |
| Kernel | Linux 6.12.115 LTS, built for this board, booted from the NAS's own flash | |
| Remote shell | OpenSSH 10.0 | port 22, key login |
| Web administration | Webmin 2.670 | `https://<nas>:10000` |
| Windows/macOS shares | Samba 4.22 (SMB2/3), `wsdd2` (Windows network discovery), Avahi (`<hostname>.local`) | ports 139/445 |
| Unix shares | NFS server (v3/v4) | port 2049 |
| Storage | Linux md RAID: mirrored root and swap on all four disks, RAID5 (or 6/10) data array, ext4 | `/srv/data` |
| Monitoring | smartd (scheduled self-tests), mdadm monitor, persistent journal; hardware watchdog disabled | |
| Fan | Quiet temperature-controlled fan service (30–50 %, full speed only when hot) | |
| Front panel | Rotating LCD status, ten-minute sleep, wake-only first button press, RAID/warning LEDs | `nvplus-lcd` |

The original blue LEDs, four bays, Gigabit port, 2×16 LCD and GPIO buttons are used. The LCD and demo
were confirmed on the real unit. The panel's button timing is software-tested; physical button-triggered
shutdown/reboot and the new idle/wake behaviour still need owner confirmation. `systemctl poweroff`
is the previously tested shutdown route. See [Front-panel controls](#85-front-panel-controls-and-display-sleep).

---

## 2. The hardware and the stock firmware

| Part | Detail |
|---|---|
| Model | NETGEAR ReadyNAS NV+ v2 (RND4000-200 family, label "RND-4B"). Not the SPARC-based NV+ v1. |
| SoC | Marvell 88F6282 "Kirkwood", Feroceon 88FR131 core, ARMv5TE, 1.6 GHz, no FPU |
| RAM | 256 MiB DDR3 |
| Flash | 128 MiB NAND, 2 KiB pages, 64-byte OOB, 128 KiB erase blocks |
| SATA | One SoC SATA port (`sata_mv`) behind a Marvell 88SM4140 4-port **port multiplier** (3 Gb/s) |
| Network | 1 × Gigabit (`mv643xx_eth`, Marvell 88E1318 PHY) |
| USB | Front: USB 2.0 from the SoC (the bootloader can read it). Rear: USB 3.0 through a NEC uPD720200 on PCIe (the bootloader cannot read it). |
| Sensors / control | GMT G762 fan controller (I²C 0x3e), Ricoh RS5C372A RTC (I²C 0x32), SoC thermal sensor |
| Buttons | Power (GPIO 47), Backup (GPIO 45), Reset (GPIO 13) |
| LEDs | Power (GPIO 31), Backup (22), Disk 1–4 (20, 23, 24, 29), all active-low; power-off GPIO 30 |
| Display | HD44780 2×16 character LCD on GPIOs, Linux `hd44780`/`charlcd` modules |
| Stock firmware | RAIDiator 5.3.13: Linux 2.6.31.8, Debian squeeze userland, X-RAID2 (md + LVM) on the disks |
| Bootloader | U-Boot 1.1.4 (Feb 6 2012), Marvell version 3.4.27, NETGEAR version `Uboot-1_1_4-NetgearNV+V4-V1008` |

Mainline Linux has supported this board since 2013 (device tree `kirkwood-netgear_readynas_nv+_v2.dts` by
Arnaud Ebalard). The hard part was never the kernel; it was getting a new kernel onto the box safely without a
serial console. Everything below is about that.

---

## 3. Key findings: why this works

These are the facts the whole procedure rests on. Each was verified on the real unit.

### 3.1 The stock bootloader has a hidden USB boot that runs entirely in RAM

The official firmware zip (`RAIDiator-arm-5.3.13.zip`) contains the bootloader image `uboot-NV+-1.0.05`.
Disassembling its board start-up code shows:

| Address | What it does |
|---|---|
| `0x601bcc` → `0x600c8c` | Reads GPIO 45 (the **Backup** button) 10 times, 100 ms apart |
| `0x600cf0`..`0x600d14` | If Backup is still held, it sets (in RAM only) `bootcmd=usb start;fatload usb 0:1 0x1200000 /uImage-recovery;fatload usb 0:1 0x2000000 /initrd-recovery.gz;bootm 1200000 2000000` and blinks the Backup LED |
| `0x63c578` | That `setenv` goes through the RAM-only `_do_setenv`; **there is no `saveenv`** |

So holding **Backup** while pressing **Power** makes the stock bootloader load `uImage-recovery` and
`initrd-recovery.gz` from the first FAT partition of a stick in the **front** USB port, and boot them. A normal
power-on afterwards boots the stock system unchanged, because nothing was saved. This gives a risk-free way
to run any kernel, and it is also the permanent recovery route, because the bootloader itself is never
rewritten.

Requirements found the hard way:

* **FAT32 only.** An exFAT stick is silently not found. Use MBR with the first partition formatted FAT32.
  USB 2.0 sticks of 32 GB or less are the safest.
* **Front port only.** The rear ports are USB 3.0 behind PCIe, which this bootloader cannot use.

### 3.2 The bootloader copies "uncompressed" kernels on top of itself, so use an XIP header

The first three boot attempts hung with the Backup LED still blinking. Reverse-engineering `do_bootm`
(`0x634cb0`..`0x634d04`) showed why. For a uImage marked "not compressed", U-Boot 1.1.4 `memmove`s the
payload to the header's load address unless the load address equals the address where the image already is.

NETGEAR's kernel is 3.4 MB with load address `0x8000`, so its copy ends below U-Boot, which runs at `0x600000`.
A 7.7 MB kernel copied to `0x8000` overwrites U-Boot in the middle of the copy, and the box hangs.

**Fix:** wrap the kernel (a self-decompressing zImage with the device tree appended) as an **XIP** uImage:

```
mkimage -A arm -O linux -T kernel -C none -a 0x01200000 -e 0x01200040 -n ... -d zImage+dtb uImage
```

Load address = the address U-Boot loads the file to (`0x1200000`), entry = right after the 64-byte header.
U-Boot then skips the copy and jumps straight in. The zImage decompresses itself to `0x8000`.

### 3.3 The normal flash boot uses the same addresses

The saved U-Boot environment on the unit holds:

```
bootcmd=nand read.e 0x1200000 0x200000 0x600000;nand read.e 0x2000000 0x800000 0x1000000;bootm 0x1200000 0x2000000
```

That is the NAND partition `uImage` (6 MiB) to `0x1200000` and the partition `minirootfs` (16 MiB) to
`0x2000000`. Those are exactly the USB boot's addresses, so **the same XIP kernel boots from USB and from
flash**. The `minirootfs` slot must hold a valid uImage ramdisk: an invalid one makes `bootm` fail.

U-Boot's compiled-in default environment (at file offset `0x736a0`) contains no `bootcmd` at all. Marvell's
board code sets the NAND command above at run time (string at `0x56980`), and on this unit it is saved in the
environment partition. The environment is 128 KiB: a CRC-32 (little-endian) followed by NUL-separated
`name=value` pairs.

### 3.4 Linux can write the flash in a format U-Boot can read

| mtd | Name | Offset | Size | Use after the install |
|---|---|---|---|---|
| mtd0 | `u-boot` | 0x0 | 1.5 MiB | NETGEAR U-Boot. **Never written** (read-only in the device tree) |
| mtd1 | `u-boot-env` | 0x180000 | 128 KiB | U-Boot settings. **Never written** (we make it read-only) |
| mtd2 | `uImage` | 0x200000 | 6 MiB | Our kernel (3.6 MiB) |
| mtd3 | `minirootfs` | 0x800000 | 16 MiB | Our boot initrd (3.0 MiB) |
| mtd4 | `jffs2` | 0x1800000 | 104 MiB | Unused (backed up, left alone) |

The risk with writing NAND from mainline Linux is the error-correction (ECC) layout: if Linux stores ECC
differently from the way U-Boot reads it, the bootloader reads garbage. The U-Boot binary uses generic NAND
code with a configurable `nandEcc`, so the binary alone does not settle it. The installer therefore **tests it
on the device before touching anything**. It reads NETGEAR's own kernel and initrd (written by U-Boot or the
stock kernel) through Linux's software Hamming ECC and requires:

* 0 ECC failures,
* valid uImage header and data CRCs,
* no bad blocks in either partition.

On the test unit: 0 failures, 0 corrected bits, both images valid. After writing, the new images read back
identical, and the NAS boots from them, which is the final proof.

### 3.5 No device tree from the bootloader

U-Boot 1.1.4 knows nothing about device trees. It passes old-style ATAGs and a stock command line (for
example `root=/dev/md0`). The kernel therefore needs:

* `CONFIG_ARM_APPENDED_DTB` and `CONFIG_ARM_ATAG_DTB_COMPAT`: the device tree is glued to the zImage, and the
  ATAG memory/initrd information is merged into it (this works; the external initrd arrives correctly).
* `CONFIG_CMDLINE_FORCE`: ignore the stock command line.
* **The MAC address in the device tree** (`local-mac-address`): otherwise the Ethernet driver invents a random
  MAC on every boot, and DHCP hands out a different address each time.

### 3.6 Disks: one SATA port and a port multiplier

All four bays hang off a single SoC SATA port through the 88SM4140 port multiplier. Linux handles it well
(`sata_mv` + `SATA_PMP`; disks detected about 4 s after boot, UDMA/133, NCQ). Findings:

* **Port multiplier port N = bay N+1.** Verified by matching each disk's SMART power-on hours with the stock
  web UI's per-slot SMART readings: identical values, all exactly +11 h after 11 hours of running.
* **Device letters move.** With a USB stick in the front port, the stick can become `sda` and the disks
  `sdb`–`sde`. Never select disks by letter. The installer selects them by their sysfs path
  (`…/f1080000.sata/…`); the system mounts by filesystem label.

### 3.7 Kernel size budget

The NAND `uImage` slot is 6 MiB, and bad blocks would be skipped, eating into it. The generic `multi_v5`
kernel is about 6.4 MB. Using `mvebu_v5_defconfig`, disabling the other SoC families, building non-boot
drivers as modules and compressing with XZ gives **3.6 MiB**, with everything needed to boot built in (SATA,
port multiplier, md RAID with the XOR engine, ext4, NAND, front USB, Ethernet). The decompressed kernel
(12.3 MB from `0x8000`) stays well clear of `0x1200000`.

### 3.8 Debian on ARMv5

* Debian 13 "trixie" officially supports **armel** (ARMv5TE), and it is the **last** Debian release that will.
  Expect security support until about mid-2028.
* There is no Debian installer or Debian kernel for this board, so the root filesystem starts from the
  official Debian container base image for armel (built by `debuerreotype`), and packages are installed
  natively on the NAS.
* Package notes for trixie armel: `wsdd` no longer exists, so use `wsdd2`; `hexdump` lives in
  `bsdextrautils`.

### 3.9 256 MiB of RAM changes priorities

* **Webmin's default "Authentic" theme is heavy.** It starts a Perl process for every page and polls a lot.
  On the first login, nine Webmin processes held about 170 MB, the box swapped hard, the load reached 21 and
  the RAID build fell to 1 MB/s. Tuning (section 7.4) fixes this.
* Swap is mirrored on all four disks, so heavy swapping competes directly with RAID builds.
* `vm.min_free_kbytes=8192` and `vm.swappiness=10` are set.

### 3.10 The fan

The G762 is used in open loop (PWM 0–255). Measured on the test unit:

| PWM | Duty | Fan speed |
|---|---|---|
| 200 | 78 % | 2,857 rpm |
| 102 | 40 % | 1,920 rpm |
| 77 | 30 % | 1,660 rpm |

At 30–40 % the disks stayed at 26–30 °C and the SoC at 41–42 °C, during the install and during the first
RAID build. For the first 10–15 seconds after pressing Power, the fan is under the bootloader's (or the fan
chip's power-on) control and runs loud; this cannot be changed without modifying U-Boot.

---

## 4. The finished system: how it works

### 4.1 Boot chain

```
Power on
  └─ NETGEAR U-Boot 1.1.4 (NAND mtd0, unchanged)
       ├─ Backup held? ── yes ─> loads uImage-recovery + initrd-recovery.gz from the front USB stick
       │                          └─> installer / rescue system (RAM only)
       └─ no ─> bootcmd: nand read mtd2 -> 0x1200000, mtd3 -> 0x2000000, bootm
                 └─ Linux 6.12.115 (XIP uImage, appended device tree)
                      └─ boot initrd (mtd3): wait for the 4 SATA disks, mdadm --assemble --scan --run,
                         e2fsck -p LABEL=nasroot, mount read-only, switch_root
                           ├─ success ─> Debian 13 systemd (about 75 s to fully up)
                           └─ failure ─> stays in the initrd: DHCP + read-only status page on
                                         http://<nas>/ explaining why; disk LEDs blink; no reboot loop
```

### 4.2 Disk layout (identical on all four disks, GPT)

| Partition | Size | Array | Contents |
|---|---|---|---|
| p1 | 8 GiB | `nasroot`: RAID1 across all 4 disks | ext4, `/` (about 0.7 GB used after install) |
| p2 | 1 GiB | `nasswap`: RAID1 across all 4 disks | swap |
| p3 | rest (about 922 GiB) | `nasdata`: RAID5 (default), RAID6 or RAID10 | ext4, `/srv/data` (RAID5: 2.7 TiB) |

Partitions start at 1 MiB. Arrays use md metadata 1.2; the data array has an internal write-intent bitmap.
The root mirror survives the loss of any three disks; RAID5 data survives one failed disk.

### 4.3 Services

| Service | Port | Configuration |
|---|---|---|
| `ssh` | 22 | Debian defaults: root may log in with a key only |
| `webmin` | 10000 (HTTPS, self-signed) | `/etc/webmin/` |
| `smbd`, `nmbd`, `wsdd2` | 139, 445; 3702 | `/etc/samba/smb.conf` (share `data` → `/srv/data/share`, group `nasusers`) |
| `nfs-server` | 2049 (+ rpcbind 111, mountd) | `/etc/exports` (empty after install) |
| `avahi-daemon` | mDNS | announces `<hostname>.local` |
| `smartmontools` | | `/etc/smartd.conf`: short test Sundays 02:00, long test on the 1st at 03:00, temperature warnings |
| `mdmonitor` | | `/etc/mdadm/mdadm.conf` |
| `nvplus-fan` | | `/usr/local/sbin/nvplus-fan` |
| `systemd-networkd` + `-resolved` + `-timesyncd` | | `/etc/systemd/network/10-nas-lan.network` (DHCP, MAC client ID) |
| `unattended-upgrades` | | `/etc/apt/apt.conf.d/20auto-upgrades` |
| `nvplus-lcd` | | LCD pages, 600 s idle timeout, GPIO buttons and RAID LEDs |
| hardware watchdog | | **Disabled**: `RuntimeWatchdogSec=off`, `RebootWatchdogSec=off`, `KExecWatchdogSec=off` (see section 8.5) |

### 4.4 Files on the NAS that make it work

| Path | Role |
|---|---|
| `/usr/local/sbin/nvplus-nand` | Back up, check and write the kernel/initrd flash partitions (section 8.4) |
| `/usr/local/share/nvplus/` | Copies of the installed `uImage-nas` and `uInitrd-nas`, checksums, README |
| `/usr/local/sbin/nvplus-fan`, `/etc/systemd/system/nvplus-fan.service` | Fan control |
| `/etc/modules-load.d/nvplus.conf` | Loads `drivetemp` and `hd44780` (with `hd44780_common`/`charlcd` dependencies) |
| `/usr/local/sbin/nvplus-lcd`, `/etc/systemd/system/nvplus-lcd.service` | LCD, buttons, disk and warning LEDs |
| `/usr/local/bin/lcd-show` | Optional demo; pauses panel LCD writes, then restores status pages |
| `/etc/systemd/logind.conf.d/nvplus-buttons.conf` | Prevents logind from treating wake/short presses as shutdown or reboot |
| `/etc/systemd/system.conf.d/nas-watchdog.conf` | Disables the unsafe short hardware watchdog |
| `/etc/systemd/journald.conf.d/nas.conf` | Persistent journal, 64 MB cap |
| `/etc/sysctl.d/90-nas.conf` | Memory tuning for 256 MiB |
| `/etc/nvplus-release` | When and how this system was installed |
| `/run/nvplus-boot.log` | Log of the boot initrd for the current boot |
| `/srv/data/nas-system/nand-<time>/` | Full flash backup taken before the install (also on the stick) |
| `/usr/lib/modules/6.12.115/` | Kernel modules (no Debian kernel package is installed) |

### 4.5 LEDs

| Stage | What you see |
|---|---|
| USB boot requested | Backup LED blinks (U-Boot) |
| Kernel started | Backup LED off, Disk 3 + Disk 4 on (kernel entry); Disk 3 off when decompressed; all disk LEDs off when the LED driver starts |
| Installer running | Disk 1 heartbeat; Disk 2 on = network up; Disk 3 blinking = installing |
| Installer writing flash | All four disk LEDs on: **do not switch off** |
| Installer stopped with an error | Disk 4 blinking (Disk 1 heartbeat continues). It never reboots on an error |
| Boot initrd could not start Debian | All four disk LEDs blinking; status page on `http://<nas>/` |
| Debian running | Power LED on |

---

## 5. Risks, safety design and recovery

**What is destroyed:** everything on the four disks (the stock OS lives on the disks too), and the stock
kernel and initrd in flash (they are backed up first).

**What is never touched:** U-Boot and its saved settings. Both are read-only to Linux in the device tree, and
no tool in this project writes them. Because the USB recovery path is part of U-Boot, you can always boot the
stick with Backup + Power, whatever state the flash or disks are in.

**Safety design of the installer:**

1. It checks everything it can **before** changing anything: exactly four internal disks, all with SMART
   "PASSED"; payload checksums; internet access; a sane clock; at least one owner hook present.
2. It backs up the entire flash (all five partitions, plus raw dumps with OOB) to the stick.
3. It runs the flash compatibility check (section 3.4). **If that fails, it stops before touching the disks.**
4. Only then does it wipe and install. On any error it stops, keeps a status page up, saves its log to the
   stick and does **not** reboot.
5. The flash is written last, after the installed system has been verified, then read back and compared.
   If writing fails, it restores the previous images.

**Remaining risks:**

* A power cut during the flash write (about one minute) leaves an unbootable flash. Fix: boot the USB stick
  (Backup + Power), which still works, and rewrite the flash (section 9).
* Disks with existing problems. The installer only requires SMART "PASSED"; it does not surface-test the
  disks. The first RAID build reads and writes every sector, which is the real test.
* Debian armel ends with trixie (about 2028).

**Back to stock firmware** (if you ever want it):

1. Boot the stick in rescue mode (any `WIPE_ALL_FOUR_DISKS` value other than `yes`).
2. Write the backed-up `mtd2-uImage.bin` and `mtd3-minirootfs.bin` back with `flash_erase` + `nandwrite -p`.
   The rescue system has no remote shell by default, so you would add one for this (see section 10).
3. Boot normally and use NETGEAR's factory-default procedure, which rebuilds the stock OS on the (erased)
   disks.

---

## 6. Before you start

### 6.1 Checklist

* [ ] It really is a **ReadyNAS NV+ v2** (ARM, 4 bays, RND4000-200 family). Not an NV+ v1, Duo, Ultra or Pro.
* [ ] Stock firmware RAIDiator 5.x running normally. The recipe expects the stock flash layout and boot
      command; the installer verifies both and stops if they differ.
* [ ] **All four bays populated** with working disks (the installer requires exactly four; each ≥ 100 GB).
      Tested with 4 × 1 TB WD Red.
* [ ] **Your data is backed up elsewhere.** All four disks are erased.
* [ ] The unit's **MAC address** (sticker on the case, the stock web UI, or your router's DHCP table).
* [ ] A **USB stick**: USB 2.0 preferred, 32 GB or less, MBR partition table, first partition FAT32,
      at least 500 MB free (payload ~90 MB, flash backup ~260 MB, logs).
* [ ] The NAS has **internet access** through your router (Debian packages are downloaded during the install,
      about 200 MB) and gets an address by **DHCP**.
* [ ] An **SSH key pair** on your PC (for example `ssh-keygen -t ed25519`). You need its public key.
* [ ] A **Linux build machine** (x86-64, about 10 GB free, the usual Buildroot host tools: `make gcc g++ perl
      python3 rsync cpio unzip bc file wget curl patch bzip2 xz-utils`). WSL2 works too.

### 6.2 Optional dry run (changes nothing)

To check that your unit boots the stick before committing, build the stick (sections 7.1–7.2) but set
`WIPE_ALL_FOUR_DISKS=no`, then boot it with Backup + Power. The installer starts in rescue mode: Disk 1
heartbeat, Disk 2 on, and a status page on `http://<nas>/` saying "rescue mode". Use the page's
**power off** link, then start the stock firmware normally. Nothing on the disks or flash is changed.

---

## 7. Step by step

### 7.1 Build the images

```sh
git clone https://github.com/JeKaQM/readynas-nvplus-v2-debian.git
cd readynas-nvplus-v2-debian/recipe

cp site.conf.example site.conf
$EDITOR site.conf            # UNIT_MAC = your NAS's MAC; FALLBACK_* = used only if DHCP fails

./prepare.sh site.conf ../build/recipe-configured    # fills your values in; refuses example values
./fetch-payload.sh ../build/payload                  # Debian armel rootfs + Webmin, checksums verified
./build.sh ../build/recipe-configured ../build/work ../build/payload
```

`build.sh` downloads Buildroot 2025.02.19 (checksum verified), the Bootlin ARMv5 musl toolchain, Linux
6.12.115 and the package sources, then builds:

| Output | What it is | Size |
|---|---|---|
| `uImage-nas` | Linux 6.12.115 + device tree, XIP uImage (also written to flash) | 3.6 MiB |
| `uInitrd-installer` | Installer/rescue ramdisk (BusyBox, mdadm, e2fsprogs, util-linux, mtd-utils, smartmontools, GNU tar) | 6.3 MiB |
| `uInitrd-nas` | Boot initrd for the flash (BusyBox, mdadm, e2fsck) | 3.0 MiB |
| `modules-6.12.115.tar.gz` | 115 kernel modules for Debian | 3.5 MiB |

The stick bundle lands in `../build/work/usb/` and as `../build/work/usb.zip`.

### 7.2 Prepare the stick

1. Format the stick: MBR, one partition, **FAT32**.
2. Copy the **contents** of `usb/` to the root of the stick. The root must contain `uImage-recovery`,
   `initrd-recovery.gz` and the folder `nas-install/`.
3. Edit `nas-install/nas-install.conf`:

   | Setting | Default | Meaning |
   |---|---|---|
   | `WIPE_ALL_FOUR_DISKS` | `yes` | `yes` = install (erases the disks). Anything else = rescue mode. Set to `done-<time>` automatically after a successful install, so the stick can never wipe twice by accident. |
   | `DATA_RAID` | `5` | `5` (about 2.7 TB with 4 × 1 TB, survives one disk), `6` (about 1.8 TB, survives two), `10` (about 1.8 TB) |
   | `HOSTNAME` | `readynas` | lowercase letters, digits, `-` |
   | `TIMEZONE` | `Europe/London` | any `/usr/share/zoneinfo` name |
   | `FLASH_NAND` | `auto` | `auto` = write the flash if all checks pass. `no` = never (experts only: the box then cannot boot Debian by itself) |

4. **Write your login hook.** The installer contains no passwords or keys of any kind, so you add your own
   access. Create a POSIX shell script `nas-install/hooks/10-login.sh`. The installer runs every
   `hooks/*.sh` (in name order) after Debian is fully installed and configured, just before the final checks
   and the flash write. What the hook environment provides:
   * BusyBox `sh`, running as root in the installer, with **no keyboard input** (stdin is `/dev/null`).
   * `TARGET=/target`: the new root filesystem, mounted, with `/proc`, `/sys` and `/dev` available, so
     `chroot "$TARGET" <command>` runs a command inside the new Debian.
   * Windows line endings are stripped first. Output goes to the install log (shown on the status page and
     saved on the stick), so never print secrets.
   * Exit status 0 means continue; anything else stops the install before the flash is written.

   What it must achieve for SSH: your public key in **`$TARGET/root/.ssh/authorized_keys`**, owned by root,
   with the `.ssh` directory at mode 700 and the file at mode 600. Debian's SSH server accepts key logins for
   root and refuses root passwords by default. Add further public keys (other admins, automation) the same
   way.

   Webmin needs a root **password**. Setting it after the first SSH login with `passwd` (section 7.4) keeps
   any password off the stick; that is the recommended way.

### 7.3 Run the installer

1. Shut the NAS down from the stock web UI and wait until it is off.
2. Put the stick in the **front** USB port.
3. Hold **Backup**, press **Power**, keep holding Backup for about 10 s until the Backup LED blinks, release.
4. Find the NAS's address (normally the same as with the stock firmware, because it uses the same MAC) and
   open `http://<nas>/`. The page refreshes itself and shows the current step, temperatures, fan, RAID
   status and the log.

Timeline of the verified run:

| Step | Duration | What happens |
|---|---|---|
| 1/10 checks | 25 s | disks, SMART, payload checksums, hooks, clock, internet |
| 2/10 flash backup + check | 65 s | backup of all flash partitions to the stick; compatibility check |
| 3/10 wipe + partition | 20 s | old RAID metadata and signatures removed; GPT written |
| 4/10 RAID + filesystems | 2 min | arrays created (data array build throttled while installing), ext4, swap |
| 5/10 unpack Debian | 30 s | base rootfs + kernel modules |
| 6/10 packages + Webmin | **about 31 min** | about 200 MB download; unpacking is CPU-bound |
| 7/10 configure | 20 s | hostname, fstab, mdadm.conf, services, config files |
| 8/10 your hooks | seconds | |
| 9/10 verify | 1 s | init, modules, packages, services, fstab, mdadm.conf |
| 10/10 flash + reboot | 1–2 min | unmount, stop arrays, write and verify flash, mark stick done, reboot |
| First Debian boot | about 75 s | kernel 8.6 s + userspace 66.6 s |

About 40 minutes in total. Then `ssh root@<nas>` works with your key.

### 7.4 After the first login

1. **Set the root password** for Webmin: `passwd`. Then log in at `https://<nas>:10000` as root and accept the
   self-signed certificate.
2. **Make Webmin lighter** (strongly recommended with 256 MiB). These are Webmin's own options; back the files
   up first:
   ```sh
   cd /etc/webmin
   cp -a miniserv.conf miniserv.conf.bak; cp -a system-status/config system-status/config.bak
   cp -a authentic-theme/settings.js authentic-theme/settings.js.bak
   echo 'premodules=WebminCore' >> miniserv.conf          # = "Pre-load Webmin functions library"
   sed -i 's/^collect_pkgs=.*/collect_pkgs=0/' system-status/config     # no apt update counting
   echo 'settings_sysinfo_real_time_status=0;' >> authentic-theme/settings.js   # no live graphs
   (cd /usr/share/webmin/system-status && WEBMIN_CONFIG=/etc/webmin WEBMIN_VAR=/var/webmin \
       /usr/share/webmin/system-status/enable-collection.pl 60)        # dashboard stats hourly
   systemctl restart webmin
   ```
   On the test unit this took the box from load 21, full RAM and 240 MB of swap to 70–105 MB free with
   almost no swap, and the RAID build from 1 MB/s to 12–15 MB/s. Pages still take several seconds; the
   **Gray** theme (Webmin Configuration → Webmin Themes) is much lighter if you prefer speed over looks.
3. **Reserve the address** for the NAS's MAC in your router's DHCP settings, so it never changes.
4. **Remove the stick** and keep it as your rescue stick. After a successful install its
   `WIPE_ALL_FOUR_DISKS` reads `done-…`, so booting it changes nothing.
5. Optional cosmetics:
   * Webmin's certificate is issued to the installer's hostname. Regenerate it under
     Webmin Configuration → SSL Encryption → Self-Signed Certificate.
   * SSH clients that send `LANG=en_GB.UTF-8` (or similar) cause Perl locale warnings and a
     `pam_env: Unable to open env file /etc/default/locale` message. Create `/etc/default/locale` with
     `LANG=C.UTF-8`, or install `locales` and generate your locale.
6. Let the data array finish its first build (`cat /proc/mdstat`). It can take 15–20 hours for 3 × 1 TB on this
   CPU. The NAS is fully usable meanwhile, but it only survives a disk failure once the build is done.

### 7.5 Verify

```sh
cat /etc/nvplus-release                     # install stamp, Debian version, kernel, RAID level
uname -r                                    # 6.12.115
cat /proc/mdstat                            # md125/126 [4/4] [UUUU]; data array recovering, then [UUUU]
grep -c '^ARRAY' /etc/mdadm/mdadm.conf      # 3
df -h / /srv/data
systemctl --failed                          # nothing listed
for s in ssh smbd nmbd wsdd2 nfs-server avahi-daemon smartmontools webmin nvplus-fan nvplus-lcd; do
    printf '%s=%s ' $s $(systemctl is-active $s); done; echo
journalctl -u nvplus-fan -b -o cat | tail -3          # e.g. "pwm 77 (30 %), hottest disk 30 C ..."
cat /run/nvplus-boot.log                    # boot initrd: 4 SATA disks, switch_root after ~8 s
nvplus-nand check                           # read-only: env CRC, bootcmd, ECC, image CRCs -> "check passed"
systemctl show -p RuntimeWatchdogUSec --value          # 15s
smartctl -H /dev/sdX                        # for each disk
```

Expected `nvplus-nand check` output on an installed unit:

```
nvplus-nand: U-Boot environment: 131072 bytes, CRC ok, bootcmd='nand read.e 0x1200000 0x200000 0x600000;nand read.e 0x2000000 0x800000 0x1000000;bootm 0x1200000 0x2000000'
nvplus-nand: /dev/mtd2 (uImage): ECC failures +0, corrected bits +0
nvplus-nand: /tmp/nvplus-nand.6212/uImage: valid uImage type 2, 3788745 bytes, load 0x01200000, entry 0x01200040, 'Linux-6.12.115-nvplus-nas'
nvplus-nand: /dev/mtd3 (minirootfs): ECC failures +0, corrected bits +0
nvplus-nand: /tmp/nvplus-nand.6212/minirootfs: valid uImage type 3, 3123283 bytes, load 0x00000000, entry 0x00000000, 'nvplus-boot'
nvplus-nand: check passed: U-Boot can read what Linux writes to uImage and minirootfs
```

---

## 8. Running the NAS day to day

### 8.1 Users and shares

* **Samba:** create a Unix user, add them to the group `nasusers`, give them a Samba password
  (Webmin → Servers → Samba Windows File Sharing → Convert/Edit users). They can then use `\\<nas>\data`.
  Add more shares in the same module.
* **NFS:** Webmin → Networking → NFS Exports, or edit `/etc/exports` and run `exportfs -ra`.
  `/srv/data/backup` exists as an empty folder for backup targets.

### 8.2 Health

* RAID: `cat /proc/mdstat`, `mdadm --detail /dev/md/nasdata`. Debian's mdadm runs a monthly consistency
  check (first Sunday) and `mdmonitor` logs failures.
* Disks: `smartctl -a /dev/sdX`; smartd runs a short self-test on Sundays and a long one monthly, and warns at
  45 °C and 52 °C.
* Fan and temperatures: `journalctl -u nvplus-fan`, and the raw values under `/sys/class/hwmon/*/`
  (`g762`: `pwm1`, `fan1_input`; `drivetemp`: `temp1_input` per disk).
* Boot problems: `/run/nvplus-boot.log` and `journalctl -b`.

### 8.3 Updates

* Debian security updates install themselves (`unattended-upgrades`). Normal updates: `apt update && apt
  full-upgrade`. There is no Debian kernel package; do not install one.
* Webmin updates itself from its own UI (Webmin Configuration → Upgrade Webmin), or you can add Webmin's
  APT repository.

### 8.4 Updating the kernel or boot initrd

Rebuild with a newer kernel version in the recipe (`BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE`, the module
directory name in `post-build-installer.sh`, `KVER` in `nas-install` and the `make-usb.sh` file name), copy
the new modules to `/usr/lib/modules/<version>/` and run `depmod <version>`, then:

```sh
nvplus-nand check                                   # read-only safety checks
nvplus-nand write uImage-nas uInitrd-nas            # verifies both images, writes, reads back, compares
```

`write` refuses images that are not valid uImages or not XIP at `0x1200000`. It keeps the previous images in
RAM and restores them if writing fails. If a new kernel does not boot, boot the USB stick and write the old
images back; the installed `/usr/local/share/nvplus/` copies are the ones that work.

---

### 8.5 Front-panel controls and display sleep

`nvplus-lcd` rotates pages every five seconds: hostname/address, RAID health/rebuild progress and ETA,
space, four disk temperatures, CPU/fan/load/uptime, RAM/swap, network rates and clock. **After ten minutes
without front-button activity, both text rows blank and the backlight switches off.** Page changes,
rebuild progress and warnings do not reset that timer. Monitoring and warning LEDs remain active.

**Any front-button press, including Power, wakes the display. The entire first press is wake-only, even
if held down:** release it, then press again to operate the panel. This avoids a wake press shutting down
or rebooting the NAS. A new ten-minute timeout starts after button activity. `lcd-show` wakes the LCD for
its demo, gives it exclusive access, then restores the status pages and a fresh ten-minute timeout.

| Button (display already awake) | Tap | Hold |
|---|---|---|
| Backup | Next page; pause rotation for 30 s | 2 s: blank the display/backlight now |
| Reset | Network page | 5 s: reboot; countdown, release early to cancel |
| Power | Show shutdown hint | 2 s: clean shutdown; countdown, release early to cancel |

The provided logind drop-in ignores its own Power/Reset actions so a wake press cannot also invoke
logind's default shutdown. If the panel is unavailable, use SSH/Webmin for a clean shutdown rather than
assuming these custom button actions still work. Bootloader/USB-recovery button behaviour is unchanged.

Disk LEDs use SATA port-multiplier identity, **not sdX order**: solid for in-sync members, blinking while
rebuilding, off for absent/faulty members. The mapping was compared with stock UI slots; physical front
bay-label order still needs independent confirmation. Backup LED warning blink continues while the
screen sleeps (degraded/failed storage, missing volume, hot hardware, full volume, stopped fan or failed
services). These indicators do not replace proper monitoring or backups.

**Watchdog safety:** an earlier `RuntimeWatchdogSec=15s` caused a hard reset when a systemd reload on
this slow, memory-constrained NAS exceeded the watchdog deadline during a RAID rebuild. The hardware
maximum is only about 21 s. The Debian recipe now disables both runtime and reboot hardware watchdogs;
**do not re-enable them just to match the original guide.** Kernel panic reboot after ten seconds remains,
but a complete kernel/userspace hang may now require manual power recovery. The installer/rescue recipe also stops auto-arming its old BusyBox hardware watchdog;
incremental builds remove only the previous exact inittab entry. No systemd manager reload or NAS reboot is required for a panel-program
only update when the driver, unit, logind drop-in and disabled watchdog are already installed.

Software tests (no LCD, GPIO, systemctl or power writes):

```sh
python3 -m unittest discover -s tests -v
```

They exercise the 600 s boundary, all three wake-only presses/holds, subsequent deliberate actions,
cancellation, demo coexistence and continuing warning checks. Passing them is **not** a physical button
or display test. Test sleep/wake first; do not deliberately reboot during an active RAID rebuild merely
to test a button. LCD modules must match the running kernel exactly; rebuild with this recipe rather than
using a module compiled for a different kernel/configuration/symbol versions. `prepare.sh` creates a copy:
use a fresh prepared tree and clean kernel build after changing the LCD fragment; stale module archives
without all three LCD drivers are rejected. New installs enable `nvplus-lcd` and install Python 3.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Backup LED keeps blinking, nothing on the network (USB boot) | The stick was not read: exFAT/NTFS, GPT, no FAT32 first partition, or the rear port | MBR + FAT32 stick in the **front** port |
| Backup LED keeps blinking after a few seconds of stick activity | U-Boot loaded the kernel but hung: a non-XIP kernel larger than about 5 MB overwrote U-Boot (section 3.2) | Use the recipe's XIP `uImage-nas` |
| Backup LED off, Disk 3 + Disk 4 stay on | The kernel started but did not finish decompressing (corrupt or truncated image on the stick) | Copy the files again; compare with `SHA256SUMS-boot` |
| Disk LEDs go off, but no Disk 1 heartbeat | The kernel runs but the initrd did not start (wrong or missing `initrd-recovery.gz`) | Copy the files again |
| Heartbeat and Disk 2 on, but you cannot find the NAS | DHCP gave it another address | Check your router's lease list for the MAC. Or use IPv6 link-local: `ping -6 fe80::<EUI-64 of MAC>%<your-interface>` and then `http://[fe80::…%25<iface>]/` |
| Status page says `rescue mode` | `WIPE_ALL_FOUR_DISKS` is not `yes` | Intended after a successful install; set `yes` only to reinstall |
| `FAILED: no nas-install/hooks/*.sh` | No login hook | Section 7.2 step 4 |
| `FAILED: expected 4 internal disks` | A bay is empty or a disk is not detected | Populate all four bays; check seating |
| `FAILED: … SMART overall health is not PASSED` | A failing disk | Replace it |
| `FAILED: cannot download from deb.debian.org` | No internet or DNS; the log shows `resolv.conf` and routes | Fix the network; reboot the stick |
| `NTP failed; keeping the RTC time` | BusyBox `ntpd -q` gives up after about 10 s ("Alarm clock") | Harmless if the logged time is correct. A wrong clock stops the install, because package signatures would fail |
| `FAILED: NAND flash check failed … nothing has been changed` | Bootloader settings, ECC layout or bad blocks differ from what was tested | **Do not force it.** Read the log lines starting `nvplus-nand:`. The disks and flash are untouched. See section 10 |
| `FAILED: package installation failed` | Network trouble during the download (3 attempts) | Reboot the stick to start again. The disks are re-wiped, which is fine at this stage |
| Install stopped late (Disk 4 blinking) | See `state.txt` / `install.txt` | Use **power off** on the status page, fix the cause, run again. **Do not boot the stock firmware** in between: its OS is gone, and it may offer to factory-reset the disks |
| After the reboot: all four disk LEDs blink, Debian unreachable | The boot initrd could not start Debian (arrays, fsck, mount) | Open `http://<nas>/`: the reason, the initrd log, `mdstat`, `blkid` and `dmesg` are there. Fix from the rescue stick |
| `rtc-mv … internal RTC not ticking` in the journal | The SoC's internal RTC is unused; the board's RS5C372A keeps time | Harmless |
| `blkmapd … rpc_pipefs/nfs/blocklayout failed` | NFS pNFS block layout helper, not used | Harmless |
| `pam_env: Unable to open env file /etc/default/locale`, Perl locale warnings | No locale configured; your SSH client sends its `LANG` | Section 7.4 step 5 |
| Webmin very slow, high load, swapping, RAID build crawling | The Authentic theme on 256 MiB | Section 7.4 step 2; consider the Gray theme |
| `stats.pl` uses about 25 MB | Authentic's live statistics helper, started when the dashboard or side panel is open | Close the dashboard; the real-time setting in 7.4 reduces it |
| LCD dark after ten minutes | Normal idle sleep | Press any front button once to wake; release and press again for actions |
| Unexpected hard reboot during systemd reload | An old 15 s runtime watchdog | Keep runtime/reboot hardware watchdog disabled; see section 8.5 |
| Fan loud for the first 10–15 s after Power | The bootloader/fan chip default before Linux runs | Normal; Linux takes over and drops to 40 %, then Debian to 30–50 % |
| Fan log says `no RPM at pwm …, raising the minimum` | This fan stalls at very low duty | Automatic; the minimum is raised in 5 % steps |
| Disk names differ between boots (`sda` vs `sdb`) | A USB stick enumerated first | Normal. Everything uses labels/UUIDs |
| Data array rebuild very slow | Competing I/O (swap, Webmin) or `speed_limit_min` (1 MB/s) | Reduce load; `cat /sys/block/md127/md/sync_speed`; optionally `echo 20000 > /proc/sys/dev/raid/speed_limit_min` while idle |

**Rewriting the flash from the rescue stick:** the rescue/installer system has `nvplus-nand`, `flash_erase`,
`nandwrite` and the images in `nas-install/payload/`, but deliberately no remote shell. To use them, add a
shell route you control (for example Dropbear with your own key in a custom build), or re-run the installer,
which ends by writing the flash.

---

## 10. Adapting this to a similar model

The method generalises to other ARM NAS boxes with an old U-Boot. The recipe itself is specific to the
NV+ v2.

### 10.1 Known relatives

| Model | SoC | Notes |
|---|---|---|
| ReadyNAS NV+ v2 | 88F6282 Kirkwood | **This guide.** |
| ReadyNAS Duo v2 | 88F6282 Kirkwood | Closest relative: mainline DTS `kirkwood-netgear_readynas_duo-v2.dts`; its U-Boot (`uboot-DUO-1.0.06`) ships in the same RAIDiator ARM zip. Two bays, no port multiplier, different LEDs/GPIOs. Needs verification (10.2) and recipe changes (10.3). |
| ReadyNAS 102/104/2120 | Armada 370/XP | Different SoC (ARMv7, armhf), different bootloader. Not covered. |
| ReadyNAS NV+ v1, Duo v1 | SPARC | Not possible this way. |
| ReadyNAS Ultra/Pro | x86 | Different world (they boot from disk or USB like PCs). |
| Other Kirkwood NAS | 88F628x | The approach applies if steps 10.2.1–10.2.4 check out. |

### 10.2 What to verify, in order (stop at the first "no")

1. **Is there a RAM-only boot path in the stock bootloader?** Extract U-Boot from the vendor firmware and
   search it for boot commands:
   ```sh
   python3 - uboot.bin <<'EOF'
   import re, sys
   d = open(sys.argv[1], 'rb').read()
   for m in re.finditer(rb'[\x20-\x7e]{6,}', d):
       s = m.group()
       if re.search(rb'bootcmd|bootm|fatload|usb start|nand read|mtdparts|nboot|saveenv', s):
           print(hex(m.start()), s.decode())
   EOF
   ```
   You want a USB load command (like `usb start;fatload usb 0:1 …`), the NAND boot command, and `mtdparts`.
   Then confirm by disassembly (for example Capstone) that the trigger (a button) only changes the
   environment in RAM, without `saveenv`.
2. **Load addresses and the copy trap.** Note where the USB and NAND commands load the kernel. If U-Boot
   copies uncompressed kernels to the header's load address, make your uImage XIP at exactly the address it is
   loaded to (section 3.2).
3. **Boot a harmless kernel first.** Before anything that can write, boot a RAM-only diagnostic kernel with
   `CONFIG_BLOCK`, `CONFIG_MTD` and `CONFIG_USB_SUPPORT` disabled (so no driver can touch a disk or flash),
   networking enabled and a tiny status web page in the initramfs. Front-panel LEDs poked from the zImage
   entry code (see `patches/linux/0001-…`) show how far a boot got without a serial console. The NV+ v2 went
   through exactly this: RAM-only image, then a read-only SATA image (disk drivers but no RAID or filesystem
   support), then the installer.
4. **Mainline device tree exists** for the board (`arch/arm/boot/dts/marvell/`), and it describes the flash
   partitions as the bootloader uses them.
5. **Flash compatibility:** with a kernel that has MTD, read the vendor kernel and initrd partitions through
   Linux and check ECC statistics (`/sys/class/mtd/mtdN/ecc_failures`, `corrected_bits`) and the uImage CRCs.
   That is exactly what `nvplus-nand check` does. Zero failures plus valid CRCs means Linux and U-Boot agree.
6. **Bootloader environment:** valid CRC and a stable boot command that loads from fixed flash offsets.
7. **Disks:** how they are attached (port multiplier, multiple ports), and a stable way to select internal
   disks only (sysfs path).
8. **RAM:** 256 MiB works for Debian with care; 128 MiB would need a lighter userland and no Webmin.
9. **MAC address:** where it is stored (sticker, `ethaddr` in the environment), because you must put it in
   the device tree.
10. **Fan, LEDs, buttons, power-off:** check that the device tree describes them and the drivers exist.

### 10.3 What is hard-coded for the NV+ v2

| Item | Where |
|---|---|
| Device tree name `kirkwood-netgear_readynas_nv+_v2` | `configs/nvplus_nas_installer_defconfig`, `post-image-installer.sh` |
| Device-tree patch (MAC, read-only env, LED pinmux) | `patches/linux/0002-…` |
| LED GPIO bits in the zImage entry code | `patches/linux/0001-…` |
| XIP load/entry `0x1200000`/`0x1200040` | `post-image-installer.sh`, `nvplus-nand` |
| Expected boot command and partition names | `nvplus-nand` (`EXPECT_BOOTCMD`, `u-boot`, `uImage`, `minirootfs`, …) |
| Size limits (5 MiB kernel, 12 MiB initrd) | `post-image-*.sh` |
| Exactly four disks; SATA sysfs path `f1080000.sata` | `nas-install`, `overlay-bootrd/init`, `nvplus-monitor` |
| Partition and RAID layout | `nas-install` (step 3/4) |
| LED names `status:blue:*_led`, fan chip `g762` | `S05nvplus-hw`, `nvplus-monitor`, `overlay-bootrd/init`, `nvplus-fan` |
| Kernel version 6.12.115 | defconfig, `post-build-installer.sh`, `nas-install`, `make-usb.sh` |

---

## 11. Reference data

### 11.1 Versions and checksums

| Item | Version | SHA-256 |
|---|---|---|
| Stock firmware zip | RAIDiator-arm-5.3.13 | `afc60847d3f37b39e975b2bcf5cdd6cc69096af1081b2a9ca01906fbbb81d8f8` |
| Buildroot | 2025.02.19 | `e5e58bff1da91f022f60cefdfe280140c08023cd0aeec1e5f6f9da0ea866d69c` |
| Linux | 6.12.115 (longterm) | `0ec90fe4b20422b1b664b77e6d2dde22b40bd41e7eb2cad8ac8739a4749cb1bb` (`linux-6.12.115.tar.xz`) |
| Toolchain | Bootlin armv5-eabi musl stable 2024.05-1 (GCC 13.3) | fetched and checked by Buildroot |
| Debian base rootfs | trixie armel, debuerreotype commit `40e479f8…`, Debian 13.7 | `49eebe9825563c4d645a935992f1602e05bccea6dfe4c79e51c1fda75045c88e` |
| Webmin | 2.670 | `9fdacf6b219a186ec5d7dbbbe0f46e9802cbd7050d91605bd0dfc48e150e47dc` |

Installed package versions on the test unit: systemd 257.13, OpenSSH 10.0p1, Samba 4.22.11, mdadm 4.4,
nfs-kernel-server 2.8.3, smartmontools 7.4, avahi 0.8, wsdd2 1.8.7, unattended-upgrades 2.12; 260 packages,
676 MB used on `/`.

### 11.2 Measurements from the test unit

| Measurement | Value |
|---|---|
| USB boot (diagnostic image): network | 1 Gb/s full duplex; 600 pings, 0 % loss, average 0.19 ms; 400/400 HTTP requests |
| Stock firmware reboot to web UI | about 2.5 min |
| Installer run | about 40 min (31 min of it packages) |
| Debian boot | U-Boot + flash read about 10–15 s; kernel 8.6 s; initrd hands over at 8 s; userspace 66.6 s |
| Memory, idle after tuning | 70–105 MB free of 241 MB; Webmin about 18–24 MB per process |
| Temperatures | disks 23–30 °C, SoC 33–42 °C (fan 30–40 %) |
| RAID5 initial build | 12–17 MB/s per member when idle; 1 MB/s under heavy swapping |
| Flash | 0 bad blocks; 0 ECC failures/corrections reading or writing mtd2/mtd3 |

### 11.3 Example: RAID status during the first build

```
md125 : active raid1 sdb1[0] sde1[3] sdd1[2] sdc1[1]
      8379392 blocks super 1.2 [4/4] [UUUU]
md126 : active raid1 sdb2[0] sde2[3] sdd2[2] sdc2[1]
      1046528 blocks super 1.2 [4/4] [UUUU]
md127 : active raid5 sdb3[0] sde3[4] sdd3[2] sdc3[1]
      2901574656 blocks super 1.2 level 5, 512k chunk, algorithm 2 [4/3] [UUU_]
      [=>...................]  recovery =  5.0% (48830784/967191552) finish=1196.0min speed=12796K/sec
      bitmap: 8/8 pages [32KB], 65536KB chunk
```

(`sda` was the USB stick in this boot. A new RAID5 array is built by "recovering" onto the fourth member;
`[UUU_]` with "recovery" is normal until it completes.)

### 11.4 Kernel configuration highlights

`mvebu_v5_defconfig` plus `board/nvplus-nas/linux-nas.fragment`:

* boot: `ARM_APPENDED_DTB`, `ARM_ATAG_DTB_COMPAT`, `CMDLINE_FORCE` (`console=ttyS0,115200n8 panic=10
  raid=noautodetect loglevel=4`), `KERNEL_XZ`, `KEXEC`
* storage: `SATA_MV`, `SATA_PMP`, md RAID 0/1/10/4/5/6 built in, `MV_XOR` + `ASYNC_TX_DMA`, ext4 built in,
  `MD_AUTODETECT` off (the initrd assembles arrays)
* flash: `MTD_NAND_ORION` with software Hamming ECC (the SmartMedia byte order option off)
* systemd needs: cgroups (incl. BPF), namespaces, seccomp, fanotify, autofs, tmpfs ACL/xattr, `DEVTMPFS_MOUNT`
* board: G762, Kirkwood thermal, RS5C372 RTC, Orion watchdog, GPIO LEDs/keys/power-off, Marvell CESA crypto
* modules (115): NFS server/client, CIFS, nftables/iptables, device mapper, loop, exFAT, NTFS3, XFS, Btrfs,
  FUSE, USB 3.0 (xHCI), UAS, `drivetemp`

---

## 12. What is in this folder

```
README.md                  this guide
LICENSE                    MIT (kernel patches: GPL-2.0, see section 13)
recipe/                    Buildroot external tree + helper scripts (tested; site values are placeholders)
  site.conf.example        your MAC and fallback network settings
  prepare.sh               fills site.conf into a build copy (refuses example values)
  fetch-payload.sh         downloads + verifies the Debian armel rootfs and Webmin
  build.sh                 downloads + verifies Buildroot, builds everything, assembles the stick bundle
  make-usb.sh              assembles the stick bundle (called by build.sh)
  configs/                 nvplus_nas_installer_defconfig (kernel + installer), nvplus_nas_bootrd_defconfig
  board/nvplus-nas/        kernel and BusyBox fragments, post-build/post-image scripts,
    overlay-installer/       installer: init scripts, nas-install, nvplus-monitor, status page
    overlay-bootrd/          flash boot initrd: /init, mdadm.conf
    common/nvplus-nand       flash backup/check/write tool (installer and installed system)
  patches/linux/           0001 LED boot checkpoints, 0002 device tree (MAC, read-only env, LED pinmux)
  debian-overlay/          files placed into Debian (network, fan, LCD/buttons/demo, disabled watchdog, Samba, smartd, README, …)
  stick/                   nas-install.conf, README.txt, hooks/README.txt for the stick
```

The recipe in `recipe/` is the one that built and installed the test unit, byte for byte. The only
differences are the four site values, which became `@UNIT_MAC@`/`@UNIT_MAC_BYTES@`, `@FALLBACK_IP@`,
`@FALLBACK_GW@` and `@FALLBACK_DNS@`, and generic paths in `make-usb.sh`. `prepare.sh` was checked to
reproduce the tested files exactly.

Validation of the published recipe: running `prepare.sh`, `fetch-payload.sh` and `build.sh` exactly as above
in an empty directory (8 minutes on a 16-core PC with a warm download cache) produced the same stick layout,
an identical kernel configuration and device tree blob, byte-identical installer and boot-initrd scripts, the
same 115 modules at that time (before adding the LCD modules) and identical Debian/Webmin payloads. Image sizes differed by a few hundred bytes (build
timestamps).

---

## 13. Credits, sources and licensing

* Mainline Linux support for the NV+ v2 and its hardware notes: Arnaud Ebalard (device tree, 2013;
  natisbad.org).
* Brian Tarricone, "Running a Modern Debian on the Netgear ReadyNAS NV+ v2" (spurint.org, 2020): flash layout
  and the stock kernel's limits; it left USB booting as an open question, which this guide answers.
* Debian (armel port, container base images via debuerreotype), Buildroot, Bootlin toolchains, Webmin, Samba.
* NETGEAR's RAIDiator 5.3.13 firmware was only downloaded from NETGEAR and analysed; nothing from it is
  redistributed here.

### Licence

* This guide and the recipe (scripts, configuration, Buildroot tree) are released under the
  [MIT licence](LICENSE).
* **Exception:** the kernel patches in `recipe/patches/linux/` modify the Linux kernel and are therefore
  licensed under **GPL-2.0-only**, like the kernel itself (see
  [`recipe/patches/linux/LICENSE`](recipe/patches/linux/LICENSE)).
* Everything the build downloads (Linux, Buildroot, BusyBox, Debian, Webmin, …) keeps its own licence.
  Nothing from NETGEAR's firmware is included in this repository.

### Trademarks and warranty

NETGEAR and ReadyNAS are trademarks of NETGEAR, Inc. This project is independent and not affiliated with or
endorsed by NETGEAR. It replaces the vendor firmware, writes to the device's flash memory and erases all
disks. It is an experimental hobby project and may brick your device. There is no warranty for anything in
it: the information, files and results are provided "as is" (see the licence), with no guarantee of
correctness, fitness for any purpose, support or updates, and the author accepts no responsibility or
liability for any damage, data loss or other consequence of its use. Verify everything yourself first, and
keep your data backed up.

### Feedback and other units

Tried it on your NV+ v2, or adapted it to a Duo v2 or another Kirkwood box? Please open an issue with the
model, the stock firmware and U-Boot versions, and the installer log (`nas-install/logs/` on the stick;
remove anything private first). Failed runs are as useful as successful ones: section 10 lists what has to be
verified for each new model.
