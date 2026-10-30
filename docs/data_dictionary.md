# Data Dictionary

This document details the relational data model for the **YottaFlex Learning Recommendation Workflow**, comprising 10 entities, relational constraints, lifecycle semantics, and derived metrics.

---

## 1. Table Summaries and Cardinalities

| Entity Table | Purpose | Primary Key | Foreign Keys | Key Cardinalities |
|---|---|---|---|---|
| `learners` | Registered platform students | `learner_id` | None | $1 \to N$ `attempts`, $1 \to N$ `learning_paths`, $1 \to N$ `recommendations` |
| `courses` | Curricular courses / subjects | `course_id` | None | $1 \to N$ `content_items` |
| `skills` | Competency nodes in knowledge graph | `skill_id` | None | $M \to N$ prerequisites (via `skill_prerequisites`), $M \to N$ content (via `content_skills`) |
| `skill_prerequisites` | Directed prerequisite relationships between skills | `(skill_id, prerequisite_skill_id)` | `skill_id` $\to$ `skills`<br>`prerequisite_skill_id` $\to$ `skills` | Directed Acyclic Graph (DAG) edges |
| `content_items` | Modular learning materials (videos, exercises, etc.) | `content_id` | `course_id` $\to$ `courses` | $N \to 1$ `courses`, $1 \to N$ `attempts`, $M \to N$ `skills` |
| `content_skills` | Association bridge between content items and skills | `(content_id, skill_id)` | `content_id` $\to$ `content_items`<br>`skill_id` $\to$ `skills` | Many-to-Many bridge table |
| `attempts` | Log of learner interactions with content items | `attempt_id` | `learner_id` $\to$ `learners`<br>`content_id` $\to$ `content_items` | $N \to 1$ `learners`, $N \to 1$ `content_items` |
| `assessment_results` | Evaluated mastery evidence per attempt and skill | `assessment_id` | `learner_id` $\to$ `learners`<br>`skill_id` $\to$ `skills`<br>`attempt_id` $\to$ `attempts` | $N \to 1$ `attempts`, $N \to 1$ `skills` |
| `learning_paths` | Sequenced study paths assigned to or tracked for learners | `(path_id, step_number)` | `learner_id` $\to$ `learners`<br>`skill_id` $\to$ `skills`<br>`content_id` $\to$ `content_items` | Ordered sequence ($step\_number \ge 1$) per path |
| `recommendations` | Explainable next-activity recommendations | `recommendation_id` | `learner_id` $\to$ `learners`<br>`content_id` $\to$ `content_items`<br>`skill_id` $\to$ `skills` | $N \to 1$ `learners`, ranked 1 to $K$ |

---

## 2. Detailed Entity Attributes

### 2.1 `learners`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `learner_id` | VARCHAR(32) | NO | - | Primary Key. Format: `LRN-XXXXXX`. |
| `full_name` | VARCHAR(128) | NO | - | Full student name. |
| `email` | VARCHAR(128) | NO | - | Unique email address. |
| `registered_at` | TEXT (ISO-8601) | NO | - | Timestamp of account registration (UTC). |
| `status` | VARCHAR(20) | NO | `'active'` | Lifecycle status: `'active'`, `'inactive'`, `'suspended'`. |

### 2.2 `courses`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `course_id` | VARCHAR(32) | NO | - | Primary Key. Format: `CRS-XXXXXX`. |
| `title` | VARCHAR(256) | NO | - | Official title of the course. |
| `description` | TEXT | YES | NULL | Overview of course curriculum. |
| `created_at` | TEXT (ISO-8601) | NO | - | Creation timestamp (UTC). |

### 2.3 `skills`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `skill_id` | VARCHAR(32) | NO | - | Primary Key. Format: `SKL-XXXXXX`. |
| `name` | VARCHAR(128) | NO | - | Unique name of the skill/competency. |
| `domain` | VARCHAR(64) | NO | - | Knowledge domain (e.g. `Machine Learning`, `Data Engineering`, `System Design`). |
| `difficulty_level`| INTEGER | NO | - | Difficulty rating from 1 (Novice) to 5 (Expert). |
| `created_at` | TEXT (ISO-8601) | NO | - | Skill catalog creation timestamp. |

