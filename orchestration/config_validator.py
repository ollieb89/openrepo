"""
Configuration Validator

Validates project.json manifests and openclaw.json agent hierarchy at load time.
Produces human-friendly, actionable error messages — not raw KeyError tracebacks.

Implements REL-02 (project.json schema validation) and REL-03 (agent hierarchy
validation for openclaw.json reports_to chains and level constraints).
"""

from typing import Any, Dict, List

from .logging import get_logger

logger = get_logger("config_validator")


class ConfigValidationError(Exception):
    """
    Raised when a configuration file fails schema or hierarchy validation.

    Attributes:
        errors: Individual error strings, one per validation failure.
    """

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        super().__init__(str(self))

    def __str__(self) -> str:
        return "\n".join(self.errors)


def validate_project_config(config: Dict[str, Any], manifest_path: str) -> None:
    """
    Validate a project.json config dict for required fields and types.

    Collects all validation errors (collect-all strategy) so the caller
    sees every problem at once rather than fixing one at a time.

    Required fields:
        - workspace: non-empty string
        - tech_stack: dict (object)

    Args:
        config: Parsed project.json dict.
        manifest_path: Filesystem path to the file (used in error messages).

    Raises:
        ConfigValidationError: If any required field is missing or wrong type.
    """
    logger.debug("Validating project config", extra={"manifest_path": manifest_path})

    errors: List[str] = []

    # workspace: required, must be a non-empty string
    if "workspace" not in config:
        errors.append(
            f'project.json ({manifest_path}): missing required field "workspace". '
            f"Add a workspace path pointing to your project directory."
        )
    elif not isinstance(config["workspace"], str) or not config["workspace"].strip():
        got = type(config["workspace"]).__name__
        errors.append(
            f'project.json ({manifest_path}): field "workspace" must be a non-empty string, '
            f"got {got}. Set workspace to the absolute path of your project directory."
        )

    # tech_stack: required, must be a dict
    if "tech_stack" not in config:
        errors.append(
            f'project.json ({manifest_path}): missing required field "tech_stack". '
            f'Define tech_stack as {{"frontend": "...", "backend": "..."}}.'
        )
    elif not isinstance(config["tech_stack"], dict):
        got = type(config["tech_stack"]).__name__
        errors.append(
            f'project.json ({manifest_path}): field "tech_stack" must be an object, '
            f'got {got}. Define tech_stack as {{"frontend": "...", "backend": "..."}}.'
        )

    if errors:
        for err in errors:
            logger.error("Project config validation error", extra={"error": err, "manifest_path": manifest_path})
        raise ConfigValidationError(errors)

    # Advisory pool config validation (non-fatal warnings only)
    l3_overrides = config.get("l3_overrides", {})
    if l3_overrides:
        _validate_pool_config(l3_overrides, manifest_path)


_VALID_POOL_MODES = {"shared", "isolated"}
_VALID_OVERFLOW_POLICIES = {"reject", "wait", "priority"}


def _validate_pool_config(l3_overrides: Dict[str, Any], manifest_path: str) -> None:
    """
    Validate pool-specific keys within l3_overrides.

    Non-fatal: all issues produce warnings rather than raising ConfigValidationError.
    This matches the locked decision: "Invalid config values log a warning and fall
    back to defaults — don't crash or block spawns."

    Args:
        l3_overrides: The l3_overrides dict from project.json.
        manifest_path: Filesystem path (used in warning messages).
    """
    # max_concurrent: must be a positive int if present
    if "max_concurrent" in l3_overrides:
        val = l3_overrides["max_concurrent"]
        if not isinstance(val, int) or val <= 0:
            logger.warning(
                "project.json pool config warning: max_concurrent must be a positive integer — will use default (3)",
                extra={"manifest_path": manifest_path, "got": val},
            )

    # pool_mode: must be a known string if present
    if "pool_mode" in l3_overrides:
        val = l3_overrides["pool_mode"]
        if not isinstance(val, str) or val not in _VALID_POOL_MODES:
            logger.warning(
                "project.json pool config warning: pool_mode must be one of %s — will use default (shared)",
                sorted(_VALID_POOL_MODES),
                extra={"manifest_path": manifest_path, "got": val},
            )

    # overflow_policy: must be a known string if present
    if "overflow_policy" in l3_overrides:
        val = l3_overrides["overflow_policy"]
        if not isinstance(val, str) or val not in _VALID_OVERFLOW_POLICIES:
            logger.warning(
                "project.json pool config warning: overflow_policy must be one of %s — will use default (wait)",
                sorted(_VALID_OVERFLOW_POLICIES),
                extra={"manifest_path": manifest_path, "got": val},
            )

    # queue_timeout_s: must be a positive int if present
    if "queue_timeout_s" in l3_overrides:
        val = l3_overrides["queue_timeout_s"]
        if not isinstance(val, int) or val <= 0:
            logger.warning(
                "project.json pool config warning: queue_timeout_s must be a positive integer — will use default (300)",
                extra={"manifest_path": manifest_path, "got": val},
            )


def validate_agent_hierarchy(config: Dict[str, Any], config_path: str) -> None:
    """
    Validate the agents.list array in an openclaw.json config dict.

    Checks:
        1. Every reports_to value (if not null) references an existing agent id.
        2. An agent's level must be strictly greater than its reports_to target
           (lower level number = higher tier: L1=1, L2=2, L3=3).
        3. Level-1 agents must have reports_to: null.

    Collects all errors before raising (collect-all strategy).

    Args:
        config: Parsed openclaw.json dict.
        config_path: Filesystem path to the file (used in error messages).

    Raises:
        ConfigValidationError: If any hierarchy rule is violated.
    """
    logger.debug("Validating agent hierarchy", extra={"config_path": config_path})

    agents_section = config.get("agents", {})
    agent_list = agents_section.get("list", [])

    if not agent_list:
        # No agents defined — nothing to validate
        return

    # Build lookup table: id -> agent dict
    agent_by_id: Dict[str, Dict[str, Any]] = {a["id"]: a for a in agent_list if "id" in a}

    errors: List[str] = []

    for agent in agent_list:
        agent_id = agent.get("id", "<unknown>")
        reports_to = agent.get("reports_to")
        level = agent.get("level")

        # Rule 3: Level-1 agents must have reports_to: null
        if level == 1 and reports_to is not None:
            errors.append(
                f'openclaw.json ({config_path}): agent "{agent_id}" is level 1 but '
                f'reports_to "{reports_to}". Level 1 agents must have reports_to: null.'
            )
            continue  # Skip further checks for this agent

        if reports_to is None:
            continue  # No reports_to — nothing else to check

        # Rule 1: reports_to must reference an existing agent id
        if reports_to not in agent_by_id:
            errors.append(
                f'openclaw.json ({config_path}): agent "{agent_id}" reports_to '
                f'"{reports_to}" which does not exist. '
                f"Check the agent ID spelling or add the missing agent."
            )
            continue  # Can't check level constraint without knowing target

        # Rule 2: Level constraint — must report to a higher-tier (lower level number) agent
        target = agent_by_id[reports_to]
        target_level = target.get("level")
        if level is not None and target_level is not None and level <= target_level:
            errors.append(
                f'openclaw.json ({config_path}): agent "{agent_id}" (level {level}) '
                f'reports_to "{reports_to}" (level {target_level}). '
                f"An agent must report to a higher-tier agent (lower level number)."
            )

    if errors:
        for err in errors:
            logger.error("Agent hierarchy validation error", extra={"error": err, "config_path": config_path})
        raise ConfigValidationError(errors)
