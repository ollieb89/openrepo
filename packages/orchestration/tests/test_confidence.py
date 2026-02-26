"""
Tests for confidence scoring module.

Covers confidence factor validation, scoring calculations, and scorer implementations.
"""
import pytest
from openclaw.autonomy.confidence import (
    ConfidenceFactors,
    ThresholdBasedScorer,
    AdaptiveScorer,
    calculate_complexity_score,
    estimate_time_factor,
    past_success_factor,
    aggregate_confidence,
    validate_confidence_score,
)


class TestConfidenceFactors:
    """Tests for ConfidenceFactors dataclass."""

    def test_default_values(self):
        """Default values should be 0.5 for all factors."""
        factors = ConfidenceFactors()
        assert factors.complexity == 0.5
        assert factors.ambiguity == 0.5
        assert factors.past_success == 0.5
        assert factors.time_estimate == 0.5

    def test_custom_values(self):
        """Custom values should be accepted."""
        factors = ConfidenceFactors(
            complexity=0.8,
            ambiguity=0.2,
            past_success=0.9,
            time_estimate=0.3,
        )
        assert factors.complexity == 0.8
        assert factors.ambiguity == 0.2
        assert factors.past_success == 0.9
        assert factors.time_estimate == 0.3

    def test_invalid_values_rejected(self):
        """Values outside 0.0-1.0 range should raise ValueError."""
        with pytest.raises(ValueError, match="complexity must be between 0.0 and 1.0"):
            ConfidenceFactors(complexity=1.5)

        with pytest.raises(ValueError, match="ambiguity must be between 0.0 and 1.0"):
            ConfidenceFactors(ambiguity=-0.1)

        with pytest.raises(ValueError, match="past_success must be between 0.0 and 1.0"):
            ConfidenceFactors(past_success=2.0)

        with pytest.raises(ValueError, match="time_estimate must be between 0.0 and 1.0"):
            ConfidenceFactors(time_estimate=-0.5)


class TestCalculateComplexityScore:
    """Tests for calculate_complexity_score function."""

    def test_empty_description_returns_base(self):
        """Empty description returns base complexity."""
        score = calculate_complexity_score("")
        assert 0.3 <= score <= 0.5  # Base complexity range

    def test_simple_task_low_complexity(self):
        """Simple short task has low complexity."""
        score = calculate_complexity_score("Fix typo")
        assert score < 0.5

    def test_long_description_increases_complexity(self):
        """Longer descriptions increase complexity."""
        short = calculate_complexity_score("Fix bug")
        long = calculate_complexity_score("Fix bug " * 50)  # 100+ words
        assert long > short

    def test_technical_keywords_increase_complexity(self):
        """Technical keywords increase complexity score."""
        base = calculate_complexity_score("Do something simple")
        technical = calculate_complexity_score("Refactor database schema with concurrency")
        assert technical > base

    def test_multi_step_indicators_increase_complexity(self):
        """Multi-step language increases complexity."""
        base = calculate_complexity_score("Do task")
        multi_step = calculate_complexity_score("First do X, then do Y, finally do Z")
        assert multi_step > base

    def test_max_complexity_capped(self):
        """Complexity score is capped at 1.0."""
        very_complex = calculate_complexity_score(
            "Refactor architecture " * 200 + "concurrency distributed security"
        )
        assert very_complex <= 1.0


