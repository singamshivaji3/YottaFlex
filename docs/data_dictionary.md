# Data Dictionary: YottaFlex Learning Recommendation Workflow

This document details the relational data model for the **YottaFlex Learning Recommendation Workflow**, comprising all 10 entities, relational constraints, lifecycle semantics, and derived metrics.

For every field in each entity, the specification defines:
- **Type**: SQL data type and storage representation
- **Required/Optional**: `Required (NOT NULL)` or `Optional (Nullable)`
- **Allowed Values**: Permitted domain ranges, enums, or regular expressions
- **Units**: Semantic measurement unit (e.g., minutes, normalized $[0.0, 1.0]$, ISO-8601 UTC)
- **Uniqueness**: Primary Key, Unique Constraint, or Non-Unique
- **Validation Rule**: Exact SQL constraint, foreign key, or business rule enforced

---

## 1. Table Summaries and Cardinalities

| # | Entity Table | Purpose | Primary Key | Foreign Keys | Key Cardinalities |
|---|---|---|---|---|---|
| 1 | `learners` | Registered platform students | `learner_id` | None | $1 \to N$ `attempts`, $1 \to N$ `learning_paths`, $1 \to N$ `recommendations` |
| 2 | `courses` | Curricular courses / subjects | `course_id` | None | $1 \to N$ `content_items` |
| 3 | `skills` | Competency nodes in knowledge graph | `skill_id` | None | $M \to N$ prerequisites (via `skill_prerequisites`), $M \to N$ content (via `content_skills`) |
| 4 | `skill_prerequisites` | Directed prerequisite relationships between skills | `(skill_id, prerequisite_skill_id)` | `skill_id` $\to$ `skills`<br>`prerequisite_skill_id` $\to$ `skills` | Directed Acyclic Graph (DAG) edges |
| 5 | `content_items` | Modular learning materials (videos, exercises, etc.) | `content_id` | `course_id` $\to$ `courses` | $N \to 1$ `courses`, $1 \to N$ `attempts`, $M \to N$ `skills` |
| 6 | `content_skills` | Association bridge between content items and skills | `(content_id, skill_id)` | `content_id` $\to$ `content_items`<br>`skill_id` $\to$ `skills` | Many-to-Many bridge table |
| 7 | `attempts` | Log of learner interactions with content items | `attempt_id` | `learner_id` $\to$ `learners`<br>`content_id` $\to$ `content_items` | $N \to 1$ `learners`, $N \to 1$ `content_items` |
| 8 | `assessment_results` | Evaluated mastery evidence per attempt and skill | `assessment_id` | `learner_id` $\to$ `learners`<br>`skill_id` $\to$ `skills`<br>`attempt_id` $\to$ `attempts` | $N \to 1$ `attempts`, $N \to 1$ `skills` |
| 9 | `learning_paths` | Sequenced study paths assigned to or tracked for learners | `(path_id, step_number)` | `learner_id` $\to$ `learners`<br>`skill_id` $\to$ `skills`<br>`content_id` $\to$ `content_items` | Ordered sequence ($step\_number \ge 1$) per path |
| 10 | `recommendations` | Explainable next-activity recommendations | `recommendation_id` | `learner_id` $\to$ `learners`<br>`content_id` $\to$ `content_items`<br>`skill_id` $\to$ `skills` | $N \to 1$ `learners`, ranked 1 to $K$ |

---

## 2. Granular Entity Field Specifications

### 2.1 `learners`
Stores registered learners in the educational platform.

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `learner_id` | VARCHAR(32) | Required | Pattern `^LRN-\d{6}$` | Identifier | Primary Key (Unique) | Must match `LRN-XXXXXX` format; immutable once assigned |
| `full_name` | VARCHAR(128) | Required | Non-empty string ($1$ to $128$ chars) | Text | Non-unique | Valid personal name |
| `email` | VARCHAR(128) | Required | Valid email string | Email Address | Unique | RFC-5322 pattern; enforced by SQLite `UNIQUE` constraint |
| `registered_at` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Must be valid past or present UTC timestamp |
| `status` | VARCHAR(20) | Required | `'active'`, `'inactive'`, `'suspended'` | Categorical | Non-unique | `CHECK (status IN ('active', 'inactive', 'suspended'))` |

---

