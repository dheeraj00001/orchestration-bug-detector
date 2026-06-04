import json
import hashlib
from typing import List, Dict, Any
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

    def _generate_fallback_id(self, finding: Dict) -> str:
        rule = finding.get("classification", "UNKNOWN")
        paths = "".join(sorted(finding.get("evidence_paths", [])))
        hash_val = hashlib.md5(f"{rule}_{paths}".encode()).hexdigest()[:8]
        return f"anomaly:fallback:{rule.lower()}:{hash_val}"

    def synthesize(self, findings: List[Any]) -> Dict[str, List[Dict]]:
        merged = {}
        quarantine = []

        for original_f in findings:
            if not isinstance(original_f, dict):
                quarantine.append({"reason": "not_a_dict", "raw": original_f})
                continue
            
            f = original_f.copy()
            
            # ARCH-03: Open Finding Schema
            # If it's missing core fields, wrap it instead of quarantining
            is_valid = "severity" in f or "classification" in f or f.get("type") == "general_insight"
            
            if not is_valid:
                # Wrap as GeneralInsight rather than discard
                f = {
                    "anomaly_id": self._generate_fallback_id(f),
                    "type": "general_insight",
                    "classification": f.get("classification", "GENERAL_INSIGHT"),
                    "severity": f.get("severity", "informational"),
                    "title": f.get("title", "Unclassified Finding"),
                    "notes": f.get("notes", str(f)),
                    "evidence_paths": f.get("evidence_paths", []),
                    "raw": original_f
                }
            
            aid = f.get("anomaly_id")
            if not aid:
                aid = self._generate_fallback_id(f)
                f["anomaly_id"] = aid
                
            if "raw" not in f:
                f["raw"] = original_f # preserve raw

            if aid not in merged:
                merged[aid] = f
                merged[aid]["evidence_paths"] = list(set(f.get("evidence_paths", [])))
            else:
                existing = merged[aid]
                # Retain higher severity
                curr_sev = self.SEVERITY_ORDER.get(f.get("severity", "low"), 0)
                exis_sev = self.SEVERITY_ORDER.get(existing.get("severity", "low"), 0)
                
                if curr_sev > exis_sev:
                    existing["severity"] = f.get("severity", "low")
                    existing["notes"] = f.get("notes", existing.get("notes"))
                
                # Merge evidence paths
                existing["evidence_paths"] = list(set(existing["evidence_paths"] + f.get("evidence_paths", [])))

        # Sort: severity desc, anomaly_id asc
        sorted_findings = sorted(
            merged.values(),
            key=lambda x: (-self.SEVERITY_ORDER.get(x.get("severity", "low"), 0), x.get("anomaly_id", ""))
        )

        return {"valid": sorted_findings, "quarantine": quarantine}

    def render_reports(self, synthesis_result: Dict[str, List[Dict]], output_dir: str = "."):
        # We can accept either the new dict format or the old list format for backward compatibility
        findings = synthesis_result.get("valid", []) if isinstance(synthesis_result, dict) else synthesis_result
        
        # Ensure output_dir exists
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        json_path = os.path.join(output_dir, "final_anomalies.json")
        report_path = os.path.join(output_dir, "report.md")

        # Render final_anomalies.json (including quarantine if dict)
        with open(json_path, "w") as f:
            json.dump(synthesis_result, f, indent=2)

        # Render report.md
        with open(report_path, "w") as f:
            f.write("# Orchestration Bug Detection Report\n\n")
            if not findings:
                f.write("No critical orchestration bugs detected.\n")
                return

            for anom in findings:
                f.write(f"## {anom['anomaly_id']}\n")
                f.write(f"- **Severity**: {anom.get('severity', 'low').upper()}\n")
                f.write(f"- **Evidence**: {', '.join(anom.get('evidence_paths', []))}\n")
                
                description = ""
                if "notes" in anom:
                    if isinstance(anom["notes"], dict):
                        description = anom["notes"].get("value", "")
                    else:
                        description = str(anom["notes"])
                
                if not description:
                    description = f"Deterministic {anom.get('classification', 'finding')} detected at service boundary."
                
                f.write(f"- **Description**: {description}\n\n")

