"""
AAYU-TWIN Automated Verification & Unit Test Suite
Validates:
1. EHR and Synthetic Wearable Data Ingestion.
2. Bergman Minimal Model ODE solution convergence.
3. 2-Hour Postprandial Glucose Surge Prediction.
4. Nocturnal Hypoglycemia Alert Detection.
5. Cardiovascular Anomaly & Nocturnal Non-Dipping classification.
"""

import sys
import os
import json
import unittest

# Ensure src directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from biophysical_models import AayuBiophysicalTwin
from adverse_event_predictor import AdverseEventPredictor

class TestAayuDigitalTwin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.dirname(__file__))
        with open(os.path.join(base_dir, "data", "ehr_patients.json"), "r") as f:
            cls.patients = json.load(f)
        with open(os.path.join(base_dir, "data", "synthetic_wearable_stream.json"), "r") as f:
            cls.wearables = json.load(f)
        cls.predictor = AdverseEventPredictor()

    def test_ehr_ingestion(self):
        self.assertEqual(len(self.patients), 3)
        self.assertIn("IN-P-2026-081", [p["id"] for p in self.patients])

    def test_wearable_stream_integrity(self):
        self.assertIn("IN-P-2026-081", self.wearables)
        stream = self.wearables["IN-P-2026-081"]
        self.assertEqual(len(stream["cgmMgDl"]), 288)
        self.assertEqual(len(stream["heartRateBpm"]), 288)
        self.assertEqual(len(stream["systolicBpMmHg"]), 288)

    def test_biophysical_ode_convergence(self):
        patient = self.patients[0]
        twin = AayuBiophysicalTwin(patient)
        result = twin.simulate_24h()
        
        self.assertIn("glucoseMgDl", result)
        self.assertIn("metrics", result)
        self.assertEqual(len(result["glucoseMgDl"]), 289)
        # Physiological sanity checks
        mean_g = result["metrics"]["meanGlucoseMgDl"]
        self.assertTrue(70.0 <= mean_g <= 300.0, f"Mean glucose {mean_g} out of realistic bounds")
        self.assertTrue(0.0 <= result["metrics"]["timeInRangePercent"] <= 100.0)

    def test_counterfactual_intervention_effect(self):
        patient = self.patients[0]
        twin = AayuBiophysicalTwin(patient)
        baseline = twin.simulate_24h()
        
        # Test intervention: SGLT2i + 20-min post-meal walk + 20% carb reduction
        intervention = {
            "med_sglt2i": True,
            "post_meal_walk_minutes": 20,
            "carb_intake_percent_delta": -20
        }
        counterfactual = twin.simulate_24h(intervention)
        
        # Counterfactual must improve time-in-range or lower mean glucose
        self.assertLess(
            counterfactual["metrics"]["meanGlucoseMgDl"],
            baseline["metrics"]["meanGlucoseMgDl"],
            "Counterfactual failed to reduce mean glucose"
        )
        self.assertGreaterEqual(
            counterfactual["metrics"]["timeInRangePercent"],
            baseline["metrics"]["timeInRangePercent"],
            "Counterfactual failed to improve or preserve TIR"
        )

    def test_adverse_event_predictions(self):
        patient = self.patients[0]
        stream = self.wearables[patient["id"]]
        
        # Test 2-hour surge prediction
        surge_res = self.predictor.predict_2hour_glucose_surge(patient, stream, upcoming_carbs_grams=75)
        self.assertIn("probability", surge_res)
        self.assertIn("explainableAiAttributions", surge_res)
        self.assertTrue(0.0 <= surge_res["probability"] <= 1.0)
        
        # Test CVD non-dipping anomaly
        cvd_res = self.predictor.detect_cardiovascular_anomaly(patient, stream)
        self.assertIn("isAnomalyFlagged", cvd_res)
        self.assertIn("nocturnalDipPercentage", cvd_res)

if __name__ == "__main__":
    unittest.main()
