from packages.orchestration.src.openclaw.soul_renderer import render_soul, build_dynamic_variables
from packages.orchestration.src.openclaw.agent_registry import AgentRegistry
from pathlib import Path

root = Path('.')
registry = AgentRegistry(root)

extra = build_dynamic_variables("main", "clawdia_prime", registry)
print("Dynamic Vars:")
for k, v in extra.items():
    print(f"  {k}: {v}")

print("\n--- Rendered SOUL ---")
try:
    rendered = render_soul("main", extra_variables=extra)
    print(rendered[:500] + "\n...")
except Exception as e:
    print(f"Error: {e}")
