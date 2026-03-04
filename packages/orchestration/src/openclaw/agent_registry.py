"""Unified agent registry that merges openclaw.json agents with agents/ directory."""

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Optional, List, Dict
import json

try:
    from openclaw.logging import get_logger
    _logger = get_logger('agent_registry')
except Exception:
    import logging
    _logger = logging.getLogger('openclaw.agent_registry')

# Identity fields that trigger drift warnings when openclaw.json and
# per-agent config.json disagree.
_DRIFT_IDENTITY_FIELDS = ("name", "level", "reports_to")

# Default max_concurrent used in the dataclass — stored here so _apply_defaults()
# knows whether the per-agent file explicitly set a value (anything != _DEFAULT_MAX_CONCURRENT
# is considered explicit).
_DEFAULT_MAX_CONCURRENT = 3


class AgentLevel(IntEnum):
    L1 = 1  # Strategic orchestrator
    L2 = 2  # Tactical project manager
    L3 = 3  # Ephemeral specialist


@dataclass
class AgentSpec:
    id: str
    name: str
    level: AgentLevel
    reports_to: Optional[str] = None
    subordinates: List[str] = field(default_factory=list)

    # From openclaw.json
    model: Optional[str] = None
    provider: Optional[str] = None

    # From agents/*/config.json
    role: Optional[str] = None  # "coordinator", "domain", "executor"
    projects: List[str] = field(default_factory=list)
    max_concurrent: int = _DEFAULT_MAX_CONCURRENT
    skill_registry: Dict[str, dict] = field(default_factory=dict)

    # From agents/*/agent/
    identity_path: Optional[Path] = None
    soul_path: Optional[Path] = None

    # L3-specific
    container: Optional[dict] = None
    runtime: Optional[dict] = None

    # Sandbox config (from agents.defaults or per-agent)
    sandbox: Optional[dict] = None

    # Source tracking — set by AgentRegistry during load
    # Values: "openclaw_json", "agents_dir", "both"
    source: str = "unknown"

    @property
    def is_orchestrator(self) -> bool:
        return self.level <= AgentLevel.L2

    @property
    def is_ephemeral(self) -> bool:
        return self.level == AgentLevel.L3