class TestEstimateTimeFactor:
    """Tests for estimate_time_factor function."""

    def test_negative_or_zero_returns_default(self):
        """Zero or negative hours returns default."""
        assert estimate_time_factor(0) == pytest.approx(0.5, abs=0.01)
        assert estimate_time_factor(-1) == pytest.approx(0.5, abs=0.01)

    def test_short_tasks_high_confidence(self):
        """Short tasks (<=1 hour) have high time factor."""
        assert estimate_time_factor(0.5) == pytest.approx(0.9, abs=0.01)
        assert estimate_time_factor(1.0) == pytest.approx(0.9, abs=0.01)

    def test_medium_tasks_decreasing_confidence(self):
        """Medium tasks have decreasing time factor."""
        four_hours = estimate_time_factor(4.0)
        eight_hours = estimate_time_factor(8.0)
        sixteen_hours = estimate_time_factor(16.0)
        assert four_hours > eight_hours > sixteen_hours

    def test_long_tasks_low_confidence(self):
        """Long tasks have low time factor."""
        forty_hours = estimate_time_factor(40.0)
        assert forty_hours == pytest.approx(0.5, abs=0.01)

    def test_very_long_tasks_min_confidence(self):
        """Very long tasks approach minimum confidence."""
        very_long = estimate_time_factor(200.0)
        assert very_long >= 0.1  # Min floor
        assert very_long < 0.5


class TestPastSuccessFactor:
    """Tests for past_success_factor function."""

    def test_returns_stub_value(self):
        """Returns neutral stub value for now."""
        score = past_success_factor("any_project", "any_type")
        assert score == 0.5

    def test_consistent_for_same_inputs(self):
        """Returns same value for same inputs."""
        score1 = past_success_factor("project_a", "bugfix")
        score2 = past_success_factor("project_a", "bugfix")
        assert score1 == score2


class TestAggregateConfidence:
    """Tests for aggregate_confidence function."""

    def test_all_perfect_factors(self):
        """All perfect factors (low complexity/ambiguity, high success/time) give high score."""
        factors = ConfidenceFactors(
            complexity=0.0,  # simple
            ambiguity=0.0,   # clear
            past_success=1.0,  # excellent
            time_estimate=1.0,  # quick
        )
        score = aggregate_confidence(factors)
        assert score > 0.9

    def test_all_worst_factors(self):
        """All worst factors give low score."""
        factors = ConfidenceFactors(
            complexity=1.0,  # complex
            ambiguity=1.0,   # unclear
            past_success=0.0,  # no success
            time_estimate=0.0,  # long
        )
        score = aggregate_confidence(factors)
        assert score < 0.1

    def test_neutral_factors(self):
        """Neutral (0.5) factors give mid-range score."""
        factors = ConfidenceFactors()
        score = aggregate_confidence(factors)
        assert 0.4 < score < 0.6

    def test_score_in_valid_range(self):
        """Result always in 0.0-1.0 range."""
        test_cases = [
            ConfidenceFactors(0.0, 0.0, 0.0, 0.0),
            ConfidenceFactors(1.0, 1.0, 1.0, 1.0),
            ConfidenceFactors(0.2, 0.8, 0.5, 0.3),
        ]
        for factors in test_cases:
            score = aggregate_confidence(factors)
            assert 0.0 <= score <= 1.0


