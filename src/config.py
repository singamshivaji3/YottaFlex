"""
Configuration module for the YottaFlex Synthetic Learning Data and Recommendation Workflow.
Centralizes volume tiers, algorithmic weights, ID format patterns, and storage paths.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


# Root directories
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = WORKSPACE_DIR / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
EXPORTS_DIR = WORKSPACE_DIR / "exports"
DOCS_DIR = WORKSPACE_DIR / "docs"

DEFAULT_SEED = 20261022
ALGORITHM_VERSION = "v1.2.0-explainable-heuristic"


@dataclass(frozen=True)
class ScaleConfig:
    """Defines target entity volumes for synthetic data generation."""
    name: str
    num_courses: int
    num_skills: int
    num_content_items: int
    num_learners: int
    num_attempts: int
    num_learning_paths: int


# Volume tiers matching requirements
SCALE_CONFIGS: Dict[str, ScaleConfig] = {
    "small": ScaleConfig(
        name="small",
        num_courses=5,
        num_skills=20,
        num_content_items=60,
        num_learners=50,
        num_attempts=600,
        num_learning_paths=30,
    ),
    "medium": ScaleConfig(
        name="medium",
        num_courses=15,
        num_skills=60,
        num_content_items=250,
        num_learners=500,
        num_attempts=8_000,
        num_learning_paths=300,
    ),
    "full": ScaleConfig(
        name="full",
        num_courses=50,
        num_skills=500,
        num_content_items=2_000,
        num_learners=10_000,
        num_attempts=500_000,
        num_learning_paths=5_000,
    ),
}


@dataclass(frozen=True)
class RecommenderWeights:
    """Configurable weights for multi-factor explainable recommendation scoring."""
    skill_gap: float = 0.45
    difficulty_fit: float = 0.35
    content_relevance: float = 0.20


@dataclass(frozen=True)
class MasteryConfig:
    """Thresholds and decay rates for learner mastery."""
    ewma_alpha: float = 0.35  # Recency weight in EWMA
    prerequisite_threshold: float = 0.70  # Min mastery needed to satisfy prerequisite
    mastery_threshold: float = 0.85  # Score at which a skill is considered mastered


# ID Prefix Formats matching official challenge specifications
ID_FORMATS = {
    "learner": "LRN-{:06d}",
    "course": "CRS-{:06d}",
    "skill": "SKL-{:06d}",
    "content": "CNT-{:06d}",
    "attempt": "ATT-{}-{:06d}",  # ATT-<learner_id>-<seq>
    "learning_path": "PATH-2026-{:06d}",
    "assessment": "ASM-{:06d}",
    "recommendation": "REC-{:06d}",
}