class AgentRegistry:
    """Merges openclaw.json agent list with agents/ directory configs."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._agents: Dict[str, AgentSpec] = {}
        # Raw identity data from openclaw.json — used for drift comparison.
        self._openclaw_json_data: Dict[str, dict] = {}
        # Tracks which agents had their max_concurrent explicitly set by per-agent config.
        self._explicit_max_concurrent: set = set()
        # Agents.defaults from openclaw.json
        self._defaults: dict = {}
        self._load()

    def _load(self):
        """Load from both sources, agents/ dir takes precedence for orchestration fields."""
        self._load_openclaw_json()
        self._load_agents_directory()
        self._detect_orphans()
        self._apply_defaults()

    def _load_openclaw_json(self):
        config_path = self.project_root / "openclaw.json"
        if not config_path.exists():
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        # Store defaults for later use in _apply_defaults()
        self._defaults = data.get("agents", {}).get("defaults", {})

        agents_list = data.get("agents", {}).get("list", [])
        for a_data in agents_list:
            aid = a_data.get("id")
            if not aid:
                continue

            level_val = a_data.get("level", 3)
            try:
                level = AgentLevel(level_val)
            except ValueError:
                level = AgentLevel.L3

            spec = AgentSpec(
                id=aid,
                name=a_data.get("name", aid),
                level=level,
                reports_to=a_data.get("reports_to"),
                subordinates=a_data.get("subordinates", []),
                model=a_data.get("model"),
                provider=a_data.get("provider"),
                source="openclaw_json",
            )

            orch = a_data.get("orchestration", {})
            if "role" in orch:
                spec.role = orch["role"]
            if "max_concurrent" in orch:
                spec.max_concurrent = orch["max_concurrent"]
                self._explicit_max_concurrent.add(aid)
            if "skill_registry" in orch:
                skills = orch["skill_registry"]
                if isinstance(skills, list):
                    spec.skill_registry = {s: {} for s in skills}
                elif isinstance(skills, dict):
                    spec.skill_registry = skills
            if "identity_ref" in orch:
                spec.identity_path = Path(orch["identity_ref"])
            if "soul_ref" in orch:
                spec.soul_path = Path(orch["soul_ref"])
            if "container" in orch:
                spec.container = orch["container"]
            if "runtime" in orch:
                spec.runtime = orch["runtime"]

            self._agents[aid] = spec

            # Store raw identity data for drift comparison
            self._openclaw_json_data[aid] = {
                "name": spec.name,
                "level": int(spec.level),
                "reports_to": spec.reports_to,
            }

    def _load_agents_directory(self):
        agents_dir = self.project_root / "agents"
        if not agents_dir.exists() or not agents_dir.is_dir():
            return

        for agent_path in agents_dir.iterdir():
            if not agent_path.is_dir():
                continue

            aid = agent_path.name
            # Silently skip underscore-prefixed directories (e.g. _templates)
            if aid.startswith("_"):
                continue

            config_file = agent_path / "agent" / "config.json"
            identity_file = agent_path / "agent" / "IDENTITY.md"
            soul_file = agent_path / "agent" / "SOUL.md"

            # Only process agents that have a config.json — no auto-registration without it
            if not config_file.exists():
                continue

            # Create spec if not exists (filesystem-only agent)
            if aid not in self._agents:
                self._agents[aid] = AgentSpec(
                    id=aid,
                    name=aid,
                    level=AgentLevel.L3,
                    source="agents_dir",
                )
            spec = self._agents[aid]

            # Update source tracking
            if spec.source == "openclaw_json":
                spec.source = "both"
            # (if already "agents_dir" or "unknown", stays as-is until set)

            if identity_file.exists():
                spec.identity_path = identity_file.relative_to(self.project_root)
            if soul_file.exists():
                spec.soul_path = soul_file.relative_to(self.project_root)

            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    c_data = json.load(f)

                # Warn on id mismatch between directory name and config.json id field
                if c_data.get("id") and c_data["id"] != aid:
                    _logger.warning(
                        "Agent directory '%s' has id='%s' in config.json — "
                        "directory name is the canonical id. Update config.json.",
                        aid, c_data["id"],
                    )

                # Apply per-agent fields (per-agent wins over openclaw.json)
                if "name" in c_data:
                    spec.name = c_data["name"]
                if "level" in c_data:
                    try:
                        spec.level = AgentLevel(c_data["level"])
                    except ValueError:
                        pass
                if "reports_to" in c_data:
                    spec.reports_to = c_data["reports_to"]
                if "subordinates" in c_data:
                    spec.subordinates = c_data["subordinates"]
                if "role" in c_data:
                    spec.role = c_data["role"]
                if "projects" in c_data:
                    spec.projects = c_data["projects"]
                if "max_concurrent" in c_data:
                    spec.max_concurrent = c_data["max_concurrent"]
                    self._explicit_max_concurrent.add(aid)
                if "model" in c_data:
                    spec.model = c_data["model"]
                if "skill_registry" in c_data:
                    spec.skill_registry = c_data["skill_registry"]
                if "container" in c_data:
                    spec.container = c_data["container"]
                if "runtime" in c_data:
                    spec.runtime = c_data["runtime"]
                if "sandbox" in c_data:
                    spec.sandbox = c_data["sandbox"]

                # Drift detection against openclaw.json identity fields
                self._detect_drift(spec)

            except Exception:
                pass

    def _detect_drift(self, spec: AgentSpec) -> None:
        """Warn when per-agent config.json disagrees with openclaw.json on identity fields."""
        central = self._openclaw_json_data.get(spec.id)
        if central is None:
            # Filesystem-only agent — no drift possible (no openclaw.json baseline)
            return
        per_agent_vals = {
            "name": spec.name,
            "level": int(spec.level),
            "reports_to": spec.reports_to,
        }
        for field_name in _DRIFT_IDENTITY_FIELDS:
            if central.get(field_name) != per_agent_vals.get(field_name):
                _logger.warning(
                    "Agent '%s' drift: field '%s' is '%s' in openclaw.json but '%s' "
                    "in agents/%s/agent/config.json. Run `openclaw agent sync` to update.",
                    spec.id, field_name, central.get(field_name), per_agent_vals.get(field_name),
                    spec.id,
                )

    def _detect_orphans(self) -> None:
        """Warn for agents in openclaw.json that have no agents/ directory."""
        for aid, spec in self._agents.items():
            if spec.source == "openclaw_json":
                _logger.warning(
                    "Agent '%s' is registered in openclaw.json but has no "
                    "agents/%s/agent/config.json. Run `openclaw agent init %s` to scaffold.",
                    aid, aid, aid,
                )

    def _apply_defaults(self) -> None:
        """Apply agents.defaults from openclaw.json to specs missing those fields."""
        if not self._defaults:
            return

        default_max_concurrent = self._defaults.get("maxConcurrent")
        default_model_primary = None
        if isinstance(self._defaults.get("model"), dict):
            default_model_primary = self._defaults["model"].get("primary")
        default_sandbox = self._defaults.get("sandbox")

        for aid, spec in self._agents.items():
            # Apply default maxConcurrent only if not explicitly set
            if (
                default_max_concurrent is not None
                and aid not in self._explicit_max_concurrent
                and spec.max_concurrent == _DEFAULT_MAX_CONCURRENT
            ):
                spec.max_concurrent = default_max_concurrent

            # Apply default model only if not set
            if default_model_primary is not None and spec.model is None:
                spec.model = default_model_primary

            # Apply default sandbox only if not set
            if default_sandbox is not None and spec.sandbox is None:
                spec.sandbox = default_sandbox

    def all_agents(self) -> List[AgentSpec]:
        """Return all registered AgentSpec objects, sorted by level then id."""
        return sorted(self._agents.values(), key=lambda a: (int(a.level), a.id))

    def get(self, agent_id: str) -> Optional[AgentSpec]:
        return self._agents.get(agent_id)

    def list_by_level(self, level: AgentLevel) -> List[AgentSpec]:
        return [a for a in self._agents.values() if a.level == level]

    def get_hierarchy(self, agent_id: str) -> List[AgentSpec]:
        """Walk up the reports_to chain."""
        chain = []
        current = self.get(agent_id)
        while current:
            chain.append(current)
            current = self.get(current.reports_to) if current.reports_to else None
        return chain

    def get_subordinates(self, agent_id: str, recursive: bool = False) -> List[AgentSpec]:
        """Get direct (or all recursive) subordinates."""
        direct = [a for a in self._agents.values() if a.reports_to == agent_id]
        if not recursive:
            return direct
        result = []
        for sub in direct:
            result.append(sub)
            result.extend(self.get_subordinates(sub.id, recursive=True))
        return result
