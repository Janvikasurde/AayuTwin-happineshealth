"""
AAYU-TWIN Local REST Server & Simulation API (Unified Single-Folder)
====================================================================
Lightweight, zero-dependency Python HTTP server serving the executive
Digital Twin Dashboard UI and the REST API for real-time multi-modal
biophysical ODE simulations and 2-hour adverse event predictions.
"""

import os
import sys
import json
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Ensure src in path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from biophysical_models import AayuBiophysicalTwin
from adverse_event_predictor import AdverseEventPredictor

DATA_DIR = os.path.join(BASE_DIR, "data")

# Load datasets
with open(os.path.join(DATA_DIR, "ehr_patients.json"), "r") as f:
    EHR_PATIENTS = json.load(f)

with open(os.path.join(DATA_DIR, "synthetic_wearable_stream.json"), "r") as f:
    WEARABLE_STREAMS = json.load(f)

with open(os.path.join(DATA_DIR, "fhir_abdm_bundle.json"), "r") as f:
    FHIR_BUNDLE = json.load(f)

PREDICTOR = AdverseEventPredictor()

class AayuTwinHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # REST API Endpoints
        if path == "/api/patients":
            self._send_json(EHR_PATIENTS)
            return
            
        elif path.startswith("/api/patient/"):
            patient_id = path.split("/api/patient/")[1]
            patient = next((p for p in EHR_PATIENTS if p["id"] == patient_id), None)
            if patient:
                self._send_json(patient)
            else:
                self._send_json({"error": "Patient not found"}, 404)
            return

        elif path.startswith("/api/stream/"):
            patient_id = path.split("/api/stream/")[1]
            stream = WEARABLE_STREAMS.get(patient_id)
            if stream:
                self._send_json(stream)
            else:
                self._send_json({"error": "Stream not found"}, 404)
            return

        elif path.startswith("/api/adverse-events/"):
            patient_id = path.split("/api/adverse-events/")[1]
            patient = next((p for p in EHR_PATIENTS if p["id"] == patient_id), EHR_PATIENTS[0])
            stream = WEARABLE_STREAMS.get(patient_id, WEARABLE_STREAMS[EHR_PATIENTS[0]["id"]])
            
            surge_res = PREDICTOR.predict_2hour_glucose_surge(patient, stream, upcoming_carbs_grams=70)
            hypo_res = PREDICTOR.predict_nocturnal_hypoglycemia(patient, stream)
            cvd_res = PREDICTOR.detect_cardiovascular_anomaly(patient, stream)
            
            self._send_json({
                "patientId": patient_id,
                "timestamp": "2026-10-23T18:30:00Z",
                "twoHourGlucoseSurge": surge_res,
                "nocturnalHypoglycemia": hypo_res,
                "cardiovascularAnomaly": cvd_res
            })
            return

        elif path == "/api/fhir" or path.startswith("/api/fhir/"):
            self._send_json(FHIR_BUNDLE)
            return

        # Static File Serving directly from BASE_DIR
        clean_path = path.lstrip("/")
        if not clean_path or clean_path == "":
            clean_path = "index.html"

        file_path = os.path.join(BASE_DIR, clean_path)

        if os.path.isfile(file_path):
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or "application/octet-stream"
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error reading file: {e}".encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/simulate":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body) if body else {}

                patient_id = payload.get("patientId", EHR_PATIENTS[0]["id"])
                patient = next((p for p in EHR_PATIENTS if p["id"] == patient_id), EHR_PATIENTS[0])
                intervention = payload.get("intervention", {})

                twin = AayuBiophysicalTwin(patient)
                baseline_sim = twin.simulate_24h()
                counterfactual_sim = twin.simulate_24h(intervention)

                self._send_json({
                    "patientId": patient_id,
                    "baseline": baseline_sim,
                    "counterfactual": counterfactual_sim,
                    "deltas": {
                        "meanGlucoseDeltaMgDl": round(counterfactual_sim["metrics"]["meanGlucoseMgDl"] - baseline_sim["metrics"]["meanGlucoseMgDl"], 1),
                        "timeInRangeGainPercent": round(counterfactual_sim["metrics"]["timeInRangePercent"] - baseline_sim["metrics"]["timeInRangePercent"], 1),
                        "estimatedA1cDelta": round(counterfactual_sim["metrics"]["estimatedA1c"] - baseline_sim["metrics"]["estimatedA1c"], 2),
                        "systolicBpReductionMmHg": round(baseline_sim["metrics"]["systolicBpMmHg"] - counterfactual_sim["metrics"]["systolicBpMmHg"], 1),
                        "cvdRisk10YearReduction": round(baseline_sim["metrics"]["cvdRisk10YearPercent"] - counterfactual_sim["metrics"]["cvdRisk10YearPercent"], 1),
                        "betaCellStressReductionPercent": round((baseline_sim["metrics"]["betaCellStressIndex"] - counterfactual_sim["metrics"]["betaCellStressIndex"]) / max(0.01, baseline_sim["metrics"]["betaCellStressIndex"]) * 100.0, 1)
                    }
                })
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        self.send_response(404)
        self.end_headers()

def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, AayuTwinHandler)
    print(f"===========================================================")
    print(f" AAYU-TWIN Healthcare Digital Twin Server Running")
    print(f" Web Cockpit URL: http://localhost:{port}")
    print(f" Presentation Deck: http://localhost:{port}/presentation.html")
    print(f" Ayushman Bharat ABDM API: http://localhost:{port}/api/fhir")
    print(f"===========================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
