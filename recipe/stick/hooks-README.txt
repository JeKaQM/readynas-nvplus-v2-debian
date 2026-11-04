Owner hooks
===========
Put your own script(s) here, named *.sh. They are required: the installer refuses to start without one.

When:   after Debian 13 and all packages are installed and configured, before the final checks,
        the NAND write and the reboot. Several hooks run in name order.
How:    busybox sh (POSIX shell) in the installer, as root, with TARGET=/target = the new root
        filesystem, mounted, with /proc, /sys and /dev available, so "chroot "$TARGET" <command>"
        runs a command inside the new system. Windows line endings are removed before running.
Output: goes to the install log, which is shown on the status page and saved to nas-install/logs/
        on the stick. Do not print secrets.
Result: exit status 0 = continue; anything else stops the install (nothing is written to NAND).
