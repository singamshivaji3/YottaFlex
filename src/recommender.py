"""
Explainable, Prerequisite-Aware Recommendation Engine.
Enforces hard pedagogical prerequisite gates before ranking eligible learning activities
with multi-factor explainable scoring and reason codes.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from src.config import (
    ALGORITHM_VERSION,
    ID_FORMATS,
    MasteryConfig,
    RecommenderWeights,
)
from src.mastery import compute_learner_skill_mastery


class LearningRecommender:
    """
    Prerequisite-aware, multi-factor learning activity recommender.
    """

    def __init__(
        self,
        weights: Optional[RecommenderWeights] = None,
        mastery_config: Optional[MasteryConfig] = None,
    ):
        self.weights = weights or RecommenderWeights()
        self.mastery_config = mastery_config or MasteryConfig()

    def get_prerequisite_graph(self, conn: sqlite3.Connection) -> Dict[str, List[Tuple[str, float]]]:
        """Loads all skill prerequisites: skill_id -> list of (prerequisite_skill_id, min_threshold)."""
        cursor = conn.cursor()
        cursor.execute("SELECT skill_id, prerequisite_skill_id, min_mastery_threshold FROM skill_prerequisites")
        graph: Dict[str, List[Tuple[str, float]]] = {}
        for row in cursor.fetchall():
            graph.setdefault(row["skill_id"], []).append(
                (row["prerequisite_skill_id"], float(row["min_mastery_threshold"]))
            )
        return graph

    def check_prerequisites_met(
        self,
        skill_id: str,
        prereq_graph: Dict[str, List[Tuple[str, float]]],
        learner_mastery: Dict[str, float],
    ) -> Tuple[bool, Optional[str], Optional[float], Optional[float]]:
        """
        Validates whether all prerequisites for a skill are met.
        Returns: (is_eligible, failing_prereq_id, current_mastery, required_threshold)
        """
        prereqs = prereq_graph.get(skill_id, [])
        for prereq_id, threshold in prereqs:
            current_m = learner_mastery.get(prereq_id, 0.0)
            if current_m < threshold:
                return False, prereq_id, current_m, threshold
        return True, None, None, None

    def recommend_for_learner(
        self,
        conn: sqlite3.Connection,
        learner_id: str,
        as_of_time: Optional[str] = None,
        top_k: int = 5,
        prereq_graph: Optional[Dict[str, List[Tuple[str, float]]]] = None,
        all_skills: Optional[Dict[str, Any]] = None,
        content_rows: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Produces top-K ranked, explainable recommendations for a specific learner as of query cutoff.
        """
        if prereq_graph is None:
            prereq_graph = self.get_prerequisite_graph(conn)

        # 1. Compute temporal-safe skill mastery as-of cutoff
        learner_mastery = compute_learner_skill_mastery(conn, learner_id, as_of_time=as_of_time)

        # 2. Identify candidate skills (deficit < mastery_threshold)
        cursor = conn.cursor()
        if all_skills is None:
            cursor.execute("SELECT skill_id, name, domain, difficulty_level FROM skills")
            all_skills = {r["skill_id"]: r for r in cursor.fetchall()}

        # 3. Load completed high-scoring content items to avoid duplicate recommendations
        attempt_query = """
            SELECT DISTINCT content_id FROM attempts 
            WHERE learner_id = ? AND status = 'completed' AND score >= 0.85
        """
        params: List[Any] = [learner_id]
        if as_of_time:
            attempt_query += " AND end_time <= ?"
            params.append(as_of_time)
        cursor.execute(attempt_query, params)
        completed_content_ids: Set[str] = {r["content_id"] for r in cursor.fetchall()}

        # 4. Fetch content items and their associated skills
        if content_rows is None:
            cursor.execute("""
                SELECT ci.content_id, ci.title, ci.content_type, ci.difficulty_level, ci.duration_minutes,
                       cs.skill_id, cs.relevance_weight
                FROM content_items ci
                JOIN content_skills cs ON ci.content_id = cs.content_id
            """)
            content_rows = cursor.fetchall()

        candidates = []
        for r in content_rows:
            cid = r["content_id"]
            sid = r["skill_id"]

            # Exclude already mastered content
            if cid in completed_content_ids:
                continue

            current_m = learner_mastery.get(sid, 0.0)
            # Skill must have a deficit
            if current_m >= self.mastery_config.mastery_threshold:
                continue

            # Hard prerequisite gate
            eligible, fail_prereq, curr_p_m, req_p_m = self.check_prerequisites_met(
                sid, prereq_graph, learner_mastery
            )
            if not eligible:
                continue

            # Calculate explainable score components
            skill_gap = 1.0 - current_m
            content_diff = r["difficulty_level"]
            learner_level = 1.0 + 4.0 * current_m
            difficulty_fit = 1.0 - (abs(learner_level - content_diff) / 4.0)
            relevance = float(r["relevance_weight"])

            score = (
                self.weights.skill_gap * skill_gap
                + self.weights.difficulty_fit * difficulty_fit
                + self.weights.content_relevance * relevance
            )
            score = round(min(1.0, max(0.0, score)), 4)

            # Determine reason code and human-readable description
            skill_meta = all_skills.get(sid)
            skill_name = skill_meta["name"] if skill_meta else sid

            reason_code = "SKILL_DEFICIT_HIGH_PRIORITY" if skill_gap > 0.5 else "SKILL_PRACTICE_RECOMMENDED"
            reason_desc = (
                f"Target skill '{skill_name}' mastery is {current_m:.2f} (gap: {skill_gap:.2f}). "
                f"Prerequisites verified. Content difficulty (L{content_diff}) matches estimated ability (L{learner_level:.1f})."
            )

            candidates.append({
                "learner_id": learner_id,
                "content_id": cid,
                "content_title": r["title"],
                "skill_id": sid,
                "skill_name": skill_name,
                "score": score,
                "skill_gap": round(skill_gap, 4),
                "difficulty_fit": round(difficulty_fit, 4),
                "relevance": relevance,
                "reason_code": reason_code,
                "reason_description": reason_desc,
            })

        # Deterministic ranking: score descending, then content_id ascending
        candidates.sort(key=lambda x: (-x["score"], x["content_id"]))

        # Deduplicate to keep best recommendation per content item
        seen_content: Set[str] = set()
        deduped = []
        for c in candidates:
            if c["content_id"] not in seen_content:
                seen_content.add(c["content_id"])
                deduped.append(c)
                if len(deduped) >= top_k:
                    break

        # Assign ranks
        deterministic_default_time = "2026-10-22T12:00:00Z"
        for idx, rec in enumerate(deduped, start=1):
            rec["rank_order"] = idx
            rec["algorithm_version"] = ALGORITHM_VERSION
            rec["generated_at"] = as_of_time or deterministic_default_time

        return deduped

    def generate_and_save_all_recommendations(
        self,
        conn: sqlite3.Connection,
        as_of_time: Optional[str] = None,
        top_k: int = 5,
    ) -> int:
        """
        Generates and stores recommendations for all active learners into the recommendations table.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT learner_id FROM learners WHERE status = 'active'")
        active_learners = [r["learner_id"] for r in cursor.fetchall()]

        cursor.execute("SELECT skill_id, name, domain, difficulty_level FROM skills")
        all_skills = {r["skill_id"]: r for r in cursor.fetchall()}

        cursor.execute("""
            SELECT ci.content_id, ci.title, ci.content_type, ci.difficulty_level, ci.duration_minutes,
                   cs.skill_id, cs.relevance_weight
            FROM content_items ci
            JOIN content_skills cs ON ci.content_id = cs.content_id
        """)
        content_rows = cursor.fetchall()

        prereq_graph = self.get_prerequisite_graph(conn)
        all_recs = []
        rec_seq = 1

        for lid in active_learners:
            recs = self.recommend_for_learner(
                conn,
                lid,
                as_of_time=as_of_time,
                top_k=top_k,
                prereq_graph=prereq_graph,
                all_skills=all_skills,
                content_rows=content_rows,
            )
            for r in recs:
                rec_id = ID_FORMATS["recommendation"].format(rec_seq)
                rec_seq += 1
                all_recs.append((
                    rec_id,
                    r["learner_id"],
                    r["content_id"],
                    r["skill_id"],
                    r["rank_order"],
                    r["score"],
                    r["reason_code"],
                    r["reason_description"],
                    r["algorithm_version"],
                    r["generated_at"],
                ))

        with conn:
            conn.execute("DELETE FROM recommendations")
            conn.executemany("""
                INSERT INTO recommendations (
                    recommendation_id, learner_id, content_id, skill_id, rank_order,
                    recommendation_score, reason_code, reason_description, algorithm_version, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, all_recs)

        return len(all_recs)
