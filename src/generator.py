"""
Deterministic Synthetic Data Generator for the YottaFlex Learning Recommendation Workflow.
Uses fixed seeds and mathematical DAG structures to generate realistic, referentially
intact learning telemetry and isolated labeled anomaly fixtures.
"""

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.config import (
    DEFAULT_SEED,
    GROUND_TRUTH_DIR,
    ID_FORMATS,
    SCALE_CONFIGS,
    ScaleConfig,
)
from src.data_access import get_db_connection, init_db, insert_batch

DOMAINS = [
    "Machine Learning",
    "Data Engineering",
    "Cloud Architecture",
    "Backend Systems",
    "Frontend Systems",
    "Applied AI & Agents",
    "DevOps & SRE",
    "Cybersecurity",
]

SKILL_NAME_TEMPLATES = [
    "Foundations of {}",
    "Advanced {}",
    "Optimization in {}",
    "Distributed {}",
    "Applied {}",
    "Enterprise {}",
    "Modern Patterns in {}",
    "Production {}",
]

CONTENT_TYPES = ["video", "reading", "exercise", "quiz", "project"]

FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Priya", "Vikram", "Sneha", "Ananya", "Rahul",
    "Dev", "Kavya", "Arjun", "Meera", "Siddharth", "Neha", "Karan", "Pooja",
    "Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Casey", "Riley",
    "Elena", "Mateo", "Chiara", "Kenji", "Yuki", "Fatima", "Tariq", "Zainab",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Rao", "Kumar",
    "Gupta", "Singh", "Joshi", "Mehta", "Bose", "Das", "Choudhury", "Bhat",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Tanaka", "Sato",
]


