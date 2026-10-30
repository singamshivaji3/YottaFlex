"""
Temporal-Safe Mastery Engine for the YottaFlex Learning Recommendation Workflow.
Calculates learner skill mastery strictly as-of an evaluation timestamp using EWMA,
preventing future attempts or assessment results from leaking into historical state.
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


def compute_learner_skill_mastery(
    conn: sqlite3.Connection,
    learner_id: str,
    as_of_time: Optional[str] = None,
    alpha: float = 0.35,
) -> Dict[str, float]:
    """
    Computes skill mastery scores in [0.0, 1.0] for a single learner as of a given timestamp.
    Applies Exponentially Weighted Moving Average (EWMA) on chronologically ordered assessments.
    
    Temporal safety rule: Any assessment with assessed_at > as_of_time is strictly excluded.
    """
    query = """
        SELECT ar.skill_id, ar.assessed_score, ar.assessed_at
        FROM assessment_results ar
        JOIN attempts a ON ar.attempt_id = a.attempt_id
        WHERE ar.learner_id = ?
    """
    params: List[Any] = [learner_id]

    if as_of_time:
        query += " AND ar.assessed_at <= ? AND a.end_time <= ?"
        params.extend([as_of_time, as_of_time])

    query += " ORDER BY ar.skill_id, ar.assessed_at ASC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Group assessments by skill
    assessments_by_skill: Dict[str, List[float]] = {}
    for r in rows:
        skill_id = r["skill_id"]
        score = float(r["assessed_score"])
        assessments_by_skill.setdefault(skill_id, []).append(score)

    mastery_scores: Dict[str, float] = {}
    for skill_id, scores in assessments_by_skill.items():
        if not scores:
            mastery_scores[skill_id] = 0.0
            continue
        # Chronological EWMA
        m = scores[0]
        for score in scores[1:]:
            m = alpha * score + (1.0 - alpha) * m
        mastery_scores[skill_id] = round(min(1.0, max(0.0, m)), 4)

    return mastery_scores


def compute_all_learners_mastery(
    conn: sqlite3.Connection,
    as_of_time: Optional[str] = None,
    alpha: float = 0.35,
) -> Dict[str, Dict[str, float]]:
    """
    Computes mastery scores for all learners as of a given timestamp.
    Optimized single-pass query over all assessments up to cutoff.
    """
    query = """
        SELECT ar.learner_id, ar.skill_id, ar.assessed_score, ar.assessed_at
        FROM assessment_results ar
        JOIN attempts a ON ar.attempt_id = a.attempt_id
    """
    params: List[Any] = []
    if as_of_time:
        query += " WHERE ar.assessed_at <= ? AND a.end_time <= ?"
        params.extend([as_of_time, as_of_time])

    query += " ORDER BY ar.learner_id, ar.skill_id, ar.assessed_at ASC"

    cursor = conn.cursor()
    cursor.execute(query, params)

    mastery_by_learner: Dict[str, Dict[str, List[float]]] = {}
    while True:
        rows = cursor.fetchmany(10_000)
        if not rows:
            break
        for r in rows:
            lid = r["learner_id"]
            sid = r["skill_id"]
            score = float(r["assessed_score"])
            if lid not in mastery_by_learner:
                mastery_by_learner[lid] = {}
            mastery_by_learner[lid].setdefault(sid, []).append(score)

    results: Dict[str, Dict[str, float]] = {}
    for lid, skill_map in mastery_by_learner.items():
        results[lid] = {}
        for sid, scores in skill_map.items():
            m = scores[0]
            for s in scores[1:]:
                m = alpha * s + (1.0 - alpha) * m
            results[lid][sid] = round(min(1.0, max(0.0, m)), 4)

    return results


def get_learner_skill_timeline(
    conn: sqlite3.Connection,
    learner_id: str,
    skill_id: str,
    as_of_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Returns chronological timeline of assessments and running mastery for inspection/explainability."""
    query = """
        SELECT ar.assessment_id, ar.attempt_id, ar.assessed_score, ar.passed, ar.assessed_at
        FROM assessment_results ar
        WHERE ar.learner_id = ? AND ar.skill_id = ?
    """
    params: List[Any] = [learner_id, skill_id]
    if as_of_time:
        query += " AND ar.assessed_at <= ?"
        params.append(as_of_time)

    query += " ORDER BY ar.assessed_at ASC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    timeline = []
    running_mastery = 0.0
    alpha = 0.35

    for idx, row in enumerate(cursor.fetchall()):
        score = float(row["assessed_score"])
        if idx == 0:
            running_mastery = score
        else:
            running_mastery = alpha * score + (1.0 - alpha) * running_mastery

        timeline.append({
            "assessment_id": row["assessment_id"],
            "attempt_id": row["attempt_id"],
            "assessed_score": score,
            "passed": bool(row["passed"]),
            "assessed_at": row["assessed_at"],
            "running_mastery": round(running_mastery, 4),
        })

    return timeline
