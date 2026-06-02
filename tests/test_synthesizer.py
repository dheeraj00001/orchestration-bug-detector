import pytest
import json
from scripts.synthesizer import DeterministicSynthesizer

def test_synthesizer_deduplication_and_merge():
    synth = DeterministicSynthesizer()
    findings = [
        {
            "anomaly_id": "MISMATCH_1",
            "severity": "high",
            "classification": "CONTRACT_MISMATCH",
            "evidence_paths": ["services/auth/src/handler.go"],
            "status": "confirmed"
        },
        {
            "anomaly_id": "MISMATCH_1",
            "severity": "critical", # Higher severity should win
            "classification": "CONTRACT_MISMATCH",
            "evidence_paths": ["services/payments/src/client.js"],
            "status": "confirmed"
        }
    ]
    
    result = synth.synthesize(findings)
    assert len(result) == 1
    assert result[0]["severity"] == "critical"
    # Evidence paths should be merged
    assert "services/auth/src/handler.go" in result[0]["evidence_paths"]
    assert "services/payments/src/client.js" in result[0]["evidence_paths"]

def test_synthesizer_sorting():
    synth = DeterministicSynthesizer()
    findings = [
        {"anomaly_id": "B", "severity": "low", "evidence_paths": ["p1"], "status": "confirmed", "classification": "C"},
        {"anomaly_id": "A", "severity": "high", "evidence_paths": ["p2"], "status": "confirmed", "classification": "C"},
        {"anomaly_id": "C", "severity": "high", "evidence_paths": ["p3"], "status": "confirmed", "classification": "C"}
    ]
    
    result = synth.synthesize(findings)
    # High severity first, then alpha by ID
    assert result[0]["anomaly_id"] == "A"
    assert result[1]["anomaly_id"] == "C"
    assert result[2]["anomaly_id"] == "B"

def test_synthesizer_report_rendering(tmp_path):
    import os
    os.chdir(tmp_path)
    synth = DeterministicSynthesizer()
    findings = [
        {
            "anomaly_id": "MISMATCH_1",
            "severity": "critical",
            "classification": "CONTRACT_MISMATCH",
            "evidence_paths": ["p1", "p2"],
            "status": "confirmed",
            "notes": {"type": "payload_detail", "value": "Token mismatch"}
        }
    ]
    
    synth.render_reports(findings)
    
    assert os.path.exists("report.md")
    assert os.path.exists("final_anomalies.json")
    
    report_content = open("report.md").read().lower()
    assert "mismatch_1" in report_content
    assert "critical" in report_content
    assert "token mismatch" in report_content
