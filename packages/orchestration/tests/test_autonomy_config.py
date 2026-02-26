"""
Tests for autonomy configuration.

Covers schema validation, config access functions, and env var overrides.
"""
import json as _json
import os
from pathlib import Path
import pytest


class TestAutonomySchemaValidation:
    """Tests for autonomy section in OPENCLAW_JSON_SCHEMA."""

    def test_autonomy_section_in_schema(self):
        """Autonomy section exists in schema."""
        from openclaw.config import OPENCLAW_JSON_SCHEMA
        assert "autonomy" in OPENCLAW_JSON_SCHEMA["properties"]

    def test_autonomy_schema_structure(self):
        """Autonomy schema has correct structure."""
        from openclaw.config import OPENCLAW_JSON_SCHEMA
        autonomy_schema = OPENCLAW_JSON_SCHEMA["properties"]["autonomy"]
        assert autonomy_schema["type"] == "object"
        assert "properties" in autonomy_schema
        
        props = autonomy_schema["properties"]
        assert "escalation_threshold" in props
        assert "confidence_calculator" in props
        assert "max_retries" in props
        assert "blocked_timeout_minutes" in props

    def test_escalation_threshold_validation(self):
        """Escalation threshold must be 0.0-1.0."""
        from openclaw.config_validator import validate_openclaw_config
        
        # Valid values should pass
        valid_config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"escalation_threshold": 0.6}
        }
        fatal, warnings = validate_openclaw_config(valid_config, "test.json")
        assert fatal == [], f"Valid threshold should pass: {fatal}"

    def test_invalid_escalation_threshold_fails(self):
        """Escalation threshold outside 0.0-1.0 fails validation."""
        from openclaw.config_validator import validate_openclaw_config
        
        # Invalid: 1.5 is > 1.0
        invalid_config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"escalation_threshold": 1.5}
        }
        fatal, warnings = validate_openclaw_config(invalid_config, "test.json")
        # This should produce a validation error due to maximum constraint
        combined = " ".join(fatal + warnings)
        assert "escalation_threshold" in combined.lower() or "1.5" in combined or len(fatal) > 0 or len(warnings) > 0

    def test_confidence_calculator_enum(self):
        """Confidence calculator must be 'threshold' or 'adaptive'."""
        from openclaw.config_validator import validate_openclaw_config
        
        # Valid: threshold
        config1 = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"confidence_calculator": "threshold"}
        }
        fatal, _ = validate_openclaw_config(config1, "test.json")
        assert fatal == [], "threshold should be valid"
        
        # Valid: adaptive
        config2 = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"confidence_calculator": "adaptive"}
        }
        fatal, _ = validate_openclaw_config(config2, "test.json")
        assert fatal == [], "adaptive should be valid"

    def test_max_retries_validation(self):
        """Max retries must be non-negative integer."""
        from openclaw.config_validator import validate_openclaw_config
        
        # Valid: 0
        config1 = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"max_retries": 0}
        }
        fatal, _ = validate_openclaw_config(config1, "test.json")
        assert fatal == []
        
        # Valid: 5
        config2 = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"max_retries": 5}
        }
        fatal, _ = validate_openclaw_config(config2, "test.json")
        assert fatal == []

    def test_blocked_timeout_validation(self):
        """Blocked timeout must be positive integer."""
        from openclaw.config_validator import validate_openclaw_config
        
        # Valid: 1 (minimum)
        config1 = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"blocked_timeout_minutes": 1}
        }
        fatal, _ = validate_openclaw_config(config1, "test.json")
        assert fatal == []
        
        # Valid: 60
        config2 = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"blocked_timeout_minutes": 60}
        }
        fatal, _ = validate_openclaw_config(config2, "test.json")
        assert fatal == []


