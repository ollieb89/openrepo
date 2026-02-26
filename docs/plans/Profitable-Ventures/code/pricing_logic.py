class PricingTier:
    def __init__(self, name, price, max_workflows, max_actions):
        self.name = name
        self.price = price
        self.max_workflows = max_workflows
        self.max_actions = max_actions

TIERS = {
    "STARTER": PricingTier("Starter", 500, 1, 200),
    "GROWTH": PricingTier("Growth", 1000, 3, 1000),
    "SCALE": PricingTier("Scale", 2000, 5, float('inf'))
}

class ClientAccount:
    def __init__(self, client_id, tier_key):
        self.client_id = client_id
        self.tier = TIERS[tier_key]
        self.active_workflows = []
        self.actions_this_month = 0
        self.is_over_limit = False

    def add_workflow(self, workflow_name):
        if len(self.active_workflows) < self.tier.max_workflows:
            self.active_workflows.append(workflow_name)
            return True
        print(f"Workflow limit reached for {self.tier.name} tier.")
        return False

    def track_action(self):
        if self.actions_this_month < self.tier.max_actions:
            self.actions_this_month += 1
            return True
        self.is_over_limit = True
        print(f"Action limit reached for {self.tier.name} tier. Please upgrade.")
        return False

    def reset_month(self):
        self.actions_this_month = 0
        self.is_over_limit = False

# Example Usage
if __name__ == "__main__":
    client = ClientAccount("client_001", "STARTER")
    client.add_workflow("Lead Qualification")
    
    # Simulate actions
    for _ in range(201):
        if not client.track_action():
            break
    
    print(f"Status: {client.tier.name} Tier - Actions: {client.actions_this_month}")
