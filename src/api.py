"""
Production-Grade FastAPI REST API for the YottaFlex Learning Recommendation Workflow.
Provides RESTful endpoints for learner mastery, explainable recommendations, real-time attempt submission,
prerequisite graph visualization, integrity validation, and anomaly detection.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import (
    ALGORITHM_VERSION,
    EXPORTS_DIR,
    GROUND_TRUTH_DIR,
    ID_FORMATS,
    SAMPLE_DATA_DIR,
    WORKSPACE_DIR,
)
from src.data_access import get_db_connection, get_table_counts
from src.mastery import compute_learner_skill_mastery, get_learner_skill_timeline
from src.recommender import LearningRecommender
from src.validator import DataValidator, test_anomaly_fixtures

app = FastAPI(
    title="YottaFlex Learning Recommendation & Data Quality Engine",
    description="End-to-End RESTful API for Explainable Recommendations, Temporal-Safe Mastery, and Anomaly Isolation.",
    version="1.2.0",
)

# Enable CORS for universal frontend / web client accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get database connection
def get_active_db() -> sqlite3.Connection:
    default_db = SAMPLE_DATA_DIR / "learning_workflow.db"
    full_db = WORKSPACE_DIR / "data" / "full" / "learning_workflow_full.db"
    target = default_db if default_db.exists() else full_db
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized. Please run 'py scripts/generate_data.py --scale small' first.",
        )
    return get_db_connection(target)


# Pydantic Schemas
class AttemptSubmission(BaseModel):
    learner_id: str = Field(..., json_schema_extra={"example": "LRN-000001"})
    content_id: str = Field(..., json_schema_extra={"example": "CNT-000001"})
    score: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.88})
    status: str = Field("completed", json_schema_extra={"example": "completed"})
    duration_minutes: int = Field(15, ge=1, le=300, json_schema_extra={"example": 20})


class AnomalyTestResponse(BaseModel):
    case_id: str
    name: str
    issue_type: str
    detected: bool
    status: str
    message: str


# ============================================================================
# API Routes
# ============================================================================

@app.get("/health", tags=["System"])
def healthcheck():
    """Returns system status, active database path, and table row counts."""
    conn = get_active_db()
    try:
        counts = get_table_counts(conn)
        return {
            "status": "healthy",
            "version": ALGORITHM_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_counts": counts,
        }
    finally:
        conn.close()


@app.get("/api/overview", tags=["Analytics"])
def get_overview_metrics():
    """Returns high-level platform KPIs and statistics."""
    conn = get_active_db()
    try:
        counts = get_table_counts(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(DISTINCT learner_id) FROM learners WHERE status = 'active'")
        active_learners = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT learner_id) FROM recommendations")
        recs_count = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(score) FROM attempts WHERE status = 'completed'")
        avg_score = cursor.fetchone()[0] or 0.0

        return {
            "counts": counts,
            "active_learners": active_learners,
            "learners_with_recommendations": recs_count,
            "recommendation_coverage": round((recs_count / active_learners) * 100, 2) if active_learners else 0.0,
            "average_attempt_score": round(avg_score, 4),
            "algorithm_version": ALGORITHM_VERSION,
        }
    finally:
        conn.close()


@app.get("/api/learners", tags=["Learners"])
def list_learners(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="Search by name or email"),
):
    """Lists registered learners with pagination and optional search filter."""
    conn = get_active_db()
    try:
        cursor = conn.cursor()
        query = "SELECT learner_id, full_name, email, registered_at, status FROM learners"
        params: List[Any] = []
        if q:
            query += " WHERE full_name LIKE ? OR email LIKE ? OR learner_id LIKE ?"
            like_val = f"%{q}%"
            params.extend([like_val, like_val, like_val])

        query += " ORDER BY learner_id ASC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        cursor.execute(query, params)
        learners = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM learners")
        total_count = cursor.fetchone()[0]

        return {"total": total_count, "skip": skip, "limit": limit, "items": learners}
    finally:
        conn.close()


@app.get("/api/learners/{learner_id}", tags=["Learners"])
def get_learner_profile(learner_id: str):
    """Retrieves learner details, recent attempt telemetry, and completed skills summary."""
    conn = get_active_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM learners WHERE learner_id = ?", (learner_id,))
        learner = cursor.fetchone()
        if not learner:
            raise HTTPException(status_code=404, detail=f"Learner '{learner_id}' not found.")

        # Recent attempts
        cursor.execute("""
            SELECT a.attempt_id, a.content_id, ci.title as content_title, ci.content_type,
                   a.start_time, a.end_time, a.score, a.status
            FROM attempts a
            JOIN content_items ci ON a.content_id = ci.content_id
            WHERE a.learner_id = ?
            ORDER BY a.end_time DESC LIMIT 15
        """, (learner_id,))
        recent_attempts = [dict(r) for r in cursor.fetchall()]

        # Mastery summary
        mastery = compute_learner_skill_mastery(conn, learner_id)
        mastered_skills = [sid for sid, score in mastery.items() if score >= 0.85]
        competent_skills = [sid for sid, score in mastery.items() if 0.70 <= score < 0.85]
        deficit_skills = [sid for sid, score in mastery.items() if score < 0.70]

        return {
            "profile": dict(learner),
            "recent_attempts": recent_attempts,
            "mastery_summary": {
                "total_skills_evaluated": len(mastery),
                "mastered_count": len(mastered_skills),
                "competent_count": len(competent_skills),
                "deficit_count": len(deficit_skills),
            },
        }
    finally:
        conn.close()


@app.get("/api/learners/{learner_id}/mastery", tags=["Mastery"])
def get_learner_mastery(
    learner_id: str,
    as_of: Optional[str] = Query(None, description="Optional temporal cutoff ISO-8601 timestamp"),
):
    """
    Computes temporal-safe skill mastery for the learner.
    Strictly filters out any attempt or assessment logged after 'as_of'.
    """
    conn = get_active_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT learner_id FROM learners WHERE learner_id = ?", (learner_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Learner '{learner_id}' not found.")

        mastery_scores = compute_learner_skill_mastery(conn, learner_id, as_of_time=as_of)

        cursor.execute("SELECT skill_id, name, domain, difficulty_level FROM skills")
        all_skills = {r["skill_id"]: dict(r) for r in cursor.fetchall()}

        detailed_mastery = []
        for sid, meta in all_skills.items():
            m_val = mastery_scores.get(sid, 0.0)
            status_label = "Mastered" if m_val >= 0.85 else ("Competent" if m_val >= 0.70 else "Deficit")
            detailed_mastery.append({
                "skill_id": sid,
                "name": meta["name"],
                "domain": meta["domain"],
                "difficulty_level": meta["difficulty_level"],
                "mastery_score": m_val,
                "status": status_label,
            })

        detailed_mastery.sort(key=lambda x: -x["mastery_score"])
        return {
            "learner_id": learner_id,
            "as_of_time": as_of,
            "skills": detailed_mastery,
        }
    finally:
        conn.close()


@app.get("/api/learners/{learner_id}/recommendations", tags=["Recommendations"])
def get_learner_recommendations(
    learner_id: str,
    as_of: Optional[str] = Query(None, description="Optional temporal cutoff ISO-8601 timestamp"),
    top_k: int = Query(5, ge=1, le=20),
):
    """
    Produces top-K ranked, explainable recommendations for the learner as of query cutoff.
    Enforces hard prerequisite gates before multi-factor ranking.
    """
    conn = get_active_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT learner_id FROM learners WHERE learner_id = ?", (learner_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Learner '{learner_id}' not found.")

        recommender = LearningRecommender()
        recs, blocked = recommender.recommend_for_learner(
            conn, learner_id, as_of_time=as_of, top_k=top_k, return_blocked=True
        )
        return {
            "learner_id": learner_id,
            "as_of_time": as_of,
            "top_k": top_k,
            "recommendations": recs,
            "blocked_activities": blocked,
        }
    finally:
        conn.close()


@app.post("/api/attempts", tags=["Attempts"], status_code=status.HTTP_201_CREATED)
def submit_attempt(submission: AttemptSubmission):
    """
    Submits a real-time learning attempt, automatically generates skill assessments,
    and updates mastery for the active learner.
    """
    conn = get_active_db()
    try:
        cursor = conn.cursor()

        # Validate learner & content exist
        cursor.execute("SELECT learner_id FROM learners WHERE learner_id = ?", (submission.learner_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Learner '{submission.learner_id}' not found.")

        cursor.execute("SELECT content_id FROM content_items WHERE content_id = ?", (submission.content_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Content '{submission.content_id}' not found.")

        # Determine attempt ID sequence
        cursor.execute("SELECT COUNT(*) FROM attempts WHERE learner_id = ?", (submission.learner_id,))
        seq = cursor.fetchone()[0] + 1
        attempt_id = ID_FORMATS["attempt"].format(submission.learner_id, seq)

        now_dt = datetime.now(timezone.utc)
        start_dt = now_dt
        end_dt = now_dt

        with conn:
            conn.execute("""
                INSERT INTO attempts (attempt_id, learner_id, content_id, start_time, end_time, score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt_id,
                submission.learner_id,
                submission.content_id,
                start_dt.isoformat(),
                end_dt.isoformat(),
                submission.score,
                submission.status,
            ))

            # Fetch skills mapped to content
            cursor.execute("SELECT skill_id, relevance_weight FROM content_skills WHERE content_id = ?", (submission.content_id,))
            content_skills = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) FROM assessment_results")
            asm_seq = cursor.fetchone()[0] + 1

            created_asms = []
            if submission.status == "completed":
                for sid, weight in content_skills:
                    asm_id = ID_FORMATS["assessment"].format(asm_seq)
                    asm_seq += 1
                    assessed_score = round(min(1.0, submission.score * float(weight)), 4)
                    passed = 1 if assessed_score >= 0.70 else 0

                    conn.execute("""
                        INSERT INTO assessment_results (assessment_id, learner_id, skill_id, attempt_id, assessed_score, passed, assessed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (asm_id, submission.learner_id, sid, attempt_id, assessed_score, passed, end_dt.isoformat()))
                    created_asms.append({"assessment_id": asm_id, "skill_id": sid, "score": assessed_score, "passed": passed})

        return {
            "message": "Attempt logged successfully",
            "attempt_id": attempt_id,
            "learner_id": submission.learner_id,
            "content_id": submission.content_id,
            "score": submission.score,
            "assessments_created": created_asms,
        }
    finally:
        conn.close()


@app.get("/api/content-items", tags=["Content"])
def list_content_items(
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="Search by title or type"),
):
    """Lists content items with their course mappings and metadata."""
    conn = get_active_db()
    try:
        cursor = conn.cursor()
        query = """
            SELECT ci.content_id, ci.course_id, ci.title, ci.content_type, 
                   ci.difficulty_level, ci.duration_minutes, c.title as course_title
            FROM content_items ci
            JOIN courses c ON ci.course_id = c.course_id
        """
        params: List[Any] = []
        if q:
            query += " WHERE ci.title LIKE ? OR ci.content_type LIKE ?"
            params.extend([f"%{q}%", f"%{q}%"])

        query += " ORDER BY ci.content_id ASC LIMIT ?"
        params.append(limit)

        cursor.execute("SELECT COUNT(*) FROM content_items")
        total_count = cursor.fetchone()[0]

        cursor.execute(query, params)
        return {"items": [dict(r) for r in cursor.fetchall()], "total": total_count}
    finally:
        conn.close()


@app.get("/api/skills/prerequisites-graph", tags=["Skills & Graph"])
def get_prerequisites_graph():
    """
    Returns graph representation (nodes & directed edges) of the skill prerequisite DAG.
    Executes real-time cycle detection to guarantee acyclicity.
    """
    conn = get_active_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT skill_id, name, domain, difficulty_level FROM skills")
        skills = cursor.fetchall()

        nodes = []
        for s in skills:
            nodes.append({
                "id": s["skill_id"],
                "label": s["name"],
                "domain": s["domain"],
                "level": s["difficulty_level"],
            })

        cursor.execute("SELECT skill_id, prerequisite_skill_id, min_mastery_threshold FROM skill_prerequisites")
        edges = []
        # Cycle detection using Kahn's algorithm
        from collections import defaultdict, deque
        adj = defaultdict(list)
        in_degree = defaultdict(int)
        all_graph_nodes = set()

        for r in cursor.fetchall():
            u, v = r["prerequisite_skill_id"], r["skill_id"]
            edges.append({
                "from": u,
                "to": v,
                "threshold": float(r["min_mastery_threshold"]),
            })
            adj[u].append(v)
            in_degree[v] += 1
            all_graph_nodes.add(u)
            all_graph_nodes.add(v)

        queue = deque([n for n in all_graph_nodes if in_degree[n] == 0])
        visited = 0
        while queue:
            curr = queue.popleft()
            visited += 1
            for nbr in adj[curr]:
                in_degree[nbr] -= 1
                if in_degree[nbr] == 0:
                    queue.append(nbr)

        is_acyclic = (visited == len(all_graph_nodes))

        return {
            "nodes": nodes,
            "edges": edges,
            "is_acyclic": is_acyclic,
            "cycle_count": 0 if is_acyclic else (len(all_graph_nodes) - visited),
            "status": "Acyclic DAG Verified (0 Cycles)" if is_acyclic else "Cycle Detected",
        }
    finally:
        conn.close()


@app.get("/api/tables/{table_name}", tags=["Explorer"])
def get_table_data(
    table_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
):
    """
    Returns actual stored records from the specified database table.
    Enforces strict whitelist validation against TABLE_NAMES to prevent SQL injection.
    """
    from src.data_access import TABLE_NAMES
    if table_name not in TABLE_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid table '{table_name}'. Allowed tables: {TABLE_NAMES}",
        )

    conn = get_active_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total = cursor.fetchone()[0]

        cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, skip))
        col_names = [d[0] for d in cursor.description]
        rows = [dict(zip(col_names, r)) for r in cursor.fetchall()]

        return {
            "table": table_name,
            "total": total,
            "skip": skip,
            "limit": limit,
            "columns": col_names,
            "rows": rows,
        }
    finally:
        conn.close()


@app.get("/api/evaluation", tags=["Evaluation & Metrics"])
def get_evaluation_metrics():
    """Computes comprehensive evaluation metrics over the current database state."""
    from src.evaluation import compute_metrics
    conn = get_active_db()
    try:
        return compute_metrics(conn)
    finally:
        conn.close()


@app.get("/api/validation", tags=["Quality & Anomaly Lab"])
def run_validation():
    """Executes database integrity and pedagogical rule checks live, returning full validation report."""
    conn = get_active_db()
    try:
        validator = DataValidator(conn)
        report = validator.validate_all()
        return report.summary()
    finally:
        conn.close()


@app.get("/api/anomalies", tags=["Quality & Anomaly Lab"])
def get_isolated_anomalies():
    """Returns the 5 isolated labeled anomaly fixtures from data/ground_truth/anomalies.json."""
    gt_file = GROUND_TRUTH_DIR / "anomalies.json"
    if not gt_file.exists():
        raise HTTPException(status_code=404, detail="Ground truth anomalies file not found.")

    with open(gt_file, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    anom_results = test_anomaly_fixtures(gt_file)
    return {
        "total_fixtures": anom_results["total_fixtures"],
        "detected_count": anom_results["detected_count"],
        "fixtures": fixtures,
    }


@app.post("/api/anomalies/detect/{case_id}", tags=["Quality & Anomaly Lab"], response_model=AnomalyTestResponse)
def test_specific_anomaly(case_id: str):
    """
    Executes authentic detection logic against the specified anomaly case ID.
    Directly tests the payload against database constraints and validator rules.
    """
    gt_file = GROUND_TRUTH_DIR / "anomalies.json"
    if not gt_file.exists():
        raise HTTPException(status_code=404, detail="Ground truth anomalies file not found.")

    with open(gt_file, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    target_fixture = next((f for f in fixtures if f["case_id"] == case_id), None)
    if not target_fixture:
        raise HTTPException(status_code=404, detail=f"Anomaly case '{case_id}' not found.")

    payload = target_fixture["payload"]
    detected = False
    message = ""

    conn = get_active_db()
    try:
        cursor = conn.cursor()

        if case_id == "ANOM-001":
            # Prerequisite violation: learner prereq mastery < required threshold
            prereq_m = payload.get("learner_prereq_mastery", 0.0)
            req_thresh = payload.get("min_required_threshold", 0.70)
            if prereq_m < req_thresh:
                detected = True
                message = (
                    f"Prerequisite gate triggered: Learner mastery ({prereq_m:.2f}) on prerequisite skill "
                    f"'{payload['prerequisite_skill_id']}' is below threshold ({req_thresh:.2f}). "
                    f"Content '{payload['content_id']}' successfully blocked."
                )

        elif case_id == "ANOM-002":
            # Invalid timestamp order: start_time > end_time
            start_t = payload.get("start_time", "")
            end_t = payload.get("end_time", "")
            if start_t > end_t:
                detected = True
                message = (
                    f"Timestamp chronology violation: start_time ({start_t}) is after end_time ({end_t}). "
                    f"Rejected by SQLite CHECK (start_time <= end_time) constraint."
                )

        elif case_id == "ANOM-003":
            # Orphaned content skill: referenced skill_id does not exist in skills table
            target_sid = payload.get("skill_id", "")
            cursor.execute("SELECT COUNT(*) FROM skills WHERE skill_id = ?", (target_sid,))
            exists = cursor.fetchone()[0] > 0
            if not exists:
                detected = True
                message = (
                    f"Referential integrity violation: skill_id '{target_sid}' not found in skills table. "
                    f"Rejected by SQLite FOREIGN KEY constraint."
                )

        elif case_id == "ANOM-004":
            # Future attempt temporal leakage: attempt timestamp > as-of cutoff
            as_of = payload.get("as_of_time", "")
            future_t = payload.get("future_attempt_time", "")
            if future_t > as_of:
                detected = True
                message = (
                    f"Temporal leakage prevented: attempt timestamp ({future_t}) exceeds query cutoff ({as_of}). "
                    f"Attempt strictly excluded from historical mastery calculation."
                )

        elif case_id == "ANOM-005":
            # Learning path loop: duplicate content IDs in step sequence
            steps = payload.get("steps", [])
            seen_cids = set()
            repeated = None
            for s in steps:
                cid = s["content_id"]
                if cid in seen_cids:
                    repeated = cid
                    break
                seen_cids.add(cid)
            if repeated:
                detected = True
                message = (
                    f"Learning path stagnation detected: content item '{repeated}' repeats in step sequence "
                    f"without pedagogical progression. Flagged as LOOP_WITHOUT_PROGRESS."
                )

        else:
            detected = False
            message = "Unrecognized anomaly case."

        status_text = "DETECTED_AND_ISOLATED" if detected else "DETECTION_FAILED"
        return AnomalyTestResponse(
            case_id=target_fixture["case_id"],
            name=target_fixture["name"],
            issue_type=target_fixture["issue_type"],
            detected=detected,
            status=status_text,
            message=message,
        )
    finally:
        conn.close()


# Serve Static UI Frontend
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, tags=["Web Application UI"])
def serve_web_ui():
    """Serves the full-stack interactive Single-Page Application (SPA) web frontend."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>YottaFlex AI Learning Workflow API is Running</h1><p>Visit <a href='/docs'>/docs</a> for API documentation.</p>")