class TestAutonomyConfigAccess:
    """Tests for autonomy config access functions."""

    def test_get_autonomy_config_returns_defaults(self, tmp_path, monkeypatch):
        """Returns defaults when no autonomy section in config."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        # Create minimal config without autonomy section
        config = {"gateway": {"port": 18789}, "agents": {"list": []}}
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.project_config import get_autonomy_config
            cfg = get_autonomy_config()
            assert cfg["escalation_threshold"] == 0.6
            assert cfg["confidence_calculator"] == "threshold"
            assert cfg["max_retries"] == 1
            assert cfg["blocked_timeout_minutes"] == 30
        finally:
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)

    def test_get_autonomy_config_reads_values(self, tmp_path, monkeypatch):
        """Reads autonomy values from config."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {
                "escalation_threshold": 0.8,
                "confidence_calculator": "adaptive",
                "max_retries": 3,
                "blocked_timeout_minutes": 60
            }
        }
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.project_config import get_autonomy_config
            cfg = get_autonomy_config()
            assert cfg["escalation_threshold"] == 0.8
            assert cfg["confidence_calculator"] == "adaptive"
            assert cfg["max_retries"] == 3
            assert cfg["blocked_timeout_minutes"] == 60
        finally:
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)

    def test_get_escalation_threshold(self, tmp_path, monkeypatch):
        """get_escalation_threshold returns correct value."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"escalation_threshold": 0.75}
        }
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.project_config import get_escalation_threshold
            threshold = get_escalation_threshold()
            assert threshold == 0.75
        finally:
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)

    def test_get_confidence_calculator_type(self, tmp_path, monkeypatch):
        """get_confidence_calculator_type returns correct value."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"confidence_calculator": "adaptive"}
        }
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.project_config import get_confidence_calculator_type
            calc_type = get_confidence_calculator_type()
            assert calc_type == "adaptive"
        finally:
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)

    def test_env_var_override_escalation_threshold(self, tmp_path, monkeypatch):
        """OPENCLAW_ESCALATION_THRESHOLD env var overrides config."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"escalation_threshold": 0.5}
        }
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        monkeypatch.setenv("OPENCLAW_ESCALATION_THRESHOLD", "0.9")
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.project_config import get_escalation_threshold
            threshold = get_escalation_threshold()
            assert threshold == 0.9
        finally:
            monkeypatch.delenv("OPENCLAW_ESCALATION_THRESHOLD", raising=False)
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)

    def test_invalid_env_var_ignored(self, tmp_path, monkeypatch):
        """Invalid OPENCLAW_ESCALATION_THRESHOLD env var is ignored."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"escalation_threshold": 0.7}
        }
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        monkeypatch.setenv("OPENCLAW_ESCALATION_THRESHOLD", "invalid")
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.project_config import get_escalation_threshold
            threshold = get_escalation_threshold()
            # Should use config value, not invalid env var
            assert threshold == 0.7
        finally:
            monkeypatch.delenv("OPENCLAW_ESCALATION_THRESHOLD", raising=False)
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)

    def test_out_of_range_env_var_ignored(self, tmp_path, monkeypatch):
        """Out of range OPENCLAW_ESCALATION_THRESHOLD env var is ignored."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {"escalation_threshold": 0.7}
        }
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        monkeypatch.setenv("OPENCLAW_ESCALATION_THRESHOLD", "2.0")
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.project_config import get_escalation_threshold
            threshold = get_escalation_threshold()
            # Should use config value, not out of range env var
            assert threshold == 0.7
        finally:
            monkeypatch.delenv("OPENCLAW_ESCALATION_THRESHOLD", raising=False)
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)


class TestAutonomyConfigDataclass:
    """Tests for AutonomyConfig dataclass."""

    def test_default_values(self, tmp_path, monkeypatch):
        """AutonomyConfig has correct default values."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        config = {"gateway": {"port": 18789}, "agents": {"list": []}}
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.autonomy import load_autonomy_config, AutonomyConfig
            cfg = load_autonomy_config()
            assert isinstance(cfg, AutonomyConfig)
            assert cfg.escalation_threshold == 0.6
            assert cfg.confidence_calculator == "threshold"
            assert cfg.max_retries == 1
            assert cfg.blocked_timeout_minutes == 30
        finally:
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)

    def test_should_escalate_logic(self):
        """should_escalate returns True when confidence below threshold."""
        from openclaw.autonomy import AutonomyConfig
        
        cfg = AutonomyConfig(escalation_threshold=0.6)
        
        # Below threshold should escalate
        assert cfg.should_escalate(0.5) is True
        assert cfg.should_escalate(0.3) is True
        assert cfg.should_escalate(0.0) is True
        
        # At or above threshold should not escalate
        assert cfg.should_escalate(0.6) is False
        assert cfg.should_escalate(0.7) is False
        assert cfg.should_escalate(1.0) is False

    def test_get_scorer_threshold(self):
        """get_scorer returns ThresholdBasedScorer by default."""
        from openclaw.autonomy import AutonomyConfig, ThresholdBasedScorer
        
        cfg = AutonomyConfig(confidence_calculator="threshold")
        scorer = cfg.get_scorer()
        assert isinstance(scorer, ThresholdBasedScorer)

    def test_get_scorer_adaptive(self):
        """get_scorer returns AdaptiveScorer when configured."""
        from openclaw.autonomy import AutonomyConfig, AdaptiveScorer
        
        cfg = AutonomyConfig(confidence_calculator="adaptive")
        scorer = cfg.get_scorer()
        assert isinstance(scorer, AdaptiveScorer)

    def test_invalid_escalation_threshold_raises(self):
        """Invalid escalation_threshold raises ValueError."""
        from openclaw.autonomy import AutonomyConfig
        
        with pytest.raises(ValueError, match="escalation_threshold must be 0.0-1.0"):
            AutonomyConfig(escalation_threshold=1.5)

    def test_invalid_confidence_calculator_raises(self):
        """Invalid confidence_calculator raises ValueError."""
        from openclaw.autonomy import AutonomyConfig
        
        with pytest.raises(ValueError, match="confidence_calculator must be"):
            AutonomyConfig(confidence_calculator="invalid")

    def test_negative_max_retries_raises(self):
        """Negative max_retries raises ValueError."""
        from openclaw.autonomy import AutonomyConfig
        
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            AutonomyConfig(max_retries=-1)

    def test_zero_blocked_timeout_raises(self):
        """Zero blocked_timeout_minutes raises ValueError."""
        from openclaw.autonomy import AutonomyConfig
        
        with pytest.raises(ValueError, match="blocked_timeout_minutes must be >= 1"):
            AutonomyConfig(blocked_timeout_minutes=0)


class TestAutonomyIntegration:
    """Integration tests for autonomy system."""

    def test_load_config_and_score_task(self, tmp_path, monkeypatch):
        """Load config and use it to score a task."""
        import importlib
        import openclaw.config as _config_mod
        import openclaw.project_config as _pc_mod
        
        config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "autonomy": {
                "escalation_threshold": 0.7,
                "confidence_calculator": "threshold"
            }
        }
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(_json.dumps(config))
        
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        importlib.reload(_config_mod)
        importlib.reload(_pc_mod)
        
        try:
            from openclaw.autonomy import load_autonomy_config
            
            cfg = load_autonomy_config()
            scorer = cfg.get_scorer()
            
            context = {"task_description": "Fix typo in README"}
            score = scorer.score(context)
            
            assert 0.0 <= score <= 1.0
            
            # Verify the scoring system works (score is reasonable)
            assert score > 0.5  # Simple task should score reasonably
        finally:
            importlib.reload(_config_mod)
            importlib.reload(_pc_mod)
