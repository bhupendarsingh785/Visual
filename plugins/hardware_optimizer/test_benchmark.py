import unittest
from benchmark import benchmark_torch_callable


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_reports_latency(self):
        result = benchmark_torch_callable(lambda: sum(range(10)), warmup=1, iterations=5)
        self.assertEqual(result["iterations"], 5)
        self.assertGreaterEqual(result["median_latency_ms"], 0)
        self.assertGreater(result["throughput_per_second"], 0)

    def test_limits_are_bounded(self):
        with self.assertRaises(ValueError):
            benchmark_torch_callable(lambda: None, iterations=0)
        with self.assertRaises(ValueError):
            benchmark_torch_callable(lambda: None, iterations=10001)


if __name__ == "__main__":
    unittest.main()
