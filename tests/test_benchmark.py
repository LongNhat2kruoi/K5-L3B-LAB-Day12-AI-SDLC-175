"""Benchmark: công thức số liệu (không cần cửa sổ), smoke có cửa sổ (BENCH_GUI=1), thiếu pyxel."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import ROOT
from chonoi.benchmark import compute_metrics

KEYS = {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"}


class ComputeMetricsTest(unittest.TestCase):
    def test_under_100_frames_uses_single_slowest(self):
        r = compute_metrics([0.01] * 49 + [0.05], 1234.5)
        self.assertEqual(r["frames"], 50)
        self.assertAlmostEqual(r["measured_s"], 0.54)
        self.assertAlmostEqual(r["avg_fps"], 50 / 0.54, places=2)
        self.assertAlmostEqual(r["p1_low_fps"], 20.0)
        self.assertEqual(r["load_ms"], 1234.5)

    def test_250_frames_uses_three_slowest(self):
        times = [0.01] * 247 + [0.04, 0.03, 0.02]
        r = compute_metrics(times, 10)
        self.assertEqual(r["frames"], 250)
        self.assertAlmostEqual(r["p1_low_fps"], 1 / 0.03, places=2)  # mean(0.04,0.03,0.02)
        self.assertAlmostEqual(r["avg_fps"], 250 / 2.56, places=2)
        self.assertEqual(set(r), KEYS)

    def test_exactly_100_frames_uses_one(self):
        r = compute_metrics([0.02] * 99 + [0.1], 0)
        self.assertAlmostEqual(r["p1_low_fps"], 10.0)


class BenchmarkCommandTest(unittest.TestCase):
    def run_bench(self, args, extra_code=None):
        env = dict(os.environ, PYTHONPATH=ROOT)
        if extra_code:
            cmd = [sys.executable, "-c", extra_code] + args
        else:
            cmd = [sys.executable, "-m", "chonoi.benchmark"] + args
        return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)

    @unittest.skipUnless(importlib.util.find_spec("pyxel") and os.environ.get("BENCH_GUI") == "1",
                         "cần pyxel và BENCH_GUI=1 (mở cửa sổ thật)")
    def test_real_window_smoke(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "bench.json")
            r = self.run_bench(["--seed", "42", "--duration", "1", "--warmup", "0.5", "--out", out])
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
        self.assertEqual(set(data), KEYS)
        self.assertIsInstance(data["frames"], int)
        for k in KEYS - {"frames"}:
            self.assertIsInstance(data[k], (int, float))
        self.assertGreater(data["frames"], 0)
        self.assertGreaterEqual(data["measured_s"], 1)

    def test_missing_pyxel_exits_1_without_output(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "bench.json")
            code = "import sys; sys.modules['pyxel']=None; from chonoi.benchmark import main; raise SystemExit(main(sys.argv[1:]))"
            r = self.run_bench(["--seed", "42", "--duration", "1", "--out", out], code)
            self.assertEqual(r.returncode, 1)
            self.assertIn("Pyxel", r.stderr)
            self.assertFalse(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
