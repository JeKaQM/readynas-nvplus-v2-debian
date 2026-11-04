"""Recipe integration checks using tiny synthetic payloads, not real flash images."""
from pathlib import Path
import os
import io
import re
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / 'recipe'
SCRATCH = ROOT / '.test-tmp'


class RecipeTests(unittest.TestCase):
    def test_watchdog_remains_off(self):
        s = (RECIPE / 'debian-overlay/etc/systemd/system.conf.d/nas-watchdog.conf').read_text()
        self.assertRegex(s, r'(?m)^RuntimeWatchdogSec=off$')
        self.assertRegex(s, r'(?m)^RebootWatchdogSec=off$')
        self.assertRegex(s, r'(?m)^KExecWatchdogSec=off$')

    def test_logind_cannot_act_on_wake_press(self):
        s = (RECIPE / 'debian-overlay/etc/systemd/logind.conf.d/nvplus-buttons.conf').read_text()
        for key in ('HandlePowerKey', 'HandlePowerKeyLongPress', 'HandleRebootKey', 'HandleRebootKeyLongPress'):
            self.assertIn(key + '=ignore', s.splitlines())

    def test_kernel_lcd_modules_and_autoload(self):
        s = (RECIPE / 'board/nvplus-nas/linux-nas.fragment').read_text()
        for line in ('CONFIG_AUXDISPLAY=y', 'CONFIG_HD44780=m', 'CONFIG_CHARLCD_BL_ON=y'):
            self.assertIn(line, s.splitlines())
        self.assertIn('hd44780', (RECIPE / 'debian-overlay/etc/modules-load.d/nvplus.conf').read_text().splitlines())

    def test_installer_dependencies_enablement_and_module_checks(self):
        s = (RECIPE / 'board/nvplus-nas/overlay-installer/usr/sbin/nas-install').read_text()
        pkgs = re.search(r'PKGS="([^"]+)"', s).group(1).split()
        self.assertIn('python3', pkgs)
        self.assertIn('util-linux', pkgs)
        self.assertIn('nvplus-lcd', re.search(r'SERVICES="([^"]+)"', s).group(1).split())
        for mod in ('hd44780', 'hd44780_common', 'charlcd'):
            self.assertIn('ok ch modinfo -k $KVER ' + mod, s)
        self.assertIn('ok test -x $T/usr/local/bin/lcd-show', s)

    def test_installer_does_not_auto_arm_watchdog(self):
        s = (RECIPE / 'board/nvplus-nas/post-build-installer.sh').read_text()
        self.assertNotIn("|| echo '::respawn:/sbin/watchdog", s)
        self.assertIn("sed -i '\\|^::respawn:/sbin/watchdog", s)

    def test_cached_module_archive_and_generated_config_are_checked(self):
        s = (RECIPE / 'board/nvplus-nas/post-build-installer.sh').read_text()
        self.assertIn('for m in hd44780 hd44780_common charlcd', s)
        s = (RECIPE / 'build.sh').read_text()
        for option in ('CONFIG_HD44780=m', 'CONFIG_HD44780_COMMON=m', 'CONFIG_CHARLCD=m'):
            self.assertIn(option, s)

    def test_post_build_checks_archive_and_preserves_other_inittab_entries(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='nas-postbuild-test-', dir=SCRATCH) as temp:
            t = Path(temp)
            target, images = t / 'target', t / 'images'
            images.mkdir()
            names = ('etc/init.d/S05nvplus-hw', 'etc/init.d/S40network', 'etc/init.d/S45nvplus-stick',
                     'etc/init.d/S60nvplus-status', 'etc/init.d/S90nas-install', 'usr/sbin/nas-install',
                     'usr/sbin/nvplus-monitor', 'www/cgi-bin/poweroff')
            for name in names:
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('#!/bin/sh\n')
            inittab = target / 'etc/inittab'
            legacy = '::respawn:/sbin/watchdog -F -t 5 -T 20 /dev/watchdog\n'
            unrelated = 'ttyS0::respawn:/sbin/getty ttyS0 115200\n'
            inittab.write_text(legacy + unrelated)
            archive = images / 'modules-6.12.115.tar.gz'
            def write_archive(modules):
                with tarfile.open(archive, 'w:gz') as tar:
                    for mod in modules:
                        entry = tarfile.TarInfo('6.12.115/kernel/drivers/auxdisplay/' + mod + '.ko')
                        data = b'SYNTHETIC MODULE FIXTURE - NOT LOADABLE\n'
                        entry.size = len(data)
                        tar.addfile(entry, io.BytesIO(data))
            env = dict(os.environ, BR2_EXTERNAL_NVPLUS_NAS_PATH=str(RECIPE), BINARIES_DIR=str(images))
            cmd = ['sh', str(RECIPE / 'board/nvplus-nas/post-build-installer.sh'), str(target)]
            write_archive(('hd44780', 'hd44780_common', 'charlcd'))
            result = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(inittab.read_text(), unrelated)
            self.assertTrue((target / 'usr/sbin/nvplus-nand').exists())
            write_archive(('hd44780', 'charlcd'))
            result = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('lacks hd44780_common', result.stdout)
            self.assertEqual(inittab.read_text(), unrelated)

    def test_bundle_keeps_programs_executable_and_configs_readonly(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='nas-bundle-test-', dir=SCRATCH) as temp:
            t = Path(temp)
            b, dl, u = t / 'build', t / 'payload', t / 'usb'
            inst, rd = b / 'out-nas-inst/images', b / 'out-nas-rd/images'
            for p in (inst, rd, dl):
                p.mkdir(parents=True)
            for p in (inst / 'uImage-nas', inst / 'uInitrd-installer', inst / 'modules-6.12.115.tar.gz',
                      rd / 'uInitrd-nas', dl / 'debian-trixie-armel-rootfs.tar.gz', dl / 'webmin_2.670_all.deb'):
                p.write_bytes(b'SYNTHETIC TEST FIXTURE - NOT BOOTABLE\n')
            env = dict(os.environ, TMPDIR=str(t))
            result = subprocess.run(['sh', str(RECIPE / 'make-usb.sh'), str(b), str(dl), str(u)],
                                    env=env, text=True, capture_output=True, timeout=20)
            if result.returncode and 'cp: cannot create directory' in result.stderr and 'Operation not permitted' in result.stderr:
                self.skipTest('Filesystem policy prevents cp -a directory creation; run bundle smoke test on the build host')
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = u / 'nas-install/payload'
            subprocess.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=payload, check=True, capture_output=True)
            with tarfile.open(payload / 'nas-overlay.tar.gz') as tar:
                for name in ('usr/local/sbin/nvplus-lcd', 'usr/local/bin/lcd-show'):
                    member = tar.getmember('./' + name)
                    self.assertEqual(member.mode, 0o755, name)
                    self.assertEqual((member.uid, member.gid), (0, 0))
                    self.assertEqual(tar.extractfile(member).read(), (RECIPE / 'debian-overlay' / name).read_bytes())
                self.assertEqual(tar.getmember('./etc/systemd/system/nvplus-lcd.service').mode, 0o644)
                watchdog = tar.extractfile('./etc/systemd/system.conf.d/nas-watchdog.conf').read()
                self.assertIn(b'RuntimeWatchdogSec=off', watchdog)


if __name__ == '__main__':
    unittest.main()