### 2.2 `courses`
Curricular subjects grouping modular content items.

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `course_id` | VARCHAR(32) | Required | Pattern `^CRS-\d{6}$` | Identifier | Primary Key (Unique) | Must match `CRS-XXXXXX` format |
| `title` | VARCHAR(256) | Required | Non-empty string ($1$ to $256$ chars) | Text | Non-unique | Course title |
| `description` | TEXT | Optional | String or NULL | Text | Non-unique | None |
| `created_at` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Must be valid UTC timestamp |

---

### 2.3 `skills`
Competency nodes within the knowledge graph.

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `skill_id` | VARCHAR(32) | Required | Pattern `^SKL-\d{6}$` | Identifier | Primary Key (Unique) | Must match `SKL-XXXXXX` format |
| `name` | VARCHAR(128) | Required | Non-empty string ($1$ to $128$ chars) | Text | Unique | Enforced by SQLite `UNIQUE` constraint |
| `domain` | VARCHAR(64) | Required | Knowledge domain (e.g. `'Machine Learning'`) | Categorical | Non-unique | Non-empty domain string |
| `difficulty_level`| INTEGER | Required | Integers $1, 2, 3, 4, 5$ | Ordinal Scale ($1$ to $5$) | Non-unique | `CHECK (difficulty_level BETWEEN 1 AND 5)` |
| `created_at` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Creation timestamp in UTC |

---

### 2.4 `skill_prerequisites`
Directed pedagogical dependencies between skills forming a Directed Acyclic Graph (DAG).

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `skill_id` | VARCHAR(32) | Required | Existing `skills.skill_id` | Identifier | Composite PK Part 1 | `FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE` |
| `prerequisite_skill_id` | VARCHAR(32) | Required | Existing `skills.skill_id` | Identifier | Composite PK Part 2 | `FOREIGN KEY (prerequisite_skill_id) REFERENCES skills(skill_id) ON DELETE RESTRICT` |
| `min_mastery_threshold` | REAL | Required | Real numbers in $[0.0, 1.0]$ | Ratio / Score | Non-unique | `CHECK (min_mastery_threshold BETWEEN 0.0 AND 1.0)`; default `0.70` |
| `created_at` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Timestamp of prerequisite link creation |

*Table Constraints:*
- Composite Primary Key `(skill_id, prerequisite_skill_id)`
- `CHECK (skill_id <> prerequisite_skill_id)` (no self-loops)
- Topological acyclicity verified via Kahn's algorithm (0 cycles permitted)

---

### 2.5 `content_items`
Modular learning materials (videos, exercises, quizzes, readings, projects).

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `content_id` | VARCHAR(32) | Required | Pattern `^CNT-\d{6}$` | Identifier | Primary Key (Unique) | Must match `CNT-XXXXXX` format |
| `course_id` | VARCHAR(32) | Required | Existing `courses.course_id` | Identifier | Foreign Key | `FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE` |
| `title` | VARCHAR(256) | Required | Non-empty string | Text | Non-unique | Descriptive content title |
| `content_type`| VARCHAR(32) | Required | `'video'`, `'reading'`, `'exercise'`, `'quiz'`, `'project'` | Categorical Enum | Non-unique | `CHECK (content_type IN ('video', 'reading', 'exercise', 'quiz', 'project'))` |
| `difficulty_level`| INTEGER | Required | Integers $1, 2, 3, 4, 5$ | Ordinal Scale ($1$ to $5$) | Non-unique | `CHECK (difficulty_level BETWEEN 1 AND 5)` |
| `duration_minutes`| INTEGER | Required | Integer $\ge 1$ | Minutes | Non-unique | `CHECK (duration_minutes > 0)` |
| `created_at` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Content item creation timestamp |

---

### 2.6 `content_skills`
Many-to-Many association bridge mapping content items to competencies.

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `content_id` | VARCHAR(32) | Required | Existing `content_items.content_id` | Identifier | Composite PK Part 1 | `FOREIGN KEY (content_id) REFERENCES content_items(content_id) ON DELETE CASCADE` |
| `skill_id` | VARCHAR(32) | Required | Existing `skills.skill_id` | Identifier | Composite PK Part 2 | `FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE` |
| `relevance_weight`| REAL | Required | Real numbers in $[0.0, 1.0]$ | Weight Ratio | Non-unique | `CHECK (relevance_weight BETWEEN 0.0 AND 1.0)`; default `1.0` |

