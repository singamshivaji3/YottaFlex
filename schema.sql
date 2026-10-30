-- ============================================================================
-- YottaFlex AI Recruiter Challenge: Learning Recommendation Workflow Schema
-- Target: SQLite 3 with Foreign Keys Enabled
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. Learners
CREATE TABLE IF NOT EXISTS learners (
    learner_id VARCHAR(32) PRIMARY KEY,
    full_name VARCHAR(128) NOT NULL,
    email VARCHAR(128) NOT NULL UNIQUE,
    registered_at TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended'))
);

-- 2. Courses
CREATE TABLE IF NOT EXISTS courses (
    course_id VARCHAR(32) PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);

-- 3. Skills
CREATE TABLE IF NOT EXISTS skills (
    skill_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    domain VARCHAR(64) NOT NULL,
    difficulty_level INTEGER NOT NULL CHECK (difficulty_level BETWEEN 1 AND 5),
    created_at TEXT NOT NULL
);

-- 4. Skill Prerequisites (Directed Acyclic Graph)
CREATE TABLE IF NOT EXISTS skill_prerequisites (
    skill_id VARCHAR(32) NOT NULL,
    prerequisite_skill_id VARCHAR(32) NOT NULL,
    min_mastery_threshold REAL NOT NULL DEFAULT 0.70 CHECK (min_mastery_threshold BETWEEN 0.0 AND 1.0),
    created_at TEXT NOT NULL,
    PRIMARY KEY (skill_id, prerequisite_skill_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_skill_id) REFERENCES skills(skill_id) ON DELETE RESTRICT,
    CHECK (skill_id <> prerequisite_skill_id)
);

-- 5. Content Items
CREATE TABLE IF NOT EXISTS content_items (
    content_id VARCHAR(32) PRIMARY KEY,
    course_id VARCHAR(32) NOT NULL,
    title VARCHAR(256) NOT NULL,
    content_type VARCHAR(32) NOT NULL CHECK (content_type IN ('video', 'reading', 'exercise', 'quiz', 'project')),
    difficulty_level INTEGER NOT NULL CHECK (difficulty_level BETWEEN 1 AND 5),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
);

-- 6. Content Skills (Bridge Table: Many-to-Many mapping)
CREATE TABLE IF NOT EXISTS content_skills (
    content_id VARCHAR(32) NOT NULL,
    skill_id VARCHAR(32) NOT NULL,
    relevance_weight REAL NOT NULL DEFAULT 1.0 CHECK (relevance_weight BETWEEN 0.0 AND 1.0),
    PRIMARY KEY (content_id, skill_id),
    FOREIGN KEY (content_id) REFERENCES content_items(content_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

-- 7. Attempts (Learner engagement with content)
CREATE TABLE IF NOT EXISTS attempts (
    attempt_id VARCHAR(64) PRIMARY KEY,
    learner_id VARCHAR(32) NOT NULL,
    content_id VARCHAR(32) NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    score REAL NOT NULL CHECK (score BETWEEN 0.0 AND 1.0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('completed', 'in_progress', 'abandoned')),
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE,
    FOREIGN KEY (content_id) REFERENCES content_items(content_id) ON DELETE CASCADE,
    CHECK (start_time <= end_time)
);

-- 8. Assessment Results (Evaluated skill mastery records)
CREATE TABLE IF NOT EXISTS assessment_results (
    assessment_id VARCHAR(32) PRIMARY KEY,
    learner_id VARCHAR(32) NOT NULL,
    skill_id VARCHAR(32) NOT NULL,
    attempt_id VARCHAR(64) NOT NULL,
    assessed_score REAL NOT NULL CHECK (assessed_score BETWEEN 0.0 AND 1.0),
    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
    assessed_at TEXT NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
    FOREIGN KEY (attempt_id) REFERENCES attempts(attempt_id) ON DELETE CASCADE
);

-- 9. Learning Paths (Ordered curriculum progression)
CREATE TABLE IF NOT EXISTS learning_paths (
    path_id VARCHAR(32) NOT NULL,
    learner_id VARCHAR(32) NOT NULL,
    skill_id VARCHAR(32) NOT NULL,
    step_number INTEGER NOT NULL CHECK (step_number > 0),
    content_id VARCHAR(32) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (path_id, step_number),
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
    FOREIGN KEY (content_id) REFERENCES content_items(content_id) ON DELETE CASCADE
);

-- 10. Recommendations (Output recommendations with explainability)
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id VARCHAR(32) PRIMARY KEY,
    learner_id VARCHAR(32) NOT NULL,
    content_id VARCHAR(32) NOT NULL,
    skill_id VARCHAR(32) NOT NULL,
    rank_order INTEGER NOT NULL CHECK (rank_order > 0),
    recommendation_score REAL NOT NULL CHECK (recommendation_score BETWEEN 0.0 AND 1.0),
    reason_code VARCHAR(64) NOT NULL,
    reason_description TEXT NOT NULL,
    algorithm_version VARCHAR(32) NOT NULL,
    generated_at TEXT NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE,
    FOREIGN KEY (content_id) REFERENCES content_items(content_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

-- Indexes for fast temporal filtering and relational traversal
CREATE INDEX IF NOT EXISTS idx_attempts_learner_end_time ON attempts(learner_id, end_time);
CREATE INDEX IF NOT EXISTS idx_attempts_content ON attempts(content_id);
CREATE INDEX IF NOT EXISTS idx_assessment_learner_skill_time ON assessment_results(learner_id, skill_id, assessed_at);
CREATE INDEX IF NOT EXISTS idx_content_skills_skill ON content_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_prereqs_skill ON skill_prerequisites(skill_id);
CREATE INDEX IF NOT EXISTS idx_prereqs_prereq ON skill_prerequisites(prerequisite_skill_id);
CREATE INDEX IF NOT EXISTS idx_learning_paths_learner ON learning_paths(learner_id, path_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_learner ON recommendations(learner_id, rank_order);