### 2.4 `skill_prerequisites`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `skill_id` | VARCHAR(32) | NO | - | Target skill. FK to `skills(skill_id)`. |
| `prerequisite_skill_id` | VARCHAR(32) | NO | - | Prerequisite skill required before learning target. FK to `skills(skill_id)`. |
| `min_mastery_threshold` | REAL | NO | `0.70` | Required prerequisite mastery score $[0.0, 1.0]$. |
| `created_at` | TEXT (ISO-8601) | NO | - | Association timestamp. |

*Constraints:* Composite Primary Key `(skill_id, prerequisite_skill_id)`. `CHECK (skill_id <> prerequisite_skill_id)`. Topological acyclicity enforced by generator and validator.

### 2.5 `content_items`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `content_id` | VARCHAR(32) | NO | - | Primary Key. Format: `CNT-XXXXXX`. |
| `course_id` | VARCHAR(32) | NO | - | FK to `courses(course_id)`. |
| `title` | VARCHAR(256) | NO | - | Title of the modular activity. |
| `content_type`| VARCHAR(32) | NO | - | Enum: `'video'`, `'reading'`, `'exercise'`, `'quiz'`, `'project'`. |
| `difficulty_level`| INTEGER | NO | - | Scale 1 to 5. |
| `duration_minutes`| INTEGER | NO | - | Estimated completion time ($>0$). |
| `created_at` | TEXT (ISO-8601) | NO | - | Content item creation timestamp. |

### 2.6 `content_skills`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `content_id` | VARCHAR(32) | NO | - | FK to `content_items(content_id)`. |
| `skill_id` | VARCHAR(32) | NO | - | FK to `skills(skill_id)`. |
| `relevance_weight`| REAL | NO | `1.0` | Weight of the skill in this content item $[0.0, 1.0]$. |

*Constraints:* Composite Primary Key `(content_id, skill_id)`.

### 2.7 `attempts`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `attempt_id` | VARCHAR(64) | NO | - | Primary Key. Format: `ATT-<learner_id>-XXXXXX`. |
| `learner_id` | VARCHAR(32) | NO | - | FK to `learners(learner_id)`. |
| `content_id` | VARCHAR(32) | NO | - | FK to `content_items(content_id)`. |
| `start_time` | TEXT (ISO-8601) | NO | - | Interaction initiation timestamp. |
| `end_time` | TEXT (ISO-8601) | NO | - | Interaction completion or abandonment timestamp. |
| `score` | REAL | NO | - | Raw performance score $[0.0, 1.0]$. |
| `status` | VARCHAR(20) | NO | - | `'completed'`, `'in_progress'`, `'abandoned'`. |

*Constraints:* `CHECK (start_time <= end_time)`.

### 2.8 `assessment_results`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `assessment_id` | VARCHAR(32) | NO | - | Primary Key. Format: `ASM-XXXXXX`. |
| `learner_id` | VARCHAR(32) | NO | - | FK to `learners(learner_id)`. |
| `skill_id` | VARCHAR(32) | NO | - | FK to `skills(skill_id)`. |
| `attempt_id` | VARCHAR(64) | NO | - | FK to `attempts(attempt_id)`. |
| `assessed_score`| REAL | NO | - | Normalized score for this specific skill $[0.0, 1.0]$. |
| `passed` | INTEGER | NO | - | Binary indicator: `1` if $\ge 0.70$, else `0`. |
| `assessed_at` | TEXT (ISO-8601) | NO | - | Assessment timestamp (matches attempt end time). |