*Table Constraints:*
- Composite Primary Key `(content_id, skill_id)`

---

### 2.7 `attempts`
Granular interaction and telemetry logs of student learning activities.

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `attempt_id` | VARCHAR(64) | Required | Pattern `^ATT-LRN-\d{6}-\d{6}$` | Identifier | Primary Key (Unique) | Formatted as `ATT-<learner_id>-<seq>` |
| `learner_id` | VARCHAR(32) | Required | Existing `learners.learner_id` | Identifier | Foreign Key | `FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE` |
| `content_id` | VARCHAR(32) | Required | Existing `content_items.content_id` | Identifier | Foreign Key | `FOREIGN KEY (content_id) REFERENCES content_items(content_id) ON DELETE CASCADE` |
| `start_time` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Interaction start timestamp |
| `end_time` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Interaction completion timestamp |
| `score` | REAL | Required | Real numbers in $[0.0, 1.0]$ | Normalized Score | Non-unique | `CHECK (score BETWEEN 0.0 AND 1.0)` |
| `status` | VARCHAR(20) | Required | `'completed'`, `'in_progress'`, `'abandoned'` | Categorical Enum | Non-unique | `CHECK (status IN ('completed', 'in_progress', 'abandoned'))` |

*Table Constraints:*
- `CHECK (start_time <= end_time)` (chronological validity)

---

### 2.8 `assessment_results`
Evaluated skill-level mastery outcomes derived from interaction attempts.

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `assessment_id` | VARCHAR(32) | Required | Pattern `^ASM-\d{6}$` | Identifier | Primary Key (Unique) | Formatted as `ASM-XXXXXX` |
| `learner_id` | VARCHAR(32) | Required | Existing `learners.learner_id` | Identifier | Foreign Key | `FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE` |
| `skill_id` | VARCHAR(32) | Required | Existing `skills.skill_id` | Identifier | Foreign Key | `FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE` |
| `attempt_id` | VARCHAR(64) | Required | Existing `attempts.attempt_id` | Identifier | Foreign Key | `FOREIGN KEY (attempt_id) REFERENCES attempts(attempt_id) ON DELETE CASCADE` |
| `assessed_score`| REAL | Required | Real numbers in $[0.0, 1.0]$ | Normalized Score | Non-unique | `CHECK (assessed_score BETWEEN 0.0 AND 1.0)` |
| `passed` | INTEGER | Required | `0` (Failed) or `1` (Passed) | Binary Indicator | Non-unique | `CHECK (passed IN (0, 1))`; derived as $1$ if `assessed_score` $\ge 0.70$ else $0$ |
| `assessed_at` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Timestamp derived from attempt completion |

---

### 2.9 `learning_paths`
Sequenced educational progression paths assigned to learners.

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `path_id` | VARCHAR(32) | Required | Pattern `^PATH-2026-\d{6}$` | Identifier | Composite PK Part 1 | Formatted as `PATH-2026-XXXXXX` |
| `learner_id` | VARCHAR(32) | Required | Existing `learners.learner_id` | Identifier | Foreign Key | `FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE` |
| `skill_id` | VARCHAR(32) | Required | Existing `skills.skill_id` | Identifier | Foreign Key | `FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE` |
| `step_number` | INTEGER | Required | Integers $\ge 1$ ($1, 2, 3, \dots$) | Step Index | Composite PK Part 2 | `CHECK (step_number > 0)` |
| `content_id` | VARCHAR(32) | Required | Existing `content_items.content_id` | Identifier | Foreign Key | `FOREIGN KEY (content_id) REFERENCES content_items(content_id) ON DELETE CASCADE` |
| `status` | VARCHAR(20) | Required | `'pending'`, `'in_progress'`, `'completed'`, `'skipped'` | Categorical Enum | Non-unique | `CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped'))`; default `'pending'` |
| `created_at` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Path assignment timestamp |

*Table Constraints:*
- Composite Primary Key `(path_id, step_number)`
- Progression acyclicity: steps must not loop across duplicate content items without skill progression

---

### 2.10 `recommendations`
Output recommendations generated by the prerequisite-gated multi-factor ranking engine.

