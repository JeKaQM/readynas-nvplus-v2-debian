"""No GPIO, LCD, systemctl or shutdown writes: all hardware/process calls are mocked."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'recipe/debian-overlay/usr/local/sbin/nvplus-lcd'
loader = importlib.machinery.SourceFileLoader('nvplus_panel', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
panel = importlib.util.module_from_spec(spec)
loader.exec_module(panel)


class FakeLcd:
    def __init__(self):
        self.backlight = True
        self.ready = True
        self.calls = []

    def show(self, *lines):
        self.calls.append(('show', *lines))

    def set_backlight(self, on):
        self.backlight = on
        self.calls.append(('light', on))


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.exists = patch.object(panel.os.path, 'exists', return_value=False).start()
        patch.object(panel.time, 'monotonic', return_value=0.0).start()
        self.popen = patch.object(panel.subprocess, 'Popen').start()
        patch.object(panel, 'run', return_value='').start()
        patch.object(panel, 'log').start()
        self.addCleanup(patch.stopall)
        self.p = panel.Panel()
        self.p.lcd = FakeLcd()
        self.p.net = Mock()
        self.p.check_alerts = Mock()
        self.p.update_leds = Mock()
        self.p.current = Mock(return_value=('Status', 'OK'))

    def tick(self, now):
        self.p.tick(now, force=True)

    def test_default_timeout_is_ten_minutes(self):
        self.assertEqual(panel.IDLE_SECONDS, 600)

    def test_no_sleep_before_boundary(self):
        self.tick(599.99)
        self.assertTrue(self.p.lcd.backlight)

    def test_sleep_at_boundary_blanks_both_rows_and_backlight(self):
        self.tick(600)
        self.assertEqual(self.p.lcd.calls, [('show', '', ''), ('light', False)])

    def test_automatic_page_updates_do_not_reset_idle(self):
        for now in range(1, 601):
            self.tick(now)
        self.assertFalse(self.p.lcd.backlight)
        self.assertEqual(self.p.last_activity, 0)

    def test_no_repeated_lcd_writes_while_asleep(self):
        self.tick(600)
        self.p.lcd.calls.clear()
        self.tick(601)
        self.tick(1200)
        self.assertEqual(self.p.lcd.calls, [])

    def test_monitoring_and_led_updates_continue_asleep(self):
        self.tick(600)
        self.p.tick(601)
        self.p.check_alerts.assert_called_once()
        self.p.update_leds.assert_called_once()
        self.assertFalse(self.p.lcd.backlight)

    def test_warning_does_not_wake_or_extend_timer(self):
        self.p.alerts = ['Data DEGRADED']
        self.tick(600)
        self.assertFalse(self.p.lcd.backlight)
        self.assertEqual(self.p.last_activity, 0)

    def test_each_button_wakes_without_short_press_action(self):
        for code in panel.HOLD:
            with self.subTest(code=code):
                self.p.sleep_display('test')
                before = self.p.idx
                self.p.on_key(code, 1, 700)
                self.assertTrue(self.p.lcd.backlight)
                self.p.on_key(code, 0, 700.1)
                self.assertEqual(self.p.idx, before)
                self.assertIsNone(self.p.message)
                self.assertFalse(self.p.final)
        self.popen.assert_not_called()

    def test_long_wake_press_never_shuts_down_reboots_or_sleeps_again(self):
        for code in panel.HOLD:
            with self.subTest(code=code):
                self.p.sleep_display('test')
                self.p.on_key(code, 1, 700)
                self.p.check_holds(720)
                self.p.on_key(code, 0, 721)
                self.assertTrue(self.p.lcd.backlight)
                self.assertFalse(self.p.final)
                self.assertFalse(self.p.countdown)
        self.popen.assert_not_called()

    def test_release_starts_fresh_ten_minutes_after_wake(self):
        self.tick(600)
        self.p.on_key(panel.KEY_POWER, 1, 700)
        self.p.on_key(panel.KEY_POWER, 0, 701)
        self.tick(1300.99)
        self.assertTrue(self.p.lcd.backlight)
        self.tick(1301)
        self.assertFalse(self.p.lcd.backlight)

    def test_next_backup_tap_after_wake_advances(self):
        self.tick(600)
        for now in (700, 701):
            self.p.on_key(panel.KEY_COPY, 1, now)
            self.p.on_key(panel.KEY_COPY, 0, now + .1)
        self.assertEqual(self.p.idx, 1)
        self.assertAlmostEqual(self.p.hold_until, 731.1)

    def test_short_power_press_awake_only_shows_hint(self):
        self.p.on_key(panel.KEY_POWER, 1, 10)
        self.p.on_key(panel.KEY_POWER, 0, 10.1)
        self.assertEqual(self.p.message[0], 'Hold Power 2s')
        self.popen.assert_not_called()

    def test_reset_tap_awake_shows_network(self):
        self.p.on_key(panel.KEY_RESTART, 1, 10)
        self.p.on_key(panel.KEY_RESTART, 0, 10.1)
        self.assertEqual(self.p.sequence()[self.p.idx], ('page', panel.page_network))
        self.popen.assert_not_called()

    def test_explicit_second_power_hold_still_works_once(self):
        self.tick(600)
        self.p.on_key(panel.KEY_POWER, 1, 700)
        self.p.on_key(panel.KEY_POWER, 0, 700.1)
        self.p.on_key(panel.KEY_POWER, 1, 701)
        self.p.check_holds(703)
        self.p.check_holds(704)
        self.popen.assert_called_once_with(['systemctl', 'poweroff'])

    def test_awake_reset_hold_works_once(self):
        self.p.on_key(panel.KEY_RESTART, 1, 10)
        self.p.check_holds(15)
        self.p.check_holds(16)
        self.popen.assert_called_once_with(['systemctl', 'reboot'])

    def test_shortened_hold_cancels(self):
        for code in (panel.KEY_POWER, panel.KEY_RESTART):
            self.p.on_key(code, 1, 10)
            self.p.check_holds(10.6)
            self.assertTrue(self.p.countdown)
            self.p.on_key(code, 0, 10.8)
            self.assertFalse(self.p.countdown)
            self.assertEqual(self.p.message[0], 'Cancelled')
        self.popen.assert_not_called()

    def test_countdown_is_not_blanked_at_old_deadline(self):
        self.p.on_key(panel.KEY_RESTART, 1, 599)
        self.p.check_holds(600)
        self.tick(600)
        self.assertTrue(self.p.lcd.backlight)
        self.popen.assert_not_called()

    def test_backup_hold_sleeps_then_any_press_wakes(self):
        self.p.on_key(panel.KEY_COPY, 1, 10)
        self.p.check_holds(12)
        self.assertFalse(self.p.lcd.backlight)
        self.p.on_key(panel.KEY_COPY, 0, 12.1)
        self.tick(13)
        self.assertFalse(self.p.lcd.backlight)
        self.p.on_key(panel.KEY_COPY, 1, 14)
        self.assertTrue(self.p.lcd.backlight)

    def test_repeat_or_duplicate_keydown_cannot_rearm_wake_press(self):
        self.tick(600)
        self.p.on_key(panel.KEY_POWER, 1, 700)
        self.p.on_key(panel.KEY_POWER, 2, 701)
        self.p.on_key(panel.KEY_POWER, 1, 702)
        self.p.check_holds(720)
        self.popen.assert_not_called()

    def test_unknown_key_and_unmatched_release_do_not_extend_timer(self):
        self.p.on_key(999, 1, 599)
        self.p.on_key(panel.KEY_POWER, 0, 599)
        self.tick(600)
        self.assertFalse(self.p.lcd.backlight)

    def test_demo_blocks_panel_lcd_writes(self):
        self.exists.return_value = True
        self.tick(700)
        self.assertEqual(self.p.lcd.calls, [])
        self.assertTrue(self.p.paused)

    def test_demo_resume_restores_glyphs_and_idle_timer(self):
        self.tick(600)
        self.exists.return_value = True
        self.tick(700)
        self.exists.return_value = False
        self.tick(800)
        self.assertTrue(self.p.lcd.backlight)
        self.assertFalse(self.p.lcd.ready)
        self.assertEqual(self.p.last_activity, 800)
        self.tick(1399.99)
        self.assertTrue(self.p.lcd.backlight)
        self.tick(1400)
        self.assertFalse(self.p.lcd.backlight)

    def test_demo_press_is_consumed_after_resume(self):
        self.exists.return_value = True
        self.p.on_key(panel.KEY_POWER, 1, 10)
        self.p.check_holds(30)
        self.exists.return_value = False
        self.p.check_holds(31)
        self.p.on_key(panel.KEY_POWER, 0, 32)
        self.popen.assert_not_called()

    def test_demo_start_during_hold_cancels_deferred_action(self):
        self.p.on_key(panel.KEY_RESTART, 1, 10)
        self.exists.return_value = True
        self.p.check_holds(20)
        self.exists.return_value = False
        self.p.check_holds(30)
        self.popen.assert_not_called()

    def test_final_action_not_overwritten_by_idle(self):
        self.p.hold_action(panel.KEY_POWER)
        self.p.lcd.calls.clear()
        self.tick(1000)
        self.assertEqual(self.p.lcd.calls, [])

    def test_simultaneous_destructive_holds_only_issue_one_action(self):
        self.p.on_key(panel.KEY_POWER, 1, 10)
        self.p.on_key(panel.KEY_RESTART, 1, 10)
        self.p.check_holds(20)
        self.assertEqual(self.popen.call_count, 1)


if __name__ == '__main__':
    unittest.main()