### 2.9 `learning_paths`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `path_id` | VARCHAR(32) | NO | - | Learning path grouping identifier. Format: `PATH-2026-XXXXXX`. |
| `learner_id` | VARCHAR(32) | NO | - | FK to `learners(learner_id)`. |
| `skill_id` | VARCHAR(32) | NO | - | FK to `skills(skill_id)` targeted by path step. |
| `step_number` | INTEGER | NO | - | Sequential order index ($1, 2, 3, \dots$). |
| `content_id` | VARCHAR(32) | NO | - | FK to `content_items(content_id)`. |
| `status` | VARCHAR(20) | NO | `'pending'` | `'pending'`, `'in_progress'`, `'completed'`, `'skipped'`. |
| `created_at` | TEXT (ISO-8601) | NO | - | Path assignment timestamp. |

*Constraints:* Composite Primary Key `(path_id, step_number)`.

### 2.10 `recommendations`
| Column | Type | Nullable | Default | Description / Rules |
|---|---|---|---|---|
| `recommendation_id` | VARCHAR(32) | NO | - | Primary Key. Format: `REC-XXXXXX`. |
| `learner_id` | VARCHAR(32) | NO | - | FK to `learners(learner_id)`. |
| `content_id` | VARCHAR(32) | NO | - | FK to `content_items(content_id)`. |
| `skill_id` | VARCHAR(32) | NO | - | FK to `skills(skill_id)` addressed. |
| `rank_order` | INTEGER | NO | - | Recommendation rank (1 = Top recommendation). |
| `recommendation_score` | REAL | NO | - | Composite ranking score $[0.0, 1.0]$. |
| `reason_code` | VARCHAR(64) | NO | - | Machine-readable rule code (`SKILL_DEFICIT`, `DIFFICULTY_ALIGNMENT`, etc.). |
| `reason_description` | TEXT | NO | - | Human-interpretable explanation. |
| `algorithm_version` | VARCHAR(32) | NO | - | Engine version (e.g. `v1.2.0-explainable-heuristic`). |
| `generated_at` | TEXT (ISO-8601) | NO | - | Timestamp recommendation was produced. |

---

## 3. Derived Metrics and Calculations

### 3.1 Temporal-Safe Mastery Formula
For learner $L$, skill $S$, and query cutoff timestamp $t_{\text{query}}$:
1. Retrieve all completed assessment results for $(L, S)$ where `assessed_at <= t_query`, ordered chronologically:
   $$\{a_1, a_2, \dots, a_k\}$$
2. If $k = 0$, $Mastery(L, S, t_{\text{query}}) = 0.0$.
3. If $k > 0$, compute Exponentially Weighted Moving Average (with smoothing parameter $\alpha = 0.35$):
   $$M_0 = a_1$$
   $$M_i = \alpha \cdot a_i + (1 - \alpha) \cdot M_{i-1} \quad \text{for } i \in [1, k]$$
   $$Mastery(L, S, t_{\text{query}}) = \min(1.0, \max(0.0, M_k))$$

### 3.2 Prerequisite Eligibility Check
A candidate skill $S$ is eligible for learner $L$ at $t_{\text{query}}$ iff:
$$\forall P \in \text{Prerequisites}(S): Mastery(L, P, t_{\text{query}}) \ge \tau_P$$
where $\tau_P$ is `min_mastery_threshold` (default 0.70).

### 3.3 Recommendation Scoring
For candidate content item $C$ addressing eligible skill $S$:
$$\text{SkillGap} = 1.0 - Mastery(L, S, t_{\text{query}})$$
$$\text{LearnerLevel} = 1 + 4 \cdot Mastery(L, S, t_{\text{query}})$$
$$\text{DifficultyFit} = 1.0 - \frac{| \text{LearnerLevel} - \text{Difficulty}(C) |}{4.0}$$
$$\text{Relevance} = \text{relevance\_weight}(C, S)$$
$$\text{Score} = w_1 \cdot \text{SkillGap} + w_2 \cdot \text{DifficultyFit} + w_3 \cdot \text{Relevance}$$
Weights: $w_1 = 0.45, w_2 = 0.35, w_3 = 0.20$.