| Field | Type | Required/Optional | Allowed Values | Units | Uniqueness | Validation Rule |
|---|---|---|---|---|---|---|
| `recommendation_id` | VARCHAR(32) | Required | Pattern `^REC-\d{6}$` | Identifier | Primary Key (Unique) | Formatted as `REC-XXXXXX` |
| `learner_id` | VARCHAR(32) | Required | Existing `learners.learner_id` | Identifier | Foreign Key | `FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE` |
| `content_id` | VARCHAR(32) | Required | Existing `content_items.content_id` | Identifier | Foreign Key | `FOREIGN KEY (content_id) REFERENCES content_items(content_id) ON DELETE CASCADE` |
| `skill_id` | VARCHAR(32) | Required | Existing `skills.skill_id` | Identifier | Foreign Key | `FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE` |
| `rank_order` | INTEGER | Required | Integers $1$ to $K$ ($1, 2, 3, \dots$) | Rank Ordinal | Non-unique | `CHECK (rank_order > 0)`; 1 denotes highest priority |
| `recommendation_score` | REAL | Required | Real numbers in $[0.0, 1.0]$ | Composite Score | Non-unique | `CHECK (recommendation_score BETWEEN 0.0 AND 1.0)` |
| `reason_code` | VARCHAR(64) | Required | `'SKILL_DEFICIT_HIGH_PRIORITY'`, `'SKILL_PRACTICE_RECOMMENDED'` | Machine Code | Non-unique | Enumerated reason code indicating algorithmic rationale |
| `reason_description` | TEXT | Required | Human-readable explanation string | Narrative Text | Non-unique | Detailed justification including prerequisite check and gap |
| `algorithm_version` | VARCHAR(32) | Required | e.g. `'v1.2.0-explainable-heuristic'` | Version Tag | Non-unique | Version of engine generating recommendation |
| `generated_at` | TEXT | Required | ISO-8601 string (`YYYY-MM-DDTHH:MM:SSZ`) | UTC Timestamp | Non-unique | Timestamp recommendation was computed |

---

## 3. Mathematical Formulations & Derived Metrics

### 3.1 Temporal-Safe EWMA Mastery Formula
For learner $L$, skill $S$, and query cutoff timestamp $t_{\text{query}}$:
1. Retrieve all completed assessment results for $(L, S)$ where `assessed_at <= t_query`, ordered chronologically:
   $$\{a_1, a_2, \dots, a_k\}$$
2. If $k = 0$, $Mastery(L, S, t_{\text{query}}) = 0.0$.
3. If $k > 0$, compute Exponentially Weighted Moving Average (EWMA) with recency weight $\alpha = 0.35$:
   $$M_0 = a_1$$
   $$M_i = \alpha \cdot a_i + (1 - \alpha) \cdot M_{i-1} \quad \text{for } i \in [1, k]$$
   $$Mastery(L, S, t_{\text{query}}) = \min(1.0, \max(0.0, M_k))$$

### 3.2 Hard Prerequisite Gate
A candidate activity targeting skill $S$ is eligible for learner $L$ at $t_{\text{query}}$ iff:
$$\forall P \in \text{Prerequisites}(S): Mastery(L, P, t_{\text{query}}) \ge \tau_P$$
where $\tau_P$ is the prerequisite's `min_mastery_threshold` (default $0.70$). Any candidate with unmastered prerequisites is strictly disqualified.

### 3.3 Explainable Multi-Factor Scoring
For eligible content item $C$ targeting skill $S$:
$$\text{SkillGap} = 1.0 - Mastery(L, S, t_{\text{query}})$$
$$\text{LearnerLevel} = 1.0 + 4.0 \cdot Mastery(L, S, t_{\text{query}})$$
$$\text{DifficultyFit} = 1.0 - \frac{| \text{LearnerLevel} - \text{Difficulty}(C) |}{4.0}$$
$$\text{Relevance} = \text{relevance\_weight}(C, S)$$
$$\text{Score} = w_1 \cdot \text{SkillGap} + w_2 \cdot \text{DifficultyFit} + w_3 \cdot \text{Relevance}$$
Weights: $w_1 = 0.45$ (Skill Gap), $w_2 = 0.35$ (Difficulty Fit), $w_3 = 0.20$ (Content Relevance).
Score is clamped to $[0.0, 1.0]$ and rounded to 4 decimal places.
