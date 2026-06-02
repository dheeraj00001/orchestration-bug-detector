import json
from typing import List, Dict
from .interception_chain import InterceptionChain

class DeterministicSynthesizer:
    """
    Implements Phase 4 synthesis:
    - Deterministic merge of subagent outputs.
    - De-duplicate by anomaly_id.
    - Merge evidence_paths.
    - Sort for stability.
    - Render report.md and final_anomalies.json.
    """

    SEVERITY_ORDER = {
        "critical": 5,
        "high": 4,
        "medium": 3,
        "low": 2,
        "informational": 1
    }

    def __init__(self):
        self.interceptor = InterceptionChain()

    def synthesize(self, findings: List[Dict]) -> List[Dict]:
        merged = {}

        for f in findings:
            aid = f["anomaly_id"]
            if aid not in merged:
                merged[aid] = f.copy()
                merged[aid]["evidence_paths"] = list(set(f.get("evidence_paths", [])))
            else:
                existing = merged[aid]
                # Retain higher severity
                curr_sev = self.SEVERITY_ORDER.get(f.get("severity", "low"), 0)
                exis_sev = self.SEVERITY_ORDER.get(existing.get("severity", "low"), 0)
                
                if curr_sev > exis_sev:
                    existing["severity"] = f["severity"]
                    # If severity is higher, we might want to adopt the new notes too if they are more comprehensive
                    # PRD: "retain the finding with the higher severity; if severity is equal, merge... retain most comprehensive notes"
                    existing["notes"] = f.get("notes", existing.get("notes"))
                
                # Merge evidence paths
                existing["evidence_paths"] = list(set(existing["evidence_paths"] + f.get("evidence_paths", [])))

        # Sort: severity desc, anomaly_id asc
        sorted_findings = sorted(
            merged.values(),
            key=lambda x: (-self.SEVERITY_ORDER.get(x.get("severity", "low"), 0), x["anomaly_id"])
        )

        return sorted_findings

    def render_reports(self, findings: List[Dict]):
        # Render final_anomalies.json
        with open("final_anomalies.json", "w") as f:
            json.dump(findings, f, indent=2)

        # Render report.md
        with open("report.md", "w") as f:
            f.write("# Orchestration Bug Detection Report\n\n")
            if not findings:
                f.write("No critical orchestration bugs detected.\n")
                return

            for anom in findings:
                f.write(f"## {anom['anomaly_id']}\n")
                f.write(f"- **Severity**: {anom['severity'].upper()}\n")
                f.write(f"- **Evidence**: {', '.join(anom.get('evidence_paths', []))}\n")
                
                description = ""
                if "notes" in anom:
                    description = anom["notes"].get("value", "")
                
                if not description:
                    description = f"Deterministic {anom.get('classification', 'finding')} detected at service boundary."
                
                f.write(f"- **Description**: {description}\n\n")
