"""
Tests for prerequisite-aware recommendation ranking, gating, and explainability.
"""

import sqlite3
import pytest
from src.config import ALGORITHM_VERSION, MasteryConfig, RecommenderWeights
from src.recommender import LearningRecommender


@pytest.fixture
def recommender_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    from src.config import WORKSPACE_DIR
    with open(WORKSPACE_DIR / "schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    with conn:
        # Base entities
        conn.execute("INSERT INTO learners VALUES ('LRN-000001', 'Alice', 'alice@test.org', '2026-01-01T00:00:00Z', 'active')")
        conn.execute("INSERT INTO courses VALUES ('CRS-000001', 'CS Track', 'Desc', '2026-01-01T00:00:00Z')")

        # Two skills: SKL-1 (Foundations) and SKL-2 (Advanced, requires SKL-1)
        conn.execute("INSERT INTO skills VALUES ('SKL-000001', 'Basics', 'CS', 1, '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO skills VALUES ('SKL-000002', 'Advanced CS', 'CS', 3, '2026-01-01T00:00:00Z')")

        # Prerequisite edge: SKL-2 requires SKL-1 (threshold 0.70)
        conn.execute("INSERT INTO skill_prerequisites VALUES ('SKL-000002', 'SKL-000001', 0.70, '2026-01-01T00:00:00Z')")

        # Content items
        conn.execute("INSERT INTO content_items VALUES ('CNT-000001', 'CRS-000001', 'Basics Intro', 'video', 1, 10, '2026-01-01T00:00:00Z')")
        conn.execute("INSERT INTO content_items VALUES ('CNT-000002', 'CRS-000001', 'Advanced Topics', 'exercise', 3, 30, '2026-01-01T00:00:00Z')")

        # Mappings
        conn.execute("INSERT INTO content_skills VALUES ('CNT-000001', 'SKL-000001', 1.0)")
        conn.execute("INSERT INTO content_skills VALUES ('CNT-000002', 'SKL-000002', 1.0)")

    yield conn
    conn.close()


def test_prerequisite_gate_blocks_advanced_content(recommender_db):
    """When learner has not mastered SKL-1, SKL-2 content MUST NOT be recommended."""
    recommender = LearningRecommender()
    recs = recommender.recommend_for_learner(recommender_db, "LRN-000001", top_k=5)

    # Only CNT-000001 (Basics) should be recommended; CNT-000002 must be blocked
    recommended_content = [r["content_id"] for r in recs]
    assert "CNT-000001" in recommended_content
    assert "CNT-000002" not in recommended_content


def test_prerequisite_gate_unlocks_content_when_mastered(recommender_db):
    """Once learner achieves >= 0.70 on SKL-1, SKL-2 content becomes eligible."""
    # Add passing attempt for SKL-1
    with recommender_db:
        recommender_db.execute("INSERT INTO attempts VALUES ('ATT-1', 'LRN-000001', 'CNT-000001', '2026-02-01T10:00:00Z', '2026-02-01T10:30:00Z', 0.90, 'completed')")
        recommender_db.execute("INSERT INTO assessment_results VALUES ('ASM-1', 'LRN-000001', 'SKL-000001', 'ATT-1', 0.90, 1, '2026-02-01T10:30:00Z')")

    recommender = LearningRecommender()
    recs = recommender.recommend_for_learner(recommender_db, "LRN-000001", top_k=5)

    recommended_content = [r["content_id"] for r in recs]
    # CNT-000002 is now unlocked!
    assert "CNT-000002" in recommended_content


def test_recommendation_explainability_and_attributes(recommender_db):
    """Verifies that each recommendation contains complete explainability metadata."""
    recommender = LearningRecommender()
    recs = recommender.recommend_for_learner(recommender_db, "LRN-000001", top_k=5)

    assert len(recs) > 0
    top_rec = recs[0]

    assert "rank_order" in top_rec and top_rec["rank_order"] == 1
    assert "score" in top_rec and 0.0 <= top_rec["score"] <= 1.0
    assert "reason_code" in top_rec and len(top_rec["reason_code"]) > 0
    assert "reason_description" in top_rec and len(top_rec["reason_description"]) > 0
    assert top_rec["algorithm_version"] == ALGORITHM_VERSION
    assert "skill_gap" in top_rec
    assert "difficulty_fit" in top_rec


def test_completed_high_score_content_excluded(recommender_db):
    """Verifies that already completed content items are not redundantly recommended."""
    # Complete CNT-000001 with high score 0.95
    with recommender_db:
        recommender_db.execute("INSERT INTO attempts VALUES ('ATT-1', 'LRN-000001', 'CNT-000001', '2026-02-01T10:00:00Z', '2026-02-01T10:30:00Z', 0.95, 'completed')")

    recommender = LearningRecommender()
    recs = recommender.recommend_for_learner(recommender_db, "LRN-000001", top_k=5)

    # CNT-000001 should be excluded
    rec_ids = [r["content_id"] for r in recs]
    assert "CNT-000001" not in rec_ids
