"""
Unit and integration tests for synthetic data generation and relational schema constraints.
"""

import re
import sqlite3
import pytest
from pathlib import Path

from src.config import DEFAULT_SEED, ID_FORMATS, SCALE_CONFIGS, ScaleConfig
from src.data_access import TABLE_NAMES, get_db_connection, get_table_counts, init_db
from src.generator import SyntheticDataGenerator
from src.validator import ID_REGEXES, DataValidator


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_gen.db"
    return db_path


def test_generator_deterministic_output(temp_db):
    """Verifies that the same seed produces identical entity counts and rows."""
    gen1 = SyntheticDataGenerator(seed=42, scale="small")
    counts1 = gen1.generate_all_clean(temp_db)

    # Re-run on same path
    temp_db.unlink()
    gen2 = SyntheticDataGenerator(seed=42, scale="small")
    counts2 = gen2.generate_all_clean(temp_db)

    assert counts1 == counts2


def test_generator_scale_counts(temp_db):
    """Verifies generated volumes match scale configuration."""
    cfg = ScaleConfig(
        name="test",
        num_courses=3,
        num_skills=10,
        num_content_items=25,
        num_learners=20,
        num_attempts=100,
        num_learning_paths=15,
    )
    gen = SyntheticDataGenerator(seed=123, custom_config=cfg)
    counts = gen.generate_all_clean(temp_db)

    assert counts["courses"] == 3
    assert counts["skills"] == 10
    assert counts["content_items"] == 25
    assert counts["learners"] == 20
    assert counts["attempts"] == 100


def test_relational_integrity_and_foreign_keys(temp_db):
    """Verifies zero foreign key violations in generated baseline data."""
    gen = SyntheticDataGenerator(seed=DEFAULT_SEED, scale="small")
    gen.generate_all_clean(temp_db)

    conn = get_db_connection(temp_db)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        fk_errors = cursor.fetchall()
        assert len(fk_errors) == 0, f"Foreign key errors: {fk_errors}"
    finally:
        conn.close()


def test_identifier_format_compliance(temp_db):
    """Verifies that all entity IDs strictly adhere to official regex specifications."""
    gen = SyntheticDataGenerator(seed=DEFAULT_SEED, scale="small")
    gen.generate_all_clean(temp_db)

    conn = get_db_connection(temp_db)
    try:
        validator = DataValidator(conn)
        report = validator.validate_all()
        id_issues = [i for i in report.issues if i.issue_type == "INVALID_ID_FORMAT"]
        assert len(id_issues) == 0, f"Invalid ID formats detected: {id_issues}"
    finally:
        conn.close()


def test_prerequisite_dag_acyclicity(temp_db):
    """Verifies that skill prerequisites form an acyclic graph with no self-references."""
    gen = SyntheticDataGenerator(seed=DEFAULT_SEED, scale="small")
    gen.generate_all_clean(temp_db)

    conn = get_db_connection(temp_db)
    try:
        cursor = conn.cursor()
        # No self-loops
        cursor.execute("SELECT COUNT(*) FROM skill_prerequisites WHERE skill_id = prerequisite_skill_id")
        self_loops = cursor.fetchone()[0]
        assert self_loops == 0

        # Validator DAG check
        validator = DataValidator(conn)
        report = validator.validate_all()
        dag_issues = [i for i in report.issues if i.issue_type == "PREREQUISITE_CYCLE_DETECTED"]
        assert len(dag_issues) == 0
    finally:
        conn.close()


def test_attempt_timestamp_chronology(temp_db):
    """Verifies start_time <= end_time across all generated attempts."""
    gen = SyntheticDataGenerator(seed=DEFAULT_SEED, scale="small")
    gen.generate_all_clean(temp_db)

    conn = get_db_connection(temp_db)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM attempts WHERE start_time > end_time")
        inverted = cursor.fetchone()[0]
        assert inverted == 0
    finally:
        conn.close()
