from typing import List, Dict

class SynthesisEngine:
    """
    Synthesizes subagent findings and performs a 'Challenge-Response' validation
    against global context to reduce false positives.
    """

    def synthesize(self, findings: List[Dict], rlm_search_results: List[Dict]) -> Dict:
        valid_bugs = []
        false_positives = []

        # Simple logic: if 'app.use' or 'Middleware' is found in search results 
        # for the same service, we flag it as a potential false positive.
        has_global_protection = any(
            "app.use" in res["content"] or "Middleware" in res["content"]
            for res in rlm_search_results
        )

        for finding in findings:
            if finding["bug_type"] == "MISSING_AUTH" and has_global_protection:
                finding["reason"] = "GLOBAL_MIDDLEWARE_PROTECTION"
                false_positives.append(finding)
            else:
                valid_bugs.append(finding)

        return {
            "valid_bugs": valid_bugs,
            "false_positives": false_positives
        }
