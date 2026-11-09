import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).with_name("TransparentOverlayV1.pyw")
spec = importlib.util.spec_from_file_location("overlay", APP_PATH)
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)


class WindowStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "window_config.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_uses_defaults(self):
        self.assertEqual(overlay.read_window_state(self.path, 1920, 1080),
                         (100, 100, 480, 270, 0.9))

    def test_offscreen_tiny_and_transparent_values_are_clamped(self):
        self.assertEqual(overlay.clamp_window_state(-500, 999999, 50, 40, 5, 1920, 1080),
                         (0, 980, 100, 100, 1.0))
        self.assertEqual(overlay.clamp_window_state(0, 0, 200, 200, 0, 1920, 1080)[4], 0.1)

    def test_corrupt_file_uses_defaults(self):
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(overlay.read_window_state(self.path, 1920, 1080),
                         (100, 100, 480, 270, 0.9))

    def test_wrong_types_use_defaults(self):
        self.path.write_text(json.dumps({"x": "far", "width": None}), encoding="utf-8")
        self.assertEqual(overlay.read_window_state(self.path, 1920, 1080),
                         (100, 100, 480, 270, 0.9))

    def test_write_then_read_round_trip(self):
        overlay.write_window_state(self.path, 30, 500, 300, 200, 0.25)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")),
                         {"x": 30, "y": 500, "width": 300, "height": 200, "alpha": 0.25})
        self.assertEqual(overlay.read_window_state(self.path, 1920, 1080),
                         (30, 500, 300, 200, 0.25))

    def test_wheel_step_clamps_and_rounds(self):
        self.assertEqual(overlay.step_alpha(0.9, 0.05), 0.95)
        self.assertEqual(overlay.step_alpha(0.1, -0.05), 0.1)
        self.assertEqual(overlay.step_alpha(1.0, 0.05), 1.0)

    def test_ui_scale_for_common_resolutions(self):
        self.assertAlmostEqual(overlay.compute_ui_scale(1080, 96), 1.0)
        self.assertAlmostEqual(overlay.compute_ui_scale(1440, 96), 4 / 3)
        self.assertAlmostEqual(overlay.compute_ui_scale(2160, 96), 2.0)
        # 系统缩放更高时取较大值：4K@150% 按分辨率，1080p@150% 按 DPI
        self.assertAlmostEqual(overlay.compute_ui_scale(2160, 144), 2.0)
        self.assertAlmostEqual(overlay.compute_ui_scale(1080, 144), 1.5)
        # 小屏不缩小
        self.assertAlmostEqual(overlay.compute_ui_scale(768, 96), 1.0)


if __name__ == "__main__":
    unittest.main()
