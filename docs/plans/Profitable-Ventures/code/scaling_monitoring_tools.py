import re
import json

class MonitoringDashboard:
    def __init__(self):
        self.metrics = {
            "api_cost_usd": 0.0,
            "success_count": 0,
            "error_count": 0,
            "latency_ms_avg": 0.0
        }

    def log_action(self, success, cost, latency):
        self.metrics["api_cost_usd"] += cost
        if success:
            self.metrics["success_count"] += 1
        else:
            self.metrics["error_count"] += 1
        
        # Simple moving average for latency
        total_actions = self.metrics["success_count"] + self.metrics["error_count"]
        self.metrics["latency_ms_avg"] = (self.metrics["latency_ms_avg"] * (total_actions - 1) + latency) / total_actions

    def get_health_status(self):
        total = self.metrics["success_count"] + self.metrics["error_count"]
        success_rate = (self.metrics["success_count"] / total) * 100 if total > 0 else 100
        return {
            "health": "GREEN" if success_rate > 95 else "AMBER" if success_rate > 85 else "RED",
            "success_rate": f"{success_rate:.2f}%",
            "current_cost": f"${self.metrics['api_cost_usd']:.2f}"
        }

class ShadowAIDiscovery:
    def __init__(self):
        self.ai_endpoints = ["api.openai.com", "api.anthropic.com", "vertexai.googleapis.com"]
        self.suspicious_patterns = [r"sk-[a-zA-Z0-9]{32,}", r"AI_SECRET", r"Bearer\s+[a-zA-Z0-9_-]{20,}"]

    def scan_outbound_log(self, log_entry):
        """Simulate scanning network traffic for unauthorized AI usage."""
        for endpoint in self.ai_endpoints:
            if endpoint in log_entry:
                for pattern in self.suspicious_patterns:
                    if re.search(pattern, log_entry):
                        return {
                            "status": "ALERT",
                            "reason": "Unauthorized AI API Call with Secret Key detected.",
                            "details": log_entry
                        }
        return {"status": "CLEAN"}

# Example Usage
if __name__ == "__main__":
    dash = MonitoringDashboard()
    dash.log_action(True, 0.05, 1200)
    dash.log_action(False, 0.02, 3500)
    
    print(f"Monitoring Dashboard: {dash.get_health_status()}")
    
    discovery = ShadowAIDiscovery()
    sample_log = "POST 10.0.0.5 -> api.openai.com Header: Authorization: Bearer sk-proj-1234567890abcdef..."
    alert = discovery.scan_outbound_log(sample_log)
    if alert["status"] == "ALERT":
        print(f"!!! SECURITY ALERT !!! {alert['reason']}")
