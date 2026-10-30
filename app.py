"""
Streamlit Local Interactive Dashboard for the YottaFlex Learning Recommendation Workflow.
Provides inspection of learner mastery, prerequisite graph, explainable recommendations,
and isolated anomaly validation results.
"""

import json
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE_DIR))

import pandas as pd
import streamlit as st

from src.config import GROUND_TRUTH_DIR, SAMPLE_DATA_DIR
from src.data_access import get_db_connection, get_table_counts
from src.mastery import compute_learner_skill_mastery, get_learner_skill_timeline
from src.recommender import LearningRecommender
from src.validator import DataValidator, test_anomaly_fixtures

st.set_page_config(
    page_title="YottaFlex AI Learning Workflow",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def load_db_connection(db_path_str: str):
    return get_db_connection(db_path_str)


def main():
    st.title("🎓 YottaFlex Learning Recommendation & Data Quality Engine")
    st.markdown(
        "*Candidate Project Demonstration: Deterministic Telemetry, Temporal-Safe Mastery, "
        "Prerequisite Gating, Explainable Recommendations & Anomaly Isolation.*"
    )

    # Sidebar: DB Selector & Status
    st.sidebar.header("Platform Controls")
    default_db = SAMPLE_DATA_DIR / "learning_workflow.db"
    full_db = WORKSPACE_DIR / "data" / "full" / "learning_workflow_full.db"

    available_dbs = []
    if default_db.exists():
        available_dbs.append(str(default_db))
    if full_db.exists():
        available_dbs.append(str(full_db))

    if not available_dbs:
        st.warning("⚠️ No database found. Please run `py scripts/generate_data.py --scale small` first.")
        return

    selected_db_path = st.sidebar.selectbox("Active Database File", available_dbs, index=0)
    conn = load_db_connection(selected_db_path)

    # Overview Metrics
    counts = get_table_counts(conn)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Learners", f"{counts['learners']:,}")
    col2.metric("Courses", f"{counts['courses']:,}")
    col3.metric("Skills", f"{counts['skills']:,}")
    col4.metric("Attempts", f"{counts['attempts']:,}")
    col5.metric("Recommendations", f"{counts['recommendations']:,}")

    tabs = st.tabs([
        "👤 Learner Profile & Mastery",
        "🎯 Explainable Recommendations",
        "🕸️ Skill Prerequisite Graph",
        "🛡️ Quality & Anomaly Lab",
        "📊 Database Explorer",
    ])

    # Tab 1: Learner Profile & Mastery
    with tabs[0]:
        st.subheader("Learner Competency & Temporal Mastery")
        cursor = conn.cursor()
        cursor.execute("SELECT learner_id, full_name, email, status FROM learners ORDER BY learner_id ASC LIMIT 100")
        learners = cursor.fetchall()
        learner_options = [f"{r['learner_id']} — {r['full_name']} ({r['status']})" for r in learners]

        selected_learner_str = st.selectbox("Select Learner", learner_options, index=0)
        selected_lid = selected_learner_str.split(" — ")[0]

        # Mastery cutoff controls
        use_cutoff = st.checkbox("Simulate Historical Temporal Cutoff (Prevent Future Leakage)", value=False)
        cutoff_time = None
        if use_cutoff:
            cutoff_time = st.text_input("As-Of Cutoff Timestamp (ISO-8601)", value="2026-10-10T00:00:00Z")

        mastery_map = compute_learner_skill_mastery(conn, selected_lid, as_of_time=cutoff_time)

        cursor.execute("SELECT skill_id, name, domain, difficulty_level FROM skills")
        all_skills = cursor.fetchall()
        mastery_data = []
        for s in all_skills:
            sid = s["skill_id"]
            m_score = mastery_map.get(sid, 0.0)
            status = "Mastered (>=0.85)" if m_score >= 0.85 else ("Competent (>=0.70)" if m_score >= 0.70 else "Deficit (<0.70)")
            mastery_data.append({
                "Skill ID": sid,
                "Skill Name": s["name"],
                "Domain": s["domain"],
                "Difficulty": s["difficulty_level"],
                "Mastery Score": m_score,
                "Status": status,
            })

        df_mastery = pd.DataFrame(mastery_data)
        st.dataframe(
            df_mastery.sort_values(by="Mastery Score", ascending=False),
            use_container_width=True,
            column_config={
                "Mastery Score": st.column_config.ProgressColumn(
                    "Mastery Score",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.2f",
                )
            },
        )

        st.markdown("#### Recent Assessment History")
        cursor.execute("""
            SELECT ar.assessment_id, ar.skill_id, ar.assessed_score, ar.passed, ar.assessed_at, a.content_id
            FROM assessment_results ar
            JOIN attempts a ON ar.attempt_id = a.attempt_id
            WHERE ar.learner_id = ?
            ORDER BY ar.assessed_at DESC LIMIT 10
        """, (selected_lid,))
        recent_asms = [dict(r) for r in cursor.fetchall()]
        if recent_asms:
            st.dataframe(pd.DataFrame(recent_asms), use_container_width=True)
        else:
            st.info("No assessment records found for this learner.")

    # Tab 2: Explainable Recommendations
    with tabs[1]:
        st.subheader("Personalized Learning Recommendations (Explainable AI)")
        st.markdown(
            "Recommendations enforce a **hard prerequisite gate** before ranking candidate items by "
            "Skill Gap (45%), Difficulty Fit (35%), and Content Relevance (20%)."
        )

        cursor.execute("""
            SELECT r.rank_order, r.content_id, ci.title as content_title, ci.content_type, ci.difficulty_level,
                   r.skill_id, s.name as skill_name, r.recommendation_score, r.reason_code, r.reason_description
            FROM recommendations r
            JOIN content_items ci ON r.content_id = ci.content_id
            JOIN skills s ON r.skill_id = s.skill_id
            WHERE r.learner_id = ?
            ORDER BY r.rank_order ASC
        """, (selected_lid,))
        recs = [dict(r) for r in cursor.fetchall()]

        if recs:
            for rec in recs:
                with st.expander(f"Rank #{rec['rank_order']}: {rec['content_title']} (Score: {rec['recommendation_score']:.3f})", expanded=(rec['rank_order'] <= 2)):
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        st.markdown(f"**Content ID:** `{rec['content_id']}`")
                        st.markdown(f"**Type:** `{rec['content_type'].capitalize()}` | **Difficulty:** Level {rec['difficulty_level']}")
                        st.markdown(f"**Target Skill:** `{rec['skill_id']}` — *{rec['skill_name']}*")
                        st.markdown(f"**Reason Code:** `{rec['reason_code']}`")
                    with col_b:
                        st.info(f"💡 **Explainability Rationale:**\n\n{rec['reason_description']}")
                        st.progress(rec["recommendation_score"], text=f"Composite Fit Score: {rec['recommendation_score']:.3f}")
        else:
            st.info(f"No active recommendations for learner `{selected_lid}`. All prerequisites may be pending or skills mastered.")

    # Tab 3: Prerequisite Graph
    with tabs[2]:
        st.subheader("Skill Prerequisite Directed Acyclic Graph (DAG)")
        cursor.execute("""
            SELECT sp.skill_id, s1.name as target_skill, sp.prerequisite_skill_id, s2.name as prereq_skill, sp.min_mastery_threshold
            FROM skill_prerequisites sp
            JOIN skills s1 ON sp.skill_id = s1.skill_id
            JOIN skills s2 ON sp.prerequisite_skill_id = s2.skill_id
            ORDER BY sp.skill_id ASC
        """)
        prereq_rows = [dict(r) for r in cursor.fetchall()]
        st.dataframe(pd.DataFrame(prereq_rows), use_container_width=True)

    # Tab 4: Quality & Anomaly Lab
    with tabs[3]:
        st.subheader("Quality Assurance, Integrity Checks & Anomaly Detection")
        if st.button("Run Full Database Validation Suite"):
            with st.spinner("Executing relational and pedagogical rule checks..."):
                validator = DataValidator(conn)
                report = validator.validate_all()
                if report.is_valid:
                    st.success(f"✅ All {report.total_checks} validation checks PASSED with 0 errors!")
                else:
                    st.error(f"❌ Detected {len(report.issues)} integrity violations.")
                    st.json([vars(i) for i in report.issues])

        st.markdown("---")
        st.markdown("#### Isolated Labeled Anomaly Fixtures")
        gt_path = GROUND_TRUTH_DIR / "anomalies.json"
        if gt_path.exists():
            with open(gt_path, "r", encoding="utf-8") as f:
                anom_fixtures = json.load(f)

            for fix in anom_fixtures:
                with st.expander(f"⚠️ {fix['case_id']}: {fix['name']} [{fix['issue_type']}]"):
                    st.markdown(f"**Description:** {fix['description']}")
                    st.markdown(f"**Expected Handling:** `{fix['expected_handling']}`")
                    st.markdown(f"**Detector Method:** `{fix['detector_method']}`")
                    st.code(json.dumps(fix["payload"], indent=2), language="json")
        else:
            st.warning("Ground truth anomalies file not found.")

    # Tab 5: Database Explorer
    with tabs[4]:
        st.subheader("Direct Relational Table Explorer")
        table_chosen = st.selectbox("Select Table to Inspect", list(counts.keys()))
        limit = st.slider("Row limit", min_value=10, max_value=200, value=25)
        cursor.execute(f"SELECT * FROM {table_chosen} LIMIT {limit}")
        table_data = [dict(r) for r in cursor.fetchall()]
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)


if __name__ == "__main__":
    main()