class TestValidateConfidenceScore:
    """Tests for validate_confidence_score function."""

    def test_valid_scores_pass(self):
        """Valid scores (0.0-1.0) pass without error."""
        validate_confidence_score(0.0)
        validate_confidence_score(0.5)
        validate_confidence_score(1.0)

    def test_invalid_type_raises(self):
        """Non-numeric types raise TypeError."""
        with pytest.raises(TypeError, match="must be a number"):
            validate_confidence_score("0.5")
        with pytest.raises(TypeError, match="must be a number"):
            validate_confidence_score(None)

    def test_out_of_range_raises(self):
        """Scores outside 0.0-1.0 raise ValueError."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_confidence_score(1.5)
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            validate_confidence_score(-0.1)


class TestThresholdBasedScorer:
    """Tests for ThresholdBasedScorer class."""

    def test_implements_protocol(self):
        """ThresholdBasedScorer implements ConfidenceScorer protocol."""
        from openclaw.autonomy.confidence import ConfidenceScorer
        scorer = ThresholdBasedScorer()
        assert isinstance(scorer, ConfidenceScorer)

    def test_returns_score_in_range(self):
        """score() returns value in 0.0-1.0 range."""
        scorer = ThresholdBasedScorer()
        context = {"task_description": "Fix bug in login form"}
        score = scorer.score(context)
        assert 0.0 <= score <= 1.0

    def test_uses_provided_factors(self):
        """Uses provided ConfidenceFactors when given."""
        scorer = ThresholdBasedScorer()
        factors = ConfidenceFactors(
            complexity=0.1,
            ambiguity=0.1,
            past_success=0.9,
            time_estimate=0.9,
        )
        score = scorer.score({"factors": factors})
        assert score > 0.7  # Should be high with good factors

    def test_rejects_invalid_factors_type(self):
        """Raises TypeError for invalid factors type."""
        scorer = ThresholdBasedScorer()
        with pytest.raises(TypeError, match="must be ConfidenceFactors"):
            scorer.score({"factors": {"complexity": 0.5}})

    def test_simple_task_higher_confidence(self):
        """Simple task description yields higher confidence."""
        scorer = ThresholdBasedScorer()
        simple = scorer.score({"task_description": "Fix typo"})
        complex_task = scorer.score({"task_description": "Refactor distributed microservices architecture"})
        assert simple > complex_task

    def test_clear_requirements_higher_confidence(self):
        """Clear acceptance criteria reduce ambiguity."""
        scorer = ThresholdBasedScorer()
        vague = scorer.score({"task_description": "Make it better"})
        clear = scorer.score({"task_description": "Given X, when Y, then Z. Expected: return 200."})
        assert clear > vague


class TestAdaptiveScorer:
    """Tests for AdaptiveScorer placeholder."""

    def test_implements_protocol(self):
        """AdaptiveScorer implements ConfidenceScorer protocol."""
        from openclaw.autonomy.confidence import ConfidenceScorer
        scorer = AdaptiveScorer()
        assert isinstance(scorer, ConfidenceScorer)

    def test_delegates_to_threshold_scorer(self):
        """Currently delegates to ThresholdBasedScorer."""
        adaptive = AdaptiveScorer()
        threshold = ThresholdBasedScorer()
        context = {"task_description": "Test task"}
        adaptive_score = adaptive.score(context)
        threshold_score = threshold.score(context)
        assert adaptive_score == pytest.approx(threshold_score, abs=0.001)

    def test_returns_score_in_range(self):
        """score() returns value in 0.0-1.0 range."""
        scorer = AdaptiveScorer()
        context = {"task_description": "Test task"}
        score = scorer.score(context)
        assert 0.0 <= score <= 1.0


class TestConfidenceIntegration:
    """Integration tests for confidence system."""

    def test_end_to_end_simple_task(self):
        """End-to-end: simple bug fix task."""
        scorer = ThresholdBasedScorer()
        context = {
            "task_description": "Fix typo in README.md",
            "hours_estimate": 0.5,
            "project": "docs",
            "task_type": "bugfix",
        }
        score = scorer.score(context)
        assert score > 0.6  # Simple task should have high confidence

    def test_end_to_end_complex_task(self):
        """End-to-end: complex architecture task."""
        scorer = ThresholdBasedScorer()
        context = {
            "task_description": "Refactor monolith to microservices with distributed transactions",
            "hours_estimate": 80.0,
            "project": "backend",
            "task_type": "refactor",
        }
        score = scorer.score(context)
        assert score < 0.55  # Complex task should have lower confidence

    def test_escalation_threshold_logic(self):
        """Test escalation decision based on threshold."""
        threshold = 0.6
        
        scorer = ThresholdBasedScorer()
        
        # Low confidence task should trigger escalation
        low_confidence_context = {
            "task_description": "Research and investigate potential solutions for unknown problem",
            "hours_estimate": 40.0,
        }
        low_score = scorer.score(low_confidence_context)
        assert low_score < threshold
        
        # High confidence task should not trigger escalation
        high_confidence_context = {
            "task_description": "Fix typo in docs. Given file, when typo found, then fix it.",
            "hours_estimate": 0.5,
        }
        high_score = scorer.score(high_confidence_context)
        assert high_score >= threshold
