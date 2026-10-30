"""
Tests for temporal-safe mastery computation and EWMA decay modeling.
"""

import sqlite3
import pytest
from src.data_access import get_db_connection, init_db
from src.mastery import compute_all_learners_mastery, compute_learner_skill_mastery


@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # Run DDL
    from src.config import WORKSPACE_DIR
    with open(WORKSPACE_DIR / "schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    yield conn
    conn.close()


def test_default_unassessed_mastery_is_empty(memory_db):
    """Verifies that an unassessed learner returns no mastery records (defaulting to 0.0)."""
    mastery = compute_learner_skill_mastery(memory_db, "LRN-999999")
    assert mastery == {}


def test_ewma_mastery_calculation(memory_db):
    """Verifies exact EWMA mathematical progression."""
    # Setup test entities
    with memory_db:
        memory_db.execute("INSERT INTO learners VALUES ('LRN-000001', 'Test User', 'test@example.com', '2026-01-01T00:00:00Z', 'active')")
        memory_db.execute("INSERT INTO courses VALUES ('CRS-000001', 'Test Course', 'Desc', '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO skills VALUES ('SKL-000001', 'Python Basics', 'Eng', 1, '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO content_items VALUES ('CNT-000001', 'CRS-000001', 'Lesson 1', 'quiz', 1, 15, '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO content_skills VALUES ('CNT-000001', 'SKL-000001', 1.0)")

        # Three sequential attempts
        attempts = [
            ("ATT-1", "LRN-000001", "CNT-000001", "2026-02-01T10:00:00Z", "2026-02-01T10:30:00Z", 0.60, "completed"),
            ("ATT-2", "LRN-000001", "CNT-000001", "2026-02-02T10:00:00Z", "2026-02-02T10:30:00Z", 0.80, "completed"),
            ("ATT-3", "LRN-000001", "CNT-000001", "2026-02-03T10:00:00Z", "2026-02-03T10:30:00Z", 0.90, "completed"),
        ]
        memory_db.executemany("INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?, ?)", attempts)

        assessments = [
            ("ASM-000001", "LRN-000001", "SKL-000001", "ATT-1", 0.60, 0, "2026-02-01T10:30:00Z"),
            ("ASM-000002", "LRN-000001", "SKL-000001", "ATT-2", 0.80, 1, "2026-02-02T10:30:00Z"),
            ("ASM-000003", "LRN-000001", "SKL-000001", "ATT-3", 0.90, 1, "2026-02-03T10:30:00Z"),
        ]
        memory_db.executemany("INSERT INTO assessment_results VALUES (?, ?, ?, ?, ?, ?, ?)", assessments)

    # Manual EWMA calculation with alpha = 0.35:
    # m0 = 0.60
    # m1 = 0.35 * 0.80 + 0.65 * 0.60 = 0.28 + 0.39 = 0.67
    # m2 = 0.35 * 0.90 + 0.65 * 0.67 = 0.315 + 0.4355 = 0.7505
    mastery = compute_learner_skill_mastery(memory_db, "LRN-000001", alpha=0.35)
    assert "SKL-000001" in mastery
    assert abs(mastery["SKL-000001"] - 0.7505) < 0.001


def test_temporal_cutoff_prevents_future_leakage(memory_db):
    """Verifies that attempts after as_of_time do NOT leak into historical mastery."""
    with memory_db:
        memory_db.execute("INSERT INTO learners VALUES ('LRN-000001', 'Test User', 'test@example.com', '2026-01-01T00:00:00Z', 'active')")
        memory_db.execute("INSERT INTO courses VALUES ('CRS-000001', 'Test Course', 'Desc', '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO skills VALUES ('SKL-000001', 'Python Basics', 'Eng', 1, '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO content_items VALUES ('CNT-000001', 'CRS-000001', 'Lesson 1', 'quiz', 1, 15, '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO content_skills VALUES ('CNT-000001', 'SKL-000001', 1.0)")

        # Attempt 1: In the past (Feb 1)
        memory_db.execute("INSERT INTO attempts VALUES ('ATT-1', 'LRN-000001', 'CNT-000001', '2026-02-01T10:00:00Z', '2026-02-01T10:30:00Z', 0.50, 'completed')")
        memory_db.execute("INSERT INTO assessment_results VALUES ('ASM-000001', 'LRN-000001', 'SKL-000001', 'ATT-1', 0.50, 0, '2026-02-01T10:30:00Z')")

        # Attempt 2: In the future (Feb 15) with perfect score 1.0
        memory_db.execute("INSERT INTO attempts VALUES ('ATT-2', 'LRN-000001', 'CNT-000001', '2026-02-15T10:00:00Z', '2026-02-15T10:30:00Z', 1.00, 'completed')")
        memory_db.execute("INSERT INTO assessment_results VALUES ('ASM-000002', 'LRN-000001', 'SKL-000001', 'ATT-2', 1.00, 1, '2026-02-15T10:30:00Z')")

    # As of Feb 5 (before Attempt 2): Mastery must strictly reflect only Attempt 1 (0.50)
    past_mastery = compute_learner_skill_mastery(memory_db, "LRN-000001", as_of_time="2026-02-05T00:00:00Z")
    assert past_mastery["SKL-000001"] == 0.50

    # As of Feb 20 (after Attempt 2): Mastery incorporates Attempt 2 (0.35 * 1.0 + 0.65 * 0.5 = 0.675)
    future_mastery = compute_learner_skill_mastery(memory_db, "LRN-000001", as_of_time="2026-02-20T00:00:00Z")
    assert past_mastery["SKL-000001"] < future_mastery["SKL-000001"]
    assert abs(future_mastery["SKL-000001"] - 0.675) < 0.001


def test_batch_vs_single_mastery_consistency(memory_db):
    """Verifies that compute_all_learners_mastery matches compute_learner_skill_mastery."""
    with memory_db:
        memory_db.execute("INSERT INTO learners VALUES ('LRN-000001', 'User 1', 'u1@example.com', '2026-01-01T00:00:00Z', 'active')")
        memory_db.execute("INSERT INTO learners VALUES ('LRN-000002', 'User 2', 'u2@example.com', '2026-01-01T00:00:00Z', 'active')")
        memory_db.execute("INSERT INTO courses VALUES ('CRS-000001', 'Course', 'Desc', '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO skills VALUES ('SKL-000001', 'Skill 1', 'Eng', 1, '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO content_items VALUES ('CNT-000001', 'CRS-000001', 'Item 1', 'quiz', 1, 10, '2026-01-01T00:00:00Z')")
        memory_db.execute("INSERT INTO attempts VALUES ('ATT-1', 'LRN-000001', 'CNT-000001', '2026-02-01T10:00:00Z', '2026-02-01T10:30:00Z', 0.85, 'completed')")
        memory_db.execute("INSERT INTO attempts VALUES ('ATT-2', 'LRN-000002', 'CNT-000001', '2026-02-01T10:00:00Z', '2026-02-01T10:30:00Z', 0.70, 'completed')")
        memory_db.execute("INSERT INTO assessment_results VALUES ('ASM-1', 'LRN-000001', 'SKL-000001', 'ATT-1', 0.85, 1, '2026-02-01T10:30:00Z')")
        memory_db.execute("INSERT INTO assessment_results VALUES ('ASM-2', 'LRN-000002', 'SKL-000001', 'ATT-2', 0.70, 1, '2026-02-01T10:30:00Z')")

    all_mastery = compute_all_learners_mastery(memory_db)
    single_1 = compute_learner_skill_mastery(memory_db, "LRN-000001")
    single_2 = compute_learner_skill_mastery(memory_db, "LRN-000002")

    assert all_mastery["LRN-000001"] == single_1
    assert all_mastery["LRN-000002"] == single_2
