from typing import List, Dict
from .synthesizer import DeterministicSynthesizer
from .interception_chain import InterceptionChain

class SynthesisEngine:
    """
    Orchestrates Phase 4: DELEGATE & SYNTHESIZE.
    Synthesizes subagent findings and performs hierarchical suppression.
    """

    def __init__(self):
        self.synth = DeterministicSynthesizer()
        self.interceptor = InterceptionChain()

    def synthesize(self, findings: List[Dict], rlm_search_results: List[Dict] = None) -> Dict:
        """
        Synthesizes findings into a deterministic report.
        rlm_search_results can be used to populate the interception evidence.
        """
        # 1. Prepare interception evidence
        # (Simplified mapping of RLM search results to layers)
        evidence = {"infra": [], "platform": [], "local": []}
        if rlm_search_results:
            for res in rlm_search_results:
                content = res.get("content", "").lower()
                if "gateway" in content or "mesh" in content:
                    evidence["infra"].append(res.get("file", "unknown"))
                elif "shared" in content or "platform" in content:
                    evidence["platform"].append(res.get("file", "unknown"))
                elif "middleware" in content or "interceptor" in content:
                    evidence["local"].append(res.get("file", "unknown"))

        # 2. Deterministic Merge and Sort
        merged_findings = self.synth.synthesize(findings)

        # 3. Apply Interception Chain
        final_findings = []
        for f in merged_findings:
            status, layer = self.interceptor.check_interception(evidence)
            if status == "suppressed":
                f["status"] = "suppressed"
                f["suppression_layer"] = layer
            else:
                f["status"] = "confirmed"
            final_findings.append(f)

        # 4. Render Reports
        self.synth.render_reports(final_findings)

        return {
            "findings": final_findings,
            "report_path": "report.md",
            "json_path": "final_anomalies.json"
        }
