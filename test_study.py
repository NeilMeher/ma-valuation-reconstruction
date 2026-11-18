import csv
import json
import unittest

from study import ROOT, cross_deal_report, endpoints, read, valuation


class DCFTests(unittest.TestCase):
    def setUp(self):
        self.a = read("inputs.csv")["A"]

    def test_higher_wacc_reduces_value(self):
        self.assertGreater(valuation(self.a, .105, .04)["price"],
                           valuation(self.a, .125, .04)["price"])

    def test_higher_growth_raises_value(self):
        self.assertLess(valuation(self.a, .115, .03)["price"],
                        valuation(self.a, .115, .05)["price"])

    def test_invalid_growth_and_multiple(self):
        with self.assertRaises(ValueError):
            valuation(self.a, .115, .115)
        with self.assertRaises(ValueError):
            valuation(self.a, .115, -1, "multiple")

    def test_disclosed_bridge_and_terminal_timing(self):
        bridge = valuation(self.a, .115, .04)
        self.assertAlmostEqual(bridge["terminal_value"], 1844.2666666667)
        self.assertAlmostEqual(bridge["terminal_pv"] / bridge["terminal_value"], .613, places=3)
        self.assertAlmostEqual(bridge["equity"] - bridge["enterprise"], -64)
        self.assertLess(abs(bridge["price"] - 15.28), .06)
        multiple = valuation(self.a, .115, 6.0, "multiple")
        self.assertAlmostEqual(multiple["terminal_pv"] / multiple["terminal_value"], .580, places=3)

    def test_stub_and_midyear_scenarios_change_discount_timing(self):
        self.assertNotEqual(endpoints(self.a, "growth"), endpoints(self.a, "growth", stub=.75))
        self.assertGreater(endpoints(self.a, "growth")[0],
                           endpoints(self.a, "growth", midyear=False)[0])

    def test_cross_deal_reconstruction_and_partial_disclosure(self):
        inputs = json.loads((ROOT / "cross_inputs.json").read_text(encoding="utf-8"))
        with (ROOT / "cross_checks.csv").open(newline="", encoding="utf-8") as file:
            report = cross_deal_report(inputs, csv.DictReader(file))
        self.assertLess(max(map(abs, report["Startek"]["gaps"])), .02)
        self.assertGreater(report["Sykes"]["gaps"][1], 2)
        self.assertNotIn("gaps", report["Thoughtworks"])
        self.assertEqual(report["CTG"]["terminal_enterprise_value_usd_m"], [164.71, 190.05])