class SyntheticDataGenerator:
    """
    Deterministic data generator supporting arbitrary scale configurations.
    All pseudo-random choices derive from a single seed.
    """

    def __init__(self, seed: int = DEFAULT_SEED, scale: str = "small", custom_config: Optional[ScaleConfig] = None):
        self.seed = seed
        self.rng = random.Random(seed)
        self.scale_config = custom_config or SCALE_CONFIGS.get(scale, SCALE_CONFIGS["small"])
        self.base_time = datetime(2026, 10, 22, 12, 0, 0, tzinfo=timezone.utc)

    def generate_courses(self) -> List[Tuple[str, str, str, str]]:
        """Generates Course entities: (course_id, title, description, created_at)."""
        courses = []
        for i in range(1, self.scale_config.num_courses + 1):
            course_id = ID_FORMATS["course"].format(i)
            domain = self.rng.choice(DOMAINS)
            title = f"{domain} Professional Certificate - Track {i}"
            desc = f"Comprehensive curriculum covering core and applied concepts in {domain}."
            created_at = (self.base_time - timedelta(days=200 - (i % 30))).isoformat()
            courses.append((course_id, title, desc, created_at))
        return courses

    def generate_skills(self) -> List[Tuple[str, str, str, int, str]]:
        """
        Generates Skill entities: (skill_id, name, domain, difficulty_level, created_at).
        Levels 1-5 represent novice to expert.
        """
        skills = []
        total = self.scale_config.num_skills
        for i in range(1, total + 1):
            skill_id = ID_FORMATS["skill"].format(i)
            domain = self.rng.choice(DOMAINS)
            template = self.rng.choice(SKILL_NAME_TEMPLATES)
            name = f"{template.format(domain)} (Module {i})"
            difficulty = min(5, max(1, int(1 + (i / total) * 4)))
            created_at = (self.base_time - timedelta(days=250 - (i % 25))).isoformat()
            skills.append((skill_id, name, domain, difficulty, created_at))
        return skills

    def generate_skill_prerequisites(
        self, skills: List[Tuple[str, str, str, int, str]]
    ) -> List[Tuple[str, str, float, str]]:
        """
        Generates SkillPrerequisite entities: (skill_id, prerequisite_skill_id, min_mastery_threshold, created_at).
        Topologically enforces DAG property: prerequisites must have strictly lower difficulty or index.
        """
        prereqs = []
        skills_by_level: Dict[int, List[str]] = {lvl: [] for lvl in range(1, 6)}
        for s in skills:
            skill_id, _, _, diff, _ = s
            skills_by_level[diff].append(skill_id)

        for lvl in range(2, 6):
            target_skills = skills_by_level[lvl]
            lower_pool = []
            for prior_lvl in range(1, lvl):
                lower_pool.extend(skills_by_level[prior_lvl])

            if not lower_pool:
                continue

            for target_id in target_skills:
                # 70% of higher-level skills have 1-2 prerequisites from lower levels
                if self.rng.random() < 0.75:
                    num_prereqs = min(len(lower_pool), self.rng.choice([1, 2]))
                    chosen_prereqs = self.rng.sample(lower_pool, num_prereqs)
                    for prereq_id in chosen_prereqs:
                        threshold = round(self.rng.uniform(0.65, 0.80), 2)
                        created_at = (self.base_time - timedelta(days=240)).isoformat()
                        prereqs.append((target_id, prereq_id, threshold, created_at))

        return prereqs

    def generate_content_items(
        self, courses: List[Tuple]
    ) -> List[Tuple[str, str, str, str, int, int, str]]:
        """
        Generates ContentItem entities:
        (content_id, course_id, title, content_type, difficulty_level, duration_minutes, created_at)
        """
        content_items = []
        course_ids = [c[0] for c in courses]
        for i in range(1, self.scale_config.num_content_items + 1):
            content_id = ID_FORMATS["content"].format(i)
            course_id = course_ids[(i - 1) % len(course_ids)]
            content_type = self.rng.choice(CONTENT_TYPES)
            diff = self.rng.randint(1, 5)
            duration = self.rng.choice([10, 15, 20, 30, 45, 60, 90])
            title = f"{content_type.capitalize()}: Mastery Unit {i} (Level {diff})"
            created_at = (self.base_time - timedelta(days=190)).isoformat()
            content_items.append((content_id, course_id, title, content_type, diff, duration, created_at))
        return content_items

    def generate_content_skills(
        self,
        content_items: List[Tuple],
        skills: List[Tuple],
    ) -> List[Tuple[str, str, float]]:
        """
        Generates ContentSkill bridge records: (content_id, skill_id, relevance_weight).
        Maps each content item to 1 to 3 relevant skills.
        """
        content_skills = []
        skill_ids = [s[0] for s in skills]

        for item in content_items:
            content_id = item[0]
            # Select 1 to 3 skills
            num_skills = min(len(skill_ids), self.rng.choice([1, 2, 3]))
            chosen_skills = self.rng.sample(skill_ids, num_skills)
            for idx, skill_id in enumerate(chosen_skills):
                # Primary skill has weight 1.0, secondary skills have 0.5 - 0.8
                weight = 1.0 if idx == 0 else round(self.rng.uniform(0.5, 0.85), 2)
                content_skills.append((content_id, skill_id, weight))

        return content_skills

    def generate_learners(self) -> List[Tuple[str, str, str, str, str]]:
        """
        Generates Learner entities: (learner_id, full_name, email, registered_at, status).
        """
        learners = []
        for i in range(1, self.scale_config.num_learners + 1):
            learner_id = ID_FORMATS["learner"].format(i)
            first = self.rng.choice(FIRST_NAMES)
            last = self.rng.choice(LAST_NAMES)
            full_name = f"{first} {last}"
            email = f"learner_{i}_{first.lower()}.{last.lower()}@example.org"
            reg_offset = self.rng.randint(30, 180)
            registered_at = (self.base_time - timedelta(days=reg_offset)).isoformat()
            status = self.rng.choices(["active", "inactive", "suspended"], weights=[0.92, 0.06, 0.02])[0]
            learners.append((learner_id, full_name, email, registered_at, status))
        return learners

    def generate_attempts_and_assessments(
        self,
        learners: List[Tuple],
        content_items: List[Tuple],
        content_skills: List[Tuple],
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Generates Attempt and AssessmentResult entities.
        Enforces start_time <= end_time <= base_time.
        """
        attempts = []
        assessments = []

        learner_ids = [l[0] for l in learners if l[4] == "active"]
        if not learner_ids:
            learner_ids = [l[0] for l in learners]

        content_ids = [c[0] for c in content_items]

        # Pre-index content -> skills mapping
        content_to_skills: Dict[str, List[Tuple[str, float]]] = {}
        for cid, sid, weight in content_skills:
            content_to_skills.setdefault(cid, []).append((sid, weight))

        total_attempts = self.scale_config.num_attempts
        assessment_seq = 1

        for i in range(1, total_attempts + 1):
            learner_id = self.rng.choice(learner_ids)
            content_id = self.rng.choice(content_ids)
            attempt_id = ID_FORMATS["attempt"].format(learner_id, i)

            # Realistic interaction timing
            days_ago = self.rng.randint(1, 45)
            hours_ago = self.rng.randint(1, 23)
            minutes_duration = self.rng.randint(5, 75)

            end_dt = self.base_time - timedelta(days=days_ago, hours=hours_ago)
            start_dt = end_dt - timedelta(minutes=minutes_duration)

            status = self.rng.choices(["completed", "abandoned", "in_progress"], weights=[0.90, 0.07, 0.03])[0]
            if status == "completed":
                # Beta distribution skewed towards good scores
                score = round(self.rng.betavariate(5, 2), 4)
            elif status == "abandoned":
                score = round(self.rng.uniform(0.1, 0.45), 4)
            else:
                score = 0.0

            attempts.append((
                attempt_id,
                learner_id,
                content_id,
                start_dt.isoformat(),
                end_dt.isoformat(),
                score,
                status,
            ))

            # If completed, generate assessment results for all tagged skills
            if status == "completed" and content_id in content_to_skills:
                for skill_id, weight in content_to_skills[content_id]:
                    asm_id = ID_FORMATS["assessment"].format(assessment_seq)
                    assessment_seq += 1
                    # Assessed score is proportional to attempt score with minor jitter
                    noise = self.rng.uniform(-0.05, 0.05)
                    assessed_score = round(min(1.0, max(0.0, score * weight + noise)), 4)
                    passed = 1 if assessed_score >= 0.70 else 0
                    assessments.append((
                        asm_id,
                        learner_id,
                        skill_id,
                        attempt_id,
                        assessed_score,
                        passed,
                        end_dt.isoformat(),
                    ))

        return attempts, assessments

    def generate_learning_paths(
        self,
        learners: List[Tuple],
        skills: List[Tuple],
        content_skills: List[Tuple],
    ) -> List[Tuple[str, str, str, int, str, str, str]]:
        """
        Generates LearningPath records:
        (path_id, learner_id, skill_id, step_number, content_id, status, created_at)
        Valid paths are acyclic and sequentially numbered.
        """
        paths = []
        skill_to_contents: Dict[str, List[str]] = {}
        for cid, sid, _ in content_skills:
            skill_to_contents.setdefault(sid, []).append(cid)

        learner_ids = [l[0] for l in learners]
        num_paths = self.scale_config.num_learning_paths

        for p_idx in range(1, num_paths + 1):
            path_id = ID_FORMATS["learning_path"].format(p_idx)
            learner_id = self.rng.choice(learner_ids)
            target_skill = self.rng.choice(skills)[0]

            available_contents = skill_to_contents.get(target_skill, [])
            if not available_contents:
                continue

            num_steps = min(len(available_contents), self.rng.randint(2, 5))
            chosen_steps = self.rng.sample(available_contents, num_steps)

            created_at = (self.base_time - timedelta(days=25)).isoformat()
            for step_num, cid in enumerate(chosen_steps, start=1):
                status = "completed" if step_num == 1 else "pending"
                paths.append((
                    path_id,
                    learner_id,
                    target_skill,
                    step_num,
                    cid,
                    status,
                    created_at,
                ))

        return paths

    def generate_all_clean(self, db_path: Path) -> Dict[str, int]:
        """
        Generates a 100% clean baseline dataset into SQLite.
        Returns the counts of inserted rows per entity.
        """
        init_db(db_path)
        conn = get_db_connection(db_path)

        courses = self.generate_courses()
        skills = self.generate_skills()
        prereqs = self.generate_skill_prerequisites(skills)
        content_items = self.generate_content_items(courses)
        content_skills = self.generate_content_skills(content_items, skills)
        learners = self.generate_learners()
        attempts, assessments = self.generate_attempts_and_assessments(learners, content_items, content_skills)
        learning_paths = self.generate_learning_paths(learners, skills, content_skills)

        try:
            insert_batch(conn, "courses", ["course_id", "title", "description", "created_at"], courses)
            insert_batch(conn, "skills", ["skill_id", "name", "domain", "difficulty_level", "created_at"], skills)
            insert_batch(conn, "skill_prerequisites", ["skill_id", "prerequisite_skill_id", "min_mastery_threshold", "created_at"], prereqs)
            insert_batch(conn, "content_items", ["content_id", "course_id", "title", "content_type", "difficulty_level", "duration_minutes", "created_at"], content_items)
            insert_batch(conn, "content_skills", ["content_id", "skill_id", "relevance_weight"], content_skills)
            insert_batch(conn, "learners", ["learner_id", "full_name", "email", "registered_at", "status"], learners)
            insert_batch(conn, "attempts", ["attempt_id", "learner_id", "content_id", "start_time", "end_time", "score", "status"], attempts)
            insert_batch(conn, "assessment_results", ["assessment_id", "learner_id", "skill_id", "attempt_id", "assessed_score", "passed", "assessed_at"], assessments)
            insert_batch(conn, "learning_paths", ["path_id", "learner_id", "skill_id", "step_number", "content_id", "status", "created_at"], learning_paths)
        finally:
            conn.close()

        return {
            "courses": len(courses),
            "skills": len(skills),
            "skill_prerequisites": len(prereqs),
            "content_items": len(content_items),
            "content_skills": len(content_skills),
            "learners": len(learners),
            "attempts": len(attempts),
            "assessment_results": len(assessments),
            "learning_paths": len(learning_paths),
        }

    def generate_anomaly_fixtures(self, output_file: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Generates the 5 explicit isolated labeled anomaly fixtures.
        Saves metadata to data/ground_truth/anomalies.json.
        """
        target_file = output_file or (GROUND_TRUTH_DIR / "anomalies.json")
        target_file.parent.mkdir(parents=True, exist_ok=True)

        fixtures = [
            {
                "case_id": "ANOM-001",
                "name": "Prerequisite Violation in Recommendation",
                "issue_type": "PREREQUISITE_VIOLATION",
                "entity": "recommendations",
                "description": "Recommendation issued for an advanced skill when learner has not achieved minimum mastery (0.70) on prerequisite skill.",
                "payload": {
                    "recommendation_id": "REC-ANOM-001",
                    "learner_id": "LRN-000001",
                    "content_id": "CNT-000010",
                    "skill_id": "SKL-000005",
                    "prerequisite_skill_id": "SKL-000001",
                    "learner_prereq_mastery": 0.25,
                    "min_required_threshold": 0.70,
                    "rank_order": 1,
                    "recommendation_score": 0.95,
                    "reason_code": "INVALID_PREREQ_OVERRIDE",
                },
                "expected_handling": "Validator flags rule violation; Recommender engine filters out item before ranking.",
                "detector_method": "validate_recommendation_prerequisites",
            },
            {
                "case_id": "ANOM-002",
                "name": "Invalid Attempt Timestamp Order",
                "issue_type": "INVALID_TIMESTAMP_ORDER",
                "entity": "attempts",
                "description": "Attempt logged with start_time occurring after end_time.",
                "payload": {
                    "attempt_id": "ATT-LRN-000001-ANOM02",
                    "learner_id": "LRN-000001",
                    "content_id": "CNT-000001",
                    "start_time": "2026-10-20T16:00:00Z",
                    "end_time": "2026-10-20T14:00:00Z",  # 2 hours before start
                    "score": 0.85,
                    "status": "completed",
                },
                "expected_handling": "SQLite CHECK constraint violation; Validator flags timestamp inversion.",
                "detector_method": "validate_attempt_timestamps",
            },
            {
                "case_id": "ANOM-003",
                "name": "Content Mapped to Nonexistent Skill",
                "issue_type": "ORPHAN_CONTENT_SKILL",
                "entity": "content_skills",
                "description": "Bridge record references a skill_id that does not exist in the skills table.",
                "payload": {
                    "content_id": "CNT-000001",
                    "skill_id": "SKL-999999",  # Nonexistent
                    "relevance_weight": 0.90,
                },
                "expected_handling": "SQLite FOREIGN KEY constraint rejection; Validator flags orphaned reference.",
                "detector_method": "validate_foreign_keys",
            },
            {
                "case_id": "ANOM-004",
                "name": "Mastery Calculation Temporal Future Leakage",
                "issue_type": "FUTURE_ATTEMPT_LEAKAGE",
                "entity": "attempts",
                "description": "Attempt occurring in the future relative to the query as-of timestamp leaked into historical mastery calculation.",
                "payload": {
                    "attempt_id": "ATT-LRN-000001-ANOM04",
                    "learner_id": "LRN-000001",
                    "skill_id": "SKL-000001",
                    "as_of_time": "2026-10-10T00:00:00Z",
                    "future_attempt_time": "2026-10-18T10:00:00Z",
                    "future_score": 1.0,
                },
                "expected_handling": "Mastery engine strictly ignores attempts where end_time > as_of_time.",
                "detector_method": "validate_temporal_safety",
            },
            {
                "case_id": "ANOM-005",
                "name": "Learning Path Loop Without Progress",
                "issue_type": "LOOP_WITHOUT_PROGRESS",
                "entity": "learning_paths",
                "description": "A learning path containing repeated cyclic steps that revisit previous content items without skill mastery advancement.",
                "payload": {
                    "path_id": "PATH-2026-ANOM05",
                    "learner_id": "LRN-000002",
                    "skill_id": "SKL-000002",
                    "steps": [
                        {"step_number": 1, "content_id": "CNT-000001"},
                        {"step_number": 2, "content_id": "CNT-000002"},
                        {"step_number": 3, "content_id": "CNT-000001"},  # Cycle back to step 1
                        {"step_number": 4, "content_id": "CNT-000002"},  # Cycle back to step 2
                    ],
                },
                "expected_handling": "Validator detects duplicate steps/cycles in path graph and flags progress stagnation.",
                "detector_method": "validate_learning_path_progress",
            },
        ]

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(fixtures, f, indent=2)

        return fixtures
