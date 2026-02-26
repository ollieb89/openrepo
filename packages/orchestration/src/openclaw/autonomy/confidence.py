"""
Confidence scoring for agent autonomy decisions.

This module provides the ConfidenceScorer protocol and implementations for
calculating confidence scores based on task complexity, ambiguity, past success,
and time estimates.
"""

import os
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class ConfidenceFactors:
    """
    Factors that contribute to confidence scoring.
    
    All factors are normalized to 0.0-1.0 range where higher is better
    (more confidence in successful completion).
    """
    complexity: float = 0.5  # 0.0 = simple, 1.0 = highly complex
    ambiguity: float = 0.5   # 0.0 = clear requirements, 1.0 = very ambiguous
    past_success: float = 0.5  # 0.0 = no past success, 1.0 = excellent track record
    time_estimate: float = 0.5  # 0.0 = very short/quick, 1.0 = long/complex
    
    def __post_init__(self):
        """Validate all factors are within valid range."""
        for field_name, value in [
            ("complexity", self.complexity),
            ("ambiguity", self.ambiguity),
            ("past_success", self.past_success),
            ("time_estimate", self.time_estimate),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0.0 and 1.0, got {value}"
                )


@runtime_checkable
class ConfidenceScorer(Protocol):
    """
    Protocol for confidence scoring implementations.
    
    Implementations calculate a confidence score (0.0-1.0) based on task context
    and factors. Scores below the escalation threshold indicate the task should
    be escalated to human oversight.
    """
    
    def score(self, context: dict) -> float:
        """
        Calculate confidence score from task context.
        
        Args:
            context: Dictionary containing task information including:
                - task_description: str describing the task
                - factors: ConfidenceFactors (optional)
                - project: str project identifier (optional)
                - task_type: str type of task (optional)
                - hours_estimate: float estimated hours (optional)
        
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        ...


def calculate_complexity_score(task_description: str) -> float:
    """
    Calculate complexity score based on task description analysis.
    
    Heuristics:
    - Longer tasks tend to be more complex
    - Tasks with many technical keywords indicate higher complexity
    - Tasks with multiple steps (numbered lists, "and then", etc.) are more complex
    
    Args:
        task_description: Description of the task
        
    Returns:
        float: Complexity score 0.0-1.0
    """
    if not task_description:
        return 0.5
    
    score = 0.3  # base complexity
    
    # Length factor: longer descriptions suggest more complexity
    word_count = len(task_description.split())
    if word_count > 100:
        score += 0.2
    elif word_count > 50:
        score += 0.1
    
    # Technical complexity indicators
    technical_keywords = [
        r"\b(architecture|refactor|redesign|migrate|implement)\b",
        r"\b(database|schema|api|integration|microservice)\b",
        r"\b(concurrency|async|threading|parallel|distributed)\b",
        r"\b(security|authentication|authorization|encryption)\b",
        r"\b(performance|optimization|caching|scaling)\b",
    ]
    
    for pattern in technical_keywords:
        if re.search(pattern, task_description, re.IGNORECASE):
            score += 0.05
    
    # Multi-step indicators
    multi_step_patterns = [
        r"\b(first|then|next|after|finally)\b",
        r"\d+\)\s+",  # numbered lists like "1) "
        r"\b(step\s+\d+)\b",
    ]
    
    for pattern in multi_step_patterns:
        if re.search(pattern, task_description, re.IGNORECASE):
            score += 0.05
    
    return min(1.0, score)


def estimate_time_factor(hours_estimate: float) -> float:
    """
    Convert time estimate to a confidence factor.
    
    Longer tasks have lower inherent confidence due to:
    - More opportunities for issues
    - Higher cognitive load
    - Greater uncertainty over time
    
    Args:
        hours_estimate: Estimated hours to complete task
        
    Returns:
        float: Time factor 0.0-1.0 (higher = more confidence/shorter task)
    """
    if hours_estimate <= 0:
        return 0.5
    
    # Scale: 0-1 hour = high confidence, 40+ hours = low confidence
    if hours_estimate <= 1:
        return 0.9
    elif hours_estimate <= 4:
        return 0.8
    elif hours_estimate <= 8:
        return 0.7
    elif hours_estimate <= 16:
        return 0.6
    elif hours_estimate <= 40:
        return 0.5
    else:
        return max(0.1, 0.5 - (hours_estimate - 40) / 200)


def past_success_factor(project: str, task_type: str) -> float:
    """
    Calculate past success factor for a project/task type combination.
    
    This is a stub implementation that returns a neutral score.
    Future implementation will track actual success rates per project/task type.
    
    Args:
        project: Project identifier
        task_type: Type of task (e.g., "feature", "bugfix", "refactor")
        
    Returns:
        float: Past success factor 0.0-1.0
    """
    # Stub: return neutral score
    # Future: query success history database
    return 0.5


def aggregate_confidence(factors: ConfidenceFactors) -> float:
    """
    Aggregate confidence factors into a single score.
    
    Uses a weighted average that prioritizes:
    - Low ambiguity (clear requirements)
    - Manageable complexity
    - Past success track record
    - Reasonable time estimate
    
    Args:
        factors: ConfidenceFactors dataclass instance
        
    Returns:
        float: Aggregated confidence score 0.0-1.0
    """
    # Weights for each factor (must sum to 1.0)
    weights = {
        "complexity": 0.25,    # lower complexity = higher confidence
        "ambiguity": 0.30,     # lower ambiguity = higher confidence
        "past_success": 0.25,  # higher past success = higher confidence
        "time_estimate": 0.20, # shorter time = higher confidence
    }
    
    # For complexity and ambiguity, invert (lower is better)
    # For past_success and time_estimate, use directly (higher is better)
    score = (
        (1.0 - factors.complexity) * weights["complexity"] +
        (1.0 - factors.ambiguity) * weights["ambiguity"] +
        factors.past_success * weights["past_success"] +
        factors.time_estimate * weights["time_estimate"]
    )
    
    # Clamp to valid range
    return max(0.0, min(1.0, score))


class ThresholdBasedScorer:
    """
    Default confidence scorer using threshold-based calculation.
    
    This implementation uses heuristics to estimate confidence factors
    from task context, then aggregates them into a final score.
    
    Example:
        scorer = ThresholdBasedScorer()
        context = {
            "task_description": "Fix bug in login form",
            "hours_estimate": 2.0,
            "project": "myapp",
            "task_type": "bugfix",
        }
        score = scorer.score(context)  # Returns 0.0-1.0
    """
    
    def score(self, context: dict) -> float:
        """
        Calculate confidence score using threshold-based heuristics.
        
        Args:
            context: Task context dictionary
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        # Extract or calculate factors
        task_description = context.get("task_description", "")
        hours_estimate = context.get("hours_estimate", 0.0)
        project = context.get("project", "")
        task_type = context.get("task_type", "")
        
        # Use provided factors if available, otherwise calculate
        if "factors" in context:
            factors = context["factors"]
            if not isinstance(factors, ConfidenceFactors):
                raise TypeError(
                    f"factors must be ConfidenceFactors, got {type(factors).__name__}"
                )
        else:
            factors = ConfidenceFactors(
                complexity=calculate_complexity_score(task_description),
                ambiguity=self._estimate_ambiguity(task_description),
                past_success=past_success_factor(project, task_type),
                time_estimate=estimate_time_factor(hours_estimate),
            )
        
        return aggregate_confidence(factors)
    
    def _estimate_ambiguity(self, task_description: str) -> float:
        """
        Estimate ambiguity level from task description.
        
        Heuristics:
        - Missing context = higher ambiguity
        - Uncertainty words = higher ambiguity
        - Clear acceptance criteria = lower ambiguity
        
        Args:
            task_description: Task description
            
        Returns:
            float: Ambiguity score 0.0-1.0
        """
        if not task_description:
            return 0.8  # high ambiguity for empty descriptions
        
        score = 0.4  # base ambiguity
        
        # Uncertainty indicators increase ambiguity
        uncertainty_words = [
            r"\b(maybe|possibly|perhaps|might|could|should|consider)\b",
            r"\b(unclear|uncertain|ambiguous|vague|tbd|tbc)\b",
            r"\b(investigate|research|explore|look into)\b",
        ]
        
        for pattern in uncertainty_words:
            if re.search(pattern, task_description, re.IGNORECASE):
                score += 0.1
        
        # Clear acceptance criteria reduce ambiguity
        clarity_indicators = [
            r"\b(acceptance criteria|given.*when.*then|a/c)\b",
            r"\b(expected|should return|must produce)\b",
            r"\b(definition of done|dod)\b",
        ]
        
        for pattern in clarity_indicators:
            if re.search(pattern, task_description, re.IGNORECASE):
                score -= 0.1
        
        return max(0.0, min(1.0, score))


class AdaptiveScorer:
    """
    Placeholder for future ML-based adaptive confidence scorer.
    
    This class is a stub that will be implemented with machine learning
    techniques to learn from actual task outcomes and improve scoring
    accuracy over time.
    """
    
    def score(self, context: dict) -> float:
        """
        Placeholder implementation that delegates to ThresholdBasedScorer.
        
        Future implementation will use historical data and ML models.
        """
        # For now, delegate to threshold-based scorer
        return ThresholdBasedScorer().score(context)


def validate_confidence_score(score: float) -> None:
    """
    Validate that a confidence score is within valid range.
    
    Args:
        score: The confidence score to validate
        
    Raises:
        ValueError: If score is outside 0.0-1.0 range
    """
    if not isinstance(score, (int, float)):
        raise TypeError(f"Confidence score must be a number, got {type(score).__name__}")
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {score}")


__all__ = [
    "ConfidenceFactors",
    "ConfidenceScorer",
    "ThresholdBasedScorer",
    "AdaptiveScorer",
    "calculate_complexity_score",
    "estimate_time_factor",
    "past_success_factor",
    "aggregate_confidence",
    "validate_confidence_score",
]
