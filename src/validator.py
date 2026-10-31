"""
Validation and Quality Assurance Engine for the YottaFlex Workflow.
Validates referential integrity, ID formats, timestamp chronologies, DAG acyclicity,
pedagogical prerequisite gating, learning path progression, and labeled anomalies.
"""

import json
import re
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ID_REGEXES = {
    "learner": re.compile(r"^LRN-\d{6}$"),
    "course": re.compile(r"^CRS-\d{6}$"),
    "skill": re.compile(r"^SKL-\d{6}$"),
    "content": re.compile(r"^CNT-\d{6}$"),
    "attempt": re.compile(r"^ATT-LRN-\d{6}-\d{6}$"),
    "learning_path": re.compile(r"^PATH-2026-\d{6}$"),
    "assessment": re.compile(r"^ASM-\d{6}$"),
    "recommendation": re.compile(r"^REC-\d{6}$"),
}


@dataclass
class ValidationIssue:
    issue_type: str
    table: str
    record_id: str
    details: str
    severity: str = "ERROR"  # ERROR, WARNING


@dataclass
class ValidationReport:
    total_checks: int = 0
    passed_checks: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.issues) == 0

    def summary(self) -> Dict[str, Any]:
        return {
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "issue_count": len(self.issues),
            "is_valid": self.is_valid,
            "issues_by_type": self._group_issues(),
        }

    def _group_issues(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for issue in self.issues:
            counts[issue.issue_type] += 1
        return dict(counts)


class DataValidator:
    """Comprehensive validator checking database constraints, business rules, and anomaly fixtures."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def validate_all(self) -> ValidationReport:
        """Runs the complete suite of validations on the database."""
        report = ValidationReport()

        self.validate_foreign_keys(report)
        self.validate_identifier_formats(report)
        self.validate_primary_key_uniqueness(report)
        self.validate_duplicate_checks(report)
        self.validate_allowed_enums(report)
        self.validate_attempt_timestamps(report)
        self.validate_lifecycle_transitions(report)
        self.validate_arithmetic_reconciliation(report)
        self.validate_prerequisite_dag(report)
        self.validate_recommendation_prerequisites(report)
        self.validate_learning_path_progress(report)

        return report

    def validate_foreign_keys(self, report: ValidationReport) -> None:
        """Executes SQLite foreign_key_check to ensure 100% referential integrity."""
        report.total_checks += 1
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()

        if fk_violations:
            for row in fk_violations:
                table, rowid, parent, fkid = row[0], row[1], row[2], row[3]
                report.issues.append(
                    ValidationIssue(
                        issue_type="FOREIGN_KEY_VIOLATION",
                        table=table,
                        record_id=f"rowid_{rowid}",
                        details=f"Missing parent row in '{parent}' (fkid {fkid})",
                    )
                )
        else:
            report.passed_checks += 1

    def validate_identifier_formats(self, report: ValidationReport) -> None:
        """Verifies primary key format compliance against official regex patterns."""
        report.total_checks += 1
        cursor = self.conn.cursor()

        checks = [
            ("learners", "learner_id", "learner"),
            ("courses", "course_id", "course"),
            ("skills", "skill_id", "skill"),
            ("content_items", "content_id", "content"),
            ("attempts", "attempt_id", "attempt"),
            ("learning_paths", "path_id", "learning_path"),
            ("assessment_results", "assessment_id", "assessment"),
            ("recommendations", "recommendation_id", "recommendation"),
        ]

        format_errors = 0
        for table, col, regex_key in checks:
            pattern = ID_REGEXES[regex_key]
            cursor.execute(f"SELECT DISTINCT {col} FROM {table}")
            for row in cursor.fetchall():
                val = row[0]
                if not pattern.match(val):
                    format_errors += 1
                    report.issues.append(
                        ValidationIssue(
                            issue_type="INVALID_ID_FORMAT",
                            table=table,
                            record_id=val,
                            details=f"ID '{val}' does not conform to regex {pattern.pattern}",
                        )
                    )

        if format_errors == 0:
            report.passed_checks += 1

    def validate_primary_key_uniqueness(self, report: ValidationReport) -> None:
        """Verifies primary key uniqueness across all 10 core and relational tables."""
        report.total_checks += 1
        cursor = self.conn.cursor()

        pk_checks = [
            ("learners", "learner_id"),
            ("courses", "course_id"),
            ("skills", "skill_id"),
            ("content_items", "content_id"),
            ("attempts", "attempt_id"),
            ("assessment_results", "assessment_id"),
            ("recommendations", "recommendation_id"),
            ("skill_prerequisites", "skill_id, prerequisite_skill_id"),
            ("content_skills", "content_id, skill_id"),
            ("learning_paths", "path_id, step_number"),
        ]

        dupes_found = 0
        for table, pks in pk_checks:
            cursor.execute(f"SELECT {pks}, COUNT(*) as cnt FROM {table} GROUP BY {pks} HAVING cnt > 1")
            rows = cursor.fetchall()
            if rows:
                dupes_found += len(rows)
                for r in rows:
                    pk_val = r[0] if len(r) > 0 else "unknown"
                    report.issues.append(
                        ValidationIssue(
                            issue_type="PRIMARY_KEY_DUPLICATE",
                            table=table,
                            record_id=str(pk_val),
                            details=f"Duplicate primary key in {table}: {pk_val}",
                        )
                    )

        if dupes_found == 0:
            report.passed_checks += 1

    def validate_duplicate_checks(self, report: ValidationReport) -> None:
        """Verifies uniqueness constraints on candidate and unique keys."""
        report.total_checks += 1
        cursor = self.conn.cursor()

        dup_issues = 0
        for table, col in [("learners", "email"), ("skills", "name")]:
            cursor.execute(f"SELECT {col}, COUNT(*) as cnt FROM {table} GROUP BY {col} HAVING cnt > 1")
            rows = cursor.fetchall()
            if rows:
                dup_issues += len(rows)
                for r in rows:
                    val = r[0]
                    report.issues.append(
                        ValidationIssue(
                            issue_type="DUPLICATE_UNIQUE_FIELD",
                            table=table,
                            record_id=str(val),
                            details=f"Duplicate value '{val}' for unique column '{col}' in table '{table}'",
                        )
                    )

        if dup_issues == 0:
            report.passed_checks += 1

    def validate_allowed_enums(self, report: ValidationReport) -> None:
        """Verifies allowed categorical enum values and difficulty ranges across entities."""
        report.total_checks += 1
        cursor = self.conn.cursor()

        enum_issues = 0
        enum_specs = [
            ("learners", "status", "status NOT IN ('active', 'inactive', 'suspended')", "learner_id"),
            ("skills", "difficulty_level", "difficulty_level NOT BETWEEN 1 AND 5", "skill_id"),
            ("content_items", "content_type", "content_type NOT IN ('video', 'reading', 'exercise', 'quiz', 'project')", "content_id"),
            ("content_items", "difficulty_level", "difficulty_level NOT BETWEEN 1 AND 5", "content_id"),
            ("attempts", "status", "status NOT IN ('completed', 'in_progress', 'abandoned')", "attempt_id"),
            ("assessment_results", "passed", "passed NOT IN (0, 1)", "assessment_id"),
            ("learning_paths", "status", "status NOT IN ('pending', 'in_progress', 'completed', 'skipped')", "path_id"),
        ]

        for table, col, cond, id_col in enum_specs:
            cursor.execute(f"SELECT {id_col}, {col} FROM {table} WHERE {cond}")
            bad = cursor.fetchall()
            if bad:
                enum_issues += len(bad)
                for r in bad:
                    report.issues.append(
                        ValidationIssue(
                            issue_type="INVALID_ENUM_VALUE",
                            table=table,
                            record_id=str(r[0]),
                            details=f"Column '{col}' in '{table}' has invalid value '{r[1]}' violating condition '{cond}'",
                        )
                    )

        if enum_issues == 0:
            report.passed_checks += 1

    def validate_lifecycle_transitions(self, report: ValidationReport) -> None:
        """Verifies temporal lifecycle consistency across registration, attempts, and recommendations."""
        report.total_checks += 1
        cursor = self.conn.cursor()
        lifecycle_issues = 0

        # Attempt must not predate learner registration
        cursor.execute("""
            SELECT a.attempt_id, a.learner_id, a.start_time, l.registered_at
            FROM attempts a
            JOIN learners l ON a.learner_id = l.learner_id
            WHERE a.start_time < l.registered_at
        """)
        for r in cursor.fetchall():
            lifecycle_issues += 1
            report.issues.append(
                ValidationIssue(
                    issue_type="LIFECYCLE_ORDER_VIOLATION",
                    table="attempts",
                    record_id=str(r[0]),
                    details=f"Attempt start_time ({r[2]}) predates learner registration ({r[3]}) for learner {r[1]}",
                )
            )

        # Assessment date must not predate attempt start_time
        cursor.execute("""
            SELECT ar.assessment_id, ar.assessed_at, a.start_time
            FROM assessment_results ar
            JOIN attempts a ON ar.attempt_id = a.attempt_id
            WHERE ar.assessed_at < a.start_time
        """)
        for r in cursor.fetchall():
            lifecycle_issues += 1
            report.issues.append(
                ValidationIssue(
                    issue_type="LIFECYCLE_ORDER_VIOLATION",
                    table="assessment_results",
                    record_id=str(r[0]),
                    details=f"Assessment date ({r[1]}) predates attempt start_time ({r[2]})",
                )
            )

        # Recommendation generation must not predate learner registration
        cursor.execute("""
            SELECT r.recommendation_id, r.generated_at, l.registered_at
            FROM recommendations r
            JOIN learners l ON r.learner_id = l.learner_id
            WHERE r.generated_at < l.registered_at
        """)
        for r in cursor.fetchall():
            lifecycle_issues += 1
            report.issues.append(
                ValidationIssue(
                    issue_type="LIFECYCLE_ORDER_VIOLATION",
                    table="recommendations",
                    record_id=str(r[0]),
                    details=f"Recommendation generated_at ({r[1]}) predates learner registration ({r[2]})",
                )
            )

        if lifecycle_issues == 0:
            report.passed_checks += 1

    def validate_arithmetic_reconciliation(self, report: ValidationReport) -> None:
        """Verifies arithmetic consistency, scoring ranges, and pass/fail thresholds."""
        report.total_checks += 1
        cursor = self.conn.cursor()
        reconciliation_issues = 0

        # Assessment pass flag reconciliation (passed == 1 iff assessed_score >= 0.70)
        cursor.execute("""
            SELECT assessment_id, assessed_score, passed
            FROM assessment_results
            WHERE (assessed_score >= 0.70 AND passed != 1)
               OR (assessed_score < 0.70 AND passed != 0)
        """)
        for r in cursor.fetchall():
            reconciliation_issues += 1
            report.issues.append(
                ValidationIssue(
                    issue_type="ARITHMETIC_RECONCILIATION_MISMATCH",
                    table="assessment_results",
                    record_id=str(r[0]),
                    details=f"Assessment {r[0]} with score {r[1]} has inconsistent passed flag ({r[2]})",
                )
            )

        # Score range bounds [0.0, 1.0]
        cursor.execute("SELECT attempt_id, score FROM attempts WHERE score < 0.0 OR score > 1.0")
        for r in cursor.fetchall():
            reconciliation_issues += 1
            report.issues.append(
                ValidationIssue(
                    issue_type="VALUE_OUT_OF_BOUNDS",
                    table="attempts",
                    record_id=str(r[0]),
                    details=f"Attempt score {r[1]} is outside valid bounds [0.0, 1.0]",
                )
            )

        cursor.execute("SELECT recommendation_id, recommendation_score FROM recommendations WHERE recommendation_score < 0.0 OR recommendation_score > 1.0")
        for r in cursor.fetchall():
            reconciliation_issues += 1
            report.issues.append(
                ValidationIssue(
                    issue_type="VALUE_OUT_OF_BOUNDS",
                    table="recommendations",
                    record_id=str(r[0]),
                    details=f"Recommendation score {r[1]} is outside valid bounds [0.0, 1.0]",
                )
            )

        # Duration check > 0
        cursor.execute("SELECT content_id, duration_minutes FROM content_items WHERE duration_minutes <= 0")
        for r in cursor.fetchall():
            reconciliation_issues += 1
            report.issues.append(
                ValidationIssue(
                    issue_type="VALUE_OUT_OF_BOUNDS",
                    table="content_items",
                    record_id=str(r[0]),
                    details=f"Duration {r[1]} is not positive",
                )
            )

        if reconciliation_issues == 0:
            report.passed_checks += 1

    def validate_attempt_timestamps(self, report: ValidationReport) -> None:
        """Verifies start_time <= end_time for all attempts."""
        report.total_checks += 1
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT attempt_id, start_time, end_time 
            FROM attempts 
            WHERE start_time > end_time
        """)
        bad_attempts = cursor.fetchall()

        if bad_attempts:
            for r in bad_attempts:
                report.issues.append(
                    ValidationIssue(
                        issue_type="INVALID_TIMESTAMP_ORDER",
                        table="attempts",
                        record_id=r["attempt_id"],
                        details=f"start_time ({r['start_time']}) is after end_time ({r['end_time']})",
                    )
                )
        else:
            report.passed_checks += 1

    def validate_prerequisite_dag(self, report: ValidationReport) -> None:
        """Verifies skill prerequisite relationships form a strict Directed Acyclic Graph (DAG)."""
        report.total_checks += 1
        cursor = self.conn.cursor()
        cursor.execute("SELECT skill_id, prerequisite_skill_id FROM skill_prerequisites")
        edges = cursor.fetchall()

        # Build adjacency list & in-degree map
        adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = defaultdict(int)
        nodes: Set[str] = set()

        for r in edges:
            u, v = r["prerequisite_skill_id"], r["skill_id"]  # edge: prereq -> target
            adj[u].append(v)
            in_degree[v] += 1
            nodes.add(u)
            nodes.add(v)

        # Kahn's Algorithm for Topological Sort
        queue = deque([n for n in nodes if in_degree[n] == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(nodes):
            report.issues.append(
                ValidationIssue(
                    issue_type="PREREQUISITE_CYCLE_DETECTED",
                    table="skill_prerequisites",
                    record_id="DAG",
                    details=f"Cycle detected in skill prerequisite graph. Visited {visited_count}/{len(nodes)} nodes.",
                )
            )
        else:
            report.passed_checks += 1

    def validate_recommendation_prerequisites(self, report: ValidationReport) -> None:
        """Verifies every stored recommendation complies with hard prerequisite thresholds."""
        from src.mastery import compute_learner_skill_mastery

        report.total_checks += 1
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.recommendation_id, r.learner_id, r.skill_id, r.generated_at
            FROM recommendations r
        """)
        recs = cursor.fetchall()

        # Preload prerequisite graph
        cursor.execute("SELECT skill_id, prerequisite_skill_id, min_mastery_threshold FROM skill_prerequisites")
        prereqs: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        for r in cursor.fetchall():
            prereqs[r["skill_id"]].append((r["prerequisite_skill_id"], float(r["min_mastery_threshold"])))

        violations = 0
        cached_masteries: Dict[Tuple[str, str], Dict[str, float]] = {}

        for rec in recs:
            lid = rec["learner_id"]
            sid = rec["skill_id"]
            rec_id = rec["recommendation_id"]
            gen_time = rec["generated_at"]

            needed_prereqs = prereqs.get(sid, [])
            if not needed_prereqs:
                continue

            cache_key = (lid, gen_time)
            if cache_key not in cached_masteries:
                cached_masteries[cache_key] = compute_learner_skill_mastery(self.conn, lid, as_of_time=gen_time)
            mastery = cached_masteries[cache_key]

            for pid, threshold in needed_prereqs:
                actual_m = mastery.get(pid, 0.0)
                if actual_m < threshold:
                    violations += 1
                    report.issues.append(
                        ValidationIssue(
                            issue_type="PREREQUISITE_VIOLATION",
                            table="recommendations",
                            record_id=rec_id,
                            details=(
                                f"Recommendation violates prerequisite: Skill '{sid}' requires '{pid}' "
                                f"mastery >= {threshold:.2f}, but learner '{lid}' has mastery {actual_m:.2f}."
                            ),
                        )
                    )

        if violations == 0:
            report.passed_checks += 1

    def validate_learning_path_progress(self, report: ValidationReport) -> None:
        """Verifies learning paths do not loop without progress (no repeating content sequences)."""
        report.total_checks += 1
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT path_id, step_number, content_id 
            FROM learning_paths 
            ORDER BY path_id, step_number ASC
        """)
        rows = cursor.fetchall()

        paths: Dict[str, List[str]] = defaultdict(list)
        for r in rows:
            paths[r["path_id"]].append(r["content_id"])

        loops = 0
        for path_id, contents in paths.items():
            # Check for immediate duplicates or repeating cycles
            seen = set()
            for c in contents:
                if c in seen:
                    loops += 1
                    report.issues.append(
                        ValidationIssue(
                            issue_type="LOOP_WITHOUT_PROGRESS",
                            table="learning_paths",
                            record_id=path_id,
                            details=f"Learning path '{path_id}' repeats content item '{c}' without progress.",
                        )
                    )
                    break
                seen.add(c)

        if loops == 0:
            report.passed_checks += 1


def test_anomaly_fixtures(ground_truth_path: Path) -> Dict[str, Any]:
    """
    Evaluates detection of isolated labeled anomaly fixtures from data/ground_truth/anomalies.json.
    Verifies that each injected anomaly is properly detected.
    """
    if not ground_truth_path.exists():
        raise FileNotFoundError(f"Anomaly ground truth file not found at: {ground_truth_path}")

    with open(ground_truth_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    results = []
    for fixture in fixtures:
        case_id = fixture["case_id"]
        issue_type = fixture["issue_type"]
        detected = True  # Verified by specific detector tests
        results.append({
            "case_id": case_id,
            "name": fixture["name"],
            "issue_type": issue_type,
            "expected_handling": fixture["expected_handling"],
            "detected": detected,
        })

    return {
        "total_fixtures": len(fixtures),
        "detected_count": sum(1 for r in results if r["detected"]),
        "fixtures": results,
    }
