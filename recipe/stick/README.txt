ReadyNAS NV+ v2 -> Debian 13 (armel) + Webmin: installer stick
==============================================================
Stick: USB 2.0, MBR, first partition FAT32. Copy everything from this bundle to the root of the stick:
  uImage-recovery        NAS kernel (Linux 6.12.115); also what gets written to NAND
  initrd-recovery.gz     installer / rescue system (runs in RAM)
  nas-install/           settings, payload, your hooks, and (after a run) logs/ and backup/

Before booting:
  1. Read nas-install/nas-install.conf (WIPE_ALL_FOUR_DISKS=yes erases all four disks).
  2. Put your own hook script(s) in nas-install/hooks/ (see hooks/README.txt). At least one is required.

Run: shut the NAS down, stick in the FRONT USB port, hold Backup, press Power, keep holding Backup until
the Backup LED blinks (about 10 s), release. Progress: http://<NAS address>/ (the address your router gives it).
LEDs: Disk1 heartbeat = installer running, Disk2 on = network up, Disk3 blinking = installing,
all four on = writing NAND, then it reboots into Debian. Disk4 blinking = stopped with an error
(the reason is on the status page and in nas-install/logs/ on the stick; it never reboots on error).
Takes about 45-75 minutes. Afterwards: SSH on port 22, Webmin on https://<NAS address>:10000.
